// V5, the method at work: the adaptive conformal recalibration of the VaR advancing day by day. Above, the raw VaR (dashed) and
// the recalibrated VaR (solid) on the same axes with the days each was exceeded; below, coupled to the Basel light of V3, the
// exceptions in the trailing 250 days without (dashed) and with (solid) the recalibration against the same zones. One shared day
// cursor drives both and the other views; "play" advances it a few days at a time and stops on any reader input. With reduced
// motion the play control is off and the reader moves the day by hand: nothing is lost.
import { prefersReducedMotion, useLinkedView, useShellLang } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type KeyboardEvent, type PointerEvent } from 'react';
import { DayScrubber, Swatch, cursorMarker, int, lin, linePath, monthLabel, pct, pointerX, stepPath, tickIndices, type Size } from './chart';
import { zoneOf, type ModelPath, type Recalibrated, type WindowModel } from './model';
import { zoneBi, zoneRange, type Lang } from './text';

const ZONE_FILL = { green: 'var(--color-good)', amber: 'var(--color-warn)', red: 'var(--color-bad)' } as const;

export function recalibrationGeometry(size: Size, w: WindowModel, raw: ModelPath, rec: Recalibrated) {
  const narrow = size.width < 560;
  const l = narrow ? 38 : 52;
  const r = size.width - (narrow ? 8 : 16);
  const area = size.height - 40;
  const t1 = narrow ? 24 : 30;
  const b1 = t1 + (area - t1 - (narrow ? 50 : 60)) * 0.58;
  const t2 = b1 + (narrow ? 22 : 26);
  const b2 = area - (narrow ? 22 : 40);
  const top = Math.max(...raw.var, ...rec.var) * 1.08;
  const yMax = Math.max(w.cuts.redStart + 3, ...raw.trailing, ...rec.trailing) + 1;
  const x = lin(0, Math.max(1, w.n - 1), l, r);
  const y1 = lin(0, top || 0.05, b1, t1);
  const y2 = lin(0, yMax, b2, t2);
  return { narrow, l, r, t1, b1, t2, b2, top, yMax, x, y1, y2 };
}

export function RecalibrationView({
  size,
  w,
  raw,
  rec,
  cursor,
  onCursor,
}: {
  size: Size;
  w: WindowModel;
  raw: ModelPath;
  rec: Recalibrated;
  cursor: number;
  onCursor: (i: number) => void;
}) {
  const lang = useShellLang() as Lang;
  const scrub = useLinkedView((s) => s.scrub);
  const tx = (en: string, es: string) => (lang === 'es' ? es : en);
  const [playing, setPlaying] = useState(false);
  const cursorRef = useCursorRef(cursor);
  const still = typeof window !== 'undefined' && prefersReducedMotion();
  const g = recalibrationGeometry(size, w, raw, rec);
  const { narrow, l, r, t1, t2, b2, x, y1, y2, yMax } = g;
  const paths = useMemo(
    () => ({
      rawVar: linePath(raw.var, x, y1),
      recVar: linePath(rec.var, x, y1),
      rawCount: stepPath(raw.trailing, x, y2),
      recCount: stepPath(rec.trailing, x, y2),
    }),
    [raw, rec, size.width, size.height], // eslint-disable-line react-hooks/exhaustive-deps
  );
  useEffect(() => {
    if (!playing) return;
    const step = Math.max(1, Math.floor(w.n / 120));
    const timer = window.setInterval(() => {
      const next = Math.min(w.n - 1, cursorRef.current + step);
      scrub(next);
      onCursor(next);
      if (next >= w.n - 1) setPlaying(false);
    }, 90);
    return () => window.clearInterval(timer);
    // the cursor is read through the ref, so the timer is not rebuilt on every day
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, w.n]);
  const byHand = (i: number) => {
    setPlaying(false);
    scrub(i);
    onCursor(i);
  };
  const move = (e: PointerEvent<SVGRectElement>) => byHand(Math.max(0, Math.min(w.n - 1, Math.round(((pointerX(e) - l) / Math.max(1, r - l)) * (w.n - 1)))));
  const key = (e: KeyboardEvent<SVGSVGElement>) => {
    const step = e.shiftKey ? 10 : 1;
    const to = e.key === 'ArrowLeft' ? cursor - step : e.key === 'ArrowRight' ? cursor + step : null;
    if (to == null) return;
    e.preventDefault();
    e.stopPropagation();
    byHand(Math.max(0, Math.min(w.n - 1, to)));
  };
  const cx = x(cursor);
  const zoneRaw = zoneOf(raw.trailing[cursor] ?? 0, w.cuts);
  const zoneRec = zoneOf(rec.trailing[cursor] ?? 0, w.cuts);
  const upto = (days: number[]) => days.filter((d) => d <= cursor).length;
  const zones = [
    { z: 'green' as const, from: 0, to: w.cuts.amberStart },
    { z: 'amber' as const, from: w.cuts.amberStart, to: w.cuts.redStart },
    { z: 'red' as const, from: w.cuts.redStart, to: yMax },
  ];
  return (
    <div className="story-view" data-view="recalibration">
      <svg width={size.width} height={Math.max(40, size.height - 40)} viewBox={`0 0 ${size.width} ${Math.max(40, size.height - 40)}`} role="group" tabIndex={0} onKeyDown={key} aria-label={tx('The VaR without and with the conformal recalibration, and the Basel light of both', 'El VaR sin y con la recalibración conforme, y el semáforo de Basilea de ambos')} data-recalibration="">
        {[0, 0.5, 1].map((k) => (
          <g key={k}>
            <line x1={l} x2={r} y1={y1(k * g.top)} y2={y1(k * g.top)} stroke="var(--color-border)" strokeOpacity={0.6} />
            <text x={l - 6} y={y1(k * g.top) + 4} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
              {pct(k * g.top, lang, 1)}
            </text>
          </g>
        ))}
        <text x={l} y={t1 - 9} fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
          {tx('VaR, % of portfolio value', 'VaR, % del valor de la cartera')}
        </text>
        <path d={paths.rawVar} fill="none" stroke="var(--color-fg-subtle)" strokeWidth={1.6} strokeDasharray="6 4" data-path="raw-var" />
        <path d={paths.recVar} fill="none" stroke="var(--color-accent)" strokeWidth={2.2} strokeLinejoin="round" data-path="recalibrated-var" />
        {raw.exceedances.map((d) => (
          <circle key={`r${d}`} cx={x(d)} cy={y1(raw.var[d]!)} r={3.2} fill="none" stroke="var(--color-fg-subtle)" strokeWidth={1.3} data-raw-exception={d} />
        ))}
        {rec.exceedances.map((d) => (
          <path key={`c${d}`} transform={`translate(${x(d)},${y1(rec.var[d]!)})`} d="M0,-4.5 L4.5,0 L0,4.5 L-4.5,0 Z" fill="var(--color-bad)" stroke="var(--color-bg)" strokeWidth={1} data-recalibrated-exception={d} />
        ))}
        {zones.map((zn) => (
          <g key={zn.z} data-zone-band={zn.z}>
            <rect x={l} y={y2(zn.to)} width={r - l} height={Math.max(0, y2(zn.from) - y2(zn.to))} fill={ZONE_FILL[zn.z]} fillOpacity={w.evaluated ? 0.14 : 0.06} />
            <text x={r - 6} y={y2(zn.to) + (narrow ? 10 : 13)} textAnchor="end" fill="var(--color-fg)" fontSize={narrow ? 8.5 : 10.5} fontWeight={650}>
              {zoneBi(zn.z)[lang]} · {zoneRange(zn.z, w.cuts, lang)}
            </text>
          </g>
        ))}
        <path d={paths.rawCount} fill="none" stroke="var(--color-fg-subtle)" strokeWidth={1.6} strokeDasharray="6 4" data-path="raw-count" />
        <path d={paths.recCount} fill="none" stroke="var(--color-accent)" strokeWidth={2.2} data-path="recalibrated-count" />
        <text x={l} y={t2 - 8} fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
          {tx('Exceptions in the trailing 250 days', 'Excepciones en los 250 días previos')}
        </text>
        {tickIndices(w.n, narrow ? 3 : 5).map((i) => (
          <text key={i} x={x(i)} y={b2 + 15} textAnchor={i === 0 ? 'start' : i === w.n - 1 ? 'end' : 'middle'} fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
            {monthLabel(w.dates[i], lang)}
          </text>
        ))}
        <rect x={l} y={t1} width={Math.max(0, r - l)} height={Math.max(0, b2 - t1)} fill="transparent" onPointerMove={move} data-scrub-area="" />
        <line x1={cx} x2={cx} y1={t1} y2={b2} stroke="var(--color-fg)" strokeOpacity={0.7} strokeDasharray="3 3" />
        <circle cx={cx} cy={y1(rec.var[cursor] ?? 0)} r={5} fill="var(--color-accent)" stroke="var(--color-bg)" strokeWidth={2.5} {...cursorMarker(cursor)} />
        <circle cx={cx} cy={y2(rec.trailing[cursor] ?? 0)} r={5} fill={ZONE_FILL[zoneRec]} stroke="var(--color-bg)" strokeWidth={2.5} {...cursorMarker(cursor)} />
        <circle cx={cx} cy={y2(raw.trailing[cursor] ?? 0)} r={4} fill="var(--color-bg)" stroke={ZONE_FILL[zoneRaw]} strokeWidth={2} />
        {!narrow && (
          <g transform={`translate(${l + 8},${size.height - 40 - 8})`} fontSize={11}>
            <Swatch x={0} y={0} color="var(--color-fg-subtle)" dash="6 4" label={tx('Without recalibration', 'Sin recalibración')} />
            <Swatch x={190} y={0} color="var(--color-accent)" label={tx('With recalibration', 'Con recalibración')} />
            <text x={380} y={4} fill="var(--color-fg-subtle)" fontSize={11}>
              {tx(`breaches to this day: ${int(upto(raw.exceedances), lang)} without, ${int(upto(rec.exceedances), lang)} with`, `excedencias hasta este día: ${int(upto(raw.exceedances), lang)} sin, ${int(upto(rec.exceedances), lang)} con`)}
            </text>
          </g>
        )}
      </svg>
      <div className="story-controls-row">
        <button type="button" className="story-play" aria-pressed={playing} disabled={still} title={still ? tx('Reduced motion is on: move the day by hand', 'El movimiento reducido está activo: mueva el día a mano') : undefined} onClick={() => { if (!playing && cursor >= w.n - 1) { scrub(0); onCursor(0); } setPlaying((v) => !v); }}>
          {playing ? tx('Pause the days', 'Pausar los días') : tx('Play the days', 'Reproducir los días')}
        </button>
        <DayScrubber dates={w.dates} index={cursor} onChange={(i) => { setPlaying(false); onCursor(i); }} />
      </div>
    </div>
  );
}

/** The latest cursor for a timer that is not rebuilt on each day. */
function useCursorRef(cursor: number) {
  const [ref] = useState(() => ({ current: cursor }));
  ref.current = cursor;
  return ref;
}
