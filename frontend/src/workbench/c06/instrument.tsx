// The C06 instrument (U5-W): mortgage lifetime PD, IFRS 9 staging and ECL at one reporting date. The rail is split in four
// sections (ADR-0071 rule 6: Scenarios, the weight of a scenario; Curves, the measure and the segment; Account, the sampled account;
// Simplex, the staging mode and the surface), each with its control and a live read-out; the groups are the validator's questions: Model,
// Validation, Impact, Findings, with the Variants and Context views. The workbench calls this hook on every case and
// uses it when the case is C06 and the variant is a reporting-date document.
import { ChipGroup, Knob, SubTabs, formatNumber, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from './RailSelect';
import { AccountReadout, C06ContextView, CurveReadout, C06FindingsView, C06VariantsView, SurfaceReadout, WeightReadout } from './C06Common';
import { STAGE_TEXT, segmentLabel } from './format';
import { StageFlowView, StageSummaryView, WaterfallView, WeightsView } from './ImpactViews';
import { defaultSel, outputsOf, type C06Sel, type Measure, type Staging, type Surface } from './selection';
import { NonLinearityView, SicrView, TermStructureView } from './TermViews';
import { BacktestView, DecileView, LadderView, RungsView } from './ValidationViews';

export interface C06Instrument {
  sel: C06Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

const MEASURES: Array<{ id: Measure; label: BiText; hint: BiText }> = [
  { id: 'cumulative', label: { en: 'F(t)', es: 'F(t)' }, hint: { en: 'Cumulative PD: the probability of default by month t.', es: 'PD acumulada: la probabilidad de incumplimiento hasta el mes t.' } },
  { id: 'marginal', label: { en: 'q(t)', es: 'q(t)' }, hint: { en: 'Marginal (unconditional) PD of month t: S(t-1) times h(t).', es: 'PD marginal (incondicional) del mes t: S(t-1) por h(t).' } },
  { id: 'hazard', label: { en: 'h(t)', es: 'h(t)' }, hint: { en: 'Conditional PD of month t given survival to t-1, the hazard.', es: 'PD condicional del mes t dada la supervivencia a t-1, el riesgo instantáneo.' } },
];

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C06Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [scenario, setScenario] = useState<string | null>(null);
  const [weight, setWeight] = useState<number | null>(null);
  const [segment, setSegment] = useState<string | null>(null);
  const [account, setAccount] = useState<string | null>(null);
  const [measure, setMeasure] = useState<Measure>('cumulative');
  const [staging, setStaging] = useState<Staging>('recomputed');
  const [surface, setSurface] = useState<Surface>('ecl');
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setScenario(null);
    setWeight(null);
    setSegment(null);
    setAccount(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C06Sel | null = useMemo(() => {
    if (!base || !o) return null;
    const sc = o.scenarios.find((s) => s.id === scenario) ?? o.scenarios.find((s) => s.id === base.scenario);
    const scenarioId = sc?.id ?? base.scenario;
    return {
      ...base,
      scenario: scenarioId,
      weight: scenario === null || weight === null ? (sc?.weight ?? base.weight) : weight,
      segment: segment ?? base.segment,
      account: account ?? base.account,
      measure,
      staging,
      surface,
    };
  }, [base, o, scenario, weight, segment, account, measure, staging, surface]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);
  const segments = [...new Set(o.term_structures.map((t) => t.segment_id))];
  const moved = o.scenarios.find((s) => s.id === sel.scenario)?.weight !== sel.weight;

  const scenarios: RailSection = {
    id: 'scenarios',
    label: { en: 'Scenarios', es: 'Escenarios' },
    content: (
      <>
        <RailSelect
          id="c06-scenario"
          label={{ en: 'Scenario', es: 'Escenario' }}
          options={o.scenarios.map((s) => ({ id: s.id, label: s.label, hint: { en: `Scenario weight ${formatNumber(s.weight, 'en', { percent: true, decimals: 0 })}, factor z ${formatNumber(s.z_mean, 'en')}`, es: `Peso del escenario ${formatNumber(s.weight, 'es', { percent: true, decimals: 0 })}, factor z ${formatNumber(s.z_mean, 'es')}` } }))}
          value={sel.scenario}
          onChange={(id) => {
            setScenario(id);
            setWeight(o.scenarios.find((s) => s.id === id)?.weight ?? null);
          }}
        />
        <Knob
          id="c06-weight"
          label={{ en: 'Weight', es: 'Peso' }}
          hint={{ en: 'The probability weight of the chosen scenario; the others keep their ratios. IFRS 9 asks for at least two probability-weighted outcomes, so 100% is a sensitivity, never the measure.', es: 'El peso de probabilidad del escenario elegido; los otros conservan sus proporciones. IFRS 9 pide al menos dos resultados ponderados por probabilidad, así que 100 % es una sensibilidad, nunca la medida.' }}
          value={sel.weight}
          min={0}
          max={1}
          step={0.01}
          format={{ percent: true, decimals: 0 }}
          onChange={(w) => {
            setScenario(sel.scenario);
            setWeight(w);
          }}
        />
        {moved && (
          <button type="button" className="ct-linkbutton" onClick={() => { setScenario(null); setWeight(null); }}>
            {pick({ en: 'Back to the contract weights', es: 'Volver a los pesos del contrato' }, lang)}
          </button>
        )}
        <WeightReadout sel={sel} />
      </>
    ),
  };
  const curves: RailSection = {
    id: 'curves',
    label: { en: 'Curves', es: 'Curvas' },
    content: (
      <>
        <ChipGroup id="c06-measure" label={{ en: 'Measure', es: 'Medida' }} options={MEASURES} value={sel.measure} onChange={(id) => setMeasure(id as Measure)} />
        <RailSelect id="c06-segment" label={{ en: 'Segment', es: 'Segmento' }} options={segments.map((id) => ({ id, label: segmentLabel(id) }))} value={sel.segment} onChange={setSegment} />
        <CurveReadout sel={sel} />
      </>
    ),
  };
  const accountSection: RailSection = {
    id: 'account',
    label: { en: 'Account', es: 'Cuenta' },
    content: (
      <>
        <RailSelect
          id="c06-account"
          label={{ en: 'Account', es: 'Cuenta' }}
          options={o.account_curves.map((a) => ({ id: a.account_id, label: { en: a.account_id, es: a.account_id }, hint: { en: `${pick(STAGE_TEXT[a.stage] ?? a.stage, 'en')}, ${segmentLabel(a.segment_id).en.toLowerCase()}`, es: `${pick(STAGE_TEXT[a.stage] ?? a.stage, 'es')}, ${segmentLabel(a.segment_id).es.toLowerCase()}` } }))}
          value={sel.account}
          onChange={setAccount}
        />
        <AccountReadout sel={sel} />
      </>
    ),
  };
  const simplex: RailSection = {
    id: 'simplex',
    label: { en: 'Simplex', es: 'Simplex' },
    content: (
      <>
        <ChipGroup
          id="c06-staging"
          label={{ en: 'Staging', es: 'Etapas' }}
          options={[
            { id: 'recomputed', label: { en: 'Recomputed', es: 'Recalculadas' }, hint: { en: 'The SICR test is rerun at each weight vector.', es: 'La prueba SICR se vuelve a correr con cada vector de pesos.' } },
            { id: 'frozen', label: { en: 'Frozen', es: 'Congeladas' }, hint: { en: 'Staging as at the weighted conditions: the ECL is linear in the weights.', es: 'Etapas como en las condiciones ponderadas: la PCE es lineal en los pesos.' } },
          ]}
          value={sel.staging}
          onChange={(id) => setStaging(id as Staging)}
        />
        <ChipGroup
          id="c06-surface"
          label={{ en: 'Surface', es: 'Superficie' }}
          options={[
            { id: 'ecl', label: { en: 'ECL', es: 'PCE' } },
            { id: 'stage2', label: { en: 'Stage 2 share', es: 'Fracción Etapa 2' } },
          ]}
          value={sel.surface}
          onChange={(id) => setSurface(id as Surface)}
        />
        <SurfaceReadout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const model = tabs(
    [
      { id: 'term', label: { en: 'Term structures', es: 'Estructuras de plazo' }, content: <TermStructureView sel={sel} /> },
      { id: 'sicr', label: { en: 'SICR', es: 'SICR' }, content: <SicrView sel={sel} /> },
      { id: 'nonlinearity', label: { en: 'Nonlinearity', es: 'No linealidad' }, content: <NonLinearityView sel={sel} /> },
      { id: 'ladder', label: { en: 'Ladder', es: 'Escalera' }, content: <LadderView sel={sel} /> },
    ],
    { en: 'Views of the lifetime PD model', es: 'Vistas del modelo de PD de vida' },
    'c06-model',
  );
  const validation = tabs(
    [
      { id: 'backtest', label: { en: 'Backtest', es: 'Retrospectiva' }, content: <BacktestView sel={sel} /> },
      { id: 'deciles', label: { en: 'Deciles', es: 'Deciles' }, content: <DecileView sel={sel} /> },
      { id: 'rungs', label: { en: 'Rungs', es: 'Peldaños' }, content: <RungsView sel={sel} /> },
    ],
    { en: 'Views of the validation', es: 'Vistas de la validación' },
    'c06-validation',
  );
  const impact = tabs(
    [
      { id: 'flow', label: { en: 'Stage flow', es: 'Flujo de etapas' }, content: <StageFlowView sel={sel} /> },
      { id: 'waterfall', label: { en: 'Waterfall', es: 'Cascada' }, content: <WaterfallView sel={sel} /> },
      { id: 'weights', label: { en: 'Weights', es: 'Pesos' }, content: <WeightsView sel={sel} /> },
      { id: 'summary', label: { en: 'Stages', es: 'Etapas' }, content: <StageSummaryView sel={sel} /> },
    ],
    { en: 'Views of the impact', es: 'Vistas del impacto' },
    'c06-impact',
  );
  return {
    sel,
    rail: [scenarios, curves, accountSection, simplex],
    groups: [
      { id: 'model', label: { en: 'Model', es: 'Modelo' }, lane: 'replay', provenance: prov, content: model },
      { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'replay', provenance: prov, content: validation },
      { id: 'impact', label: { en: 'Impact', es: 'Impacto' }, lane: 'live', provenance: prov, content: impact },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C06FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C06VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C06ContextView sel={sel} /> },
    controls: { scenario: sel.scenario, weight: sel.weight, segment: sel.segment, account: sel.account, measure: sel.measure, staging: sel.staging, surface: sel.surface },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC06Instrument = useInstrument;
