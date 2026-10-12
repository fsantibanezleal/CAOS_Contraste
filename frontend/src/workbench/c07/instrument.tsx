// The C07 instrument (U5-W): the Chile provisions trilogy of the synthetic Banco Andino under CMF B-1, IFRS 9 and BdE
// Annex 9 for one scenario variant. The rail has three sections (Regimes: the regime and the segment; IFRS 9: the
// weight of a weighted scenario; B-1: the additional provisions within the board's limits), each with a live
// read-out; the groups are Comparison (with the scenario change), Regimes, Validation and Findings (the shell allows six peers), with the Variants and Context views.
import { ChipGroup, Knob, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { B1Readout, C07ContextView, C07FindingsView, C07VariantsView, GapReadout, Ifrs9Readout } from './C07Common';
import { B1View, BdeView, BridgeView, DeltaView, Ifrs9View, SegmentsView, ThreeRegimeView } from './RegimeViews';
import { componentLabel, defaultSel, outputsOf, type C07Sel, type RegimeId } from './selection';
import { TablesView } from './ValidationViews';

export interface C07Instrument {
  sel: C07Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

const REGIMES: Array<{ id: RegimeId; label: BiText; hint: BiText }> = [
  { id: 'cmf-b1', label: { en: 'B-1', es: 'B-1' }, hint: { en: 'CMF CNCB Chapter B-1: the statutory provision on loans in Chile.', es: 'CMF CNCB Capítulo B-1: la provisión estatutaria sobre créditos en Chile.' } },
  { id: 'ifrs9', label: { en: 'IFRS 9', es: 'IFRS 9' }, hint: { en: 'The probability-weighted ECL: a comparison measure, not the Chilean statutory provision.', es: 'La PCE ponderada por probabilidad: una medida de comparación, no la provisión estatutaria chilena.' } },
  { id: 'bde-annex9', label: { en: 'BdE 9', es: 'BdE 9' }, hint: { en: 'Banco de España Circular 4/2017 Annex 9: the Spanish GAAP alternative solutions.', es: 'Banco de España Circular 4/2017 Anejo 9: las soluciones alternativas del PGC español.' } },
];

/** Short names of the four B-1 portfolios for the rail's chips; the full label is each chip's hint. */
const SHORT: Record<string, BiText> = {
  mortgage: { en: 'Mortgage', es: 'Hipotecario' },
  consumer: { en: 'Consumer', es: 'Consumo' },
  'commercial-group': { en: 'Comm. group', es: 'Com. grupal' },
  'commercial-individual': { en: 'Comm. indiv.', es: 'Com. indiv.' },
};

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C07Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [regime, setRegime] = useState<RegimeId>('cmf-b1');
  const [segment, setSegment] = useState<string | null>(null);
  const [scenario, setScenario] = useState<string | null>(null);
  const [weight, setWeight] = useState<number | null>(null);
  const [additional, setAdditional] = useState<number | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setSegment(null);
    setScenario(null);
    setWeight(null);
    setAdditional(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C07Sel | null = useMemo(() => {
    if (!base || !o) return null;
    const comps = o.ifrs9_detail.weighted_components;
    const comp = comps.find((c) => c.scenario_id === scenario) ?? comps.find((c) => c.scenario_id === base.scenario);
    return {
      ...base,
      regime,
      segment: segment ?? base.segment,
      scenario: comp?.scenario_id ?? base.scenario,
      weight: scenario === null || weight === null ? (comp?.weight ?? base.weight) : weight,
      additional,
    };
  }, [base, o, regime, segment, scenario, weight, additional]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);
  const comps = o.ifrs9_detail.weighted_components;
  const add = o.b1_detail.additional_provisions;
  const moved = comps.find((c) => c.scenario_id === sel.scenario)?.weight !== sel.weight;

  const regimes: RailSection = {
    id: 'regimes',
    label: { en: 'Regimes', es: 'Regímenes' },
    content: (
      <>
        <ChipGroup id="c07-regime" label={{ en: 'Regime in focus', es: 'Régimen en foco' }} options={REGIMES} value={sel.regime} onChange={(id) => setRegime(id as RegimeId)} />
        <ChipGroup
          id="c07-segment"
          label={{ en: 'Segment', es: 'Segmento' }}
          options={o.portfolio.segments.map((s) => ({ id: s.segment_id, label: SHORT[s.segment_id] ?? s.label, hint: s.label }))}
          value={sel.segment}
          onChange={setSegment}
        />
        <GapReadout sel={sel} />
      </>
    ),
  };
  const ifrs9: RailSection = {
    id: 'ifrs9',
    label: { en: 'IFRS 9', es: 'IFRS 9' },
    content: (
      <>
        <ChipGroup
          id="c07-scenario"
          label={{ en: 'Weighted scenario', es: 'Escenario ponderado' }}
          options={comps.map((c) => ({ id: c.scenario_id, label: componentLabel(sel, c.scenario_id), hint: { en: `Contract weight ${(c.weight * 100).toFixed(0)}%, factor z ${c.z}`, es: `Peso del contrato ${(c.weight * 100).toFixed(0)}%, factor z ${String(c.z).replace('.', ',')}` } }))}
          value={sel.scenario}
          onChange={(id) => {
            setScenario(id);
            setWeight(comps.find((c) => c.scenario_id === id)?.weight ?? null);
          }}
        />
        <Knob
          id="c07-weight"
          label={{ en: 'Weight', es: 'Peso' }}
          hint={{ en: 'The probability weight of the chosen scenario; the others keep their ratios. IFRS 9 asks for at least two probability-weighted outcomes, so 100% is a sensitivity, never the measure.', es: 'El peso de probabilidad del escenario elegido; los otros conservan sus proporciones. IFRS 9 pide al menos dos resultados ponderados por probabilidad, así que 100% es una sensibilidad, nunca la medida.' }}
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
        <Ifrs9Readout sel={sel} />
      </>
    ),
  };
  const b1: RailSection = {
    id: 'b1',
    label: { en: 'B-1', es: 'B-1' },
    content: (
      <>
        {add.policy_max > add.policy_min ? (
          <Knob
            id="c07-additional"
            label={{ en: 'Additional provisions', es: 'Provisiones adicionales' }}
            hint={{ en: 'Counter-cyclical, set by the board within its policy limits; outside the comparable total and never a cover for model deficiencies.', es: 'Contracíclicas, fijadas por el directorio dentro de sus límites de política; fuera del total comparable y nunca una cobertura para deficiencias de los modelos.' }}
            value={sel.additional ?? add.amount}
            min={add.policy_min}
            max={add.policy_max}
            step={(add.policy_max - add.policy_min) / 100}
            format={{ decimals: 0 }}
            onChange={setAdditional}
          />
        ) : (
          <p className="ct-note">{pick({ en: 'The board policy fixes the additional provisions: there is nothing to move.', es: 'La política del directorio fija las provisiones adicionales: no hay nada que mover.' }, lang)}</p>
        )}
        <B1Readout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const comparison = tabs(
    [
      { id: 'three', label: { en: 'Three regimes', es: 'Tres regímenes' }, content: <ThreeRegimeView sel={sel} /> },
      { id: 'segments', label: { en: 'Segments', es: 'Segmentos' }, content: <SegmentsView sel={sel} /> },
      { id: 'bridge', label: { en: 'Bridge', es: 'Puente' }, content: <BridgeView sel={sel} /> },
      { id: 'scenario', label: { en: 'Scenario change', es: 'Cambio de escenario' }, content: <DeltaView sel={sel} /> },
    ],
    { en: 'Views of the comparison', es: 'Vistas de la comparación' },
    'c07-comparison',
  );
  const regimesGroup = tabs(
    [
      { id: 'b1', label: { en: 'CMF B-1', es: 'CMF B-1' }, content: <B1View sel={sel} /> },
      { id: 'ifrs9', label: { en: 'IFRS 9', es: 'IFRS 9' }, content: <Ifrs9View sel={sel} /> },
      { id: 'bde', label: { en: 'BdE Annex 9', es: 'BdE Anexo 9' }, content: <BdeView sel={sel} /> },
    ],
    { en: 'Views of each regime', es: 'Vistas de cada régimen' },
    'c07-regimes',
  );
  const validation = <TablesView sel={sel} />;
  return {
    sel,
    rail: [regimes, ifrs9, b1],
    groups: [
      { id: 'comparison', label: { en: 'Comparison', es: 'Comparación' }, lane: 'replay', provenance: prov, content: comparison },
      { id: 'regimes', label: { en: 'Regimes', es: 'Regímenes' }, lane: 'live', provenance: prov, content: regimesGroup },
      { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'replay', provenance: prov, content: validation },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C07FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C07VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C07ContextView sel={sel} /> },
    controls: { regime: sel.regime, segment: sel.segment, scenario: sel.scenario, weight: sel.weight, additional: sel.additional ?? add.amount },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC07Instrument = useInstrument;
