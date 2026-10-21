// The C21 instrument (U14-W): fair-lending disparity testing on public HMDA decisions, one SDD variant a year pair (fitted
// on year t, confirmed on t+1). Statistical disparity only: every view says "no legal claim" and carries the three legal
// sentences of the research addendum, and no outcome-conditioned test exists because HMDA has no performance outcome.
// The rail has two sections (Attribute, Group; ADR-0071 rule 6), each with its control and a live read-out; the groups are
// the questions: do approval disparities by protected class exist (rates, the four-fifths line labelled an employment
// benchmark, the tests), do they persist after the permitted controls (the decision model and the rate spread), is the
// finding stable from one year to the next (replication and situation testing), and what the validation found, with the
// year pairs as the Variants view. The workbench calls this hook on every case and uses it when the case is C21.
import { SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { AttributeReadout, C21ContextView, C21FindingsView, C21VariantsView, GroupReadout } from './C21Common';
import { ControlledView, RateSpreadView, ReplicationView, SituationView } from './EstimateViews';
import { FourFifthsView, RatesView, TestsView } from './RateViews';
import { FIELD_TEXT, attributeOf, defaultSel, groupBi, outputsOf, text, type C21Sel } from './selection';

export interface C21Instrument {
  sel: C21Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C21Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [field, setField] = useState<string | null>(null);
  const [group, setGroup] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setField(null);
    setGroup(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C21Sel | null = useMemo(() => {
    if (!base || !o) return null;
    const f = field !== null && o.attributes.some((a) => a.field === field) ? field : base.field;
    const a = attributeOf(o, f);
    const groups = a?.contrasts.map((c) => c.group) ?? [];
    return { ...base, field: f, group: group !== null && groups.includes(group) ? group : (groups[0] ?? base.group) };
  }, [base, o, field, group]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);
  const a = attributeOf(o, sel.field);

  const attributeSection: RailSection = {
    id: 'attribute',
    label: { en: 'Attribute', es: 'Atributo' },
    content: (
      <>
        {o.attributes.length > 1 && <RailSelect id="c21-attribute" label={{ en: 'Protected attribute', es: 'Atributo protegido' }} options={o.attributes.map((x) => ({ id: x.field, label: text(FIELD_TEXT, x.field) }))} value={sel.field} onChange={setField} />}
        <AttributeReadout sel={sel} />
      </>
    ),
  };
  const groupSection: RailSection = {
    id: 'group',
    label: { en: 'Group', es: 'Grupo' },
    content: (
      <>
        {/* a choice only when there is one to make (a one-option select changes nothing, gate G9) */}
        {a && a.contrasts.length > 1 && <RailSelect id="c21-group" label={{ en: 'Group against the reference', es: 'Grupo contra la referencia' }} options={a.contrasts.map((c) => ({ id: c.group, label: groupBi(c.group) }))} value={sel.group} onChange={setGroup} />}
        <GroupReadout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const rates = tabs(
    [
      { id: 'rates', label: { en: 'Rates by group', es: 'Tasas por grupo' }, content: <RatesView sel={sel} /> },
      { id: 'four-fifths', label: { en: 'Four-fifths line', es: 'Línea de cuatro quintos' }, content: <FourFifthsView sel={sel} /> },
      { id: 'tests', label: { en: 'Tests on the rates', es: 'Pruebas sobre las tasas' }, content: <TestsView sel={sel} /> },
    ],
    { en: 'Views of the approval rates', es: 'Vistas de las tasas de aprobación' },
    'c21-rates',
  );
  const controlled = tabs(
    [
      { id: 'controlled', label: { en: 'Approval after controls', es: 'Aprobación con controles' }, content: <ControlledView sel={sel} /> },
      { id: 'rate-spread', label: { en: 'Rate spread', es: 'Diferencial de tasa' }, content: <RateSpreadView sel={sel} /> },
    ],
    { en: 'Views of the controlled disparity', es: 'Vistas de la disparidad controlada' },
    'c21-controlled',
  );
  const replication = tabs(
    [
      { id: 'replication', label: { en: 'Next year', es: 'Año siguiente' }, content: <ReplicationView sel={sel} /> },
      { id: 'situation', label: { en: 'Situation testing', es: 'Pruebas de situación' }, content: <SituationView sel={sel} /> },
    ],
    { en: 'Views of the stability of the finding', es: 'Vistas de la estabilidad del hallazgo' },
    'c21-replication',
  );
  return {
    sel,
    rail: [attributeSection, groupSection],
    groups: [
      { id: 'rates', label: { en: 'Rates', es: 'Tasas' }, lane: 'replay', provenance: prov, content: rates },
      { id: 'controlled', label: { en: 'After the controls', es: 'Con controles' }, lane: 'replay', provenance: prov, content: controlled },
      { id: 'replication', label: { en: 'Stability', es: 'Estabilidad' }, lane: 'replay', provenance: prov, content: replication },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C21FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Year pairs', es: 'Pares de años' }, lane: 'replay', provenance: prov, content: <C21VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C21ContextView sel={sel} /> },
    controls: { attribute: sel.field, group: sel.group },
  };
}

export const useC21Instrument = useInstrument;
