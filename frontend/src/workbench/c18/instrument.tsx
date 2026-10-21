// The C18 instrument (U13-W): ICAAP and IAPE capital aggregation under macro scenarios, on the synthetic Banco Andino. A scenario
// variant has the rail sections Capital (the year of the projection), Path, Loan type and Risk; the t-copula aggregation
// variant has Matrix, Row and Risk; the reverse-stress variant has Factor and Start, each with its control and a live read-out
// (ADR-0071 rule 6). The groups are the validator's questions: does the bank hold its internal capital target for three
// years (Capital), how does the scenario reach the book and did the satellites back-cast the last episode (Stress), how much
// of the capital rests on the aggregation method and how is it allocated (Aggregation), which is the most plausible scenario
// that breaks the bank (Reverse stress), and what the tests and the findings say, with the variants as the Variants view and
// the Context view. The workbench calls this hook on every case and uses it when the case is C18.
import { ChipGroup, Knob, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import {
  C18ContextView, C18FindingsView, C18TestsView, C18VariantsView, CapitalReadout, FactorReadout, LoanReadout, MatrixReadout, PathReadout, RiskReadout, RowReadout, StartReadout,
} from './C18Common';
import { Annex3View, FanView, StackView } from './CapitalViews';
import { BackcastView, LossesView, PathsView, SatellitesView, SeverityView } from './StressViews';
import { BandView, EulerView, MarginalsView, SensitivityView } from './AggregationViews';
import { ReverseSearchView, ReverseSolutionView } from './ReverseViews';
import { LOAN_ORDER, LOAN_TEXT, REGRESSOR_TEXT, RISK_ORDER, RISK_TEXT, aggDocOf, aggOf, defaultSel, methodShort, outputsOf, reverseOf, text, type C18Sel, type LoanId, type RiskId } from './selection';

export interface C18Instrument {
  sel: C18Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C18Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [year, setYear] = useState<number | null>(null);
  const [path, setPath] = useState<string | null>(null);
  const [loan, setLoan] = useState<string | null>(null);
  const [risk, setRisk] = useState<string | null>(null);
  const [matrix, setMatrix] = useState<string | null>(null);
  const [row, setRow] = useState<string | null>(null);
  const [factor, setFactor] = useState<string | null>(null);
  const [start, setStart] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setYear(null);
    setPath(null);
    setLoan(null);
    setRisk(null);
    setMatrix(null);
    setRow(null);
    setFactor(null);
    setStart(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const ad = base ? aggDocOf(base) : null;
  const r = base ? reverseOf(base) : null;
  const sel: C18Sel | null = useMemo(() => {
    if (!base) return null;
    const matrixId = matrix === 'stress' && ad ? 'stress' : 'base';
    const a = aggOf({ ...base, matrix: matrixId });
    const nPaths = o?.scenario.paths.length ?? 1;
    return {
      ...base,
      year: year !== null && year >= 1 && year <= 3 ? year : base.year,
      path: path !== null && Number(path) >= 0 && Number(path) < nPaths ? Number(path) : 0,
      loan: (loan !== null && LOAN_ORDER.includes(loan as LoanId) ? loan : base.loan) as LoanId,
      risk: (risk !== null && RISK_ORDER.includes(risk as RiskId) ? risk : base.risk) as RiskId,
      matrix: matrixId,
      row: row !== null && Number(row) >= 0 && a && Number(row) < a.band.length ? Number(row) : 0,
      factor: factor !== null && r && Number(factor) >= 0 && Number(factor) < r.factor_space.factors.length ? Number(factor) : 0,
      start: start !== null && r?.starts.some((s) => s.start_id === start) ? start : base.start,
    };
  }, [base, o, ad, r, year, path, loan, risk, matrix, row, factor, start]);
  if (!sel || !data || (!o && !ad && !r)) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const group = (id: string, label: BiText, content: ReactElement) => ({ id, label, lane: 'replay' as const, provenance: prov, content });
  const testsGroup = group(
    'tests',
    { en: 'Tests and findings', es: 'Pruebas y hallazgos' },
    tabs(
      [
        { id: 'tests', label: { en: 'Tests', es: 'Pruebas' }, content: <C18TestsView sel={sel} /> },
        { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, content: <C18FindingsView sel={sel} /> },
      ],
      { en: 'Views of the tests and findings', es: 'Vistas de las pruebas y hallazgos' },
      'c18-tests',
    ),
  );
  const compare = { label: { en: 'Variants', es: 'Variantes' } as BiText, lane: 'replay' as const, provenance: prov, content: <C18VariantsView sel={sel} onPick={onPick} /> };
  const context = { content: <C18ContextView sel={sel} /> };

  const riskSection: RailSection = {
    id: 'risk',
    label: { en: 'Risk', es: 'Riesgo' },
    content: (
      <>
        <RailSelect id="c18-risk" label={{ en: 'Risk of the aggregation', es: 'Riesgo de la agregación' }} options={RISK_ORDER.map((id) => ({ id, label: text(RISK_TEXT, id) }))} value={sel.risk} onChange={setRisk} />
        <RiskReadout sel={sel} />
      </>
    ),
  };

  if (r) {
    return {
      sel,
      rail: [
        {
          id: 'factor',
          label: { en: 'Factor', es: 'Factor' },
          content: (
            <>
              <RailSelect id="c18-factor" label={{ en: 'Factor of the scenario', es: 'Factor del escenario' }} options={r.factor_space.factors.map((f, i) => ({ id: String(i), label: f.label }))} value={String(sel.factor)} onChange={setFactor} />
              <FactorReadout sel={sel} />
            </>
          ),
        },
        {
          id: 'start',
          label: { en: 'Start', es: 'Inicio' },
          content: (
            <>
              <RailSelect id="c18-start" label={{ en: 'Start of the search', es: 'Inicio de la búsqueda' }} options={r.starts.map((s, i) => ({ id: s.start_id, label: { en: `Start ${i + 1}`, es: `Inicio ${i + 1}` } }))} value={sel.start} onChange={setStart} />
              <StartReadout sel={sel} />
            </>
          ),
        },
      ],
      groups: [
        group(
          'reverse',
          { en: 'Reverse stress', es: 'Estrés inverso' },
          tabs(
            [
              { id: 'scenario', label: { en: 'Scenario', es: 'Escenario' }, content: <ReverseSolutionView sel={sel} /> },
              { id: 'search', label: { en: 'Search and check', es: 'Búsqueda y verificación' }, content: <ReverseSearchView sel={sel} /> },
            ],
            { en: 'Views of the reverse stress', es: 'Vistas del estrés inverso' },
            'c18-reverse',
          ),
        ),
        testsGroup,
      ],
      compare,
      context,
      controls: { factor: sel.factor, start: sel.start },
    };
  }

  if (ad) {
    const a = aggOf(sel);
    return {
      sel,
      rail: [
        {
          id: 'matrix',
          label: { en: 'Matrix', es: 'Matriz' },
          content: (
            <>
              <ChipGroup
                id="c18-matrix"
                label={{ en: 'Correlation matrix', es: 'Matriz de correlación' }}
                options={[
                  { id: 'base', label: { en: 'Base', es: 'Base' }, hint: { en: 'Rosenberg and Schuermann, with the IRRBB correlations as a convention', es: 'Rosenberg y Schuermann, con las correlaciones de IRRBB como convención' } },
                  { id: 'stress', label: { en: 'Stress 0.8', es: 'Estrés 0,8' }, hint: { en: 'The base matrix with market-credit raised to 0.8', es: 'La matriz base con mercado-crédito elevada a 0,8' } },
                ]}
                value={sel.matrix}
                onChange={setMatrix}
              />
              <MatrixReadout sel={sel} />
            </>
          ),
        },
        {
          id: 'row',
          label: { en: 'Row', es: 'Fila' },
          content: (
            <>
              <RailSelect id="c18-row" label={{ en: 'Method of the band', es: 'Método de la banda' }} options={(a?.band ?? []).map((b, i) => ({ id: String(i), label: methodShort(b) }))} value={String(sel.row)} onChange={setRow} />
              <RowReadout sel={sel} />
            </>
          ),
        },
        riskSection,
      ],
      groups: [
        group(
          'aggregation',
          { en: 'Aggregation', es: 'Agregación' },
          tabs(
            [
              { id: 'band', label: { en: 'Band', es: 'Banda' }, content: <BandView sel={sel} /> },
              { id: 'euler', label: { en: 'Euler allocation', es: 'Asignación de Euler' }, content: <EulerView sel={sel} /> },
              { id: 'marginals', label: { en: 'Marginals', es: 'Marginales' }, content: <MarginalsView sel={sel} /> },
              { id: 'sensitivity', label: { en: 'Copula and correlation', es: 'Cópula y correlación' }, content: <SensitivityView sel={sel} /> },
            ],
            { en: 'Views of the aggregation', es: 'Vistas de la agregación' },
            'c18-aggregation-doc',
          ),
        ),
        testsGroup,
      ],
      compare,
      context,
      controls: { matrix: sel.matrix, row: sel.row, risk: sel.risk },
    };
  }

  const paths = o?.scenario.paths ?? [];
  return {
    sel,
    rail: [
      {
        id: 'capital',
        label: { en: 'Year', es: 'Año' },
        content: (
          <>
            <Knob
              id="c18-year"
              label={{ en: 'Year of the projection', es: 'Año de la proyección' }}
              value={sel.year}
              min={1}
              max={3}
              step={1}
              unit={{ en: 'year', es: 'año' }}
              hint={{ en: 'The year of the three-year planning period that the read-out and the marked line show.', es: 'El año del periodo de planificación de tres años que muestran la lectura y la línea marcada.' }}
              format={{ decimals: 0 }}
              onChange={setYear}
            />
            <CapitalReadout sel={sel} />
          </>
        ),
      },
      {
        id: 'path',
        label: { en: 'Path', es: 'Ruta' },
        content: (
          <>
            <RailSelect id="c18-path" label={{ en: 'Variable of the scenario', es: 'Variable del escenario' }} options={paths.map((p, i) => ({ id: String(i), label: text(REGRESSOR_TEXT, p.maps_to_regressor) }))} value={String(sel.path)} onChange={setPath} />
            <PathReadout sel={sel} />
          </>
        ),
      },
      {
        id: 'loan',
        label: { en: 'Loan', es: 'Préstamo' },
        content: (
          <>
            <RailSelect id="c18-loan" label={{ en: 'Loan type', es: 'Tipo de préstamo' }} options={LOAN_ORDER.map((id) => ({ id, label: text(LOAN_TEXT, id) }))} value={sel.loan} onChange={setLoan} />
            <LoanReadout sel={sel} />
          </>
        ),
      },
      riskSection,
    ],
    groups: [
      group(
        'capital',
        { en: 'Capital', es: 'Capital' },
        tabs(
          [
            { id: 'fan', label: { en: 'CET1 fan', es: 'Abanico de CET1' }, content: <FanView sel={sel} /> },
            { id: 'stack', label: { en: 'Capital stack', es: 'Capital apilado' }, content: <StackView sel={sel} /> },
            { id: 'annex3', label: { en: 'Annex 3', es: 'Anexo 3' }, content: <Annex3View sel={sel} /> },
          ],
          { en: 'Views of the capital', es: 'Vistas del capital' },
          'c18-capital',
        ),
      ),
      group(
        'stress',
        { en: 'Stress', es: 'Estrés' },
        tabs(
          [
            { id: 'paths', label: { en: 'Scenario path', es: 'Trayectoria' }, content: <PathsView sel={sel} /> },
            { id: 'satellites', label: { en: 'Satellites', es: 'Satélites' }, content: <SatellitesView sel={sel} /> },
            { id: 'backcast', label: { en: 'Back-cast', es: 'Back-cast' }, content: <BackcastView sel={sel} /> },
            { id: 'severity', label: { en: 'Severity', es: 'Severidad' }, content: <SeverityView sel={sel} /> },
            { id: 'losses', label: { en: 'Losses', es: 'Pérdidas' }, content: <LossesView sel={sel} /> },
          ],
          { en: 'Views of the stress', es: 'Vistas del estrés' },
          'c18-stress',
        ),
      ),
      group(
        'aggregation',
        { en: 'Aggregation', es: 'Agregación' },
        tabs(
          [
            { id: 'band', label: { en: 'Band', es: 'Banda' }, content: <BandView sel={sel} /> },
            { id: 'euler', label: { en: 'Euler allocation', es: 'Asignación de Euler' }, content: <EulerView sel={sel} /> },
            { id: 'marginals', label: { en: 'Marginals', es: 'Marginales' }, content: <MarginalsView sel={sel} /> },
          ],
          { en: 'Views of the aggregation', es: 'Vistas de la agregación' },
          'c18-aggregation',
        ),
      ),
      testsGroup,
    ],
    compare,
    context,
    controls: { year: sel.year, path: sel.path, loan: sel.loan, risk: sel.risk },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC18Instrument = useInstrument;
