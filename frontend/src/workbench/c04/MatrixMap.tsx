// The heat map of a transition matrix (C04, CT-411; the interactive visualisation rubric's heat maps): rows the grade
// at the start of the period, columns the state at its end, each cell coloured on viridis (perceptually uniform, the
// same in both themes) with its value printed where the cell is wide enough. The cell under the pointer is read out
// with its count and its row's total; a click on a row or its label picks that grade for the linked views. Three
// colour scales: the migrations only (linear, the diagonal kept out of the range: 80% to 95% of a row stays in its
// grade, which would turn every migration the same dark colour), every cell linear, and every cell on a log scale
// (zeros at the bottom of the scale, printed 0). The shell has no matrix chart; this one is drawn as SVG at the size
// its stage measures, so the gate judges the drawing, not the host.
import { Stage, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { useId, useMemo, useState, type KeyboardEvent } from 'react';

export type MapScale = 'migrations' | 'linear' | 'log';

// viridis at 17 evenly spaced stops (matplotlib 3.11.2, colormaps['viridis'](numpy.linspace(0, 1, 17))), interpolated
// linearly between them
const VIRIDIS = ['#440154', '#48186a', '#472d7b', '#424086', '#3b528b', '#33638d', '#2c728e', '#26828e', '#21918c', '#1fa088', '#28ae80', '#3fbc73', '#5ec962', '#84d44b', '#addc30', '#d8e219', '#fde725'];
const RGB = VIRIDIS.map((h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)));

/** The viridis colour at t in [0, 1]. */
export function viridis(t: number): string {
  const x = Math.min(1, Math.max(0, t)) * (RGB.length - 1);
  const i = Math.min(RGB.length - 2, Math.floor(x));
  const f = x - i;
  const c = RGB[i].map((a, k) => Math.round(a + f * (RGB[i + 1][k] - a)));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

/** Dark ink from the green half of viridis up, light ink below it (its luminance rises with t). */
const inkOn = (t: number) => (t >= 0.55 ? '#141414' : '#f4f4f4');

export interface MatrixMapProps {
  /** what the matrix is: the stage's name and the drawing's accessible label */
  label: BiText;
  rows: string[];
  cols: string[];
  /** probabilities; a row of nulls is a grade with no ratings at the start */
  values: (number | null)[][];
  /** the counts behind each cell, read out with the row's total */
  counts?: (number | null)[][] | null;
  scale: MapScale;
  /** the column of each row's own grade (the diagonal); -1 where the row has none */
  diagonal: number[];
  /** columns kept out of the migrations scale's range, drawn like the diagonal: the withdrawals (up to 28% of a row
   * in CEREP's speculative grades), which are not migrations and would otherwise set the top of the range */
  outside?: number[];
  selectedRow?: number | null;
  onPickRow?: (row: number) => void;
}

interface Range {
  lo: number;
  hi: number;
  log: boolean;
}

function rangeOf(values: (number | null)[][], diagonal: number[], scale: MapScale, outside: readonly number[] = []): Range {
  const cells = values.flatMap((r, i) => r.map((v, j) => ({ v, diag: diagonal[i] === j || outside.includes(j) })));
  const usable = cells.filter((c) => c.v !== null && Number.isFinite(c.v) && !(scale === 'migrations' && c.diag)).map((c) => c.v as number);
  const hi = usable.length ? Math.max(...usable) : 1;
  if (scale !== 'log') return { lo: 0, hi: hi > 0 ? hi : 1, log: false };
  const positive = usable.filter((v) => v > 0);
  const lo = positive.length ? Math.min(...positive) : hi / 1e4;
  return { lo: Math.min(lo, hi / 10), hi: hi > 0 ? hi : 1, log: true };
}

/** Where a value sits on the colour scale, in [0, 1]; zeros sit at 0 on the log scale. */
function position(v: number, r: Range): number {
  if (!r.log) return (v - r.lo) / (r.hi - r.lo);
  if (v <= 0) return 0;
  return (Math.log10(v) - Math.log10(r.lo)) / (Math.log10(r.hi) - Math.log10(r.lo));
}

/** A cell's printed value: one decimal from 10%, two below, "<0.01 %" (the shell's percent spacing) for a positive value that would print as zero. */
function cellText(v: number, lang: 'en' | 'es'): string {
  if (v === 0) return '0';
  if (v < 0.00005) return lang === 'es' ? '<0,01 %' : '<0.01 %';
  return formatNumber(v, lang, { percent: true, decimals: v >= 0.1 ? 1 : 2 });
}

function ticksOf(r: Range): number[] {
  if (!r.log) return [0, r.hi / 2, r.hi];
  const out: number[] = [];
  for (let e = Math.ceil(Math.log10(r.lo)); e <= Math.floor(Math.log10(r.hi)); e += 1) out.push(10 ** e);
  return out.length >= 2 ? out : [r.lo, r.hi];
}

const LEFT = 62;
const TOP = 34;
const BAR = 12;
const BAR_GAP = 12;
const BAR_LABELS = 50;
const RIGHT = BAR_GAP + BAR + BAR_LABELS;
/** Room under the grid for half of the colour bar's lowest tick label, which is centred on its tick (the gate's G10
 * measured "0 %" cut by 4 px when the bar ran to the drawing's edge). */
const BOTTOM = 8;

/** The second line of the column labels when they alternate (see MatrixDrawing). */
const STAGGER = 12;

/** The page's font family as the browser resolves it (the gate's wide font included); empty on the server. */
function pageFont(): string {
  return typeof document === 'undefined' ? '' : getComputedStyle(document.body).fontFamily;
}

let measurer: CanvasRenderingContext2D | null | undefined;
/** A label's width in pixels at a size in the page's font, measured on a canvas; on the server (no canvas), an estimate
 * of 0.62 em a character. */
export function textWidth(text: string, px: number, family: string): number {
  if (family && typeof document !== 'undefined') {
    if (measurer === undefined) measurer = document.createElement('canvas').getContext('2d');
    if (measurer) {
      measurer.font = `${px}px ${family}`;
      return measurer.measureText(text).width;
    }
  }
  return text.length * px * 0.62;
}

/** The drawing at a measured size (exported for the server-rendered tests, where a stage never gets a size). */
export function MatrixDrawing({ p, width, height, hover, setHover }: { p: MatrixMapProps; width: number; height: number; hover: [number, number] | null; setHover: (h: [number, number] | null) => void }) {
  const lang = useShellLang();
  const gradient = useId().replace(/:/g, '');
  const range = useMemo(() => rangeOf(p.values, p.diagonal, p.scale, p.outside), [p.values, p.diagonal, p.scale, p.outside]);
  const n = p.rows.length;
  const m = p.cols.length;
  const cw = Math.max(1, (width - LEFT - RIGHT) / m);
  const family = pageFont();
  // column labels too wide for their column alternate between two lines, the grid moving down a line
  const stagger = p.cols.some((c) => textWidth(c, 12, family) > cw - 3);
  const top = stagger ? TOP + STAGGER : TOP;
  const ch = Math.max(1, (height - top - BOTTOM) / n);
  const printValues = ch >= 15;
  const font = Math.max(9, Math.min(12, ch * 0.42));
  const pickRow = (i: number) => p.onPickRow?.(i);
  const onKey = (i: number) => (e: KeyboardEvent<SVGTextElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      pickRow(i);
    }
  };
  const barH = n * ch;
  const ticks = ticksOf(range);
  return (
    <svg width={width} height={height} role="group" aria-label={pick(p.label, lang)} data-matrix={pick(p.label, 'en')} data-scale={p.scale} data-cells={n * m} onMouseLeave={() => setHover(null)}>
      <defs>
        <linearGradient id={gradient} x1="0" y1="1" x2="0" y2="0">
          {VIRIDIS.map((c, k) => (
            <stop key={c} offset={k / (VIRIDIS.length - 1)} stopColor={c} />
          ))}
        </linearGradient>
        {p.cols.map((_, j) => (
          <clipPath key={j} id={`${gradient}-col-${j}`}>
            <rect x={LEFT + j * cw + 1} y={0} width={cw - 2} height={top - 2} />
          </clipPath>
        ))}
      </defs>
      <text x={LEFT + (m * cw) / 2} y={11} textAnchor="middle" fontSize={11} fill="var(--color-fg-subtle)">
        {pick({ en: 'At the end of the period', es: 'Al final del período' }, lang)}
      </text>
      <text x={LEFT - 8} y={top - 8} textAnchor="end" fontSize={11} fill="var(--color-fg-subtle)">
        {pick({ en: 'Start', es: 'Inicio' }, lang)}
      </text>
      {p.cols.map((c, j) => (
        <text key={c} x={LEFT + (j + 0.5) * cw} y={top - 8 - (stagger && j % 2 === 0 ? STAGGER : 0)} textAnchor="middle" fontSize={Math.min(12, font + 1)} fill="var(--color-fg)" clipPath={`url(#${gradient}-col-${j})`}>
          {c}
        </text>
      ))}
      {p.rows.map((r, i) => {
        const selected = p.selectedRow === i;
        const empty = p.values[i].every((v) => v === null);
        return (
          <g key={r} data-row={r} data-selected={selected ? '1' : undefined}>
            {selected && <rect x={2} y={top + i * ch + 2} width={3} height={ch - 4} fill="var(--color-accent)" />}
            <text
              x={LEFT - 8}
              y={top + (i + 0.5) * ch}
              dominantBaseline="middle"
              textAnchor="end"
              fontSize={Math.min(12, font + 1)}
              fontWeight={selected ? 700 : 400}
              fill={empty ? 'var(--color-fg-faint)' : 'var(--color-fg)'}
              tabIndex={p.onPickRow ? 0 : undefined}
              role={p.onPickRow ? 'button' : undefined}
              aria-pressed={p.onPickRow ? selected : undefined}
              style={p.onPickRow ? { cursor: 'pointer' } : undefined}
              onClick={() => pickRow(i)}
              onKeyDown={onKey(i)}
            >
              {r}
            </text>
            {p.values[i].map((v, j) => {
              const x = LEFT + j * cw;
              const y = top + i * ch;
              const diag = p.diagonal[i] === j || (p.outside ?? []).includes(j);
              const outOfRange = diag && p.scale === 'migrations';
              const t = v === null ? 0 : position(v, range);
              const fill = v === null ? 'none' : outOfRange ? 'var(--color-surface-2)' : viridis(t);
              const ink = v === null || outOfRange ? 'var(--color-fg)' : inkOn(t);
              const on = hover !== null && hover[0] === i && hover[1] === j;
              // a value prints where it fits its cell in the page's font; the read-out gives every cell
              const label = v === null ? '-' : cellText(v, lang);
              return (
                <g key={j} onMouseEnter={() => setHover([i, j])} onClick={() => { setHover([i, j]); pickRow(i); }} style={p.onPickRow ? { cursor: 'pointer' } : undefined}>
                  <rect x={x + 0.5} y={y + 0.5} width={cw - 1} height={ch - 1} fill={fill} stroke={on ? 'var(--color-fg)' : outOfRange || v === null ? 'var(--color-border)' : 'none'} strokeWidth={on ? 2 : 1} strokeDasharray={v === null ? '3 3' : undefined} />
                  {printValues && textWidth(label, font, family) <= cw - 4 && (
                    <text x={x + cw / 2} y={y + ch / 2} dominantBaseline="middle" textAnchor="middle" fontSize={font} fill={ink} style={{ pointerEvents: 'none', fontVariantNumeric: 'tabular-nums' }}>
                      {label}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        );
      })}
      <rect x={LEFT + m * cw + BAR_GAP} y={top} width={BAR} height={barH} fill={`url(#${gradient})`} />
      {ticks.map((v) => {
        const y = top + barH * (1 - position(v, range));
        return (
          <g key={v}>
            <line x1={LEFT + m * cw + BAR_GAP + BAR} x2={LEFT + m * cw + BAR_GAP + BAR + 4} y1={y} y2={y} stroke="var(--color-fg-subtle)" />
            <text x={LEFT + m * cw + BAR_GAP + BAR + 6} y={y} dominantBaseline="middle" fontSize={10} fill="var(--color-fg-subtle)">
              {formatNumber(v, lang, { percent: true, digits: 2 })}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** The readout of the cell under the pointer: the move, its probability, and its count of the row's ratings. */
export function matrixReadout(p: MatrixMapProps, hover: [number, number] | null, lang: 'en' | 'es'): string {
  if (!hover) {
    return pick({ en: 'Point at a cell for its value and count; click a row to pick its grade.', es: 'Apunte a una celda para ver su valor y conteo; haga clic en una fila para elegir su grado.' }, lang);
  }
  const [i, j] = hover;
  const v = p.values[i]?.[j];
  const move = `${p.rows[i]} ${lang === 'es' ? 'a' : 'to'} ${p.cols[j]}`;
  if (v === null || v === undefined) return `${move}: ${pick({ en: 'no ratings in this grade at the start', es: 'sin calificaciones en este grado al inicio' }, lang)}`;
  const value = formatNumber(v, lang, { percent: true, decimals: v > 0 && v < 0.001 ? 4 : 2 });
  const row = p.counts?.[i];
  const k = p.counts?.[i]?.[j];
  if (!row || k === null || k === undefined) return `${move}: ${value}`;
  const total = row.reduce<number>((a, b) => a + (b ?? 0), 0);
  const of = lang === 'es' ? 'de' : 'of';
  const ratings = lang === 'es' ? 'calificaciones' : 'ratings';
  return `${move}: ${value} (${formatNumber(k, lang, { decimals: 0 })} ${of} ${formatNumber(total, lang, { decimals: 0 })} ${ratings})`;
}

export function MatrixMap(props: MatrixMapProps) {
  const lang = useShellLang();
  const [hover, setHover] = useState<[number, number] | null>(null);
  const readout = matrixReadout(props, hover, lang);
  return (
    <div className="ct-map">
      <Stage label={props.label} className="ct-map-stage">
        {({ width, height }) => <MatrixDrawing p={props} width={width} height={height} hover={hover} setHover={setHover} />}
      </Stage>
      {/* the line is cut with an ellipsis where the card is narrow, so it carries its text as a title (the gate's G5),
          as the shell's chart readout does */}
      <p className="caos-chart-readout" data-readout="matrix" title={readout}>
        {readout}
      </p>
    </div>
  );
}
