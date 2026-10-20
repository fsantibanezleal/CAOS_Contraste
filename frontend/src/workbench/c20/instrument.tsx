// The C20 instrument (U14-W): ML model validation, five kinds of variant (SGCD shocks seen and held out, the Federal
// Reserve shift probes, the seed sweep, the perturbation grid and the planted leak). The rail has a section of the focus
// of the kind (the SGCD block and shock, the shift and window, the rung, the noise scale or the screen) and one of the
// labelled fairness battery, each with its control and a live read-out (ADR-0071 rule 6). The groups are the validator's
// questions: does performance, drift and data quality survive shocks the model has and has not seen and shifted
// populations, do noise, retraining seeds and the explainers keep it stable and does the leakage screen catch a leak,
// what the labelled fairness battery and the decisions that flip say, and what the validation found; the variants are
// the Variants view. The tabs of a group are the ones the open kind of variant carries. The workbench calls this hook on
// every case and uses it when the case is C20.
import { ChipGroup, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import {
  C20ContextView, C20FindingsView, C20VariantsView, FairnessReadout, NoiseReadout, ScreenReadout, SeedReadout, ShiftReadout, ShockReadout, WindowReadout,
} from './C20Common';
import { DecisionFlipView, FairnessView } from './FairnessViews';
import { ExplainerView, LeakageView, PerturbationView, SeedsView } from './RobustnessViews';
import { CbpeView, ConformalView, RealDriftView, SyntheticShiftView } from './ShiftViews';
import { DegradationView, DriftView, QualityView } from './ShockViews';
import {
  ATTRIBUTE_TEXT, FAIR_TESTS, SCREEN_TEXT, SHOCK_TEXT, blockRows, defaultSel, outputsOf, text, type Block, type C20Kind, type C20Sel, type Screen,
} from './selection';
import { testName } from './U14Common';

export interface C20Instrument {
  sel: C20Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

type Tab = { id: string; label: BiText; kinds: C20Kind[]; content: (sel: C20Sel) => ReactElement };

const STRESS: Tab[] = [
  { id: 'degradation', label: { en: 'Degradation', es: 'Degradación' }, kinds: ['shock'], content: (s) => <DegradationView sel={s} /> },
  { id: 'drift', label: { en: 'PSI and CSI', es: 'PSI y CSI' }, kinds: ['shock'], content: (s) => <DriftView sel={s} /> },
  { id: 'quality', label: { en: 'Quality and attribution', es: 'Calidad y atribución' }, kinds: ['shock'], content: (s) => <QualityView sel={s} /> },
  { id: 'real', label: { en: 'Real drift', es: 'Deriva real' }, kinds: ['shift'], content: (s) => <RealDriftView sel={s} /> },
  { id: 'synthetic', label: { en: 'Synthetic shift', es: 'Cambio sintético' }, kinds: ['shift'], content: (s) => <SyntheticShiftView sel={s} /> },
  { id: 'conformal', label: { en: 'Conformal coverage', es: 'Cobertura conforme' }, kinds: ['shift'], content: (s) => <ConformalView sel={s} /> },
  { id: 'cbpe', label: { en: 'Label-free estimate', es: 'Estimación sin etiquetas' }, kinds: ['shift'], content: (s) => <CbpeView sel={s} /> },
];
const ROBUST: Tab[] = [
  { id: 'noise', label: { en: 'Noise', es: 'Ruido' }, kinds: ['perturbation'], content: (s) => <PerturbationView sel={s} /> },
  { id: 'seeds', label: { en: 'Seeds', es: 'Semillas' }, kinds: ['seeds'], content: (s) => <SeedsView sel={s} /> },
  { id: 'explainers', label: { en: 'Explainers', es: 'Explicadores' }, kinds: ['seeds'], content: (s) => <ExplainerView sel={s} /> },
  { id: 'leakage', label: { en: 'Leakage', es: 'Fuga' }, kinds: ['leakage'], content: (s) => <LeakageView sel={s} /> },
];

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C20Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [block, setBlock] = useState<string | null>(null);
  const [shock, setShock] = useState<string | null>(null);
  const [shift, setShift] = useState<string | null>(null);
  const [win, setWin] = useState<string | null>(null);
  const [rung, setRung] = useState<string | null>(null);
  const [eps, setEps] = useState<string | null>(null);
  const [screen, setScreen] = useState<string | null>(null);
  const [test, setTest] = useState<string | null>(null);
  const [attribute, setAttribute] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    for (const set of [setBlock, setShock, setShift, setWin, setRung, setEps, setScreen, setTest, setAttribute]) set(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C20Sel | null = useMemo(() => {
    if (!base || !o) return null;
    const rows = o.kind === 'shock' ? blockRows(o, block === 'applied' ? 'applied' : 'shipped') : [];
    const shocks: string[] = rows.map((r) => r.shock_id);
    const shifts = o.kind === 'shift' ? o.synthetic_shift.shifts.map((x) => x.shift_id) : [];
    const wins = o.kind === 'shift' ? o.synthetic_shift.label_free.conformal.coverage_by_window.map((w) => w.window) : [];
    const rungs = o.kind === 'seeds' ? o.rows.map((r) => r.rung) : [];
    const epsRows = o.kind === 'perturbation' ? o.rows.map((r) => String(r.eps)) : [];
    const attrs: string[] = [...new Set((o.fairness_battery?.rows ?? []).map((r) => r.attribute))];
    const tests: string[] = [...new Set((o.fairness_battery?.rows ?? []).map((r) => r.test_id))];
    return {
      ...base,
      block: (block === 'applied' ? 'applied' : 'shipped') as Block,
      shock: shock !== null && shocks.includes(shock) ? shock : shocks.includes(base.shock) ? base.shock : shocks[0] ?? base.shock,
      shift: shift !== null && shifts.includes(shift) ? shift : base.shift,
      window: win !== null && wins.includes(win) ? win : base.window,
      rung: rung !== null && rungs.includes(rung) ? rung : base.rung,
      eps: eps !== null && epsRows.includes(eps) ? epsRows.indexOf(eps) : base.eps,
      screen: (screen !== null && screen in SCREEN_TEXT ? screen : base.screen) as Screen,
      test: test !== null && tests.includes(test) ? test : base.test,
      attribute: attribute !== null && attrs.includes(attribute) ? attribute : base.attribute,
    };
  }, [base, o, block, shock, shift, win, rung, eps, screen, test, attribute]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);

  let focus: RailSection;
  if (o.kind === 'shock') {
    const rows = blockRows(o, sel.block);
    focus = {
      id: 'shock',
      label: { en: 'Shock', es: 'Choque' },
      content: (
        <>
          <ChipGroup
            id="c20-block"
            label={{ en: 'Shocks', es: 'Choques' }}
            options={[
              { id: 'shipped', label: { en: 'As shipped', es: 'Entregados' }, hint: { en: 'The shocks as the dataset ships them.', es: 'Los choques como los entrega el conjunto de datos.' } },
              { id: 'applied', label: { en: 'Contraste-applied', es: 'De Contraste' }, hint: { en: 'Contraste applies each shock family to the structured view itself.', es: 'Contraste aplica cada familia de choques a la vista estructurada misma.' } },
            ]}
            value={sel.block}
            onChange={setBlock}
          />
          {rows.length > 1 && <RailSelect id="c20-shock" label={{ en: 'Shock in focus', es: 'Choque en foco' }} options={rows.map((r) => ({ id: r.shock_id, label: text(SHOCK_TEXT, r.shock_id) }))} value={sel.shock} onChange={setShock} />}
          <ShockReadout sel={sel} />
        </>
      ),
    };
  } else if (o.kind === 'shift') {
    const shifts = o.synthetic_shift.shifts;
    const wins = o.synthetic_shift.label_free.conformal.coverage_by_window;
    focus = {
      id: 'shift',
      label: { en: 'Shift', es: 'Cambio' },
      content: (
        <>
          {shifts.length > 1 && <RailSelect id="c20-shift" label={{ en: 'Synthetic shift', es: 'Cambio sintético' }} options={shifts.map((x) => ({ id: x.shift_id, label: { en: x.shift_id, es: x.shift_id } }))} value={sel.shift} onChange={setShift} />}
          <ShiftReadout sel={sel} />
          {wins.length > 1 && <RailSelect id="c20-window" label={{ en: 'Conformal window', es: 'Ventana conforme' }} options={wins.map((w) => ({ id: w.window, label: { en: w.window, es: w.window } }))} value={sel.window} onChange={setWin} />}
          <WindowReadout sel={sel} />
        </>
      ),
    };
  } else if (o.kind === 'seeds') {
    focus = {
      id: 'rung',
      label: { en: 'Rung', es: 'Peldaño' },
      content: (
        <>
          {o.rows.length > 1 && <RailSelect id="c20-rung" label={{ en: 'Rung in focus', es: 'Peldaño en foco' }} options={o.rows.map((r) => ({ id: r.rung, label: { en: r.rung, es: r.rung } }))} value={sel.rung} onChange={setRung} />}
          <SeedReadout sel={sel} />
        </>
      ),
    };
  } else if (o.kind === 'perturbation') {
    focus = {
      id: 'noise',
      label: { en: 'Noise', es: 'Ruido' },
      content: (
        <>
          {o.rows.length > 1 && <RailSelect id="c20-eps" label={{ en: 'Noise scale', es: 'Escala de ruido' }} options={o.rows.map((r) => ({ id: String(r.eps), label: { en: String(r.eps), es: String(r.eps).replace('.', ',') } }))} value={String(o.rows[sel.eps]?.eps ?? '')} onChange={setEps} />}
          <NoiseReadout sel={sel} />
        </>
      ),
    };
  } else {
    focus = {
      id: 'screen',
      label: { en: 'Screen', es: 'Filtro' },
      content: (
        <>
          <RailSelect id="c20-screen" label={{ en: 'Leakage screen', es: 'Filtro de fuga' }} options={(Object.keys(SCREEN_TEXT) as Screen[]).map((k) => ({ id: k, label: SCREEN_TEXT[k] }))} value={sel.screen} onChange={setScreen} />
          <ScreenReadout sel={sel} />
        </>
      ),
    };
  }
  const battery = o.fairness_battery;
  const fairness: RailSection | null = battery
    ? {
        id: 'fairness',
        label: { en: 'Fairness', es: 'Equidad' },
        content: (
          <>
            <RailSelect id="c20-test" label={{ en: 'Fairness test', es: 'Prueba de equidad' }} options={FAIR_TESTS.map((t) => ({ id: t, label: testName(t) }))} value={sel.test} onChange={setTest} />
            <RailSelect
              id="c20-attribute"
              label={{ en: 'Protected attribute', es: 'Atributo protegido' }}
              options={[...new Set(battery.rows.map((r) => r.attribute))].map((a) => ({ id: a, label: text(ATTRIBUTE_TEXT, a) }))}
              value={sel.attribute}
              onChange={setAttribute}
            />
            <FairnessReadout sel={sel} />
          </>
        ),
      }
    : null;

  const tabs = (list: Tab[], aria: BiText, key: string): ReactElement => {
    const mine = list.filter((t) => t.kinds.includes(o.kind));
    if (mine.length === 0) {
      return (
        <p className="caos-pending" data-state="unavailable" data-group={key}>
          {pick({ en: 'Not available in this variant: pick another variant for these views.', es: 'No disponible en esta variante: elija otra variante para estas vistas.' }, lang)}
        </p>
      );
    }
    return <SubTabs key={`${key}-${o.kind}`} ariaLabel={pick(aria, lang)} tabs={mine.map((t) => ({ id: t.id, label: pick(t.label, lang), content: t.content(sel) }))} />;
  };
  const fairImpact = (
    <SubTabs
      key="c20-fairness"
      ariaLabel={pick({ en: 'Views of the fairness battery and the decisions', es: 'Vistas de la batería de equidad y las decisiones' }, lang)}
      tabs={[
        { id: 'battery', label: pick({ en: 'Fairness battery', es: 'Batería de equidad' }, lang), content: <FairnessView sel={sel} /> },
        { id: 'flips', label: pick({ en: 'Decisions that flip', es: 'Decisiones que cambian' }, lang), content: <DecisionFlipView sel={sel} /> },
      ]}
    />
  );
  return {
    sel,
    rail: fairness ? [focus, fairness] : [focus],
    groups: [
      { id: 'stress', label: { en: 'Shocks and shifts', es: 'Choques y cambios' }, lane: 'replay', provenance: prov, content: tabs(STRESS, { en: 'Views of the shocks and shifts', es: 'Vistas de los choques y cambios' }, 'c20-stress') },
      { id: 'robustness', label: { en: 'Robustness', es: 'Robustez' }, lane: 'replay', provenance: prov, content: tabs(ROBUST, { en: 'Views of the robustness', es: 'Vistas de la robustez' }, 'c20-robust') },
      { id: 'impact', label: { en: 'Fairness and impact', es: 'Equidad e impacto' }, lane: 'replay', provenance: prov, content: fairImpact },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C20FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C20VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C20ContextView sel={sel} /> },
    controls: { kind: o.kind, block: sel.block, shock: sel.shock, shift: sel.shift, window: sel.window, rung: sel.rung, eps: sel.eps, screen: sel.screen, test: sel.test, attribute: sel.attribute },
  };
}

export const useC20Instrument = useInstrument;
