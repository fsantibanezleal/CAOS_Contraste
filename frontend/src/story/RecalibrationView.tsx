// V5, the method at work: the adaptive conformal recalibration of the VaR advancing day by day. Above, the raw VaR (dashed) and
// the recalibrated VaR (solid) on the same axes with the days each was exceeded; under it a thin track with the quantity the method
// moves, the working tail level, against the target and the floor of its band; below, coupled to the Basel light of V3, the
// exceptions in the trailing 250 days without (dashed) and with (solid) the recalibration against the same zones. One shared day
// cursor drives all and the other views; "play" advances it a few days at a time and stops on any reader input. With reduced
// motion the play control is off and the reader moves the day by hand: nothing is lost. The count is a breach count against its
// expected count: the view never reads a recalibrated zone as a pass (the back-tests accept recalibrated runs too easily).
import { prefersReducedMotion, useLinkedView, useShellLang } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type KeyboardEvent, type PointerEvent } from 'react';
import { DayScrubber, Legend, SrTable, cursorMarker, dayLabel, fullRange, int, lin, linePath, monthLabel, pct, pointerX, stepPath, tickIndicesIn, useBrush, useEasedSeries, xOfRange, type Range, type Size } from './chart';
import { zoneOf, type ModelPath, type Recalibrated, type WindowModel } from './model';
import { zoneBi, zoneRange, type Lang } from './text';

const ZONE_FILL = { green: 'var(--color-good)', amber: 'var(--color-warn)', red: 'var(--color-bad)' } as const;

export function recalibrationGeometry(size: Size, w: WindowModel, raw: ModelPath, rec: Recalibrated, range: Range = fullRange(w.n)) {
  const narrow = size.width < 560;
  const l = narrow ? 38 : 52;
  const r = size.width - (narrow ? 8 : 16);
  const area = size.height - 40;
  const t1 = narrow ? 24 : 30;
  const track = narrow ? 34 : 46;
  const b1 = t1 + (area - t1 - (narrow ? 66 : 60) - track - 24) * 0.58;
  const tL = b1 + (narrow ? 20 : 22);
  const bL = tL + track;
  const t2 = bL + (narrow ? 22 : 26);
  const b2 = area - (narrow ? 36 : 40);
  const top = Math.max(...raw.var, ...rec.var) * 1.08;
  const yMax = Math.max(w.cuts.redStart + 3, ...raw.trailing, ...rec.trailing) + 1;
  const levelTop = Math.max(rec.target * 1.6, ...rec.workingLevel) * 1.08;
  const x = xOfRange(range, l, r);
  const y1 = lin(0, top || 0.05, b1, t1);
  const yL = lin(0, levelTop || 0.02, bL, tL);
  const y2 = lin(0, yMax, b2, t2);
  return { narrow, l, r, t1, b1, tL, bL, t2, b2, top, levelTop, yMax, x, y1, yL, y2 };
}

export function RecalibrationView({
  size,
  w,
  raw,
  rec,
  cursor,
  onCursor,
  range,
  onRange,
}: {
  size: Size;
  w: WindowModel;
  raw: ModelPath;
  rec: Recalibrated;
  cursor: number;
  onCursor: (i: number) => void;
  /** The days shown (a zoom); the whole window when absent. */
  range?: Range;
  onRange?: (r: Range | null) => void;
}) {
  const lang = useShellLang() as Lang;
  const scrub = useLinkedView((s) => s.scrub);
  const tx = (en: string, es: string) => (lang === 'es' ? es : en);
  const [playing, setPlaying] = useState(false);
  const cursorRef = useCursorRef(cursor);
  const still = typeof window !== 'undefined' && prefersReducedMotion();
  const shown = range ?? fullRange(w.n);
  const g = recalibrationGeometry(size, w, raw, rec, shown);
  const { narrow, l, r, t1, tL, bL, t2, b2, x, y1, yL, y2, yMax } = g;
  // the paths ease to the next model's or window's, so a change of selection is a short move and not a cut
  const rawVar = useEasedSeries(raw.var);
  const recVar = useEasedSeries(rec.var);
  const rawCount = useEasedSeries(raw.trailing);
  const recCount = useEasedSeries(rec.trailing);
  const level = useEasedSeries(rec.workingLevel);
  const paths = useMemo(
    () => ({
      rawVar: linePath(rawVar as number[], x, y1),
      recVar: linePath(recVar as number[], x, y1),
      rawCount: stepPath(rawCount as number[], x, y2),
      recCount: stepPath(recCount as number[], x, y2),
      level: linePath(level as number[], x, yL),
    }),
    [rawVar, recVar, rawCount, recCount, level, size.width, size.height, shown[0], shown[1]], // eslint-disable-line react-hooks/exhaustive-deps
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
  const hover = (e: PointerEvent<SVGRectElement>) => byHand(Math.max(0, Math.min(w.n - 1, Math.round(shown[0] + ((pointerX(e) - l) / Math.max(1, r - l)) * (shown[1] - shown[0])))));
  const { handlers, brush } = useBrush({ l, r, range: shown, n: w.n, onRange, hover });
  const key = (e: KeyboardEvent<SVGSVGElement>) => {
    const step = e.shiftKey ? 10 : 1;
    const to = e.key === 'ArrowLeft' ? cursor - step : e.key === 'ArrowRight' ? cursor + step : null;
    if (to == null) return;
    e.preventDefault();
    e.stopPropagation();
    byHand(Math.max(0, Math.min(w.n - 1, to)));
  };
  const cx = x(cursor);
  const inView = cursor >= shown[0] && cursor <= shown[1];
  const zoneRaw = zoneOf(raw.trailing[cursor] ?? 0, w.cuts);
  const zoneRec = zoneOf(rec.trailing[cursor] ?? 0, w.cuts);
  const upto = (days: number[]) => days.filter((d) => d <= cursor).length;
  const zones = [
    { z: 'green' as const, from: 0, to: w.cuts.amberStart },
    { z: 'amber' as const, from: w.cuts.amberStart, to: w.cuts.redStart },
    { z: 'red' as const, from: w.cuts.redStart, to: yMax },
  ];
  const fs = narrow ? 9 : 11;
  const table = useMemo(
    () => (
      <SrTable
        id="recalibration"
        caption={tx(`${rec.label.en} without and with the adaptive conformal recalibration, by day`, `${rec.label.es} sin y con la recalibración conforme adaptativa, por día`)}
        head={[tx('Day', 'Día'), tx('VaR without', 'VaR sin'), tx('VaR with', 'VaR con'), tx('Working tail level', 'Nivel de cola de trabajo'), tx('Exceptions in 250 days without', 'Excepciones en 250 días sin'), tx('Exceptions in 250 days with', 'Excepciones en 250 días con')]}
        rows={w.dates.map((d, i) => [dayLabel(d, lang), pct(raw.var[i], lang), pct(rec.var[i], lang), pct(rec.workingLevel[i], lang, 3), int(raw.trailing[i] ?? 0, lang), int(rec.trailing[i] ?? 0, lang)])}
      />
    ),
    [w, raw, rec, lang], // eslint-disable-line react-hooks/exhaustive-deps
  );
  return (
    <div className="story-view" data-view="recalibration">
      <svg width={size.width} height={Math.max(40, size.height - 40)} viewBox={`0 0 ${size.width} ${Math.max(40, size.height - 40)}`} role="group" tabIndex={0} onKeyDown={key} aria-label={tx('The VaR without and with the conformal recalibration, the working tail level, and the Basel light of both', 'El VaR sin y con la recalibración conforme, el nivel de cola de trabajo, y el semáforo de Basilea de ambos')} data-recalibration="">
        <clipPath id="story-recal-clip">
          <rect x={l} y={t1} width={Math.max(0, r - l)} height={Math.max(0, b2 - t1)} />
        </clipPath>
        {[0, 0.5, 1].map((k) => (
          <g key={k}>
            <line x1={l} x2={r} y1={y1(k * g.top)} y2={y1(k * g.top)} stroke="var(--color-border)" strokeOpacity={0.6} />
            <text x={l - 6} y={y1(k * g.top) + 4} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={fs}>
              {pct(k * g.top, lang, 1)}
            </text>
          </g>
        ))}
        <text x={l} y={t1 - 9} fill="var(--color-fg-subtle)" fontSize={fs}>
          {tx('VaR, % of portfolio value', 'VaR, % del valor de la cartera')}
        </text>
        <g clipPath="url(#story-recal-clip)">
          <path d={paths.rawVar} fill="none" stroke="var(--color-fg-subtle)" strokeWidth={1.6} strokeDasharray="6 4" data-path="raw-var" />
          <path d={paths.recVar} fill="none" stroke="var(--color-accent)" strokeWidth={2.2} strokeLinejoin="round" data-path="recalibrated-var" />
          {raw.exceedances
            .filter((d) => d >= shown[0] && d <= shown[1])
            .map((d) => (
              <circle key={`r${d}`} cx={x(d)} cy={y1(raw.var[d]!)} r={3.2} fill="none" stroke="var(--color-fg-subtle)" strokeWidth={1.3} data-raw-exception={d} />
            ))}
          {rec.exceedances
            .filter((d) => d >= shown[0] && d <= shown[1])
            .map((d) => (
              <path key={`c${d}`} transform={`translate(${x(d)},${y1(rec.var[d]!)})`} d="M0,-4.5 L4.5,0 L0,4.5 L-4.5,0 Z" fill="var(--color-bad)" stroke="var(--color-bg)" strokeWidth={1} data-recalibrated-exception={d} />
            ))}
        </g>
        <g data-working-level="">
          <rect x={l} y={tL} width={r - l} height={bL - tL} fill="var(--color-fg)" fillOpacity={0.04} />
          <line x1={l} x2={r} y1={yL(rec.target)} y2={yL(rec.target)} stroke="var(--color-accent)" strokeWidth={1.4} strokeDasharray="5 3" data-level-target="" />
          <text x={r - 4} y={yL(rec.target) - 4} textAnchor="end" fill="var(--color-accent)" fontSize={narrow ? 8.5 : 10.5} fontWeight={650}>
            {tx(`target ${pct(rec.target, lang, 1)}`, `objetivo ${pct(rec.target, lang, 1)}`)}
          </text>
          <line x1={l} x2={r} y1={yL(rec.levelMin)} y2={yL(rec.levelMin)} stroke="var(--color-fg-subtle)" strokeWidth={1} strokeDasharray="2 3" data-level-floor="" />
          <text x={r - 4} y={yL(rec.levelMin) + (narrow ? 9 : 11)} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={narrow ? 8.5 : 10.5}>
            {tx(`floor ${pct(rec.levelMin, lang, 1)}`, `piso ${pct(rec.levelMin, lang, 1)}`)}
          </text>
          <path d={paths.level} fill="none" stroke="var(--color-magenta)" strokeWidth={1.8} clipPath="url(#story-recal-clip)" data-path="working-level" />
          <text x={l} y={tL - 6} fill="var(--color-fg-subtle)" fontSize={fs}>
            {narrow ? tx('Working tail level', 'Nivel de cola de trabajo') : tx('Working tail level: the level the model is asked for after each day', 'Nivel de cola de trabajo: el nivel que se le pide al modelo tras cada día')}
          </text>
        </g>
        {zones.map((zn) => (
          <g key={zn.z} data-zone-band={zn.z}>
            <rect x={l} y={y2(zn.to)} width={r - l} height={Math.max(0, y2(zn.from) - y2(zn.to))} fill={ZONE_FILL[zn.z]} fillOpacity={w.evaluated ? 0.14 : 0.06} />
            <text x={r - 6} y={y2(zn.to) + (narrow ? 10 : 13)} textAnchor="end" fill="var(--color-fg)" fontSize={narrow ? 8.5 : 10.5} fontWeight={650}>
              {zoneBi(zn.z)[lang]} · {zoneRange(zn.z, w.cuts, lang)}
            </text>
          </g>
        ))}
        <g clipPath="url(#story-recal-clip)">
          <path d={paths.rawCount} fill="none" stroke="var(--color-fg-subtle)" strokeWidth={1.6} strokeDasharray="6 4" data-path="raw-count" />
          <path d={paths.recCount} fill="none" stroke="var(--color-accent)" strokeWidth={2.2} data-path="recalibrated-count" />
        </g>
        <text x={l} y={t2 - 8} fill="var(--color-fg-subtle)" fontSize={fs}>
          {tx('Exceptions in the trailing 250 days', 'Excepciones en los 250 días previos')}
        </text>
        {tickIndicesIn(shown, narrow ? 3 : 5).map((i) => (
          <text key={i} x={x(i)} y={b2 + 15} textAnchor={i === shown[0] ? 'start' : i === shown[1] ? 'end' : 'middle'} fill="var(--color-fg-subtle)" fontSize={fs}>
            {monthLabel(w.dates[i], lang)}
          </text>
        ))}
        <rect x={l} y={t1} width={Math.max(0, r - l)} height={Math.max(0, b2 - t1)} fill="transparent" {...handlers} data-scrub-area="" />
        {brush && <rect x={brush[0]} y={t1} width={brush[1] - brush[0]} height={b2 - t1} fill="var(--color-accent)" fillOpacity={0.14} stroke="var(--color-accent)" strokeDasharray="4 3" data-brush="" style={{ pointerEvents: 'none' }} />}
        {inView && (
          <g style={{ pointerEvents: 'none' }}>
            <line x1={cx} x2={cx} y1={t1} y2={b2} stroke="var(--color-fg)" strokeOpacity={0.7} strokeDasharray="3 3" />
            <circle cx={cx} cy={y1(rec.var[cursor] ?? 0)} r={5} fill="var(--color-accent)" stroke="var(--color-bg)" strokeWidth={2.5} {...cursorMarker(cursor)} />
            <circle cx={cx} cy={yL(rec.workingLevel[cursor] ?? 0)} r={3.5} fill="var(--color-magenta)" stroke="var(--color-bg)" strokeWidth={1.5} />
            <circle cx={cx} cy={y2(rec.trailing[cursor] ?? 0)} r={5} fill={ZONE_FILL[zoneRec]} stroke="var(--color-bg)" strokeWidth={2.5} {...cursorMarker(cursor)} />
            <circle cx={cx} cy={y2(raw.trailing[cursor] ?? 0)} r={4} fill="var(--color-bg)" stroke={ZONE_FILL[zoneRaw]} strokeWidth={2} />
          </g>
        )}
        <Legend
          items={[
            { kind: 'dash', color: 'var(--color-fg-subtle)', label: narrow ? tx('Without', 'Sin') : tx('Without recalibration', 'Sin recalibración') },
            { kind: 'line', color: 'var(--color-accent)', label: narrow ? tx('With', 'Con') : tx('With recalibration', 'Con recalibración') },
            { kind: 'line', color: 'var(--color-magenta)', label: narrow ? tx('Level', 'Nivel') : tx('Working tail level', 'Nivel de cola de trabajo') },
          ]}
          x={l + 8}
          y={size.height - 40 - 8}
          maxWidth={r - l - 8}
          fontSize={narrow ? 9.5 : 11}
        />
        {!narrow && (
          <text x={r - 4} y={size.height - 40 - 4} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={11}>
            {tx(`breaches to this day: ${int(upto(raw.exceedances), lang)} without, ${int(upto(rec.exceedances), lang)} with`, `excedencias hasta este día: ${int(upto(raw.exceedances), lang)} sin, ${int(upto(rec.exceedances), lang)} con`)}
          </text>
        )}
      </svg>
      {table}
      <div className="story-controls-row">
        <button type="button" className="story-play" aria-pressed={playing} disabled={still} title={still ? tx('Reduced motion is on: move the day by hand', 'El movimiento reducido está activo: mueva el día a mano') : undefined} onClick={() => { if (!playing && cursor >= w.n - 1) { scrub(0); onCursor(0); } setPlaying((v) => !v); }}>
          {playing ? tx('Pause the days', 'Pausar los días') : tx('Play the days', 'Reproducir los días')}
        </button>
        <DayScrubber dates={w.dates} index={cursor} onChange={(i) => { setPlaying(false); onCursor(i); }} range={shown} onRange={onRange} />
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
