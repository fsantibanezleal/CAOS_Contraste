// The C03 instrument (U6-W): the PD of SME loans by approval vintage (SBA 7(a)), one test cohort per variant. The rail is
// split in three sections (ADR-0071 rule 6: Vintage, Horizon, Model), each with its control and a live read-out; the
// groups are the validator's questions: Vintages, Model, Validation and Findings, with the Variants and Context views.
// The workbench calls this hook on every case and uses it when the case is C03 and the variant is a vintage-cohort document.
import { SubTabs, formatNumber, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { C03ContextView, C03FindingsView, C03VariantsView, HorizonReadout, ModelReadout, VintageReadout } from './C03Common';
import { CalibrationView, RungsView, TrainingView } from './ModelViews';
import { SequentialView } from './SequentialView';
import { defaultSel, outputsOf, rungLabel, type C03Sel } from './selection';
import { CurvesView, FiveYearView, StabilityView, fyText } from './VintageViews';

export interface C03Instrument {
  sel: C03Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C03Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [vintage, setVintage] = useState<number | null>(null);
  const [horizon, setHorizon] = useState<number | null>(null);
  const [rung, setRung] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setVintage(null);
    setHorizon(null);
    setRung(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C03Sel | null = useMemo(() => {
    if (!base || !o) return null;
    const months = [...new Set(o.vintage_curves.flatMap((c) => c.months))];
    return {
      ...base,
      vintage: vintage !== null && o.vintage_curves.some((c) => c.fiscal_year === vintage) ? vintage : base.vintage,
      horizon: horizon !== null && months.includes(horizon) ? horizon : base.horizon,
      rung: rung !== null && o.rung_comparison.some((r) => r.rung_id === rung) ? rung : base.rung,
    };
  }, [base, o, vintage, horizon, rung]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);
  const months = [...new Set(o.vintage_curves.flatMap((c) => c.months))].sort((a, b) => a - b);

  const vintageSection: RailSection = {
    id: 'vintage',
    label: { en: 'Vintage', es: 'Cosecha' },
    content: (
      <>
        <RailSelect
          id="c03-vintage"
          label={{ en: 'Vintage', es: 'Cosecha' }}
          options={o.vintage_curves.map((c) => ({ id: `${c.fiscal_year}`, label: fyText(c.fiscal_year), hint: { en: `${formatNumber(c.n, 'en', { decimals: 0 })} loans approved`, es: `${formatNumber(c.n, 'es', { decimals: 0 })} créditos aprobados` } }))}
          value={`${sel.vintage}`}
          onChange={(id) => setVintage(Number(id))}
        />
        <VintageReadout sel={sel} />
      </>
    ),
  };
  const horizonSection: RailSection = {
    id: 'horizon',
    label: { en: 'Horizon', es: 'Horizonte' },
    content: (
      <>
        <RailSelect
          id="c03-horizon"
          label={{ en: 'Horizon', es: 'Horizonte' }}
          options={months.map((m) => ({ id: `${m}`, label: { en: `${m} months`, es: `${m} meses` } }))}
          value={`${sel.horizon}`}
          onChange={(id) => setHorizon(Number(id))}
        />
        <HorizonReadout sel={sel} />
      </>
    ),
  };
  const modelSection: RailSection = {
    id: 'model',
    label: { en: 'Model', es: 'Modelo' },
    content: (
      <>
        <RailSelect
          id="c03-model"
          label={{ en: 'Model', es: 'Modelo' }}
          options={o.rung_comparison.map((r) => ({ id: r.rung_id, label: rungLabel(sel, r.rung_id) }))}
          value={sel.rung}
          onChange={setRung}
        />
        <ModelReadout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const vintages = tabs(
    [
      { id: 'curves', label: { en: 'Curves', es: 'Curvas' }, content: <CurvesView sel={sel} /> },
      { id: 'five-year', label: { en: 'Five-year mark', es: 'Marca de cinco años' }, content: <FiveYearView sel={sel} /> },
    ],
    { en: 'Views of the vintages', es: 'Vistas de las cosechas' },
    'c03-vintages',
  );
  const model = tabs(
    [
      { id: 'rungs', label: { en: 'Rungs', es: 'Peldaños' }, content: <RungsView sel={sel} /> },
      { id: 'training', label: { en: 'Training window', es: 'Ventana de entrenamiento' }, content: <TrainingView sel={sel} /> },
    ],
    { en: 'Views of the model', es: 'Vistas del modelo' },
    'c03-model',
  );
  const validation = tabs(
    [
      { id: 'calibration', label: { en: 'Calibration and tests', es: 'Calibración y pruebas' }, content: <CalibrationView sel={sel} /> },
      { id: 'stability', label: { en: 'Stability', es: 'Estabilidad' }, content: <StabilityView sel={sel} /> },
      // BS-15 (D15): the e-process monitor read at every age, beside the fixed-window tests read at the mark
      { id: 'sequential', label: { en: 'Sequential', es: 'Secuencial' }, content: <SequentialView sel={sel} /> },
    ],
    { en: 'Views of the validation', es: 'Vistas de la validación' },
    'c03-validation',
  );
  return {
    sel,
    rail: [vintageSection, horizonSection, modelSection],
    groups: [
      { id: 'vintages', label: { en: 'Vintages', es: 'Cosechas' }, lane: 'replay', provenance: prov, content: vintages },
      { id: 'model', label: { en: 'Model', es: 'Modelo' }, lane: 'replay', provenance: prov, content: model },
      { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'replay', provenance: prov, content: validation },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C03FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C03VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C03ContextView sel={sel} /> },
    controls: { vintage: sel.vintage, horizon: sel.horizon, model: sel.rung },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC03Instrument = useInstrument;
