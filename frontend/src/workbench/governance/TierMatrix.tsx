// The tier matrix (dossier 06 I.4, B.3): materiality M by complexity C, a 4 by 4 heat map with the number of entries in
// each cell under their adopted reading, and the tier the stated rule gives that cell printed in its corner. The shell has
// no heat map, so the grid is drawn as SVG at the size its stage measures. A cell is a button: it picks the entries it
// counts for the inventory table beside it (the click-through of I.4). Beside the matrix, the sensitivity table shows
// the tier counts under the four readings of the rubric (decision W15-3), the adopted one marked.
import { Stage, fitLabel, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import type { KeyboardEvent } from 'react';
import { viridis } from '../c04/MatrixMap';
import { matrixCells, tierName, tierOf, type GovInventory } from './model';

const LEFT = 76;
const TOP = 40;
const CELL_H = 52;
export const MATRIX_HEIGHT = TOP + 4 * CELL_H + 8;

export interface CellPick {
  m: number;
  c: number;
}

export function MatrixDrawing({ inv, width, picked, onPick }: { inv: GovInventory; width: number; picked: CellPick | null; onPick?: (cell: CellPick | null) => void }) {
  const lang = useShellLang();
  const { counts } = matrixCells(inv.entries);
  const max = Math.max(1, ...counts.flat());
  const cw = Math.max(20, (width - LEFT - 4) / 4);
  const ink = (t: number) => (t >= 0.55 ? '#141414' : '#f4f4f4');
  const key = (cell: CellPick) => (e: KeyboardEvent<SVGGElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onPick?.(picked && picked.m === cell.m && picked.c === cell.c ? null : cell);
    }
  };
  const tag = (tier: number) => fitLabel(lang === 'es' ? `Niv. ${tier}` : `Tier ${tier}`, cw - 8, 10, 1).lines[0];
  return (
    <svg width={width} height={MATRIX_HEIGHT} role="group" aria-label={pick({ en: 'The tier matrix: materiality by complexity, with the number of entries in each cell', es: 'La matriz de niveles: materialidad por complejidad, con el número de entradas en cada celda' }, lang)} data-matrix="tiers" data-cells={16}>
      <text x={LEFT + 2 * cw} y={14} textAnchor="middle" fontSize={11} fill="var(--color-fg-subtle)">
        {pick({ en: 'Complexity C', es: 'Complejidad C' }, lang)}
      </text>
      <text x={LEFT - 8} y={TOP - 8} textAnchor="end" fontSize={11} fill="var(--color-fg-subtle)">
        {fitLabel(pick({ en: 'Materiality M', es: 'Materialidad M' }, lang), LEFT - 10, 11, 1).lines[0]}
      </text>
      {[1, 2, 3, 4].map((c) => (
        <text key={c} x={LEFT + (c - 0.5) * cw} y={TOP - 8} textAnchor="middle" fontSize={11} fill="var(--color-fg)">
          {c}
        </text>
      ))}
      {[4, 3, 2, 1].map((m, r) => (
        <g key={m}>
          <text x={LEFT - 8} y={TOP + (r + 0.5) * CELL_H} dominantBaseline="middle" textAnchor="end" fontSize={11} fill="var(--color-fg)">
            {m}
          </text>
          {[1, 2, 3, 4].map((c) => {
            const n = counts[m][c];
            const t = n / max;
            const on = picked?.m === m && picked.c === c;
            const x = LEFT + (c - 1) * cw;
            const y = TOP + r * CELL_H;
            const tier = tierOf(m, c);
            return (
              <g
                key={c}
                data-cell={`${m}-${c}`}
                data-count={n}
                data-tier={tier}
                role="button"
                tabIndex={0}
                aria-pressed={on}
                aria-label={`M ${m}, C ${c}, ${tierName(tier, lang)}: ${n}`}
                style={{ cursor: 'pointer' }}
                onClick={() => onPick?.(on ? null : { m, c })}
                onKeyDown={key({ m, c })}
              >
                <rect x={x + 0.5} y={y + 0.5} width={cw - 1} height={CELL_H - 1} fill={n === 0 ? 'var(--color-surface-2)' : viridis(0.15 + 0.85 * t)} stroke={on ? 'var(--color-fg)' : 'var(--color-border)'} strokeWidth={on ? 2.5 : 1} strokeDasharray={n === 0 ? '3 3' : undefined} />
                <text x={x + 5} y={y + 14} fontSize={10} fill={n === 0 ? 'var(--color-fg-subtle)' : ink(0.15 + 0.85 * t)} style={{ pointerEvents: 'none' }}>
                  {tag(tier)}
                </text>
                <text x={x + cw / 2} y={y + CELL_H / 2 + 9} textAnchor="middle" fontSize={16} fontWeight={700} fill={n === 0 ? 'var(--color-fg-subtle)' : ink(0.15 + 0.85 * t)} style={{ pointerEvents: 'none', fontVariantNumeric: 'tabular-nums' }}>
                  {n}
                </text>
              </g>
            );
          })}
        </g>
      ))}
    </svg>
  );
}

export function TierMatrix({ inv, picked, onPick }: { inv: GovInventory; picked: CellPick | null; onPick: (cell: CellPick | null) => void }) {
  return (
    <div style={{ height: MATRIX_HEIGHT, minWidth: 0 }} data-matrix-host>
      <Stage label={{ en: 'The tier matrix of the model inventory', es: 'La matriz de niveles del inventario de modelos' }}>{({ width }) => <MatrixDrawing inv={inv} width={width} picked={picked} onPick={onPick} />}</Stage>
    </div>
  );
}

const READING_USE = { literal: { en: 'literal', es: 'literal' }, graded: { en: 'graded', es: 'graduado' } } as const;
const READING_C = { mean: { en: 'mean', es: 'media' }, maximum: { en: 'maximum', es: 'máximo' } } as const;

/** The tier counts under the four readings of the rubric; the adopted reading is marked, and each reading says what it changes. */
export function SensitivityTable({ inv }: { inv: GovInventory }) {
  const lang = useShellLang();
  const first = inv.entries[0];
  const readings = first ? first.tier_block.tier_sensitivity : [];
  const adopted = inv.conventions.adopted_reading.reading;
  return (
    <table className="caos-table" data-state="ready" data-sensitivity>
      <caption className="ct-note">
        {pick(
          {
            en: 'Entries per tier under the four readings of the rubric. The tier rests on two choices: how the regulatory use is graded, and whether complexity is the mean or the maximum of its factors.',
            es: 'Entradas por nivel bajo las cuatro lecturas de la rúbrica. El nivel descansa en dos decisiones: cómo se gradúa el uso regulatorio, y si la complejidad es la media o el máximo de sus factores.',
          },
          lang,
        )}
      </caption>
      <thead>
        <tr>
          <th>{pick({ en: 'Reading', es: 'Lectura' }, lang)}</th>
          <th className="caos-col-text">{pick({ en: 'Regulatory use', es: 'Uso regulatorio' }, lang)}</th>
          <th className="caos-col-text">{pick({ en: 'Complexity', es: 'Complejidad' }, lang)}</th>
          {[1, 2, 3, 4].map((t) => (
            <th key={t}>{tierName(t, lang)}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {inv.tier_counts.map((row) => {
          const def = readings.find((r) => r.reading === row.reading);
          const isAdopted = row.reading === adopted;
          return (
            <tr key={row.reading} data-reading={row.reading} data-adopted={isAdopted ? 'true' : 'false'} className={isAdopted ? 'ct-current' : undefined}>
              <td>
                {row.reading}
                {isAdopted ? ` (${pick({ en: 'adopted', es: 'adoptada' }, lang)})` : ''}
              </td>
              <td className="caos-col-text">{def ? pick(READING_USE[def.regulatory_use as keyof typeof READING_USE], lang) : '-'}</td>
              <td className="caos-col-text">{def ? pick(READING_C[def.complexity as keyof typeof READING_C], lang) : '-'}</td>
              {row.counts.map((n, i) => (
                <td key={i}>{formatNumber(n, lang, { decimals: 0 })}</td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
