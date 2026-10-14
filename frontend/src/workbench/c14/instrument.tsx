// The C14 instrument (U10-W): IRRBB on a USD balance sheet, one valuation date per variant. The rail is split in four
// sections (Calibration, Deposit assumption, Shock, Deposit category; ADR-0071 rule 6), each with its control and a live
// read-out; the groups are the validator's questions: how large is the loss under each prescribed shock, how much of it
// hangs on the deposit assumptions, what the NII and its dynamics say, and what the validation found, with the valuation
// dates as the Variants view and the Context view. The workbench calls this hook on every case and uses it when the case is C14.
import { ChipGroup, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { C14ContextView, C14FindingsView, C14VariantsView, CalibrationReadout, NmdReadout, SegmentReadout, ShockReadout } from './C14Common';
import { CapsView, ChangesView, ReplicatingView, WithWithoutView } from './BehaviouralViews';
import { DynamicNiiView, EarEvarView, GapView } from './NiiViews';
import { EveByShockView, OutlierView, ShapesView } from './ShockViews';
import {
  CALIBRATION_TEXT, CATEGORY_TEXT, NMD_LONG, NMD_TEXT, SHOCK_ORDER, SHOCK_TEXT, categoriesOf, defaultSel, fitOf, outputsOf, text,
  type C14Sel, type Calibration, type NmdAssumption, type NmdCategory, type ShockId,
} from './selection';

export interface C14Instrument {
  sel: C14Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C14Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [calibration, setCalibration] = useState<string | null>(null);
  const [nmd, setNmd] = useState<string | null>(null);
  const [shock, setShock] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setCalibration(null);
    setNmd(null);
    setShock(null);
    setCategory(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const categories = useMemo(() => (base ? categoriesOf(fitOf(base)) : []), [base]);
  const sel: C14Sel | null = useMemo(() => {
    if (!base || !o) return null;
    const calibrations = [...new Set(o.scenarios.map((s) => s.calibration))];
    return {
      ...base,
      calibration: (calibration !== null && calibrations.includes(calibration as Calibration) ? calibration : base.calibration) as Calibration,
      nmd: (nmd === 'behavioural' || nmd === 'contractual' ? nmd : base.nmd) as NmdAssumption,
      shock: (shock !== null && SHOCK_ORDER.includes(shock as ShockId) ? shock : base.shock) as ShockId,
      category: (category !== null && categories.includes(category as NmdCategory) ? category : base.category) as NmdCategory,
    };
  }, [base, o, calibration, nmd, shock, category, categories]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);
  const calibrations = [...new Set(o.scenarios.map((s) => s.calibration))];

  const calibrationSection: RailSection = {
    id: 'calibration',
    label: { en: 'Calibration', es: 'Calibración' },
    content: (
      <>
        <ChipGroup
          id="c14-calibration"
          label={{ en: 'Calibration of the shock sizes', es: 'Calibración de los tamaños de choque' }}
          options={calibrations.map((c) => ({ id: c, label: { en: c, es: c }, hint: text(CALIBRATION_TEXT, c) }))}
          value={sel.calibration}
          onChange={setCalibration}
        />
        <CalibrationReadout sel={sel} />
      </>
    ),
  };
  const nmdSection: RailSection = {
    id: 'nmd',
    label: { en: 'Deposit assumption', es: 'Supuesto de depósitos' },
    content: (
      <>
        <ChipGroup
          id="c14-nmd"
          label={{ en: 'Non-maturity deposits', es: 'Depósitos sin vencimiento' }}
          options={(['behavioural', 'contractual'] as const).map((k) => ({ id: k, label: text(NMD_TEXT, k), hint: text(NMD_LONG, k) }))}
          value={sel.nmd}
          onChange={setNmd}
        />
        <NmdReadout sel={sel} />
      </>
    ),
  };
  const shockSection: RailSection = {
    id: 'shock',
    label: { en: 'Shock', es: 'Choque' },
    content: (
      <>
        <RailSelect id="c14-shock" label={{ en: 'Prescribed shock', es: 'Choque prescrito' }} options={SHOCK_ORDER.map((s) => ({ id: s, label: text(SHOCK_TEXT, s) }))} value={sel.shock} onChange={setShock} />
        <ShockReadout sel={sel} />
      </>
    ),
  };
  const segmentSection: RailSection = {
    id: 'segment',
    label: { en: 'Deposit category', es: 'Categoría de depósitos' },
    content: (
      <>
        <RailSelect id="c14-segment" label={{ en: 'Deposit category', es: 'Categoría de depósitos' }} options={categories.map((c) => ({ id: c, label: text(CATEGORY_TEXT, c) }))} value={sel.category} onChange={setCategory} />
        <SegmentReadout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const shocks = tabs(
    [
      { id: 'eve', label: { en: 'Delta EVE by shock', es: 'Delta EVE por choque' }, content: <EveByShockView sel={sel} /> },
      { id: 'shapes', label: { en: 'Shock shapes', es: 'Formas de los choques' }, content: <ShapesView sel={sel} /> },
      { id: 'outlier', label: { en: 'Outlier test', es: 'Prueba de valor atípico' }, content: <OutlierView sel={sel} /> },
    ],
    { en: 'Views of the shocks', es: 'Vistas de los choques' },
    'c14-shocks',
  );
  const behaviour = tabs(
    [
      { id: 'with-without', label: { en: 'With and without', es: 'Con y sin' }, content: <WithWithoutView sel={sel} /> },
      { id: 'replicating', label: { en: 'Replicating portfolio', es: 'Cartera replicante' }, content: <ReplicatingView sel={sel} /> },
      { id: 'caps', label: { en: 'Caps', es: 'Topes' }, content: <CapsView sel={sel} /> },
      { id: 'changes', label: { en: 'Parameter changes', es: 'Cambios de parámetros' }, content: <ChangesView sel={sel} /> },
    ],
    { en: 'Views of the deposit behaviour', es: 'Vistas de la conducta de depósitos' },
    'c14-behaviour',
  );
  const nii = tabs(
    [
      { id: 'gap', label: { en: 'Repricing and duration gap', es: 'Brecha de repreciación y duración' }, content: <GapView sel={sel} /> },
      { id: 'dynamic', label: { en: 'Dynamic NII', es: 'NII dinámico' }, content: <DynamicNiiView sel={sel} /> },
      { id: 'ear', label: { en: 'EaR and EVaR', es: 'EaR y EVaR' }, content: <EarEvarView sel={sel} /> },
    ],
    { en: 'Views of the net interest income', es: 'Vistas del margen financiero neto' },
    'c14-nii',
  );
  return {
    sel,
    rail: [calibrationSection, nmdSection, shockSection, segmentSection],
    groups: [
      { id: 'shocks', label: { en: 'Shocks', es: 'Choques' }, lane: 'replay', provenance: prov, content: shocks },
      { id: 'behaviour', label: { en: 'Deposit behaviour', es: 'Conducta de depósitos' }, lane: 'replay', provenance: prov, content: behaviour },
      { id: 'nii', label: { en: 'NII and dynamics', es: 'NII y dinámica' }, lane: 'replay', provenance: prov, content: nii },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C14FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Valuation dates', es: 'Fechas de valoración' }, lane: 'replay', provenance: prov, content: <C14VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C14ContextView sel={sel} /> },
    controls: { calibration: sel.calibration, nmd: sel.nmd, shock: sel.shock, segment: sel.category },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC14Instrument = useInstrument;
