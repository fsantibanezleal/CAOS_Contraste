// V3, the domain's own diagram: the Basel traffic light. The exceptions of each model in the trailing 250 days against the three
// zones of the MAR32.9 table (green 0 to 4, amber 5 to 9, red 10 or more), day by day over the window. The selected model is
// drawn heavy, the others light; selecting a line selects the model in the panel and back; the day cursor is the story's shared
// one. A window shorter than 250 days has no Basel light: the counts so far are drawn against the zones, labelled as not
// evaluated, with the reason of the document.
import { useLinkedView, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo, type KeyboardEvent, type PointerEvent } from 'react';
import { DayScrubber, Swatch, cursorMarker, int, lin, monthLabel, pointerX, stepPath, tickIndices, type Size } from './chart';
import { zoneOf, type WindowModel } from './model';
import { zoneBi, zoneRange, type Lang } from './text';

const ZONE_FILL = { green: 'var(--color-good)', amber: 'var(--color-warn)', red: 'var(--color-bad)' } as const;

/** The plot rectangle of the view in its own pixels, and its scales: also what the callouts anchor to. */
export function lightGeometry(size: Size, w: WindowModel) {
  const narrow = size.width < 560;
  const l = narrow ? 34 : 48;
  const r = size.width - (narrow ? 8 : 16);
  const t = narrow ? 26 : 34;
  const b = size.height - 40 - (narrow ? 26 : 44);
  const yMax = Math.max(w.cuts.redStart + 4, ...w.models.map((m) => Math.max(0, ...m.trailing))) + 1;
  const x = lin(0, Math.max(1, w.n - 1), l, r);
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
}: {
  size: Size;
  w: WindowModel;
  selected: string;
  cursor: number;
  onSelect: (id: string) => void;
  onCursor: (i: number) => void;
}) {
  const lang = useShellLang() as Lang;
  const select = useLinkedView((s) => s.select);
  const scrub = useLinkedView((s) => s.scrub);
  const tx = (en: string, es: string) => (lang === 'es' ? es : en);
  const g = lightGeometry(size, w);
  const { narrow, l, r, t, b, yMax, x, y } = g;
  const chosen = w.models.find((m) => m.id === selected) ?? w.models[0]!;
  // the lines are drawn for the pointer; the keyboard and a screen reader choose a model in the panel's list, which holds the same ids
  // the 18 paths do not depend on the cursor: built once per window and size, so scrubbing redraws one marker
  const lines = useMemo(() => w.models.map((m) => ({ id: m.id, d: stepPath(m.trailing, x, y) })), [w, size.width, size.height]); // eslint-disable-line react-hooks/exhaustive-deps
  const chosenLine = lines.find((p) => p.id === chosen.id)!;
  const zones = [
    { z: 'green' as const, from: 0, to: w.cuts.amberStart },
    { z: 'amber' as const, from: w.cuts.amberStart, to: w.cuts.redStart },
    { z: 'red' as const, from: w.cuts.redStart, to: yMax },
  ];
  const fill = w.evaluated ? 0.14 : 0.06;
  const here = chosen.trailing[cursor] ?? 0;
  const zoneHere = zoneOf(here, w.cuts);
  const cx = x(cursor);
  const move = (e: PointerEvent<SVGRectElement>) => {
    const i = Math.max(0, Math.min(w.n - 1, Math.round(((pointerX(e) - l) / Math.max(1, r - l)) * (w.n - 1))));
    scrub(i);
    onCursor(i);
  };
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
        {w.evaluated && (
          <g data-lead-in="">
            <rect x={l} y={t} width={Math.max(0, x(249) - l)} height={b - t} fill="var(--color-fg)" fillOpacity={0.05} />
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
        {tickIndices(w.n, narrow ? 3 : 5).map((i) => (
          <text key={i} x={x(i)} y={b + 16} textAnchor={i === 0 ? 'start' : i === w.n - 1 ? 'end' : 'middle'} fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
            {monthLabel(w.dates[i], lang)}
          </text>
        ))}
        <text x={l} y={t - 10} fill="var(--color-fg-subtle)" fontSize={narrow ? 9 : 11}>
          {tx('Exceptions in the trailing 250 days', 'Excepciones en los 250 días previos')}
        </text>
        <rect x={l} y={t} width={Math.max(0, r - l)} height={Math.max(0, b - t)} fill="transparent" onPointerMove={move} data-scrub-area="" />
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
          <path d={chosenLine.d} fill="none" stroke="var(--color-accent)" strokeWidth={2.6} strokeLinejoin="round" />
        </g>
        <line x1={cx} x2={cx} y1={t} y2={b} stroke="var(--color-fg)" strokeOpacity={0.7} strokeDasharray="3 3" />
        <circle cx={cx} cy={y(here)} r={5.5} fill={ZONE_FILL[zoneHere]} stroke="var(--color-bg)" strokeWidth={2.5} {...cursorMarker(cursor)} />
        <text x={cx + (cx > (l + r) / 2 ? -9 : 9)} y={Math.max(t + 12, y(here) - 10)} textAnchor={cx > (l + r) / 2 ? 'end' : 'start'} fill="var(--color-fg)" fontSize={narrow ? 10 : 12} fontWeight={700} data-cursor-readout="">
          {int(here, lang)} · {zoneBi(zoneHere)[lang]}
        </text>
        {!narrow && (
          <g transform={`translate(${l + 8},${size.height - 40 - 8})`}>
            <Swatch x={0} y={0} color="var(--color-accent)" label={tx('Selected model', 'Modelo seleccionado')} />
            <Swatch x={170} y={0} color="var(--color-fg-faint)" label={tx('The other models of the ladder', 'Los demás modelos de la escalera')} />
          </g>
        )}
      </svg>
      <DayScrubber dates={w.dates} index={cursor} onChange={onCursor} />
    </div>
  );
}
