// U16-F12b (fix round 5, the R4 capture review of C02, batch c03 NB1, NB2 and the minors of these views), on the six committed C02
// documents in both languages: the Context ladder names the single-variable rung's input as the codebook does (NB1: "Una variable
// (Attr39)"), and the input is the loaded file's own, not the 1-year file's on every variant (NB2); the pooled file's inputs are the
// 64 ratios and the horizon indicator (n1, "Ratios 65"); the split and the intervals keep their numbers on one line (m10, n6).
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc } from '../c14/testkit';
import { fixtureData, html, setLang } from '../c20/testkit';
import { segmentName } from '../names';
import { C02ContextView } from './C02Common';
import { CalibrationView, RocCapView } from './DiscriminationViews';
import { defaultSel, type C02Sel } from './selection';

type Outputs = components['schemas']['c02Outputs'];
const TITLE = { en: 'Corporate PD across horizons', es: 'PD corporativa a distintos horizontes' };
const FILES = ['h1', 'h2', 'h3', 'h4', 'h5', 'pooled'] as const;
const models = committedDoc<ModelsArtifact>('C02', 'models-polish-horizons');
const doc = (id: string) => committedDoc<VariantArtifact<Outputs>>('C02', id);
const selOf = (id: string): C02Sel => defaultSel(fixtureData('C02', doc(id) as unknown as VariantArtifact, models, TITLE)) as C02Sel;
const text = (markup: string) => markup.replace(/<[^>]*>/g, ' ').replace(/&#x27;/g, "'").replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
const rowsOf = (markup: string, table: string) => {
  const t = markup.match(new RegExp(String.raw`<table[^>]*data-table="${table}"[\s\S]*?</table>`))?.[0] ?? '';
  return [...t.matchAll(/<tr([^>]*)>([\s\S]*?)<\/tr>/g)].map((m) => ({ attrs: m[1], cells: [...m[2].matchAll(/<td([^>]*)>([\s\S]*?)<\/td>/g)].map((c) => ({ attrs: c[1], text: text(c[2]) })) }));
};

/** The input of the file's single-variable rung, from its own committed model title ("Single variable (Attr27_missing)"). */
function ownInput(id: string): string {
  const m = /\(([^()]+)\)$/.exec(doc(id).model.find((x) => /-P0-single$/.test(x.id))?.title.en ?? '');
  if (!m) throw new Error(`${id}: no single-variable rung`);
  return m[1];
}

describe('U16-R4 c03 on the committed C02 documents', () => {
  afterEach(() => setLang('en'));

  it('NB1 and NB2: the ladder names the loaded file\'s own single-variable input by its codebook name, in both languages', () => {
    const seen = new Set<string>();
    for (const id of FILES) {
      const input = ownInput(id);
      seen.add(input);
      const name = segmentName(`characteristic:${input}`, { caseId: 'C02' });
      expect(name, input).not.toBeNull();
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const ladder = rowsOf(html(<C02ContextView sel={selOf(id)} />), 'c02-ladder').filter((r) => r.cells.length);
        const single = ladder.filter((r) => r.attrs.includes('data-ladder="P0"'))[1];
        expect(single?.cells[1].text, `${id} ${lang}`).toBe(lang === 'en' ? `Single variable: ${name!.en}` : `Una variable: ${name!.es}`);
        // no other file's input, and no column code without its name
        for (const r of ladder) expect(r.cells[1].text, `${id} ${lang}`).not.toMatch(/(?:variable|variable:) \(?Attr\d+(?:_missing)?\)?$/);
      }
    }
    // the six files do not share one input: the 1-year file's is not printed on every variant
    expect(seen.size).toBeGreaterThan(1);
  });

  it('n1: the pooled Context counts 64 ratios and the horizon indicator, a horizon file its 64 ratios', () => {
    setLang('en');
    expect(text(html(<C02ContextView sel={selOf('pooled')} />))).toContain('Ratios 64 and the horizon indicator');
    expect(text(html(<C02ContextView sel={selOf('h1')} />))).toMatch(/Ratios 64 Event/);
    setLang('es');
    expect(text(html(<C02ContextView sel={selOf('pooled')} />))).toContain('Razones 64 y el indicador de horizonte');
  });

  it('m10 and n6: the split and every interval keep their numbers on one line', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const ctx = html(<C02ContextView sel={selOf('h1')} />);
      expect(ctx).toMatch(/<dl class="ct-defs" data-table="c02-split"><dt>[^<]*<\/dt><dd style="white-space:nowrap">/);
      const roc = rowsOf(html(<RocCapView sel={selOf('h1')} />), 'discrimination').filter((r) => r.cells.length);
      expect(roc.length).toBeGreaterThan(0);
      for (const r of roc) expect(r.cells.find((c) => / (to|a) /.test(c.text))?.attrs, lang).toContain('white-space:nowrap');
      const dec = rowsOf(html(<CalibrationView sel={selOf('h1')} />), 'reliability').filter((r) => r.cells.length);
      expect(dec.length).toBe(10);
      for (const r of dec) expect(r.cells.find((c) => / (to|a) /.test(c.text))?.attrs, lang).toContain('white-space:nowrap');
    }
  });
});
