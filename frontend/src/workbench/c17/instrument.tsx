// The C17 instrument (U12-W): operational risk, the LDA against the SMA on a generator of loss histories with a known
// true annual loss distribution, one tail index per variant. The rail is split in four sections (ADR-0071 rule 6: Years,
// Threshold, Method, Scenario), each with its control and a live read-out; the groups are the validator's questions:
// Loss (the curve and its tail), Capital (how far from the truth, across the grid, and the scenarios), SMA (against the
// LDA, and against one large loss) and Model (the ladder, the OPE25 specification and the findings), with the Variants
// (the tail indices) and Context views. The workbench calls this hook on every case and uses it when the case is C17.
import { ChipGroup, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { C17ContextView, C17FindingsView, C17VariantsView, RungReadout, ScenarioReadout, ThresholdReadout, YearsReadout } from './C17Common';
import { ByMethodView, ByYearsView, ScenarioView } from './CapitalViews';
import { ExceedanceView, TailIndexView } from './LossViews';
import { LadderView, SmaSpecView } from './ModelViews';
import { ResponseView, SmaView } from './SmaViews';
import { RUNG_ORDER, defaultSel, eurText, outputsOf, rungName, thresholdsOf, yearsOf, type C17Sel } from './selection';

export interface C17Instrument {
  sel: C17Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C17Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [years, setYears] = useState<number | null>(null);
  const [threshold, setThreshold] = useState<number | null>(null);
  const [rung, setRung] = useState<string | null>(null);
  const [scenario, setScenario] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setYears(null);
    setThreshold(null);
    setRung(null);
    setScenario(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C17Sel | null = useMemo(() => {
    if (!base || !o) return null;
    return {
      ...base,
      years: years !== null && yearsOf(o).includes(years) ? years : base.years,
      threshold: threshold !== null && thresholdsOf(o).includes(threshold) ? threshold : base.threshold,
      rung: rung !== null && (RUNG_ORDER as readonly string[]).includes(rung) ? rung : base.rung,
      scenario: scenario !== null && o.scenario_influence.scenarios.some((s) => s.scenario_id === scenario) ? scenario : base.scenario,
    };
  }, [base, o, years, threshold, rung, scenario]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);

  const yearsSection: RailSection = {
    id: 'years',
    label: { en: 'Years', es: 'Años' },
    content: (
      <>
        <ChipGroup
          id="c17-years"
          label={{ en: 'Years of data', es: 'Años de datos' }}
          options={yearsOf(o).map((y) => ({ id: String(y), label: { en: String(y), es: String(y) }, hint: { en: `Each history records ${y} years of losses.`, es: `Cada historia registra ${y} años de pérdidas.` } }))}
          value={String(sel.years)}
          onChange={(id) => setYears(Number(id))}
        />
        <YearsReadout sel={sel} />
      </>
    ),
  };
  const thresholdSection: RailSection = {
    id: 'threshold',
    label: { en: 'Threshold', es: 'Umbral' },
    content: (
      <>
        <ChipGroup
          id="c17-threshold"
          label={{ en: 'Collection threshold', es: 'Umbral de recolección' }}
          options={thresholdsOf(o).map((t) => ({ id: String(t), label: eurText(t), hint: { en: `Losses under ${eurText(t).en} are not recorded.`, es: `Las pérdidas bajo ${eurText(t).es} no se registran.` } }))}
          value={String(sel.threshold)}
          onChange={(id) => setThreshold(Number(id))}
        />
        <ThresholdReadout sel={sel} />
      </>
    ),
  };
  const rungSection: RailSection = {
    id: 'rung',
    label: { en: 'Method', es: 'Método' },
    content: (
      <>
        <RailSelect id="c17-rung" label={{ en: 'Method', es: 'Método' }} options={RUNG_ORDER.map((r) => ({ id: r, label: rungName(r) }))} value={sel.rung} onChange={setRung} />
        <RungReadout sel={sel} />
      </>
    ),
  };
  const scenarioSection: RailSection = {
    id: 'scenario',
    label: { en: 'Scenario', es: 'Escenario' },
    content: (
      <>
        <RailSelect id="c17-scenario" label={{ en: 'Scenario', es: 'Escenario' }} options={o.scenario_influence.scenarios.map((s) => ({ id: s.scenario_id, label: s.label }))} value={sel.scenario} onChange={setScenario} />
        <ScenarioReadout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const loss = tabs(
    [
      { id: 'exceedance', label: { en: 'Exceedance curve', es: 'Curva de excedencia' }, content: <ExceedanceView sel={sel} /> },
      { id: 'tail', label: { en: 'Tail index', es: 'Índice de cola' }, content: <TailIndexView sel={sel} /> },
    ],
    { en: 'Views of the loss', es: 'Vistas de la pérdida' },
    'c17-loss',
  );
  const capital = tabs(
    [
      { id: 'by-method', label: { en: 'By method', es: 'Por método' }, content: <ByMethodView sel={sel} /> },
      { id: 'by-years', label: { en: 'By years and threshold', es: 'Por años y umbral' }, content: <ByYearsView sel={sel} /> },
      { id: 'scenarios', label: { en: 'Scenarios', es: 'Escenarios' }, content: <ScenarioView sel={sel} /> },
    ],
    { en: 'Views of the capital', es: 'Vistas del capital' },
    'c17-capital',
  );
  const sma = tabs(
    [
      { id: 'sma', label: { en: 'Against the LDA', es: 'Contra el LDA' }, content: <SmaView sel={sel} /> },
      { id: 'response', label: { en: 'One large loss', es: 'Una pérdida grande' }, content: <ResponseView sel={sel} /> },
    ],
    { en: 'Views of the SMA', es: 'Vistas del SMA' },
    'c17-sma',
  );
  const model = tabs(
    [
      { id: 'ladder', label: { en: 'Ladder', es: 'Escalera' }, content: <LadderView sel={sel} /> },
      { id: 'spec', label: { en: 'Standardised approach', es: 'Enfoque estandarizado' }, content: <SmaSpecView sel={sel} /> },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, content: <C17FindingsView sel={sel} /> },
    ],
    { en: 'Views of the model', es: 'Vistas del modelo' },
    'c17-model',
  );
  return {
    sel,
    rail: [yearsSection, thresholdSection, rungSection, scenarioSection],
    groups: [
      { id: 'loss', label: { en: 'Loss', es: 'Pérdida' }, lane: 'replay', provenance: prov, content: loss },
      { id: 'capital', label: { en: 'Capital', es: 'Capital' }, lane: 'replay', provenance: prov, content: capital },
      { id: 'sma', label: { en: 'SMA', es: 'SMA' }, lane: 'replay', provenance: prov, content: sma },
      { id: 'model', label: { en: 'Model', es: 'Modelo' }, lane: 'replay', provenance: prov, content: model },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C17VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C17ContextView sel={sel} /> },
    controls: { years: sel.years, threshold: sel.threshold, rung: sel.rung, scenario: sel.scenario },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC17Instrument = useInstrument;
