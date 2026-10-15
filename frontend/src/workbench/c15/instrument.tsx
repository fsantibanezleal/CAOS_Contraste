// The C15 instrument (U10-W): IRRBB on a CLP and UF balance sheet under RAN 21-13 Annex 1, one SDD variant per document.
// The rail is split in three sections (Shock, Offset, Leg; ADR-0071 rule 6), each with its control and a live read-out;
// the groups are the validator's questions: how large is the loss on each leg and with or without the 50 percent offset,
// how the indexation risk of a UF book adds to the rate risk, and where the floors bind and whether the bank is
// prioritised, with the variants as the Variants view and the Context view. C15 stays on its fixtures until owner
// prerequisite 7 (the BCCh account) is met. The workbench calls this hook on every case and uses it when the case is C15.
import { ChipGroup, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { C15ContextView, C15FindingsView, C15VariantsView, LegReadout, OffsetReadout, ShockReadout } from './C15Common';
import { FloorsView, ThresholdsView } from './FloorViews';
import { DynamicLegView, EveByLegView, PositionsView } from './LegViews';
import { IndexationView, NiiView } from './RateViews';
import { LEG_SHORT, LEG_TEXT, OFFSET_LONG, OFFSET_TEXT, SHOCK_ORDER, SHOCK_TEXT, defaultSel, outputsOf, text, type C15Sel, type LegId, type OffsetChoice, type ShockId } from './selection';

export interface C15Instrument {
  sel: C15Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C15Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [shock, setShock] = useState<string | null>(null);
  const [offset, setOffset] = useState<string | null>(null);
  const [leg, setLeg] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setShock(null);
    setOffset(null);
    setLeg(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C15Sel | null = useMemo(() => {
    if (!base || !o) return null;
    return {
      ...base,
      shock: (shock !== null && SHOCK_ORDER.includes(shock as ShockId) ? shock : base.shock) as ShockId,
      offset: (offset === 'on' || offset === 'off' ? offset : base.offset) as OffsetChoice,
      leg: (leg === 'CLP' || leg === 'UR' ? leg : base.leg) as LegId,
    };
  }, [base, o, shock, offset, leg]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);

  const shockSection: RailSection = {
    id: 'shock',
    label: { en: 'Shock', es: 'Choque' },
    content: (
      <>
        <RailSelect id="c15-shock" label={{ en: 'Prescribed shock', es: 'Choque prescrito' }} options={SHOCK_ORDER.map((s) => ({ id: s, label: text(SHOCK_TEXT, s) }))} value={sel.shock} onChange={setShock} />
        <ShockReadout sel={sel} />
      </>
    ),
  };
  const offsetSection: RailSection = {
    id: 'offset',
    label: { en: 'Offset', es: 'Compensación' },
    content: (
      <>
        <ChipGroup
          id="c15-offset"
          label={{ en: 'CLP and CLF offset', es: 'Compensación CLP y CLF' }}
          options={(['on', 'off'] as const).map((k) => ({ id: k, label: text(OFFSET_TEXT, k), hint: text(OFFSET_LONG, k) }))}
          value={sel.offset}
          onChange={setOffset}
        />
        <OffsetReadout sel={sel} />
      </>
    ),
  };
  const legSection: RailSection = {
    id: 'leg',
    label: { en: 'Leg', es: 'Tramo' },
    content: (
      <>
        <ChipGroup
          id="c15-leg"
          label={{ en: 'Leg of the book', es: 'Tramo del libro' }}
          options={(['CLP', 'UR'] as const).map((k) => ({ id: k, label: text(LEG_SHORT, k), hint: text(LEG_TEXT, k) }))}
          value={sel.leg}
          onChange={setLeg}
        />
        <LegReadout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const legs = tabs(
    [
      { id: 'eve', label: { en: 'Delta EVE by leg', es: 'Delta EVE por tramo' }, content: <EveByLegView sel={sel} /> },
      { id: 'positions', label: { en: 'Positions', es: 'Posiciones' }, content: <PositionsView sel={sel} /> },
      { id: 'dynamic', label: { en: 'Dynamic NII', es: 'NII dinámico' }, content: <DynamicLegView sel={sel} /> },
    ],
    { en: 'Views of the legs', es: 'Vistas de los tramos' },
    'c15-legs',
  );
  const rate = tabs(
    [
      { id: 'nii', label: { en: 'Delta NII', es: 'Delta NII' }, content: <NiiView sel={sel} /> },
      { id: 'indexation', label: { en: 'Indexation', es: 'Reajustabilidad' }, content: <IndexationView sel={sel} /> },
    ],
    { en: 'Views of the rate and indexation risk', es: 'Vistas del riesgo de tasa y reajustabilidad' },
    'c15-rate',
  );
  const floors = tabs(
    [
      { id: 'floors', label: { en: 'Floors', es: 'Pisos' }, content: <FloorsView sel={sel} /> },
      { id: 'thresholds', label: { en: 'Thresholds', es: 'Umbrales' }, content: <ThresholdsView sel={sel} /> },
    ],
    { en: 'Views of the floors and thresholds', es: 'Vistas de los pisos y umbrales' },
    'c15-floors',
  );
  return {
    sel,
    rail: [shockSection, offsetSection, legSection],
    groups: [
      { id: 'legs', label: { en: 'Legs', es: 'Tramos' }, lane: 'replay', provenance: prov, content: legs },
      { id: 'rate', label: { en: 'Rate and indexation', es: 'Tasa y reajustabilidad' }, lane: 'replay', provenance: prov, content: rate },
      { id: 'floors', label: { en: 'Floors and thresholds', es: 'Pisos y umbrales' }, lane: 'replay', provenance: prov, content: floors },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C15FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C15VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C15ContextView sel={sel} /> },
    controls: { shock: sel.shock, offset: sel.offset, leg: sel.leg },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC15Instrument = useInstrument;
