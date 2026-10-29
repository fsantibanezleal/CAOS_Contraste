// The C11 instrument (U8-W): market VaR and ES back-testing across stress and calm windows, one window per variant. The
// rail is split in three sections (ADR-0071 rule 6: Level, Model, Back-test), each with its control and a live read-out;
// the groups are the validator's questions: where the losses exceeded the forecasts (Exceedances), do the back-tests
// reject the model (Back-tests), and which model beats the champion under a consistent score (Comparison), with the
// Findings, the Variants (the windows) and Context views. The workbench calls this hook on every case and uses it when
// the case is C11.
import { ChipGroup, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { C11ContextView, C11FindingsView, C11VariantsView, LevelReadout, ModelReadout, TestReadout } from './C11Common';
import { EsBacktestView, TestsView } from './BacktestViews';
import { ChampionView, DmView } from './ComparisonViews';
import { ConformalVerdictView, ConformalView } from './ConformalViews';
import { TimelineView, ZonesView } from './ExceedanceViews';
import { alphaLabel, alphaShort, defaultSel, levelOf, modelLabel, outputsOf, testName, type C11Alpha, type C11Sel } from './selection';

export interface C11Instrument {
  sel: C11Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C11Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [alpha, setAlpha] = useState<C11Alpha | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [test, setTest] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new window starts every control on its own defaults
  useEffect(() => {
    setAlpha(null);
    setModel(null);
    setTest(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C11Sel | null = useMemo(() => {
    if (!base || !o) return null;
    const a = alpha !== null && o.levels.some((l) => l.alpha === alpha) ? alpha : base.alpha;
    const m = model !== null && o.models.some((x) => x.model_id === model) ? model : base.model;
    const tests = levelOf(o, m, a)?.test_ids ?? [];
    // a back-test the model and level do not carry falls back to the first they do
    return { ...base, alpha: a, model: m, test: test !== null && tests.includes(test) ? test : (tests[0] ?? '') };
  }, [base, o, alpha, model, test]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);
  const tests = levelOf(o, sel.model, sel.alpha)?.test_ids ?? [];

  const levelSection: RailSection = {
    id: 'level',
    label: { en: 'Level', es: 'Nivel' },
    content: (
      <>
        <ChipGroup
          id="c11-level"
          label={{ en: 'Tail level', es: 'Nivel de cola' }}
          options={o.levels.map((l) => ({ id: String(l.alpha), label: alphaShort(l.alpha), hint: alphaLabel(l.alpha) }))}
          value={String(sel.alpha)}
          onChange={(v) => setAlpha(Number(v) as C11Alpha)}
        />
        <LevelReadout sel={sel} />
      </>
    ),
  };
  const modelSection: RailSection = {
    id: 'model',
    label: { en: 'Model', es: 'Modelo' },
    content: (
      <>
        <RailSelect id="c11-model" label={{ en: 'Model', es: 'Modelo' }} options={o.models.map((m) => ({ id: m.model_id, label: modelLabel(sel, m.model_id) }))} value={sel.model} onChange={setModel} />
        <ModelReadout sel={sel} />
      </>
    ),
  };
  const testSection: RailSection = {
    id: 'test',
    label: { en: 'Back-test', es: 'Prueba' },
    content: (
      <>
        <RailSelect id="c11-test" label={{ en: 'Back-test', es: 'Prueba retrospectiva' }} options={tests.map((t) => ({ id: t, label: testName(t) }))} value={sel.test} onChange={setTest} />
        <TestReadout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const exceedances = tabs(
    [
      { id: 'timeline', label: { en: 'Timeline', es: 'Línea de tiempo' }, content: <TimelineView sel={sel} /> },
      { id: 'zones', label: { en: 'Traffic light', es: 'Semáforo' }, content: <ZonesView sel={sel} /> },
    ],
    { en: 'Views of the exceedances', es: 'Vistas de las excedencias' },
    'c11-exceedances',
  );
  const backtests = tabs(
    [
      { id: 'traditional', label: { en: 'Coverage and independence', es: 'Cobertura e independencia' }, content: <TestsView sel={sel} /> },
      { id: 'es', label: { en: 'Expected shortfall', es: 'Pérdida esperada' }, content: <EsBacktestView sel={sel} /> },
    ],
    { en: 'Views of the back-tests', es: 'Vistas de las pruebas retrospectivas' },
    'c11-backtests',
  );
  const comparison = tabs(
    [
      { id: 'champion', label: { en: 'Champion and set', es: 'Campeón y conjunto' }, content: <ChampionView sel={sel} /> },
      { id: 'dm', label: { en: 'Diebold-Mariano', es: 'Diebold-Mariano' }, content: <DmView sel={sel} /> },
      { id: 'conformal', label: { en: 'Conformal recalibration', es: 'Recalibración conforme' }, content: <ConformalView sel={sel} /> },
      { id: 'bs16', label: { en: 'Conformal hypothesis', es: 'Hipótesis conforme' }, content: <ConformalVerdictView sel={sel} /> },
    ],
    { en: 'Views of the comparison', es: 'Vistas de la comparación' },
    'c11-comparison',
  );
  return {
    sel,
    rail: [levelSection, modelSection, testSection],
    groups: [
      { id: 'exceedances', label: { en: 'Exceedances', es: 'Excedencias' }, lane: 'replay', provenance: prov, content: exceedances },
      { id: 'backtests', label: { en: 'Back-tests', es: 'Pruebas retrospectivas' }, lane: 'replay', provenance: prov, content: backtests },
      { id: 'comparison', label: { en: 'Comparison', es: 'Comparación' }, lane: 'replay', provenance: prov, content: comparison },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C11FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C11VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C11ContextView sel={sel} /> },
    controls: { level: sel.alpha, model: sel.model, test: sel.test },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC11Instrument = useInstrument;
