// CT-411: the transition-matrix heat map. The colour scale is viridis at its ends, the three scales place the cells
// as declared (the migrations scale keeps the diagonal out of the range, the log scale puts zeros at the bottom), the
// drawing has one cell per entry with the selected row marked, and the readout gives the move, its value and its count.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { MatrixDrawing, matrixReadout, viridis, type MatrixMapProps } from './MatrixMap';

const base: MatrixMapProps = {
  label: { en: 'A test matrix', es: 'Una matriz de prueba' },
  rows: ['AAA', 'AA'],
  cols: ['AAA', 'AA', 'D'],
  values: [
    [0.9, 0.1, 0],
    [0.05, 0.9, 0.05],
  ],
  counts: [
    [90, 10, 0],
    [5, 90, 5],
  ],
  scale: 'migrations',
  diagonal: [0, 1],
  selectedRow: 1,
};

const draw = (p: MatrixMapProps, hover: [number, number] | null = null) =>
  renderToStaticMarkup(<MatrixDrawing p={p} width={480} height={240} hover={hover} setHover={() => undefined} />);

const fills = (markup: string) => [...markup.matchAll(/<rect x="[\d.]+" y="[\d.]+" width="[\d.]+" height="[\d.]+" fill="([^"]+)"/g)].map((m) => m[1]);

describe('MatrixMap', () => {
  it('is viridis at its ends and clamps outside [0, 1]', () => {
    expect(viridis(0)).toBe('rgb(68, 1, 84)');
    expect(viridis(1)).toBe('rgb(253, 231, 37)');
    expect(viridis(-1)).toBe(viridis(0));
    expect(viridis(2)).toBe(viridis(1));
  });

  it('draws one cell per entry, marks the selected row, and keeps the diagonal out of the migrations scale', () => {
    const m = draw(base);
    expect(m).toContain('data-cells="6"');
    expect(m).toContain('data-row="AA" data-selected="1"');
    // the selected row's marker is the accent bar beside its label, not a cell
    const f = fills(m).filter((x) => x !== 'var(--color-accent)');
    // row AAA: diagonal out of range, 0.1 the top of the range, 0 the bottom
    expect(f.slice(0, 3)).toEqual(['var(--color-surface-2)', viridis(1), viridis(0)]);
    expect(f.slice(3, 6)).toEqual([viridis(0.5), 'var(--color-surface-2)', viridis(0.5)]);
  });

  it('puts every cell on the linear and log scales, zeros at the bottom of the log scale', () => {
    const lin = fills(draw({ ...base, scale: 'linear' })).filter((x) => x.startsWith('rgb'));
    expect(lin[0]).toBe(viridis(1));
    expect(lin[1]).toBe(viridis(0.1 / 0.9));
    const log = fills(draw({ ...base, scale: 'log' })).filter((x) => x.startsWith('rgb'));
    expect(log[2]).toBe(viridis(0));
    expect(log[0]).toBe(viridis(1));
  });

  it('reads out the move, its value and its count of the row', () => {
    expect(matrixReadout(base, [1, 2], 'en')).toBe(`AA to D: ${formatNumber(0.05, 'en', { percent: true, decimals: 2 })} (5 of 100 ratings)`);
    expect(matrixReadout(base, [1, 2], 'es')).toBe(`AA a D: ${formatNumber(0.05, 'es', { percent: true, decimals: 2 })} (5 de 100 calificaciones)`);
    expect(matrixReadout({ ...base, values: [[null, null, null], base.values[1]] }, [0, 1], 'en')).toBe('AAA to AA: no ratings in this grade at the start');
    expect(matrixReadout(base, null, 'en')).toMatch(/^Point at a cell/);
  });

  it('prints a dash in a grade with no ratings and never paints it', () => {
    const m = draw({ ...base, values: [[null, null, null], base.values[1]] });
    expect(fills(m).slice(0, 3)).toEqual(['none', 'none', 'none']);
    expect(m).toContain('>-</text>');
  });
});
