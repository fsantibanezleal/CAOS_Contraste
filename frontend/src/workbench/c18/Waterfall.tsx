// One horizontal waterfall for the two places C18 builds a total from layers: the capital stack (the layers of the internal
// target, the requirement, the legal minimum stack) and the Euler allocation of the expected shortfall. Each row is a bar from
// `from` to `to` on one axis, labelled with the shell's text kit and valued at its end; a row of `kind` total or reference
// starts at zero. Every number drawn is a field of the document: the running sum that places a layer is layout, nothing is
// computed that the document does not contain. The numbers also sit in a table beside the drawing, so a reader without the
// drawing loses nothing.
import { Stage, fitLabel, niceTicks, pick, useShellLang, type BiText, type ShellColorToken } from '@fasl-work/caos-app-shell';

export interface WaterfallRow {
  id: string;
  label: BiText;
  from: number;
  to: number;
  tone: ShellColorToken;
  /** The value written at the bar, already formatted. */
  value: string;
  /** A title for the bar: the whole label and its status. */
  hint?: string;
}

/** The rows of a waterfall of `layers` (each a size) that ends in a total, as running sums. */
export function stackRows(layers: Array<{ id: string; label: BiText; size: number; tone: ShellColorToken; value: string; hint?: string }>, total?: { id: string; label: BiText; value: string; tone: ShellColorToken }): WaterfallRow[] {
  let run = 0;
  const rows: WaterfallRow[] = layers.map((l) => {
    const from = run;
    run += l.size;
    return { id: l.id, label: l.label, from, to: run, tone: l.tone, value: l.value, ...(l.hint ? { hint: l.hint } : {}) };
  });
  if (total) rows.push({ id: total.id, label: total.label, from: 0, to: run, tone: total.tone, value: total.value });
  return rows;
}

export function HWaterfall({ rows, axisLabel, tickFormat, ariaLabel }: { rows: WaterfallRow[]; axisLabel: BiText; tickFormat: (v: number) => string; ariaLabel: BiText }) {
  const lang = useShellLang();
  return (
    <div className="ct-map">
      <Stage label={ariaLabel} className="ct-map-stage">
        {({ width, height }) => {
          const labelW = Math.min(Math.max(width * 0.34, 96), 200);
          const x0 = labelW + 8;
          const valueW = 70;
          const plotW = Math.max(width - x0 - valueW, 40);
          const top = 6;
          const axis = 34;
          const rowH = (height - top - axis) / Math.max(rows.length, 1);
          const lo = Math.min(0, ...rows.map((r) => Math.min(r.from, r.to)));
          const hi = Math.max(...rows.map((r) => Math.max(r.from, r.to)), 1e-9);
          const ticks = niceTicks(lo, hi, plotW, 54, 6);
          const dmin = Math.min(lo, ticks[0]);
          const dmax = Math.max(hi, ticks[ticks.length - 1]);
          const sx = (v: number) => x0 + ((v - dmin) / (dmax - dmin)) * plotW;
          return (
            <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={pick(ariaLabel, lang)}>
              {ticks.map((t) => (
                <g key={t}>
                  <line className="dg-grid" x1={sx(t)} x2={sx(t)} y1={top} y2={height - axis} />
                  <text className="dg-tick" x={sx(t)} y={height - axis + 14} textAnchor="middle">{tickFormat(t)}</text>
                </g>
              ))}
              <text className="dg-axis-label" x={x0 + plotW / 2} y={height - 6} textAnchor="middle">{fitLabel(pick(axisLabel, lang), plotW, 12, 1).lines[0]}</text>
              {rows.map((r, i) => {
                const y = top + i * rowH;
                const h = Math.max(rowH * 0.62, 3);
                const xa = sx(Math.min(r.from, r.to));
                const wd = Math.max(sx(Math.max(r.from, r.to)) - xa, 1.5);
                const label = pick(r.label, lang);
                return (
                  <g key={r.id} data-wf={r.id}>
                    <title>{r.hint ?? label}</title>
                    <text className="dg-bar-label" x={labelW} y={y + rowH / 2 + 4} textAnchor="end">{fitLabel(label, labelW, 11, 1).lines[0]}</text>
                    <rect x={xa} y={y + (rowH - h) / 2} width={wd} height={h} style={{ fill: `var(${r.tone})` }} />
                    <text className="dg-tick" x={Math.min(xa + wd + 4, width - valueW + 4)} y={y + rowH / 2 + 4}>{r.value}</text>
                  </g>
                );
              })}
            </svg>
          );
        }}
      </Stage>
    </div>
  );
}
