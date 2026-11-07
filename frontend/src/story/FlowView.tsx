// V1, the system: the flow of the bank. Exposures (what the models are exposed to) to the model families to what they set
// (provisions, capital, liquidity, decisions), each family node with its findings by severity. The domain's known form for a
// bank's models is the model inventory of SR 11-7 drawn as flow, not a generic node diagram. Selecting a family node selects its
// row in the panel (V2) and back; the market node carries the Basel zone of the shared day (V3's cursor). Every count is read
// from the governance documents (model.ts).
import { flowSpeed, useLinkedView, useShellLang } from '@fasl-work/caos-app-shell';
import type { KeyboardEvent } from 'react';
import { DayScrubber, cursorMarker, fit, int, type Size } from './chart';
import { SEVERITIES, type Bi, type Flow, type FlowNode, type Zone } from './model';
import { entriesLabel, findingsLabel, zoneBi, type Lang } from './text';

export interface Box {
  id: string;
  node: FlowNode;
  x: number;
  y: number;
  w: number;
  h: number;
}

const SEV_COLOR: Record<string, string> = { S1: 'var(--color-bad)', S2: 'var(--color-warn)', S3: 'var(--color-accent-2)', S4: 'var(--color-fg-faint)' };
export const nodeId = (n: FlowNode): string => `${n.kind}:${n.id}`;

/** The boxes of the three columns in a drawing of `size`, in the drawing's own pixels. The bottom rows are the day control's. */
export function flowGeometry(size: Size, flow: Flow): { boxes: Box[]; narrow: boolean; top: number; bottom: number } {
  const narrow = size.width < 560;
  const pad = narrow ? 6 : 14;
  const wE = narrow ? 74 : Math.min(200, size.width * 0.22);
  const wF = narrow ? 134 : Math.min(300, size.width * 0.3);
  const wO = narrow ? 72 : Math.min(210, size.width * 0.22);
  const top = narrow ? 24 : 28;
  const bottom = size.height - 40;
  const span = Math.max(40, bottom - top);
  const xE = pad;
  const xO = size.width - pad - wO;
  const xF = (xE + wE + xO) / 2 - wF / 2 + (wE - wO) / 4;
  const column = (nodes: FlowNode[], x: number, w: number, maxH: number): Box[] => {
    const pitch = span / nodes.length;
    const h = Math.max(20, Math.min(maxH, pitch - (narrow ? 4 : 6)));
    return nodes.map((node, i) => ({ id: nodeId(node), node, x, w, h, y: top + i * pitch + (pitch - h) / 2 }));
  };
  return {
    boxes: [...column(flow.exposures, xE, wE, narrow ? 28 : 40), ...column(flow.families, xF, wF, narrow ? 34 : 50), ...column(flow.outputs, xO, wO, narrow ? 48 : 70)],
    narrow,
    top,
    bottom,
  };
}

export interface MarketInfo {
  /** The model drawn, its zone and its trailing exceptions on the shared day; null when the window is not loaded. */
  label: Bi;
  zone: Zone | null;
  exceptions: number;
  day: number;
}

export function FlowView({
  size,
  flow,
  selected,
  entryExposure,
  market,
  dates,
  cursor,
  onSelect,
}: {
  size: Size;
  flow: Flow;
  /** The selected family node id (`family:market`) or null. */
  selected: string | null;
  /** The exposure node of a selected finding's entry (`exposure:sme`), ringed apart from the family's own path. */
  entryExposure: string | null;
  market: MarketInfo | null;
  dates: readonly string[] | null;
  cursor: number;
  onSelect: (id: string) => void;
}) {
  const lang = useShellLang() as Lang;
  const select = useLinkedView((s) => s.select);
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const { boxes, narrow, top } = flowGeometry(size, flow);
  const at = new Map(boxes.map((b) => [b.id, b]));
  const maxEntries = Math.max(1, ...flow.links.map((l) => l.entries));
  const selectedFamily = selected?.startsWith('family:') ? selected : null;
  const onPath = (l: { from: string; to: string }) => selectedFamily !== null && (l.from === selectedFamily || l.to === selectedFamily);
  const pathIds = new Set<string>();
  if (selectedFamily) {
    pathIds.add(selectedFamily);
    for (const l of flow.links) if (onPath(l)) (l.from === selectedFamily ? pathIds.add(l.to) : pathIds.add(l.from));
  }
  const pick = (id: string) => {
    select(id, 'scene');
    onSelect(id);
  };
  const key = (id: string) => (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      pick(id);
    }
  };
  const fs = narrow ? 9.5 : 12.5;
  const heads: [string, string, number, number][] = [
    [t('EXPOSED TO', 'EXPUESTO A'), 'exposure', 0, 0],
    [t('MODEL FAMILY', 'FAMILIA DE MODELOS'), 'family', 0, 0],
    [t('SETS', 'FIJA'), 'output', 0, 0],
  ];
  return (
    <div className="story-view" data-view="flow">
      <svg width={size.width} height={Math.max(40, size.height - 40)} viewBox={`0 0 ${size.width} ${Math.max(40, size.height - 40)}`} role="group" aria-label={t('The flow of the bank: exposures, model families and what they set, with the findings of each family', 'El flujo del banco: exposiciones, familias de modelos y lo que fijan, con los hallazgos de cada familia')} data-flow="">
        {heads.map(([label, kind]) => {
          const first = boxes.find((b) => b.node.kind === kind)!;
          return (
            <text key={kind} x={first.x} y={top - 9} fill="var(--color-fg-faint)" fontSize={narrow ? 8.5 : 10.5} fontWeight={700} letterSpacing=".8">
              {label}
            </text>
          );
        })}
        {flow.links.map((l) => {
          const a = at.get(l.from);
          const b = at.get(l.to);
          if (!a || !b) return null;
          const x1 = a.x + a.w;
          const y1 = a.y + a.h / 2;
          const x2 = b.x;
          const y2 = b.y + b.h / 2;
          const mid = (x1 + x2) / 2;
          const hot = onPath(l);
          const d = `M${x1},${y1}C${mid},${y1} ${mid},${y2} ${x2},${y2}`;
          // the flow moves from the exposure to what it sets, at a speed set by the entries it carries (the shell's flowSpeed)
          const speed = flowSpeed(l.entries, maxEntries);
          return (
            <g key={`${l.from}>${l.to}`}>
              <path d={d} fill="none" stroke={hot ? 'var(--color-accent)' : 'var(--color-border)'} strokeOpacity={hot ? 0.95 : selectedFamily ? 0.35 : 0.8} strokeWidth={(hot ? 1.5 : 0.6) + (4.5 * l.entries) / maxEntries} data-flow-link={`${l.from}>${l.to}`} />
              <path d={d} className="story-flow-pulse" fill="none" stroke={hot ? 'var(--color-bg)' : 'var(--color-fg-subtle)'} strokeOpacity={hot ? 0.9 : 0.5} strokeWidth={1.4} strokeLinecap="round" strokeDasharray="1.5 9" style={{ animationDuration: `${Math.round((160 / Math.max(0.1, speed))) / 100}s` }} data-flow-speed={Math.round(speed * 1000) / 1000} pointerEvents="none" />
            </g>
          );
        })}
        {boxes.map((b) => {
          const n = b.node;
          const isFamily = n.kind === 'family';
          const chosen = selected === b.id;
          const inPath = pathIds.has(b.id);
          const ringed = entryExposure === b.id;
          const stroke = chosen ? 'var(--color-accent)' : ringed ? 'var(--color-warn)' : inPath ? 'var(--color-accent)' : 'var(--color-border)';
          const full = n.label[lang];
          const maxChars = Math.floor((b.w - 14) / (fs * 0.56));
          // the whole name when it fits the node, else the short one
          const name = narrow || full.length > maxChars ? n.short[lang] : full;
          const sevTotal = Math.max(1, n.total);
          const props = isFamily
            ? { role: 'button' as const, tabIndex: 0, 'aria-pressed': chosen, 'data-linked-id': b.id, 'data-linked-view': 'scene', 'data-linked-selected': chosen ? 'true' : 'false', onClick: () => pick(b.id), onKeyDown: key(b.id), style: { cursor: 'pointer' } }
            : {};
          let x = b.x + 8;
          const isMarket = n.id === 'market' && isFamily;
          return (
            <g key={b.id} {...props} aria-label={isFamily ? `${full}: ${findingsLabel(n.total, lang)}, ${entriesLabel(n.entries.length, lang)}` : undefined} data-flow-node={b.id}>
              <title>{`${full} · ${entriesLabel(n.entries.length, lang)} · ${findingsLabel(n.total, lang)}${isMarket && market ? ` · ${market.label[lang]}` : ''}`}</title>
              <rect x={b.x} y={b.y} width={b.w} height={b.h} rx={8} fill={chosen ? 'var(--color-accent-soft)' : 'var(--color-surface)'} stroke={stroke} strokeWidth={chosen || ringed ? 2.5 : inPath ? 1.8 : 1.2} strokeDasharray={ringed && !chosen ? '4 3' : undefined} />
              <text x={b.x + 8} y={b.y + (narrow ? 12 : 17)} fill="var(--color-fg)" fontSize={fs} fontWeight={650}>
                {fit(name, maxChars)}
              </text>
              {b.h >= (narrow ? 30 : 38) && n.kind !== 'exposure' && (
                <text x={b.x + 8} y={b.y + (narrow ? 25 : 33)} fill="var(--color-fg-subtle)" fontSize={narrow ? 8.5 : 11} fontFamily="var(--font-mono)">
                  {entriesLabel(n.entries.length, lang, narrow)}
                  {/* the output column of a phone is too narrow for the findings count: it stays in the node's title and the panel */}
                  {narrow && n.kind === 'output' ? '' : ` · ${findingsLabel(n.total, lang, narrow)}`}
                </text>
              )}
              {n.kind === 'exposure' && b.h >= 26 && !narrow && (
                <text x={b.x + 8} y={b.y + 33} fill="var(--color-fg-subtle)" fontSize={11} fontFamily="var(--font-mono)">
                  {entriesLabel(n.entries.length, lang)}
                </text>
              )}
              {n.total > 0 && isFamily && (
                <g>
                  {SEVERITIES.map((s) => {
                    const w = ((b.w - 16) * n.sev[s]) / sevTotal;
                    const seg = w > 0 ? (
                      <rect key={s} x={x} y={b.y + b.h - 8} width={Math.max(1.5, w)} height={4} fill={SEV_COLOR[s]} data-severity={s} />
                    ) : null;
                    x += w;
                    return seg;
                  })}
                </g>
              )}
              {isMarket && market && market.zone && (
                <g>
                  <text x={b.x + b.w - 8} y={b.y + (narrow ? 12 : 17)} textAnchor="end" fill={market.zone === 'red' ? 'var(--color-bad)' : market.zone === 'amber' ? 'var(--color-warn)' : 'var(--color-good)'} fontSize={narrow ? 8.5 : 11} fontWeight={700} data-market-zone={market.zone}>
                    {zoneBi(market.zone)[lang]} · {int(market.exceptions, lang)}
                  </text>
                  <circle cx={b.x + b.w - 8} cy={b.y + b.h - 6} r={3.5} fill="var(--color-accent)" {...cursorMarker(market.day)} />
                </g>
              )}
              {isMarket && market && !market.zone && <circle cx={b.x + b.w - 8} cy={b.y + b.h - 6} r={3.5} fill="var(--color-accent)" {...cursorMarker(market.day)} />}
            </g>
          );
        })}
        <g transform={`translate(${size.width - (narrow ? 4 : 10)},${size.height - 54})`} textAnchor="end" fontSize={narrow ? 8 : 10} fill="var(--color-fg-subtle)">
          {SEVERITIES.map((s, i) => (
            <g key={s}>
              <rect x={-(i + 1) * (narrow ? 30 : 46) + 6} y={-7} width={8} height={4} fill={SEV_COLOR[s]} />
              <text x={-(i * (narrow ? 30 : 46)) - 2} y={-3}>
                {s}
              </text>
            </g>
          ))}
        </g>
      </svg>
      {dates && dates.length > 0 ? <DayScrubber dates={dates} index={cursor} onChange={() => undefined} /> : <p className="story-scrub story-note" data-state="unavailable">{market === null ? t('The market window is not loaded, so the day control has nothing to read.', 'La ventana de mercado no está cargada, así que el control de día no tiene qué leer.') : ''}</p>}
    </div>
  );
}

