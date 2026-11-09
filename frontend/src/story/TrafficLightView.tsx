// V3, the domain's own diagram: the Basel traffic light. The exceptions of each model in the trailing 250 days against the three
// zones of the MAR32.9 table (green 0 to 4, amber 5 to 9, red 10 or more), day by day over the window. The selected model is
// drawn heavy, the others light; selecting a line selects the model in the panel and back; the day cursor is the story's shared
// one. A window shorter than 250 days has no Basel light: the counts so far are drawn against the zones, labelled as not
// evaluated, with the reason of the document. A press-drag on the plot zooms to the days it covers (the buttons of the day control
// do the same from the keyboard); the selected model's path eases to the next one's; a hidden table holds the plotted series.
import { useLinkedView, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo, type KeyboardEvent, type PointerEvent } from 'react';
import { DayScrubber, Legend, SrTable, cursorMarker, dayLabel, fullRange, int, lin, monthLabel, pointerX, stepPath, tickIndicesIn, useBrush, useEasedSeries, xOfRange, type Range, type Size } from './chart';
import { zoneOf, type WindowModel } from './model';
import { zoneBi, zoneRange, type Lang } from './text';

const ZONE_FILL = { green: 'var(--color-good)', amber: 'var(--color-warn)', red: 'var(--color-bad)' } as const;

/** The plot rectangle of the view in its own pixels, and its scales: also what the callouts anchor to. */
export function lightGeometry(size: Size, w: WindowModel, range: Range = fullRange(w.n)) {
  const narrow = size.width < 560;
  const l = narrow ? 34 : 48;
  const r = size.width - (narrow ? 8 : 16);
  const t = narrow ? 26 : 34;
  const b = size.height - 40 - (narrow ? 26 : 44);
  const yMax = Math.max(w.cuts.redStart + 4, ...w.models.map((m) => Math.max(0, ...m.trailing))) + 1;
  const x = xOfRange(range, l, r);
  const y = lin(0, yMax, b, t);
  return { narrow, l, r, t, b, yMax, x, y };
}

export function TrafficLightView({
  size,
  w,
  selected,
  cursor,
  onSelect,
  onCursor,
  range,
  onRange,
}: {
  size: Size;
  w: WindowModel;
  selected: string;
  cursor: number;
  onSelect: (id: string) => void;
  onCursor: (i: number) => void;
  /** The days shown (a zoom); the whole window when absent. */
  range?: Range;
  onRange?: (r: Range | null) => void;
}) {
  const lang = useShellLang() as Lang;
  const select = useLinkedView((s) => s.select);
  const scrub = useLinkedView((s) => s.scrub);
  const tx = (en: string, es: string) => (lang === 'es' ? es : en);
  const shown = range ?? fullRange(w.n);
  const g = lightGeometry(size, w, shown);
  const { narrow, l, r, t, b, yMax, x, y } = g;
  const chosen = w.models.find((m) => m.id === selected) ?? w.models[0]!;
  // the selected model's path eases to the next one's, so a change of model is a short move and not a cut
  const chosenTrail = useEasedSeries(chosen.trailing);
  // the lines are drawn for the pointer; the keyboard and a screen reader choose a model in the panel's list, which holds the same ids
  // the 18 paths do not depend on the cursor: built once per window, size and zoom, so scrubbing redraws one marker
  const lines = useMemo(() => w.models.map((m) => ({ id: m.id, d: stepPath(m.trailing, x, y) })), [w, size.width, size.height, shown[0], shown[1]]); // eslint-disable-line react-hooks/exhaustive-deps
  const chosenD = useMemo(() => stepPath(chosenTrail as number[], x, y), [chosenTrail, size.width, size.height, shown[0], shown[1]]); // eslint-disable-line react-hooks/exhaustive-deps
  const zones = [
    { z: 'green' as const, from: 0, to: w.cuts.amberStart },
    { z: 'amber' as const, from: w.cuts.amberStart, to: w.cuts.redStart },
    { z: 'red' as const, from: w.cuts.redStart, to: yMax },
  ];
  const fill = w.evaluated ? 0.14 : 0.06;
  const here = chosen.trailing[cursor] ?? 0;
  const zoneHere = zoneOf(here, w.cuts);
  const cx = x(cursor);
  const inView = cursor >= shown[0] && cursor <= shown[1];
  const hover = (e: PointerEvent<SVGRectElement>) => {
    const i = Math.max(0, Math.min(w.n - 1, Math.round(shown[0] + ((pointerX(e) - l) / Math.max(1, r - l)) * (shown[1] - shown[0]))));
    scrub(i);
    onCursor(i);
  };
  const { handlers, brush } = useBrush({ l, r, range: shown, n: w.n, onRange, hover });
  const key = (e: KeyboardEvent<SVGSVGElement>) => {
    const step = e.shiftKey ? 10 : 1;
    const to = e.key === 'ArrowLeft' ? cursor - step : e.key === 'ArrowRight' ? cursor + step : e.key === 'Home' ? 0 : e.key === 'End' ? w.n - 1 : null;
    if (to == null) return;
    e.preventDefault();
    e.stopPropagation();
    const i = Math.max(0, Math.min(w.n - 1, to));
    scrub(i);
    onCursor(i);
  };
  const leadIn = Math.min(249, shown[1]);
  // the hidden table of the plotted series is built once per model and window, not on every day the cursor visits
  const table = useMemo(
    () => (
      <SrTable
        id="light"
        caption={tx(`Exceptions in the trailing 250 days of ${chosen.label.en}, by day`, `Excepciones en los 250 días previos de ${chosen.label.es}, por día`)}
        head={[tx('Day', 'Día'), tx('Exceptions in 250 days', 'Excepciones en 250 días'), tx('Zone', 'Zona')]}
        rows={w.dates.map((d, i) => [dayLabel(d, lang), int(chosen.trailing[i] ?? 0, lang), zoneBi(zoneOf(chosen.trailing[i] ?? 0, w.cuts))[lang]])}
      />
    ),
    [w, chosen, lang], // eslint-disable-line react-hooks/exhaustive-deps
  );
  return (
    <div className="story-view" data-view="light">
      <svg width={size.width} height={Math.max(40, size.height - 40)} viewBox={`0 0 ${size.width} ${Math.max(40, size.height - 40)}`} role="group" tabIndex={0} onKeyDown={key} aria-label={tx('Basel traffic light: exceptions in the trailing 250 days of each model, by day', 'Semáforo de Basilea: excepciones de cada modelo en los 250 días previos, por día')} data-traffic-light="">
        {zones.map((zn) => (
          <g key={zn.z} data-zone-band={zn.z}>
            <rect x={l} y={y(zn.to)} width={r - l} height={Math.max(0, y(zn.from) - y(zn.to))} fill={ZONE_FILL[zn.z]} fillOpacity={fill} stroke={ZONE_FILL[zn.z]} strokeOpacity={w.evaluated ? 0 : 0.5} strokeDasharray="4 3" />
            <text x={r - 6} y={y(zn.to) + (narrow ? 11 : 15)} textAnchor="end" fill="var(--color-fg)" fontSize={narrow ? 9 : 11.5} fontWeight={650}>
              {zoneBi(zn.z)[lang]} · {zoneRange(zn.z, w.cuts, lang)}
            </text>
          </g>
        ))}
        {w.evaluated && shown[0] < 249 && (
          <g data-lead-in="">
            <rect x={l} y={t} width={Math.max(0, x(leadIn) - l)} height={b - t} fill="var(--color-fg)" fillOpacity={0.05} />
            <text x={l + 6} y={b - 6} fill="var(--color-fg-subtle)" fontSize={narrow ? 8.5 : 10.5}>
              {tx('window filling: fewer than 250 days', 'ventana llenándose: menos de 250 días')}
            </text>
          </g>
        )}
        {!w.evaluated && (
          <text x={l + 6} y={b - 6} fill="var(--color-fg)" fontSize={narrow ? 8.5 : 10.5} fontWeight={650} data-not-evaluated="">
            {tx(`Not evaluated: the light needs 250 days, the window has ${int(w.n, lang)}`, `No evaluado: el semáforo necesita 250 días, la ventana tiene ${int(w.n, lang)}`)}
          </text>
        )}
        {[0, w.cuts.amberStart, w.cuts.redStart, yMax - 1].map((v) => (
          <g key={v}>
            <line x1={l} x2={r} y1={y(v)} y2={y(v)} stroke="var(--color-border)" strokeOpacity={0.6} />
            <text x={l - 6} y={y(v) + 4} textAnchor="end" fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
              {int(v, lang)}
            </text>
          </g>
        ))}
        {tickIndicesIn(shown, narrow ? 3 : 5).map((i) => (
          <text key={i} x={x(i)} y={b + 16} textAnchor={i === shown[0] ? 'start' : i === shown[1] ? 'end' : 'middle'} fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
            {monthLabel(w.dates[i], lang)}
          </text>
        ))}
        <text x={l} y={t - 10} fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
          {tx('Exceptions in the trailing 250 days', 'Excepciones en los 250 días previos')}
        </text>
        <clipPath id="story-light-clip">
          <rect x={l} y={t} width={Math.max(0, r - l)} height={Math.max(0, b - t)} />
        </clipPath>
        <rect x={l} y={t} width={Math.max(0, r - l)} height={Math.max(0, b - t)} fill="transparent" {...handlers} data-scrub-area="" />
        <g clipPath="url(#story-light-clip)">
          {lines
            .filter((p) => p.id !== chosen.id)
            .map((p) => {
              const m = w.models.find((q) => q.id === p.id)!;
              const id = `model:${p.id}`;
              return (
                <g key={p.id} aria-hidden="true" data-line-label={m.label[lang]} data-linked-id={id} data-linked-view="scene" data-linked-selected="false" onClick={() => { select(id, 'scene'); onSelect(p.id); }} style={{ cursor: 'pointer' }}>
                  <path d={p.d} fill="none" stroke="var(--color-fg-faint)" strokeOpacity={0.55} strokeWidth={1} />
                  <path d={p.d} fill="none" stroke="transparent" strokeWidth={9} />
                </g>
              );
            })}
          <g aria-hidden="true" data-line-label={chosen.label[lang]} data-linked-id={`model:${chosen.id}`} data-linked-view="scene" data-linked-selected="true" onClick={() => { select(`model:${chosen.id}`, 'scene'); onSelect(chosen.id); }}>
            <path d={chosenD} fill="none" stroke="var(--color-accent)" strokeWidth={2.6} strokeLinejoin="round" />
          </g>
        </g>
        {brush && <rect x={brush[0]} y={t} width={brush[1] - brush[0]} height={b - t} fill="var(--color-accent)" fillOpacity={0.14} stroke="var(--color-accent)" strokeDasharray="4 3" data-brush="" style={{ pointerEvents: 'none' }} />}
        {inView && (
          <>
            <line x1={cx} x2={cx} y1={t} y2={b} stroke="var(--color-fg)" strokeOpacity={0.7} strokeDasharray="3 3" style={{ pointerEvents: 'none' }} />
            <circle cx={cx} cy={y(here)} r={5.5} fill={ZONE_FILL[zoneHere]} stroke="var(--color-bg)" strokeWidth={2.5} {...cursorMarker(cursor)} style={{ pointerEvents: 'none' }} />
            <text x={cx + (cx > (l + r) / 2 ? -9 : 9)} y={Math.max(t + 12, y(here) - 10)} textAnchor={cx > (l + r) / 2 ? 'end' : 'start'} fill="var(--color-fg)" fontSize={narrow ? 10 : 12} fontWeight={700} data-cursor-readout="" style={{ pointerEvents: 'none' }}>
              {dayLabel(w.dates[cursor], lang)} · {int(here, lang)} {tx('exceptions', 'excepciones')} · {zoneBi(zoneHere)[lang]}
            </text>
          </>
        )}
        <Legend
          items={[
            { kind: 'line', color: 'var(--color-accent)', label: narrow ? tx('Selected', 'Elegido') : tx('Selected model', 'Modelo seleccionado') },
            { kind: 'line', color: 'var(--color-fg-faint)', label: narrow ? tx('Others', 'Otros') : tx('The other models of the ladder', 'Los demás modelos de la escalera') },
          ]}
          x={l + 8}
          y={size.height - 40 - 8}
          maxWidth={r - l - 8}
          fontSize={narrow ? 9.5 : 11}
        />
      </svg>
      {table}
      <DayScrubber dates={w.dates} index={cursor} onChange={onCursor} range={shown} onRange={onRange} />
    </div>
  );
}
