// The inventory map (dossier 06 I.4): the dependency graph of the models, drawn from the inventory's edges and the
// bake's layered layout (the `generation` of each entry's map block is its column, and the bake's y orders it inside the
// column). A node is coloured by its tier and ringed by the worst severity among its open findings; each dependency edge
// is drawn with its kind (`document`: the downstream reads the upstream's committed document; `code`: it imports the
// upstream's code). The engine node `riskvalidation` is drawn once, with a faint line to every entry, because every entry
// depends on it (decision W15-8). The "related" links are not dependencies and are not drawn here: they are listed apart,
// dashed (RelatedLinks). The nodes are numbered, and the numbers key the inventory table beside the map, so the drawing
// carries no label that can collide with another. Drawn as SVG at the size its stage measures (no graph library).
import { Stage, fitLabel, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { viridis } from '../c04/MatrixMap';
import { layers, tierName, worstOpen, type GovInventory, type InvEntry, type Severity } from './model';

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

export function MapDrawing({ inv, width, height }: { inv: GovInventory; width: number; height: number }) {
  const lang = useShellLang();
  const { engine, nodes, colW } = placeNodes(inv.entries, width, height);
  const ls = layers(inv.entries);
  const header = (text: string) => fitLabel(text, Math.max(20, colW - 6), 11, 1);
  const curve = (a: { x: number; y: number }, b: { x: number; y: number }) => {
    const x0 = a.x + R + 3;
    const x1 = b.x - R - 6;
    const mid = (x0 + x1) / 2;
    return `M${x0} ${a.y} C${mid} ${a.y} ${mid} ${b.y} ${x1} ${b.y}`;
  };
  return (
    <svg width={width} height={height} role="group" aria-label={pick({ en: 'The dependency map of the model inventory', es: 'El mapa de dependencias del inventario de modelos' }, lang)} data-map="dependencies" data-nodes={inv.entries.length} data-edges={inv.edges.length}>
      <defs>
        {(['document', 'code'] as const).map((k) => (
          <marker key={k} id={`gov-arrow-${k}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 L8 4 L0 8 z" fill={EDGE_COLOR[k]} />
          </marker>
        ))}
      </defs>
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
      {inv.entries.map((e) => {
        const n = nodes.get(e.key);
        if (!n) return null;
        const worst = worstOpen(e);
        const ring = worst ? SEVERITY_RING[worst] : null;
        return (
          <g key={e.key} data-node={e.key} data-tier={e.tier_block.tier} data-worst={worst ?? 'none'}>
            <title>{`${e.key}: ${pick(e.title, lang)}, ${tierName(e.tier_block.tier, lang)}`}</title>
            {ring && <circle cx={n.x} cy={n.y} r={R + 3} fill="none" stroke={ring.color} strokeWidth={ring.width} />}
            <circle cx={n.x} cy={n.y} r={R} fill={tierColor(e.tier_block.tier)} stroke="var(--color-border)" strokeWidth={1} />
            <text x={n.x} y={n.y} textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600} fill={inkOn(e.tier_block.tier)} style={{ pointerEvents: 'none' }}>
              {n.n}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** The map in a sized box: the stage measures it and draws once it has a width. */
export function DependencyMap({ inv }: { inv: GovInventory }) {
  const height = mapHeight(inv.entries);
  return (
    <div style={{ height, minWidth: 0 }} data-map-host>
      <Stage label={{ en: 'The dependency map of the model inventory', es: 'El mapa de dependencias del inventario de modelos' }}>{({ width }) => <MapDrawing inv={inv} width={width} height={height} />}</Stage>
    </div>
  );
}
