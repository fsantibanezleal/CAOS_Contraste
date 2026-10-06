// The C22 instrument (CT-309): the rail's sections, each with its controls and a live read-out, and the six groups of
// CT-112 with C22's views. The workbench calls this hook on every case and uses it when the case is C22.
import { ChipGroup, Knob, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { COMMITTED, type PolicyAlphas } from '../../lib/policy';
import { provenanceOf } from '../model';
import { isC22, type C22Sel, type Portfolio } from './selection';
import {
  C22ContextView,
  C22FindingsView,
  C22VariantsView,
  EstimatorsView,
  GeneratorsView,
  LiveCalculatorView,
  PValuesView,
  PaperView,
  PortfolioReadout,
  PowerView,
  RatesTableView,
  SizeView,
  SpecimenView,
} from './Views';

export interface C22Instrument {
  sel: C22Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

/** The portfolio the live calculator starts from: WP14's Example 3 (1,000 obligors, PD 1%). */
export const START: Portfolio = { n: 1000, pd: 0.01, ratio: 1, rhoTrue: 0, rhoAssumed: 0.12 };

export function useC22Instrument(data: CaseData | null, onPick: (id: string) => void): C22Instrument | null {
  const lang = useShellLang();
  const [level, setLevel] = useState(0.05);
  const [portfolio, setPortfolio] = useState<Portfolio>(START);
  const [alphas] = useState<PolicyAlphas>(COMMITTED);
  const v = data && data.manifest.case_id === 'C22' ? (data.variant as VariantArtifact<unknown>) : null;
  const c22 = v && isC22(v) ? v : null;
  const sel: C22Sel | null = useMemo(() => (c22 && data ? { data, alphas, level, portfolio } : null), [c22, data, alphas, level, portfolio]);
  if (!c22 || !data) return null;
  const prov = provenanceOf(c22.provenance.truth_status);
  const set = (k: keyof Portfolio) => (x: number) => setPortfolio((p) => ({ ...p, [k]: x }));

  const portfolioSection: RailSection = {
    id: 'portfolio',
    label: { en: 'Your portfolio', es: 'Su cartera' },
    content: (
      <>
        <div className="ct-pair">
          <Knob id="c22-n" label={{ en: 'Obligors', es: 'Deudores' }} hint={{ en: 'Obligors in the grade or portfolio tested.', es: 'Deudores del grado o la cartera probada.' }} value={portfolio.n} min={100} max={10000} step={100} format={{ decimals: 0 }} onChange={set('n')} />
          <Knob id="c22-pd" label={{ en: 'PD applied', es: 'PD aplicada' }} hint={{ en: "The model's PD for the grade.", es: 'La PD del modelo para el grado.' }} value={portfolio.pd} min={0.001} max={0.2} step={0.001} format={{ percent: true, decimals: 1 }} onChange={set('pd')} />
        </div>
        <div className="ct-pair">
          <Knob id="c22-ratio" label={{ en: 'PD ratio', es: 'Razón de PD' }} hint={{ en: 'The true PD over the PD applied: 1 gives the size, above 1 the power against an underestimation.', es: 'La PD verdadera sobre la aplicada: 1 da el tamaño, sobre 1 la potencia contra una subestimación.' }} value={portfolio.ratio} min={1} max={3} step={0.05} format={{ decimals: 2 }} onChange={set('ratio')} />
          <Knob id="c22-rho" label={{ en: 'Correlation', es: 'Correlación' }} hint={{ en: 'The asset correlation the defaults really have (one systematic factor).', es: 'La correlación de activos que realmente tienen los incumplimientos (un factor sistemático).' }} value={portfolio.rhoTrue} min={0} max={0.3} step={0.01} format={{ percent: true, decimals: 0 }} onChange={set('rhoTrue')} />
        </div>
        <PortfolioReadout sel={sel} />
      </>
    ),
  };
  const testsSection: RailSection = {
    id: 'tests',
    label: { en: 'The tests', es: 'Las pruebas' },
    content: (
      <>
        <ChipGroup
          id="c22-level"
          label={{ en: 'Level', es: 'Nivel' }}
          options={[
            { id: '0.05', label: { en: '5%', es: '5%' }, hint: { en: 'Reject when p < 0.05 (amber or red under the committed policy); every replayed view reads this level.', es: 'Rechazar cuando p < 0,05 (ámbar o rojo con la política comprometida); cada vista reproducida lee este nivel.' } },
            { id: '0.01', label: { en: '1%', es: '1%' }, hint: { en: 'Reject when p < 0.01 (red under the committed policy); every replayed view reads this level.', es: 'Rechazar cuando p < 0,01 (rojo con la política comprometida); cada vista reproducida lee este nivel.' } },
          ]}
          value={String(level)}
          onChange={(id) => setLevel(Number(id))}
        />
        <Knob id="c22-rho-assumed" label={{ en: "Vasicek's assumed correlation", es: 'Correlación de Vasicek' }} hint={{ en: 'The correlation the Vasicek-corrected test assumes: a modelling assumption to document; the IRB corporate correlations run from 12% to 24%.', es: 'La correlación que supone la prueba corregida de Vasicek: un supuesto de modelación a documentar; las correlaciones corporativas IRB van de 12% a 24%.' }} value={portfolio.rhoAssumed} min={0.01} max={0.3} step={0.01} format={{ percent: true, decimals: 0 }} onChange={set('rhoAssumed')} />
        <PortfolioReadout sel={sel} />
      </>
    ),
  };
  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const isNull = c22.outputs.ladder === null;
  const validation = isNull
    ? tabs(
        [
          { id: 'size', label: { en: 'Size', es: 'Tamaño' }, content: <SizeView sel={sel} /> },
          { id: 'p-values', label: { en: 'p-values', es: 'Valores p' }, content: <PValuesView sel={sel} /> },
          { id: 'estimators', label: { en: 'Estimators', es: 'Estimadores' }, content: <EstimatorsView sel={sel} /> },
          { id: 'report', label: { en: 'One report', es: 'Un reporte' }, content: <SpecimenView sel={sel} /> },
        ],
        { en: 'Views of the measurements', es: 'Vistas de las mediciones' },
        'validation-null',
      )
    : tabs(
        [
          c22.outputs.panels.every((p) => p.measures === 'size')
            ? { id: 'power', label: { en: 'Size', es: 'Tamaño' }, content: <PowerView sel={sel} /> }
            : { id: 'power', label: { en: 'Power', es: 'Potencia' }, content: <PowerView sel={sel} /> },
          { id: 'rates', label: { en: 'Rates', es: 'Tasas' }, content: <RatesTableView sel={sel} /> },
          ...(c22.outputs.golden.length ? [{ id: 'paper', label: { en: 'Papers', es: 'Artículos' }, content: <PaperView sel={sel} /> }] : []),
          { id: 'report', label: { en: 'One report', es: 'Un reporte' }, content: <SpecimenView sel={sel} /> },
        ],
        { en: 'Views of the measurements', es: 'Vistas de las mediciones' },
        `validation-${c22.variant_id}`,
      );
  return {
    sel,
    rail: [portfolioSection, testsSection],
    groups: [
      { id: 'model', label: { en: 'Model', es: 'Modelo' }, lane: 'replay', provenance: prov, content: <GeneratorsView sel={sel} /> },
      { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'replay', provenance: prov, content: validation },
      { id: 'impact', label: { en: 'Impact', es: 'Impacto' }, lane: 'live', provenance: prov, content: <LiveCalculatorView sel={sel} /> },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C22FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C22VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C22ContextView sel={sel} /> },
    controls: { level, n: portfolio.n, pd: portfolio.pd, ratio: portfolio.ratio, rhoTrue: portfolio.rhoTrue, rhoAssumed: portfolio.rhoAssumed },
  };
}
