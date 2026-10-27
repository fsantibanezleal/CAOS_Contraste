// What the 1.00.000 full gate found on the merged fix rounds, on the committed documents: the rails of C05, C10, C16, C18 and
// C20 scrolled at 1280 x 800 in Spanish in the gate's wide font (ADR-0071 rule 6), the C06 SICR card counted as undrawn (G6)
// and the simplex's top label was cut at the drawing's edge (G10). Each test fails on the defect it names.
import { readFileSync } from 'node:fs';
import { useLangStore } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';
import { committedData, render, textOf, variantIds } from './c03/u16f2-kit';
import { setLang } from './c03/u6-testkit';
import { useInstrument as useC05Instrument } from './c05/instrument';
import { CASE1 } from './c05/selection';
import { simplexLayout } from './c06/ImpactViews';
import { SicrView } from './c06/TermViews';
import { defaultSel as c06Sel, outputsOf as c06Outputs, type C06Sel } from './c06/selection';
import { RungReadout } from './c10/C10Common';
import { defaultSel as c10Sel } from './c10/selection';
import { C20ContextView } from './c20/C20Common';
import { defaultSel as c20Sel } from './c20/selection';
import { DENSE_RAIL } from './Workbench';

const langState = useLangStore.getInitialState() as { lang: 'en' | 'es' };

function C05Section({ id }: { id: string }) {
  const inst = useC05Instrument(committedData('C05', 'sp-2010'), () => undefined);
  return <div>{inst?.rail.find((r) => r.id === id)?.content ?? null}</div>;
}
const c05Rail = (id: string, lang: 'en' | 'es') => {
  const before = langState.lang;
  langState.lang = lang;
  try {
    return renderToStaticMarkup(<MemoryRouter><C05Section id={id} /></MemoryRouter>);
  } finally {
    langState.lang = before;
  }
};

describe('the full gate on the first stable release candidate', () => {
  afterEach(() => setLang('en'));

  it('C16, C18 and C20 leave the variant title out of the rail, as the other dense rails do', () => {
    for (const c of ['C05', 'C10', 'C16', 'C18', 'C20']) expect(DENSE_RAIL.has(c), c).toBe(true);
  });

  for (const lang of ['en', 'es'] as const) {
    it(`C05 (${lang}): the four approaches of case 1 are one select in the paper's order, each option titled`, () => {
      const markup = c05Rail('calibration', lang);
      const group = markup.match(/<div class="caos-chipgroup" data-control="c05-approach">[\s\S]*?<\/select>/)?.[0] ?? '';
      expect(group).toContain('<select');
      expect([...group.matchAll(/<option value="([^"]+)"/g)].map((m) => m[1])).toEqual(CASE1);
      expect(group).not.toMatch(/role="radio"/);
      for (const o of group.matchAll(/<option [^>]*>/g)) expect(o[0]).toMatch(/title="[^"]+"/);
    });

    it(`C10 (${lang}): the rung read-out has three rows; the VaR's Monte Carlo error stays in the rung view`, () => {
      const markup = render(<RungReadout sel={c10Sel(committedData('C10'))} />, lang);
      expect([...markup.matchAll(/<dt>/g)]).toHaveLength(3);
      expect(textOf(markup)).not.toMatch(/Error of the VaR|Error del VaR/);
    });

    for (const v of variantIds('C20')) {
      it(`C20 (${lang}, ${v}): the Context's Variant row names the variant's whole title`, () => {
        const data = committedData('C20', v);
        const title = data.manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === v)?.title;
        const markup = render(<C20ContextView sel={c20Sel(data)} />, lang);
        const row = markup.match(/<dl class="ct-defs" data-table="c20-case">\s*<dt>[^<]*<\/dt><dd[^>]*>([^<]*)<\/dd>/)?.[1] ?? '';
        expect(row).toBe(title?.[lang]);
      });
    }

    it(`C06 (${lang}): the SICR rule is a table of test and condition above the counts, so the card's tables span it`, () => {
      const s = c06Sel(committedData('C06')) as C06Sel;
      const markup = render(<SicrView sel={s} />, lang);
      const rule = markup.match(/<table[^>]*data-table="sicr-rule"[\s\S]*?<\/table>/)?.[0] ?? '';
      expect(rule).not.toBe('');
      expect(markup).not.toMatch(/<ul[^>]*data-table="sicr-rule"/);
      for (const m of c06Outputs(s)!.settings.sicr.multiplier_schedule) expect(rule).toContain(`data-multiplier="${m.multiplier}"`);
      for (const attr of ['data-floor=', 'data-threefold=', 'data-dpd=', 'data-lcr=']) expect(rule).toContain(attr);
      expect(markup.indexOf('data-table="sicr-rule"')).toBeLessThan(markup.indexOf('data-table="sicr-summary"'));
    });
  }

  it('the data-contracts figure counts the sources the registry holds, in both languages (it said 49 from U1 on)', () => {
    const registry = JSON.parse(readFileSync(new URL('../../../data-pipeline/config/sources.json', import.meta.url), 'utf8')) as { sources: unknown[] };
    const figure = readFileSync(new URL('../architecture/05-data-contracts.svg', import.meta.url), 'utf8');
    expect(figure).toContain(`>${registry.sources.length} sources, each with`);
    expect(figure).toContain(`>${registry.sources.length} fuentes, cada una con`);
  });

  it('the simplex keeps its labels inside the drawing at every size the card takes', () => {
    for (const width of [260, 340, 480, 620, 760]) {
      for (const height of [220, 300, 380, 440, 520, 640]) {
        for (const top of [1, 2, 3]) {
          for (const bottom of [1, 2, 3, 4]) {
            const { r, apex } = simplexLayout(width, height, top, bottom);
            const at = `${width}x${height}, ${top} and ${bottom} lines`;
            expect(2 * r * 0.866, at).toBeLessThanOrEqual(width - 28 + 1e-9);
            if (r === 30) continue; // the floor: a drawing too small for the labels keeps a readable triangle
            // the top label's first line: its baseline 20 px over the apex, less its other lines, and a 12 px type's ascent
            expect(apex - 20 - (top - 1) * 13 - 11, at).toBeGreaterThanOrEqual(0);
            // the lower labels' last line: 28 px under the corners, then the other lines and the descent
            expect(apex + 1.5 * r + 28 + (bottom - 1) * 13 + 4, at).toBeLessThanOrEqual(height);
          }
        }
      }
    }
  });
});
