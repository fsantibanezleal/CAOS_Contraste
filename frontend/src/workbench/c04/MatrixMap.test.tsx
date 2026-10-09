// CT-411: the transition-matrix heat map. The colour scale is viridis at its ends, the three scales place the cells
// as declared (the migrations scale keeps the diagonal out of the range, the log scale puts zeros at the bottom), the
// drawing has one cell per entry with the selected row marked, and the readout gives the move, its value and its count.
import { formatNumber, textWidth } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { MatrixDrawing, MatrixMap, matrixReadout, viridis, type MatrixMapProps } from './MatrixMap';

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
  it('prints a value only where it fits its cell, and staggers column labels that do not fit their column (gate G10)', () => {
    // nine states as in an agency's matrix, on a phone's card: each column narrower than "CCC-C"
    const grades = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC-C', 'D', 'W'];
    const nine: MatrixMapProps = {
      ...base,
      rows: ['AAA'],
      cols: grades,
      values: [[0.79, 0.161, 0.0082, 0, 0, 0.0026, 0.001, 0, 0.0282]],
      counts: [[1, 1, 1, 0, 0, 1, 1, 0, 1]],
      diagonal: [0],
      selectedRow: 0,
    };
    const column = (markup: string, j: number) => {
      const m = new RegExp(`<text data-col="${j}" x="[\\d.]+" y="([\\d.]+)"[^>]*>(?:<title>([^<]*)</title>)?([^<]*)</text>`).exec(markup);
      expect(m, `column ${j}`).not.toBeNull();
      return { y: Number(m![1]), title: m![2], text: m![3] };
    };
    const narrow = renderToStaticMarkup(<MatrixDrawing p={nine} width={300} height={200} hover={null} setHover={() => undefined} />);
    const cols = grades.map((_, j) => column(narrow, j));
    const ys = [...new Set(cols.map((c) => c.y))].sort((a, b) => a - b);
    expect(ys, 'two lines of column labels').toHaveLength(2);
    // the lines a label's box apart, so a label on one never reaches into the other
    expect(ys[1] - ys[0]).toBeGreaterThanOrEqual(16);
    // neighbours on different lines, so no two adjacent labels share one
    for (let j = 1; j < grades.length; j++) expect(cols[j].y).not.toBe(cols[j - 1].y);
    // a label gets two columns of room on its line; "CCC-C" needs more here and is shortened, its whole name the title
    const cw = (300 - 62 - 74) / 9;
    for (const c of cols) expect(textWidth(c.text, 12)).toBeLessThanOrEqual(2 * cw - 4);
    expect(cols[6].title).toBe('CCC-C');
    expect(cols[6].text.endsWith('\u2026')).toBe(true);
    expect(cols[0]).toEqual({ y: cols[0].y, title: undefined, text: 'AAA' });
    // no value printed wider than its cell (the server's estimate: 0.62 em a character)
    expect(narrow).not.toContain('>79 %<');
    const wide = draw(base);
    // a cell wide enough prints its value (three significant digits, as the map writes it), and its labels whole
    expect(wide).toContain('>90.0\u00a0%<');
    expect(column(wide, 2).text).toBe('D');
  });

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

  it('keeps the outside columns (the withdrawals) out of the migrations range, and only that scale', () => {
    // a withdrawals column holding the largest off-diagonal share would otherwise set the top of the range
    const w: MatrixMapProps = {
      ...base,
      cols: ['AAA', 'AA', 'D', 'W'],
      values: [
        [0.8, 0.05, 0, 0.15],
        [0.05, 0.8, 0.1, 0.05],
      ],
      counts: null,
      outside: [3],
    };
    const f = fills(draw(w)).filter((x) => x !== 'var(--color-accent)');
    // the range is the migrations without W: 0 to 0.1 (AA to D)
    expect(f.slice(0, 4)).toEqual(['var(--color-surface-2)', viridis(0.5), viridis(0), 'var(--color-surface-2)']);
    expect(f.slice(4, 8)).toEqual([viridis(0.5), 'var(--color-surface-2)', viridis(1), 'var(--color-surface-2)']);
    // on the linear scale every cell is in range again, W included
    const lin = fills(draw({ ...w, scale: 'linear' })).filter((x) => x.startsWith('rgb'));
    expect(lin).toHaveLength(8);
  });

  it('puts every cell on the linear and log scales, zeros at the bottom of the log scale', () => {
    const lin = fills(draw({ ...base, scale: 'linear' })).filter((x) => x.startsWith('rgb'));
    expect(lin[0]).toBe(viridis(1));
    expect(lin[1]).toBe(viridis(0.1 / 0.9));
    const log = fills(draw({ ...base, scale: 'log' })).filter((x) => x.startsWith('rgb'));
    expect(log[2]).toBe(viridis(0));
    expect(log[0]).toBe(viridis(1));
  });

  it('gives the readout line its text as a title, since a narrow card cuts it with an ellipsis (gate G5)', () => {
    const markup = renderToStaticMarkup(<MatrixMap {...base} />);
    const m = markup.match(/<p class="caos-chart-readout" data-readout="matrix" title="([^"]*)">([^<]*)<\/p>/);
    expect(m, markup).not.toBeNull();
    expect(m![1]).toBe(m![2]);
    expect(m![1].length).toBeGreaterThan(0);
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
