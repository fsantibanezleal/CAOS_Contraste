// The C02 instrument (U14-W): corporate PD across 1 to 5 year horizons, one SDD variant a horizon file and the pooled one.
// The rail is split in two sections (Rung, Challenger; ADR-0071 rule 6), each with its control and a live read-out; the
// groups are the validator's questions: how well does each rung discriminate and stay calibrated and do the learned rungs
// beat the scorecard by a margin a paired test supports, what the exploratory transfer between horizons and the term
// structure of the five event rates say, what the horizon PDs do to the ECL (exploratory), and what the validation found,
// with the discrimination by horizon as the Variants view and the Context view. The workbench calls this hook on every
// case and uses it when the case is C02.
import { SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { C02ContextView, C02FindingsView, C02VariantsView, ChallengerReadout, RungReadout } from './C02Common';
import { CalibrationView, RocCapView, RungsView, StabilityView } from './DiscriminationViews';
import { EclImpactView, TermStructureView, TransferView } from './HorizonViews';
import { defaultSel, outputsOf, rungName, type C02Sel } from './selection';

export interface C02Instrument {
  sel: C02Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C02Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [rung, setRung] = useState<string | null>(null);
  const [challenger, setChallenger] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setRung(null);
    setChallenger(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C02Sel | null = useMemo(() => {
    if (!base || !o) return null;
    const ids = o.rungs.map((r) => r.model_id);
    const challengers = o.challenger.map((c) => c.challenger);
    return {
      ...base,
      rung: rung !== null && ids.includes(rung) ? rung : base.rung,
      challenger: challenger !== null && challengers.includes(challenger) ? challenger : base.challenger,
    };
  }, [base, o, rung, challenger]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);

  const rungSection: RailSection = {
    id: 'rung',
    label: { en: 'Rung', es: 'Peldaño' },
    content: (
      <>
        <RailSelect id="c02-rung" label={{ en: 'Rung in focus', es: 'Peldaño en foco' }} options={o.rungs.map((r) => ({ id: r.model_id, label: rungName(sel, r.model_id) }))} value={sel.rung} onChange={setRung} />
        <RungReadout sel={sel} />
      </>
    ),
  };
  const challengerSection: RailSection = {
    id: 'challenger',
    label: { en: 'Challenger', es: 'Retador' },
    content: (
      <>
        {/* a choice only when there is one to make: one challenger is a control that changes nothing (gate G9) */}
        {o.challenger.length > 1 && (
          <RailSelect id="c02-challenger" label={{ en: 'Challenger against the champion', es: 'Retador contra el campeón' }} options={o.challenger.map((c) => ({ id: c.challenger, label: rungName(sel, c.challenger) }))} value={sel.challenger} onChange={setChallenger} />
        )}
        <ChallengerReadout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const validation = tabs(
    [
      { id: 'roc', label: { en: 'ROC and CAP', es: 'ROC y CAP' }, content: <RocCapView sel={sel} /> },
      { id: 'rungs', label: { en: 'Rungs compared', es: 'Peldaños comparados' }, content: <RungsView sel={sel} /> },
      { id: 'calibration', label: { en: 'Calibration', es: 'Calibración' }, content: <CalibrationView sel={sel} /> },
      { id: 'overfit', label: { en: 'Overfit and stability', es: 'Sobreajuste y estabilidad' }, content: <StabilityView sel={sel} /> },
    ],
    { en: 'Views of the validation', es: 'Vistas de la validación' },
    'c02-validation',
  );
  const horizons = tabs(
    [
      { id: 'transfer', label: { en: 'Transfer', es: 'Transferencia' }, content: <TransferView sel={sel} /> },
      { id: 'term', label: { en: 'Term structure', es: 'Estructura de plazos' }, content: <TermStructureView sel={sel} /> },
    ],
    { en: 'Exploratory views across horizons', es: 'Vistas exploratorias entre horizontes' },
    'c02-horizons',
  );
  return {
    sel,
    rail: [rungSection, challengerSection],
    groups: [
      { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'replay', provenance: prov, content: validation },
      { id: 'horizons', label: { en: 'Exploratory horizons', es: 'Horizontes exploratorios' }, lane: 'replay', provenance: prov, content: horizons },
      { id: 'impact', label: { en: 'Impact', es: 'Impacto' }, lane: 'replay', provenance: prov, content: <EclImpactView sel={sel} /> },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C02FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'By horizon', es: 'Por horizonte' }, lane: 'replay', provenance: prov, content: <C02VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C02ContextView sel={sel} /> },
    controls: { rung: sel.rung, challenger: sel.challenger },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC02Instrument = useInstrument;
