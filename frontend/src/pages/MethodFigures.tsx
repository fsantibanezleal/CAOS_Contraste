// The measured figure of a Methodology topic (ADR-0017 section 2.1: a method names a figure): grouped bars of the numbers the topic's own
// table prints, drawn as an inline SVG on the shell's `dg-*` tokens, in both languages. Unlike the schematics of DocFigures, nothing here
// is illustrative: every bar is a value the topic transcribes from a committed document or from the study it cites, and carries it as
// `data-value`, so a test reads the figure against the table beside it and a drift between the two fails the build.
import { formatNumber, useShellLang } from '@fasl-work/caos-app-shell';
import type { CSSProperties } from 'react';
import { useT } from '../content/bi';

/** One series of bars: its label in both languages, the colour token of its fill and one value per group. */
export interface BarSeries {
  id: string;
  label: { en: string; es: string };
  token: '--color-accent' | '--color-magenta' | '--color-good' | '--color-warn' | '--color-bad';
  values: number[];
}

/** A reference line across the plot: the bound or the target the bars are read against. */
export interface BarReference {
  value: number;
  label: { en: string; es: string };
}

export interface GroupedBarsProps {
  /** The groups along the axis; a `|` in a label starts a second line. */
  groups: Array<{ en: string; es: string }>;
  series: BarSeries[];
  /** The value axis: its lowest and highest value and the decimals its labels and the bars' values print. */
  axis: { min: number; max: number; decimals: number; tickDecimals?: number; percent?: boolean; title: { en: string; es: string } };
  reference?: BarReference;
  /** The accessible description of the figure, in both languages. */
  label: { en: string; es: string };
}

const W = 480;
const H = 262;
const LEFT = 62;
const RIGHT = 468;
const TOP = 48;
const BASE = 196;

const r1 = (v: number): number => Math.round(v * 10) / 10;

/** Grouped bars: the groups side by side, one bar per series in each, negative values below the zero line. */
export function GroupedBars({ groups, series, axis, reference, label }: GroupedBarsProps) {
  const lang = useShellLang();
  const t = useT();
  const { min, max, decimals, percent } = axis;
  const y = (v: number): number => BASE - ((v - min) / (max - min)) * (BASE - TOP);
  const zero = y(Math.max(min, Math.min(0, max)));
  const slot = (RIGHT - LEFT) / groups.length;
  const inner = slot * 0.84;
  const bw = inner / series.length;
  const fmt = (v: number): string => formatNumber(v, lang, { decimals, percent: false });
  const fmtTick = (v: number): string => formatNumber(v, lang, { decimals: axis.tickDecimals ?? decimals, percent: false });
  const ticks = [min, (min + max) / 2, max];
  const legend = (RIGHT - LEFT) / series.length;
  // a value is printed over its bar only where the bar is wide enough for it: a neighbour's value never overlaps it (gate G10)
  const widest = Math.max(...series.flatMap((s) => s.values.map((v) => fmt(v).length)));
  const showValues = bw >= 5.6 * widest + 4;
  return (
    <div className="ct-docfig-box">
      <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label[lang]} data-measured="true">
        <line className="dg-axis" x1={LEFT} y1={BASE} x2={RIGHT} y2={BASE} />
        <line className="dg-axis" x1={LEFT} y1={TOP} x2={LEFT} y2={BASE} />
        {ticks.map((v) => (
          <g key={v}>
            <line className="dg-grid" x1={LEFT} y1={y(v)} x2={RIGHT} y2={y(v)} />
            <text className="dg-tick" x={LEFT - 6} y={y(v) + 4} textAnchor="end">{`${fmtTick(v)}${percent ? ' %' : ''}`}</text>
          </g>
        ))}
        {min < 0 && max > 0 ? <line className="dg-axis" x1={LEFT} y1={zero} x2={RIGHT} y2={zero} /> : null}
        {groups.map((g, gi) => {
          const x0 = LEFT + gi * slot + (slot - inner) / 2;
          const lines = g[lang].split('|');
          return (
            <g key={g.en}>
              {series.map((s, si) => {
                const v = s.values[gi];
                const top = Math.min(y(v), zero);
                const height = Math.abs(y(v) - zero);
                const style: CSSProperties = { fill: `color-mix(in oklab, var(${s.token}) 55%, transparent)`, stroke: `var(${s.token})`, strokeWidth: 1 };
                return (
                  <g key={s.id}>
                    <rect data-series={s.id} data-group={g.en} data-value={v} style={style} x={r1(x0 + si * bw + 1)} y={r1(top)} width={r1(Math.max(1, bw - 2))} height={r1(Math.max(height, 0.8))}>
                      <title>{`${s.label[lang]}, ${g[lang].replace('|', ' ')}: ${fmt(v)}${percent ? ' %' : ''}`}</title>
                    </rect>
                    {showValues ? (
                      <text className="dg-tick" x={r1(x0 + si * bw + bw / 2)} y={r1(v >= 0 ? top - 3 : top + height + 10)} textAnchor="middle">{fmt(v)}</text>
                    ) : null}
                  </g>
                );
              })}
              {lines.map((line, li) => (
                <text key={li} className="dg-bar-label" x={r1(LEFT + gi * slot + slot / 2)} y={BASE + 15 + li * 15} textAnchor="middle">{line}</text>
              ))}
            </g>
          );
        })}
        {reference ? (
          <g>
            <line className="dg-asymptote" x1={LEFT} y1={y(reference.value)} x2={RIGHT} y2={y(reference.value)} />
            <line className="dg-asymptote" x1={LEFT + 4} y1={34} x2={LEFT + 16} y2={34} />
            <text className="dg-bar-label" x={LEFT + 22} y={38}>{`${reference.label[lang]}: ${fmt(reference.value)}${percent ? ' %' : ''}`}</text>
          </g>
        ) : null}
        {series.map((s, si) => (
          <g key={s.id}>
            <rect style={{ fill: `color-mix(in oklab, var(${s.token}) 55%, transparent)`, stroke: `var(${s.token})`, strokeWidth: 1 }} x={LEFT + 4 + si * legend} y={14} width={12} height={12} />
            <text className="dg-bar-label" x={LEFT + 22 + si * legend} y={24}>{s.label[lang]}</text>
          </g>
        ))}
        <text className="dg-axis-label" x={14} y={(TOP + BASE) / 2} textAnchor="middle" transform={`rotate(-90 14 ${(TOP + BASE) / 2})`}>{axis.title[lang]}</text>
        <text className="dg-note" x={RIGHT} y={H - 6} textAnchor="end">{t('Values transcribed from the table of this topic', 'Valores transcritos de la tabla de este tema')}</text>
      </svg>
    </div>
  );
}
