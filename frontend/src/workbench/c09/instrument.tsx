// The C09 instrument (U6-W): the CCF and the EAD of revolving lines on a generator with a known CCF, one acceleration
// level per variant. The rail is split in four sections (ADR-0071 rule 6: Design, Treatment, Model, Band), each with its
// control and a live read-out; the groups are the validator's questions: CCF, EAD (each with its tests) and Findings,
// with the Variants (the levels) and Context views. The workbench calls this hook on every case and uses it when the case is C09.
import { ChipGroup, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { BandReadout, C09ContextView, C09FindingsView, C09VariantsView, DesignReadout, ModelReadout, TreatmentReadout } from './C09Common';
import { ByDesignView, DistributionView } from './CcfViews';
import { BacktestView, FloorsView, ModelsView } from './EadViews';
import { DESIGN_SHORT, DESIGN_TEXT, TREATMENT_TEXT, bandLabel, bandsOf, defaultSel, modelLabel, outputsOf, text, treatmentsOf, type C09Sel } from './selection';

export interface C09Instrument {
  sel: C09Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C09Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [design, setDesign] = useState<string | null>(null);
  const [treatment, setTreatment] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [band, setBand] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setDesign(null);
    setTreatment(null);
    setModel(null);
    setBand(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C09Sel | null = useMemo(() => {
    if (!base || !o) return null;
    const designs: string[] = [...new Set(o.ccf_by_design.rows.map((r) => r.design))];
    const d = design !== null && designs.includes(design) ? design : base.design;
    const treatments = treatmentsOf(o, d);
    return {
      ...base,
      design: d,
      // a treatment the design does not carry falls back to the first it does
      treatment: treatment !== null && treatments.includes(treatment) ? treatment : (treatments.includes(base.treatment) ? base.treatment : (treatments[0] ?? base.treatment)),
      model: model !== null && o.ead_models.some((m) => m.model_id === model) ? model : base.model,
      band: band !== null && bandsOf(o).some((b) => b.id === band) ? band : base.band,
    };
  }, [base, o, design, treatment, model, band]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);
  const designs = [...new Set(o.ccf_by_design.rows.map((r) => r.design))];

  const designSection: RailSection = {
    id: 'design',
    label: { en: 'Design', es: 'Diseño' },
    content: (
      <>
        <ChipGroup
          id="c09-design"
          label={{ en: 'Reference-date design', es: 'Diseño de fecha de referencia' }}
          options={designs.map((d) => ({ id: d, label: text(DESIGN_SHORT, d), hint: text(DESIGN_TEXT, d) }))}
          value={sel.design}
          onChange={setDesign}
        />
        <DesignReadout sel={sel} />
      </>
    ),
  };
  const treatmentSection: RailSection = {
    id: 'treatment',
    label: { en: 'Treatment', es: 'Tratamiento' },
    content: (
      <>
        <RailSelect
          id="c09-treatment"
          label={{ en: 'Treatment of CCF outside 0 to 1', es: 'Tratamiento del CCF fuera de 0 a 1' }}
          options={treatmentsOf(o, sel.design).map((t) => ({ id: t, label: text(TREATMENT_TEXT, t) }))}
          value={sel.treatment}
          onChange={setTreatment}
        />
        <TreatmentReadout sel={sel} />
      </>
    ),
  };
  const modelSection: RailSection = {
    id: 'model',
    label: { en: 'Model', es: 'Modelo' },
    content: (
      <>
        <RailSelect id="c09-model" label={{ en: 'EAD model', es: 'Modelo de EAD' }} options={o.ead_models.map((m) => ({ id: m.model_id, label: modelLabel(o, m.model_id) }))} value={sel.model} onChange={setModel} />
        <ModelReadout sel={sel} />
      </>
    ),
  };
  const bandSection: RailSection = {
    id: 'band',
    label: { en: 'Band', es: 'Tramo' },
    content: (
      <>
        <RailSelect id="c09-band" label={{ en: 'Utilisation band', es: 'Tramo de utilización' }} options={bandsOf(o).map((b) => ({ id: b.id, label: bandLabel(b) }))} value={sel.band} onChange={setBand} />
        <BandReadout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const ccf = tabs(
    [
      { id: 'by-design', label: { en: 'By design and tests', es: 'Por diseño y pruebas' }, content: <ByDesignView sel={sel} /> },
      { id: 'distribution', label: { en: 'Distribution', es: 'Distribución' }, content: <DistributionView sel={sel} /> },
    ],
    { en: 'Views of the CCF', es: 'Vistas del CCF' },
    'c09-ccf',
  );
  const ead = tabs(
    [
      { id: 'backtest', label: { en: 'Back-test and tests', es: 'Backtest y pruebas' }, content: <BacktestView sel={sel} /> },
      { id: 'models', label: { en: 'Models', es: 'Modelos' }, content: <ModelsView sel={sel} /> },
      { id: 'floors', label: { en: 'Floor', es: 'Piso' }, content: <FloorsView sel={sel} /> },
    ],
    { en: 'Views of the EAD', es: 'Vistas de la EAD' },
    'c09-ead',
  );
  return {
    sel,
    rail: [designSection, treatmentSection, modelSection, bandSection],
    groups: [
      { id: 'ccf', label: { en: 'CCF', es: 'CCF' }, lane: 'replay', provenance: prov, content: ccf },
      { id: 'ead', label: { en: 'EAD', es: 'EAD' }, lane: 'replay', provenance: prov, content: ead },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C09FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C09VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C09ContextView sel={sel} /> },
    controls: { design: sel.design, treatment: sel.treatment, model: sel.model, band: sel.band },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC09Instrument = useInstrument;
