// The C16 instrument (U11-W): the LCR and the liquidity stress models against the deposit run of March 2023. A scenario
// variant with a daily path has three rail sections (Day, Realised run, Table A.1 row), the LCR variant swaps the Day for
// the Deposit mapping, and the reverse-stress document has two (Base scenario, Multiplier), each with its control and a
// live read-out (ADR-0071 rule 6). The groups are the validator's questions: how many days would the bank have survived and
// where is the run against what each model assumed (Survival), what was the buffer and what did the HTM loss take from it
// (Buffer and LCR), how much does the survival period move (Sensitivities), what multiplier breaks a 30-day survival
// (Reverse stress), and what the tests and the findings say, with the variants as the Variants view and the Context view.
// The workbench calls this hook on every case and uses it when the case is C16.
import { ChipGroup, Knob, SubTabs, formatNumber, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { BaseReadout, C16ContextView, C16FindingsView, C16TestsView, C16VariantsView, DayReadout, DenominatorReadout, MappingReadout, PointReadout, RowReadout } from './C16Common';
import { CbcStackView, LadderView, RunSpeedsView, RunoffView } from './LadderViews';
import { CbcView, HtmView, LcrView, TimeBlockView } from './BufferViews';
import { HtmLossView, ReverseBasesView, ReverseCurveView, UninsuredShareView } from './SensitivityViews';
import {
  BASE_ORDER, BASE_TEXT, DENOMINATORS, DENOMINATOR_LONG, DENOMINATOR_SHORT, LCR_CATEGORY_TEXT, baseOf, dayRange, defaultSel, outputsOf, reverseOf, text,
  type A1RowId, type BaseId, type C16Sel, type DenominatorId,
} from './selection';

export interface C16Instrument {
  sel: C16Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

const A1_ORDER: A1RowId[] = ['svb-2023', 'first-republic-2023', 'svb-uk-2023', 'credit-suisse-2023', 'signature-2023', 'icesave-2008', 'northern-rock-2007', 'wamu-2008', 'indymac-2008'];

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C16Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [day, setDay] = useState<number | null>(null);
  const [denominator, setDenominator] = useState<string | null>(null);
  const [row, setRow] = useState<string | null>(null);
  const [mapping, setMapping] = useState<string | null>(null);
  const [baseId, setBaseId] = useState<string | null>(null);
  const [point, setPoint] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setDay(null);
    setDenominator(null);
    setRow(null);
    setMapping(null);
    setBaseId(null);
    setPoint(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const r = base ? reverseOf(base) : null;
  const range = dayRange(o);
  const sel: C16Sel | null = useMemo(() => {
    if (!base) return null;
    const reverseBase = (baseId !== null && r?.bases.some((b) => b.base_id === baseId) ? baseId : base.base) as BaseId;
    const curve = baseOf(r, reverseBase)?.curve ?? [];
    return {
      ...base,
      day: day !== null && range && day >= range.min && day <= range.max ? day : base.day,
      denominator: (denominator !== null && DENOMINATORS.includes(denominator as DenominatorId) ? denominator : base.denominator) as DenominatorId,
      row: (row !== null && A1_ORDER.includes(row as A1RowId) ? row : base.row) as A1RowId,
      mapping: mapping !== null && o?.lcr?.mapping_sensitivity.some((m) => m.mapping_id === mapping) ? mapping : base.mapping,
      base: reverseBase,
      point: point !== null && Number(point) >= 0 && Number(point) < curve.length ? Number(point) : 0,
    };
  }, [base, o, r, range, day, denominator, row, mapping, baseId, point]);
  if (!sel || !data || (!o && !r)) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const group = (id: string, label: BiText, content: ReactElement) => ({ id, label, lane: 'replay' as const, provenance: prov, content });
  const testsGroup = group(
    'tests',
    { en: 'Tests and findings', es: 'Pruebas y hallazgos' },
    tabs(
      [
        { id: 'tests', label: { en: 'Tests', es: 'Pruebas' }, content: <C16TestsView sel={sel} /> },
        { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, content: <C16FindingsView sel={sel} /> },
      ],
      { en: 'Views of the tests and findings', es: 'Vistas de las pruebas y hallazgos' },
      'c16-tests',
    ),
  );
  const compare = { label: { en: 'Variants', es: 'Variantes' } as BiText, lane: 'replay' as const, provenance: prov, content: <C16VariantsView sel={sel} onPick={onPick} /> };
  const context = { content: <C16ContextView sel={sel} /> };

  const runSection: RailSection = {
    id: 'run',
    label: { en: 'Run', es: 'Corrida' },
    content: (
      <>
        <ChipGroup
          id="c16-denominator"
          label={{ en: 'Denominator of the run', es: 'Denominador de la corrida' }}
          options={DENOMINATORS.map((d) => ({ id: d, label: text(DENOMINATOR_SHORT, d), hint: text(DENOMINATOR_LONG, d) }))}
          value={sel.denominator}
          onChange={setDenominator}
        />
        <DenominatorReadout sel={sel} />
      </>
    ),
  };
  const rowSection: RailSection = {
    id: 'row',
    label: { en: 'Row', es: 'Fila' },
    content: (
      <>
        <RailSelect
          id="c16-row"
          label={{ en: 'Row of BCBS Table A.1', es: 'Fila de la Tabla A.1 del BCBS' }}
          options={(o?.scoring.table_a1_scoring ?? []).map((a) => ({ id: a.row_id, label: { en: `${a.bank} ${a.year}`, es: `${a.bank} ${a.year}` } }))}
          value={sel.row}
          onChange={setRow}
        />
        <RowReadout sel={sel} />
      </>
    ),
  };

  if (r) {
    const b = baseOf(r, sel.base) ?? r.bases[0];
    const baseSection: RailSection = {
      id: 'base',
      label: { en: 'Base', es: 'Base' },
      content: (
        <>
          <RailSelect
            id="c16-base"
            label={{ en: 'Base scenario of the stress', es: 'Escenario base del estrés' }}
            options={BASE_ORDER.map((id) => ({ id, label: text(BASE_TEXT, id) }))}
            value={sel.base}
            onChange={setBaseId}
          />
          <BaseReadout sel={sel} />
        </>
      ),
    };
    const pointSection: RailSection = {
      id: 'point',
      label: { en: 'Multiplier', es: 'Multiplicador' },
      content: (
        <>
          <RailSelect
            id="c16-point"
            label={{ en: 'Point of the curve', es: 'Punto de la curva' }}
            options={b.curve.map((p, i) => ({ id: String(i), label: { en: formatNumber(p.multiplier, 'en', { digits: 4 }), es: formatNumber(p.multiplier, 'es', { digits: 4 }) } }))}
            value={String(sel.point)}
            onChange={setPoint}
          />
          <PointReadout sel={sel} />
        </>
      ),
    };
    return {
      sel,
      rail: [baseSection, pointSection],
      groups: [
        group(
          'reverse',
          { en: 'Reverse stress', es: 'Estrés inverso' },
          tabs(
            [
              { id: 'curve', label: { en: 'Curve', es: 'Curva' }, content: <ReverseCurveView sel={sel} /> },
              { id: 'bases', label: { en: 'Solved multipliers', es: 'Multiplicadores resueltos' }, content: <ReverseBasesView sel={sel} /> },
            ],
            { en: 'Views of the reverse stress', es: 'Vistas del estrés inverso' },
            'c16-reverse',
          ),
        ),
        testsGroup,
      ],
      compare,
      context,
      controls: { base: sel.base, point: sel.point },
    };
  }

  const lead: RailSection =
    o?.path && range
      ? {
          id: 'day',
          label: { en: 'Day', es: 'Día' },
          content: (
            <>
              <Knob
                id="c16-day"
                label={{ en: 'Day of the ladder', es: 'Día de la escalera' }}
                value={sel.day}
                min={range.min}
                max={range.max}
                step={1}
                unit={{ en: 'd', es: 'd' }}
                hint={{ en: 'The day of the ladder, in days, that the read-out and the marked line show.', es: 'El día de la escalera que muestran la lectura y la línea marcada.' }}
                format={{ decimals: 0 }}
                onChange={setDay}
              />
              <DayReadout sel={sel} />
            </>
          ),
        }
      : {
          id: 'mapping',
          label: { en: 'Mapping', es: 'Mapeo' },
          content: (
            <>
              <RailSelect
                id="c16-mapping"
                label={{ en: 'Mapping of the uninsured balance', es: 'Mapeo del saldo no asegurado' }}
                options={(o?.lcr?.mapping_sensitivity ?? []).map((m) => ({ id: m.mapping_id, label: text(LCR_CATEGORY_TEXT, m.lcr_category) }))}
                value={sel.mapping}
                onChange={setMapping}
              />
              <MappingReadout sel={sel} />
            </>
          ),
        };

  return {
    sel,
    rail: [lead, runSection, rowSection],
    groups: [
      group(
        'survival',
        { en: 'Survival', es: 'Supervivencia' },
        tabs(
          [
            { id: 'ladder', label: { en: 'Survival ladder', es: 'Escalera' }, content: <LadderView sel={sel} /> },
            { id: 'stack', label: { en: 'CBC stack', es: 'CBC apilado' }, content: <CbcStackView sel={sel} /> },
            { id: 'runoff', label: { en: 'Run-off and the run', es: 'Salidas y corrida' }, content: <RunoffView sel={sel} /> },
            { id: 'speeds', label: { en: 'Run speeds', es: 'Velocidades' }, content: <RunSpeedsView sel={sel} /> },
          ],
          { en: 'Views of the survival period', es: 'Vistas del periodo de supervivencia' },
          'c16-survival',
        ),
      ),
      group(
        'buffer',
        { en: 'Buffer and LCR', es: 'Colchón y LCR' },
        tabs(
          [
            { id: 'cbc', label: { en: 'CBC', es: 'CBC' }, content: <CbcView sel={sel} /> },
            { id: 'htm', label: { en: 'HTM loss', es: 'Pérdida HTM' }, content: <HtmView sel={sel} /> },
            { id: 'lcr', label: { en: 'LCR', es: 'LCR' }, content: <LcrView sel={sel} /> },
            { id: 'time', label: { en: 'Time block', es: 'Bloque temporal' }, content: <TimeBlockView sel={sel} /> },
          ],
          { en: 'Views of the buffer and the LCR', es: 'Vistas del colchón y el LCR' },
          'c16-buffer',
        ),
      ),
      group(
        'sensitivity',
        { en: 'Sensitivities', es: 'Sensibilidades' },
        tabs(
          [
            { id: 'share', label: { en: 'Uninsured share', es: 'Parte no asegurada' }, content: <UninsuredShareView sel={sel} /> },
            { id: 'htm-loss', label: { en: 'HTM loss', es: 'Pérdida HTM' }, content: <HtmLossView sel={sel} /> },
          ],
          { en: 'Views of the sensitivities', es: 'Vistas de las sensibilidades' },
          'c16-sensitivity',
        ),
      ),
      testsGroup,
    ],
    compare,
    context,
    controls: { day: sel.day, denominator: sel.denominator, row: sel.row, mapping: sel.mapping },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC16Instrument = useInstrument;
