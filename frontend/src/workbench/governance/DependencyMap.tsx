// The inventory map (dossier 06 I.4): the dependency graph of the models, drawn from the inventory's edges and the
// bake's layered layout (the `generation` of each entry's map block is its column, and the bake's y orders it inside the
// column). A node is coloured by its tier and ringed by the worst severity among its open findings; each dependency edge
// is drawn with its kind (`document`: the downstream reads the upstream's committed document; `code`: it imports the
// upstream's code). The engine node `riskvalidation` is drawn once, with a faint line to every entry, because every entry
// depends on it (decision W15-8). The "related" links are not dependencies and are not drawn here: they are listed apart,
// dashed (RelatedLinks). The nodes are numbered, and the numbers key the inventory table beside the map, so the drawing
// carries no label that can collide with another. Drawn as SVG at the size its stage measures (no graph library).
import { Stage, fitLabel, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { useRef, useState, type KeyboardEvent, type PointerEvent, type WheelEvent } from 'react';
import { viridis } from '../c04/MatrixMap';
import { layers, tierName, worstOpen, type GovInventory, type InvEntry, type Severity } from './model';
import { entryText } from '../names';

/** Tier 1 (the most material) is the darkest end of viridis, Tier 4 the lightest: four steps a reader can tell apart. */
export const tierColor = (tier: number): string => viridis([0.04, 0.36, 0.68, 0.96][Math.min(4, Math.max(1, tier)) - 1]);
const inkOn = (tier: number) => (tier >= 3 ? '#141414' : '#f4f4f4');

export const SEVERITY_RING: Record<Severity, { color: string; width: number }> = {
  S1: { color: 'var(--color-bad)', width: 4 },
  S2: { color: 'var(--color-warn)', width: 3 },
  S3: { color: 'var(--color-accent)', width: 2.5 },
  S4: { color: 'var(--color-fg-faint)', width: 2 },
};

export const EDGE_COLOR = { document: 'var(--color-accent)', code: 'var(--color-magenta)' } as const;

const TOP = 36;
const ROW = 30;
const PAD = 22;
const R = 11;

/** The height the drawing needs for the tallest generation. */
export const mapHeight = (entries: InvEntry[]): number => Math.max(180, TOP + Math.max(1, ...layers(entries).map((l) => l.length)) * ROW + 8);

/** Where each entry is drawn: the column of its generation (the engine takes the first), rows spread evenly inside the column. */
export function placeNodes(entries: InvEntry[], width: number, height: number): { engine: { x: number; y: number }; nodes: Map<string, { x: number; y: number; n: number }>; colW: number } {
  const ls = layers(entries);
  const cols = ls.length + 1;
  const colW = (width - 2 * PAD) / cols;
  const x = (col: number) => PAD + (col + 0.5) * colW;
  const nodes = new Map<string, { x: number; y: number; n: number }>();
  const order = new Map(entries.map((e, i) => [e.key, i + 1]));
  ls.forEach((layer, g) => {
    const step = Math.min(ROW, (height - TOP - 8) / Math.max(1, layer.length));
    layer.forEach((e, i) => nodes.set(e.key, { x: x(g + 1), y: TOP + step * (i + 0.5), n: order.get(e.key) ?? 0 }));
  });
  return { engine: { x: x(0), y: TOP + (height - TOP - 8) / 2 }, nodes, colW };
}

/** The zoom range of the map: whole at 1, a node four times its size at most. */
const ZOOM_MIN = 1;
const ZOOM_MAX = 4;
/** The height of the read-out line under the drawing. */
export const READOUT_HEIGHT = 28;

/**
 * The map with the interactions of the rubric (Tier A, R3 c23 M4): zoom with the buttons, the wheel or the + and - keys; pan by
 * dragging or with the arrow keys while zoomed; reset with the button, a double click or 0; every node is focusable, and Tab, the
 * arrow keys (unzoomed) or a pointer read it out in the line under the drawing. The edges table beside the map is the data-table
 * fallback.
 */
export function MapDrawing({ inv, width, height, current: shownKey, onCurrent, readout = true }: { inv: GovInventory; width: number; height: number; current?: string | null; onCurrent?: (key: string) => void; readout?: boolean }) {
  const lang = useShellLang();
  const [view, setView] = useState({ k: 1, x: 0, y: 0 });
  const [own, setOwn] = useState<string | null>(null);
  // the node read out: the host's when it holds the read-out line below its stage (DependencyMap), else the drawing's own
  const current = onCurrent ? (shownKey ?? null) : own;
  const setCurrent = (key: string) => (onCurrent ? onCurrent(key) : setOwn(key));
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);
  const nodeRefs = useRef(new Map<string, SVGGElement>());
  const { engine, nodes, colW } = placeNodes(inv.entries, width, height);
  // a view that keeps the drawing over its box: the pan is bounded by how much the zoom enlarged it
  const clamp = (k: number, x: number, y: number) => {
    const kk = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, k));
    return { k: kk, x: Math.min(0, Math.max(width - width * kk, x)), y: Math.min(0, Math.max(height - height * kk, y)) };
  };
  const zoomAt = (factor: number, cx = width / 2, cy = height / 2) =>
    setView((v) => {
      const k = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, v.k * factor));
      return clamp(k, cx - ((cx - v.x) * k) / v.k, cy - ((cy - v.y) * k) / v.k);
    });
  const reset = () => setView({ k: 1, x: 0, y: 0 });
  const entryWords = (e: InvEntry) => entryWordsOf(inv, e, lang);
  const focusEntry = (i: number) => {
    const e = inv.entries[(i + inv.entries.length) % inv.entries.length];
    if (e) nodeRefs.current.get(e.key)?.focus();
  };
  const onKey = (ev: KeyboardEvent<SVGGElement>, i: number) => {
    const step = 40;
    if (ev.key === '+' || ev.key === '=') zoomAt(1.25);
    else if (ev.key === '-' || ev.key === '_') zoomAt(0.8);
    else if (ev.key === '0') reset();
    else if (view.k > 1 && ev.key.startsWith('Arrow')) {
      const dx = ev.key === 'ArrowLeft' ? step : ev.key === 'ArrowRight' ? -step : 0;
      const dy = ev.key === 'ArrowUp' ? step : ev.key === 'ArrowDown' ? -step : 0;
      setView((v) => clamp(v.k, v.x + dx, v.y + dy));
    } else if (ev.key === 'ArrowDown' || ev.key === 'ArrowRight') focusEntry(i + 1);
    else if (ev.key === 'ArrowUp' || ev.key === 'ArrowLeft') focusEntry(i - 1);
    else return;
    ev.preventDefault();
  };
  const onWheel = (ev: WheelEvent<SVGSVGElement>) => {
    const box = ev.currentTarget.getBoundingClientRect();
    zoomAt(ev.deltaY < 0 ? 1.15 : 1 / 1.15, ev.clientX - box.left, ev.clientY - box.top);
  };
  const onDown = (ev: PointerEvent<SVGSVGElement>) => {
    if (view.k === 1) return;
    drag.current = { x: ev.clientX, y: ev.clientY, vx: view.x, vy: view.y };
    ev.currentTarget.setPointerCapture?.(ev.pointerId);
  };
  const onMove = (ev: PointerEvent<SVGSVGElement>) => {
    const d = drag.current;
    if (d) setView((v) => clamp(v.k, d.vx + ev.clientX - d.x, d.vy + ev.clientY - d.y));
  };
  const onUp = () => {
    drag.current = null;
  };
  const button = (kind: 'in' | 'out' | 'reset', label: string, title: { en: string; es: string }, act: () => void) => (
    <button type="button" className="chip" data-map-zoom={kind} aria-label={pick(title, lang)} title={pick(title, lang)} onClick={act} style={{ minWidth: '2rem', padding: '0 0.4rem' }}>
      {label}
    </button>
  );
  const ls = layers(inv.entries);
  const header = (text: string) => fitLabel(text, Math.max(20, colW - 6), 11, 1);
  const curve = (a: { x: number; y: number }, b: { x: number; y: number }) => {
    const x0 = a.x + R + 3;
    const x1 = b.x - R - 6;
    const mid = (x0 + x1) / 2;
    return `M${x0} ${a.y} C${mid} ${a.y} ${mid} ${b.y} ${x1} ${b.y}`;
  };
  return (
    <div style={{ position: 'relative', minWidth: 0 }} data-map-frame>
      <div style={{ position: 'absolute', top: 0, right: 0, display: 'flex', gap: '0.25rem', zIndex: 1 }} role="toolbar" aria-label={pick({ en: 'Zoom of the map', es: 'Zoom del mapa' }, lang)}>
        {button('in', '+', { en: 'Zoom in', es: 'Acercar' }, () => zoomAt(1.25))}
        {button('out', '\u2212', { en: 'Zoom out', es: 'Alejar' }, () => zoomAt(0.8))}
        {button('reset', '1:1', { en: 'Reset the view', es: 'Restablecer la vista' }, reset)}
      </div>
    <svg width={width} height={height} role="group" aria-label={pick({ en: 'The dependency map of the model inventory', es: 'El mapa de dependencias del inventario de modelos' }, lang)} data-map="dependencies" data-nodes={inv.entries.length} data-edges={inv.edges.length} data-zoom={view.k} onWheel={onWheel} onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp} onDoubleClick={reset} style={{ touchAction: view.k > 1 ? 'none' : 'pan-y', cursor: view.k > 1 ? 'grab' : 'default', display: 'block' }}>
      <defs>
        {(['document', 'code'] as const).map((k) => (
          <marker key={k} id={`gov-arrow-${k}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 L8 4 L0 8 z" fill={EDGE_COLOR[k]} />
          </marker>
        ))}
      </defs>
      <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
      <text x={engine.x} y={14} textAnchor="middle" fontSize={11} fill="var(--color-fg-subtle)">
        {header(inv.engine_node.key).lines[0]}
      </text>
      {ls.map((_, g) => {
        const label = header(`${pick({ en: 'Level', es: 'Nivel' }, lang)} ${g}`);
        return (
          <text key={g} x={PAD + (g + 1.5) * colW} y={14} textAnchor="middle" fontSize={11} fill="var(--color-fg-subtle)">
            {label.lines[0]}
          </text>
        );
      })}
      {inv.entries.map((e) => {
        const n = nodes.get(e.key);
        if (!n) return null;
        return <path key={`engine-${e.key}`} data-edge="engine" d={curve(engine, n)} fill="none" stroke="var(--color-fg-faint)" strokeWidth={1} opacity={0.3} />;
      })}
      {inv.edges.map((ed) => {
        const a = nodes.get(ed.upstream);
        const b = nodes.get(ed.downstream);
        if (!a || !b) return null;
        return <path key={`${ed.upstream}>${ed.downstream}`} data-edge={ed.kind} data-from={ed.upstream} data-to={ed.downstream} d={curve(a, b)} fill="none" stroke={EDGE_COLOR[ed.kind as 'document' | 'code'] ?? 'var(--color-fg)'} strokeWidth={2} markerEnd={`url(#gov-arrow-${ed.kind === 'code' ? 'code' : 'document'})`} />;
      })}
      <rect x={engine.x - 11} y={engine.y - 11} width={22} height={22} rx={4} fill="var(--color-surface-2)" stroke="var(--color-fg-subtle)" strokeWidth={1.5} data-node="engine">
        <title>{`${inv.engine_node.key} ${inv.engine_node.version}`}</title>
      </rect>
      {inv.entries.map((e, i) => {
        const n = nodes.get(e.key);
        if (!n) return null;
        const worst = worstOpen(e);
        const ring = worst ? SEVERITY_RING[worst] : null;
        return (
          <g
            key={e.key}
            data-node={e.key}
            data-tier={e.tier_block.tier}
            data-worst={worst ?? 'none'}
            tabIndex={0}
            role="button"
            aria-label={entryWords(e)}
            ref={(el) => {
              if (el) nodeRefs.current.set(e.key, el);
              else nodeRefs.current.delete(e.key);
            }}
            onFocus={() => setCurrent(e.key)}
            onPointerEnter={() => setCurrent(e.key)}
            onKeyDown={(ev) => onKey(ev, i)}
            style={{ outline: 'none', cursor: 'pointer' }}
          >
            <title>{`${pick(entryText(e.key), lang)}: ${pick(e.title, lang)}, ${tierName(e.tier_block.tier, lang)}`}</title>
            {current === e.key && <circle cx={n.x} cy={n.y} r={R + 6} fill="none" stroke="var(--color-fg)" strokeWidth={1.5} strokeDasharray="3 2" data-focus-ring />}
            {ring && <circle cx={n.x} cy={n.y} r={R + 3} fill="none" stroke={ring.color} strokeWidth={ring.width} />}
            <circle cx={n.x} cy={n.y} r={R} fill={tierColor(e.tier_block.tier)} stroke="var(--color-border)" strokeWidth={1} />
            <text x={n.x} y={n.y} textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600} fill={inkOn(e.tier_block.tier)} style={{ pointerEvents: 'none' }}>
              {n.n}
            </text>
          </g>
        );
      })}
      </g>
    </svg>
      {readout ? <MapReadout inv={inv} current={current} /> : null}
    </div>
  );
}

/** What the read-out line says of a node: its number, name, title, tier, worst open finding and its dependencies. */
function entryWordsOf(inv: GovInventory, e: InvEntry, lang: 'en' | 'es'): string {
  const worst = worstOpen(e);
  const open = worst ? `${pick({ en: 'worst open finding ', es: 'peor hallazgo abierto ' }, lang)}${worst}` : pick({ en: 'no open finding', es: 'sin hallazgos abiertos' }, lang);
  const ups = inv.edges.filter((d) => d.downstream === e.key).length;
  const downs = inv.edges.filter((d) => d.upstream === e.key).length;
  // the node's number is its place in the inventory, as placeNodes numbers it
  const n = inv.entries.findIndex((x) => x.key === e.key) + 1;
  return `${n}. ${pick(entryText(e.key), lang)}: ${pick(e.title, lang)}, ${tierName(e.tier_block.tier, lang)}, ${open}; ${pick({ en: 'depends on ', es: 'depende de ' }, lang)}${ups}, ${pick({ en: 'feeds ', es: 'alimenta a ' }, lang)}${downs}`;
}

/**
 * The read-out line of the map. It wraps: a node's description runs to about 150 characters, and a line capped at two lines of
 * 28 px cut its tier, findings and dependencies at 390 (R4 c28 M2). It keeps at least that height, so the page does not jump.
 */
export function MapReadout({ inv, current }: { inv: GovInventory; current: string | null }) {
  const lang = useShellLang();
  const shown = current ? inv.entries.find((e) => e.key === current) : undefined;
  return (
    <p className="ct-note" data-map-readout aria-live="polite" style={{ margin: 0, minHeight: READOUT_HEIGHT, lineHeight: `${READOUT_HEIGHT / 2}px` }}>
      {shown
        ? entryWordsOf(inv, shown, lang)
        : pick({ en: 'Point at a node, or Tab to it, to read it; + and - zoom, the arrows pan when zoomed, 0 resets.', es: 'Apunte a un nodo, o llegue a él con Tab, para leerlo; + y - acercan y alejan, las flechas desplazan con zoom, 0 restablece.' }, lang)}
    </p>
  );
}

/** The map in a sized box: the stage measures the drawing's box and draws once it has a width; the read-out wraps below it. */
export function DependencyMap({ inv }: { inv: GovInventory }) {
  const height = mapHeight(inv.entries);
  const [current, setCurrent] = useState<string | null>(null);
  return (
    <div style={{ minWidth: 0 }} data-map-host>
      <div style={{ height, minWidth: 0 }}>
        <Stage label={{ en: 'The dependency map of the model inventory', es: 'El mapa de dependencias del inventario de modelos' }}>{({ width }) => <MapDrawing inv={inv} width={width} height={height} current={current} onCurrent={setCurrent} readout={false} />}</Stage>
      </div>
      <MapReadout inv={inv} current={current} />
    </div>
  );
}
