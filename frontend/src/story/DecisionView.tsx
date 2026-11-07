// V6, comparison and decision: the models of the ladder on the same axis and the same days. Each row is a model's exception rate
// with its 95% Wilson interval against the tail level the VaR promises, its eligibility (the gates it fails), whether the model
// confidence set keeps it, the p-value of its expected-shortfall back-test, and the champion marked with its reason. A window
// that has no champion says why in the document's own words. Selecting a row selects the model in the panel and back. A model that
// forecasts no ES never entered the set's comparison: it is "not ranked", never "out". The rows ease to their new rates when the
// window changes; a hidden table holds the rows for a screen reader.
import { formatNumber, useLinkedView, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo, type KeyboardEvent } from 'react';
import { Legend, SrTable, fit, int, lin, pct, useEasedSeries, type Size } from './chart';
import type { Decision, DecisionRow } from './model';
import type { Lang } from './text';

export const decisionOrder = (d: Decision): DecisionRow[] => [...d.rows].sort((a, b) => a.rate - b.rate || a.label.en.localeCompare(b.label.en));

export function decisionGeometry(size: Size, d: Decision, alpha: number) {
  const narrow = size.width < 560;
  const rows = decisionOrder(d);
  const nameW = narrow ? 128 : Math.min(300, size.width * 0.33);
  const colW = narrow ? 74 : 168;
  const l = nameW + 6;
  const r = size.width - colW - 8;
  const top = narrow ? 34 : 44;
  const bottom = size.height - (narrow ? 44 : 50);
  const pitch = (bottom - top) / Math.max(1, rows.length);
  const xMax = Math.max(alpha * 3, ...rows.map((q) => q.hi)) * 1.05;
  const x = lin(0, xMax, l, r);
  return { narrow, rows, nameW, colW, l, r, top, bottom, pitch, xMax, x, rowY: (i: number) => top + i * pitch + pitch / 2 };
}

/** The words of a model's place in the confidence set; a mark on a phone, where the column is narrow. */
export function setWords(state: DecisionRow['setState'], lang: Lang, narrow = false): string {
  const tx = (en: string, es: string) => (lang === 'es' ? es : en);
  if (state == null) return '·';
  if (narrow) return state === 'in' ? tx('in', 'sí') : state === 'out' ? tx('out', 'no') : '–';
  return state === 'in' ? tx('in set', 'dentro') : state === 'out' ? tx('out', 'fuera') : tx('not ranked (no ES)', 'sin ranking (sin ES)');
}

export function DecisionView({
  size,
  d,
  alpha,
  selected,
  onSelect,
}: {
  size: Size;
  d: Decision;
  alpha: number;
  selected: string;
  onSelect: (id: string) => void;
}) {
  const lang = useShellLang() as Lang;
  const select = useLinkedView((s) => s.select);
  const tx = (en: string, es: string) => (lang === 'es' ? es : en);
  const g = decisionGeometry(size, d, alpha);
  const { narrow, rows, nameW, l, r, top, bottom, pitch, x, rowY } = g;
  const fs = narrow ? 9.5 : 12;
  // the rate and its interval ease to the next window's, so a change of window moves the dots and the bars
  const rate = useEasedSeries(useMemo(() => rows.map((q) => q.rate), [rows]));
  const lo = useEasedSeries(useMemo(() => rows.map((q) => q.lo), [rows]));
  const hi = useEasedSeries(useMemo(() => rows.map((q) => q.hi), [rows]));
  const pick = (id: string) => {
    select(`model:${id}`, 'scene');
    onSelect(id);
  };
  const keyOf = (id: string) => (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      pick(id);
    }
  };
  // a phone shows the promised level and the double of it: a 3 % tick next to the "Gates" header ran into it
  const ticks = [0, alpha, alpha * 2, alpha * 3].filter((v, i, a) => a.indexOf(v) === i && v <= g.xMax && (!narrow || v < alpha * 3));
  const champRow = rows.find((q) => q.id === d.champion);
  const table = useMemo(
    () => (
      <SrTable
        id="decision"
        caption={tx('The models of the ladder: exception rate with its 95% interval, gates, confidence set and expected-shortfall back-test', 'Los modelos de la escalera: tasa de excepciones con su intervalo de 95 %, compuertas, conjunto de confianza y prueba retrospectiva de la pérdida esperada')}
        head={[tx('Model', 'Modelo'), tx('Exceptions', 'Excepciones'), tx('Rate', 'Tasa'), tx('Interval low', 'Intervalo, inferior'), tx('Interval high', 'Intervalo, superior'), tx('Gates failed', 'Compuertas fallidas'), tx('Confidence set', 'Conjunto de confianza'), tx('ES back-test p-value', 'Valor p de la prueba de ES')]}
        rows={rows.map((q) => [q.label[lang], int(q.exceptions, lang), pct(q.rate, lang), pct(q.lo, lang), pct(q.hi, lang), int(q.failedGates.length, lang), setWords(q.setState, lang), q.esP == null ? tx('n/a', 'n/d') : formatNumber(q.esP, lang, { decimals: 3 })])}
      />
    ),
    [rows, lang], // eslint-disable-line react-hooks/exhaustive-deps
  );
  return (
    <div className="story-view" data-view="decision">
      <svg width={size.width} height={Math.max(40, size.height)} viewBox={`0 0 ${size.width} ${Math.max(40, size.height)}`} role="group" aria-label={tx('The models of the ladder on one axis: exception rate with its interval, gates, confidence set and expected-shortfall back-test', 'Los modelos de la escalera en un eje: tasa de excepciones con su intervalo, compuertas, conjunto de confianza y prueba retrospectiva de la pérdida esperada')} data-decision="">
        {!narrow && (
          <text x={l} y={top - 22} fill="var(--color-fg-subtle)" fontSize={11}>
            {tx('Exception rate, with 95% interval', 'Tasa de excepciones, con intervalo de 95 %')}
          </text>
        )}
        {ticks.map((v) => (
          <g key={v}>
            <line x1={x(v)} x2={x(v)} y1={top - 6} y2={bottom} stroke={v === alpha ? 'var(--color-accent)' : 'var(--color-border)'} strokeWidth={v === alpha ? 1.8 : 1} strokeDasharray={v === alpha ? '5 3' : undefined} />
            <text x={x(v)} y={bottom + 14} textAnchor="middle" fill={v === alpha ? 'var(--color-accent)' : 'var(--color-fg-subtle)'} fontSize={narrow ? 9 : 11} fontWeight={v === alpha ? 700 : 400}>
              {pct(v, lang, v < 0.01 ? 1 : 0)}
            </text>
          </g>
        ))}
        <text x={x(alpha) + 4} y={top - 8} fill="var(--color-accent)" fontSize={narrow ? 8.5 : 10.5} fontWeight={650}>
          {tx(`promised ${pct(alpha, lang, 0)}`, `prometido ${pct(alpha, lang, 0)}`)}
        </text>
        <text x={r + 10} y={top - 22} fill="var(--color-fg-subtle)" fontSize={narrow ? 8.5 : 10.5}>
          {narrow ? tx('Gates · set', 'Compuertas · conj.') : tx('Gates · set · ES p-value', 'Compuertas · conjunto · p de ES')}
        </text>
        {rows.map((q, i) => {
          const y = rowY(i);
          const on = q.id === selected;
          const champion = q.id === d.champion;
          const rowRate = rate[i] ?? q.rate;
          const rowLo = lo[i] ?? q.lo;
          const rowHi = hi[i] ?? q.hi;
          return (
            <g key={q.id} role="button" tabIndex={0} aria-pressed={on} aria-label={`${q.label[lang]}: ${int(q.exceptions, lang)} ${tx('exceptions', 'excepciones')}`} data-linked-id={`model:${q.id}`} data-linked-view="scene" data-linked-selected={on ? 'true' : 'false'} onClick={() => pick(q.id)} onKeyDown={keyOf(q.id)} style={{ cursor: 'pointer' }} data-decision-row={q.id}>
              <rect x={2} y={y - pitch / 2 + 1} width={size.width - 4} height={pitch - 2} rx={5} fill={on ? 'var(--color-accent-soft)' : 'transparent'} stroke={on ? 'var(--color-accent)' : 'none'} strokeWidth={1.5} />
              <text x={8} y={y + 4} fill="var(--color-fg)" fontSize={fs} fontWeight={on || champion ? 700 : 400}>
                {champion ? '★ ' : ''}
                {fit(q.label[lang], Math.floor((nameW - 8) / (fs * 0.5)))}
              </text>
              <line x1={x(rowLo)} x2={x(rowHi)} y1={y} y2={y} stroke={q.eligible ? 'var(--color-accent)' : 'var(--color-fg-subtle)'} strokeWidth={2} />
              <circle cx={x(rowRate)} cy={y} r={on ? 5.5 : 4.5} fill={q.eligible ? 'var(--color-accent)' : 'var(--color-bg)'} stroke={q.eligible ? 'var(--color-accent)' : 'var(--color-fg-subtle)'} strokeWidth={2} data-eligible={q.eligible ? 'true' : 'false'} />
              <text x={r + 10} y={y + 4} fill={q.eligible ? 'var(--color-good)' : 'var(--color-bad)'} fontSize={narrow ? 9 : 11.5} fontWeight={650}>
                {q.eligible ? tx('pass', 'pasa') : tx(`fails ${int(q.failedGates.length, lang)}`, `falla ${int(q.failedGates.length, lang)}`)}
              </text>
              {narrow ? (
                <text x={r + 10 + 44} y={y + 4} fill="var(--color-fg-subtle)" fontSize={9.5} fontFamily="var(--font-mono)" data-set-state={q.setState ?? 'none'}>
                  {setWords(q.setState, lang, true)}
                </text>
              ) : (
                <text x={r + 10 + 64} y={y + 4} fill="var(--color-fg-subtle)" fontSize={11} fontFamily="var(--font-mono)" data-set-state={q.setState ?? 'none'}>
                  {setWords(q.setState, lang)}
                  {'  '}
                  {q.esP == null ? tx('n/a', 'n/d') : formatNumber(q.esP, lang, { decimals: 3 })}
                </text>
              )}
            </g>
          );
        })}
        {champRow ? null : (
          <text x={8} y={bottom + 34} fill="var(--color-fg)" fontSize={narrow ? 9 : 11.5} fontWeight={650} data-no-champion="">
            {tx('No champion at this level', 'Sin campeón en este nivel')}
          </text>
        )}
        {narrow && (
          <Legend
            items={[
              { kind: 'line', color: 'var(--color-accent)', label: tx('passes gates', 'pasa') },
              { kind: 'line', color: 'var(--color-fg-subtle)', label: tx('fails', 'falla') },
            ]}
            x={Math.max(l, size.width - 170)}
            y={bottom + 34}
            maxWidth={170}
            fontSize={9}
          />
        )}
      </svg>
      {table}
    </div>
  );
}
