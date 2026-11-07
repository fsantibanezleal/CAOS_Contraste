// V4, state and dynamics: the losses and the VaR forecasts through the window. The VaR and the ES of the selected model by day,
// the range the ladder's VaR spans as the uncertainty band, the days the VaR was exceeded marked, the stretch the Basel light
// stood in amber or red and the end of the evaluation. The realised loss is drawn where the document commits it; where its
// licence class withholds it (derived results only) the exceedance days the document lists are marked on the VaR and the view says so.
import { useLinkedView, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo, type KeyboardEvent, type PointerEvent } from 'react';
import { DayScrubber, Swatch, bandPath, cursorMarker, dayLabel, int, lin, linePath, monthLabel, pct, pointerX, tickIndices, type Size } from './chart';
import { stressSpan, varEnvelope, zoneOf, type WindowModel } from './model';
import { type Lang } from './text';

export function crisisGeometry(size: Size, w: WindowModel, modelId: string) {
  const narrow = size.width < 560;
  const l = narrow ? 40 : 54;
  const r = size.width - (narrow ? 8 : 16);
  const t = narrow ? 26 : 34;
  const b = size.height - 40 - (narrow ? 28 : 46);
  const m = w.models.find((q) => q.id === modelId) ?? w.models[0]!;
  const env = varEnvelope(w.models, w.n);
  // the axis follows the selected model and the 90th percentile of the ladder's highest VaR: one model's single wild day (a committed
  // fact of the ladder) must not flatten the rest, so the band is clipped at the axis and the view says so
  const highs = env.hi.filter(Number.isFinite).sort((a, b) => a - b);
  const p90 = highs.length ? highs[Math.floor(0.9 * (highs.length - 1))]! : 0;
  const top = Math.max(...m.var, ...m.es.map((v) => v ?? 0), p90, ...(w.loss ?? [0])) * 1.1;
  const clipped = Math.max(0, ...highs) > top;
  const x = lin(0, Math.max(1, w.n - 1), l, r);
  const y = lin(0, top || 0.05, b, t);
  return { narrow, l, r, t, b, top, x, y, m, env, clipped };
}

export function CrisisView({
  size,
  w,
  modelId,
  cursor,
  onCursor,
}: {
  size: Size;
  w: WindowModel;
  modelId: string;
  cursor: number;
  onCursor: (i: number) => void;
}) {
  const lang = useShellLang() as Lang;
  const scrub = useLinkedView((s) => s.scrub);
  const tx = (en: string, es: string) => (lang === 'es' ? es : en);
  const g = crisisGeometry(size, w, modelId);
  const { narrow, l, r, t, b, x, y, m, env } = g;
  const paths = useMemo(
    () => ({
      band: bandPath(env.lo, env.hi, x, y),
      var: linePath(m.var, x, y),
      es: m.es.some((v) => v != null) ? linePath(m.es, x, y) : '',
      loss: w.loss ? linePath(w.loss, x, y) : '',
    }),
    [w, m, size.width, size.height], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const span = stressSpan(m, w.cuts);
  const hasEs = m.es.some((v) => v != null);
  const move = (e: PointerEvent<SVGRectElement>) => {
    const i = Math.max(0, Math.min(w.n - 1, Math.round(((pointerX(e) - l) / Math.max(1, r - l)) * (w.n - 1))));
    scrub(i);
    onCursor(i);
  };
  const key = (e: KeyboardEvent<SVGSVGElement>) => {
    const step = e.shiftKey ? 10 : 1;
    const to = e.key === 'ArrowLeft' ? cursor - step : e.key === 'ArrowRight' ? cursor + step : null;
    if (to == null) return;
    e.preventDefault();
    e.stopPropagation();
    const i = Math.max(0, Math.min(w.n - 1, to));
    scrub(i);
    onCursor(i);
  };
  const cx = x(cursor);
  const marks = m.exceedances.map((d) => ({ d, v: w.loss ? w.loss[d]! : m.var[d]! }));
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((k) => k * g.top);
  return (
    <div className="story-view" data-view="crisis">
      <svg width={size.width} height={Math.max(40, size.height - 40)} viewBox={`0 0 ${size.width} ${Math.max(40, size.height - 40)}`} role="group" tabIndex={0} onKeyDown={key} aria-label={tx('Value at risk and expected shortfall by day, with the days the VaR was exceeded', 'Valor en riesgo y pérdida esperada por día, con los días en que se excedió el VaR')} data-crisis="">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={l} x2={r} y1={y(v)} y2={y(v)} stroke="var(--color-border)" strokeOpacity={0.6} />
            <text x={l - 6} y={y(v) + 4} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
              {pct(v, lang, v >= 0.1 ? 0 : 1)}
            </text>
          </g>
        ))}
        {span && (
          <g data-stress-span="">
            <rect x={x(span[0])} y={t} width={Math.max(2, x(span[1]) - x(span[0]))} height={b - t} fill="var(--color-bad)" fillOpacity={0.08} />
            <text x={x(span[0]) + 4} y={t + 12} fill="var(--color-fg)" fontSize={narrow ? 8.5 : 10.5} fontWeight={650}>
              {tx('amber or red zone', 'zona ámbar o roja')}
            </text>
          </g>
        )}
        <clipPath id="story-crisis-clip">
          <rect x={l} y={t} width={Math.max(0, r - l)} height={Math.max(0, b - t)} />
        </clipPath>
        <path d={paths.band} fill="var(--color-accent)" fillOpacity={0.12} clipPath="url(#story-crisis-clip)" data-envelope="" />
        {paths.loss && <path d={paths.loss} fill="none" stroke="var(--color-fg-faint)" strokeWidth={1} data-realised-loss="" />}
        {paths.es && <path d={paths.es} fill="none" stroke="var(--color-magenta)" strokeWidth={1.6} strokeDasharray="6 4" />}
        <path d={paths.var} fill="none" stroke="var(--color-accent)" strokeWidth={2.2} strokeLinejoin="round" />
        {marks.map(({ d, v }) => (
          <path key={d} transform={`translate(${x(d)},${y(v)})`} d="M0,-5 L5,0 L0,5 L-5,0 Z" fill="var(--color-bad)" stroke="var(--color-bg)" strokeWidth={1} data-exception-day={d} />
        ))}
        <line x1={x(w.n - 1)} x2={x(w.n - 1)} y1={t} y2={b} stroke="var(--color-fg-subtle)" strokeDasharray="2 4" />
        <text x={x(w.n - 1) - 4} y={b - 6} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={narrow ? 8.5 : 10.5}>
          {tx('end of evaluation', 'fin de la evaluación')} · {dayLabel(w.dates[w.n - 1], lang)}
        </text>
        {tickIndices(w.n, narrow ? 3 : 5).map((i) => (
          <text key={i} x={x(i)} y={b + 16} textAnchor={i === 0 ? 'start' : i === w.n - 1 ? 'end' : 'middle'} fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
            {monthLabel(w.dates[i], lang)}
          </text>
        ))}
        <text x={l} y={t - 10} fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
          {tx('Loss, % of portfolio value', 'Pérdida, % del valor de la cartera')}
        </text>
        <rect x={l} y={t} width={Math.max(0, r - l)} height={Math.max(0, b - t)} fill="transparent" onPointerMove={move} data-scrub-area="" />
        <line x1={cx} x2={cx} y1={t} y2={b} stroke="var(--color-fg)" strokeOpacity={0.7} strokeDasharray="3 3" />
        <circle cx={cx} cy={y(m.var[cursor] ?? 0)} r={5} fill="var(--color-accent)" stroke="var(--color-bg)" strokeWidth={2.5} {...cursorMarker(cursor)} />
        {!narrow && (
          <g transform={`translate(${l + 8},${size.height - 40 - 8})`} fontSize={11}>
            <Swatch x={0} y={0} color="var(--color-accent)" label="VaR" />
            {hasEs && <Swatch x={64} y={0} color="var(--color-magenta)" dash="6 4" label="ES" />}
            <rect x={hasEs ? 124 : 70} y={-5} width={14} height={9} fill="var(--color-accent)" fillOpacity={0.12} stroke="var(--color-accent)" strokeOpacity={0.4} />
            <text x={(hasEs ? 124 : 70) + 20} y={4} fill="var(--color-fg-subtle)" fontSize={11}>
              {tx(`range of the ${int(w.models.length, lang)} models`, `rango de los ${int(w.models.length, lang)} modelos`)}
            </text>
            <path transform={`translate(${(hasEs ? 124 : 70) + 190},0)`} d="M0,-5 L5,0 L0,5 L-5,0 Z" fill="var(--color-bad)" />
            <text x={(hasEs ? 124 : 70) + 200} y={4} fill="var(--color-fg-subtle)" fontSize={11}>
              {tx('day the VaR was exceeded', 'día en que se excedió el VaR')}
            </text>
          </g>
        )}
        {g.clipped && (
          <text x={r - 4} y={t + (w.loss === null ? 26 : 12)} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={narrow ? 8.5 : 10.5} data-band-clipped="">
            {tx('Band cut at the axis: one model forecasts far above it', 'Banda cortada en el eje: un modelo pronostica muy por encima')}
          </text>
        )}
        {w.loss === null && (
          <text x={r - 4} y={t + 12} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={narrow ? 8.5 : 10.5} data-loss-withheld="">
            {tx('Realised loss withheld (licence: derived results only)', 'Pérdida realizada retenida (licencia: solo resultados derivados)')}
          </text>
        )}
      </svg>
      <DayScrubber dates={w.dates} index={cursor} onChange={onCursor} />
    </div>
  );
}

/** What the reader reads off the crisis on the shared day: the VaR, the ES, the exceptions of the trailing window and its zone. */
export function crisisReadout(w: WindowModel, modelId: string, cursor: number) {
  const m = w.models.find((q) => q.id === modelId) ?? w.models[0]!;
  const trailing = m.trailing[cursor] ?? 0;
  return {
    date: w.dates[cursor],
    var: m.var[cursor] ?? null,
    es: m.es[cursor] ?? null,
    trailing,
    zone: zoneOf(trailing, w.cuts),
    exceeded: m.exceedances.includes(cursor),
    loss: w.loss ? (w.loss[cursor] ?? null) : null,
  };
}

