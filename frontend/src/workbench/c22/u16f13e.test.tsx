// U16-F13e (fix round 6, the fifth capture review R5, batches c28 and c29), on the committed documents in both languages: a code of
// the Generators appendix breaks only at its separators (c28 m1, c29 n5: the shared text-cell rule broke "logistic / _ / portfoli /
// o"); the One report's rung nests no parenthesis (c28 m4); the Spanish attribution joins its authors with "y" and writes "n.º"
// (c28 m8, R5 ruling 5); the write-up's formula takes the Spanish decimal comma (c28 m3), "G − 2" a minus sign (c29 N1), a Spanish
// percent its space (c28 m2) and DeLong's test its own citation (c28 m5, c29 N4); a curve past the seventh is not dashed as an
// exact curve (c29 N2); and the One report names the dataset of every row (R5 ruling 2: its Generator configuration column).
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { COMMITTED } from '../../lib/policy';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { C22WriteUp } from '../../content/cases/C22';
import { START } from './instrument';
import { seriesStyle, type C22Sel } from './selection';
import { C22ContextView, GeneratorsView, SpecimenView, attributionText } from './Views';

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C22.json');
const selOf = (id: string): C22Sel => {
  const entry = manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === id)!;
  const data: CaseData = { manifest, variant: read<VariantArtifact>(entry.path), models: read<ModelsArtifact>(entry.models_ref as string) };
  return { data, alphas: COMMITTED, level: 0.05, portfolio: { ...START } };
};
const VARIANTS = manifest.artifacts.filter((a) => a.role === 'variant').map((a) => a.variant_id);
const LANGS = ['en', 'es'] as const;

describe('U16-F13e C22', () => {
  afterEach(() => setLang('en'));

  it('c28 m1, c29 n5: a code of the Generators appendix breaks only at its separators', () => {
    for (const id of ['null', 'other-families', 'miscalibration']) {
      const html = render(<GeneratorsView sel={selOf(id)} />, 'en');
      const codes = [...html.matchAll(/<td class="ct-text"><code translate="no"([^>]*)>/g)];
      expect(codes.length, id).toBeGreaterThan(10);
      for (const m of codes) expect(m[1], id).toContain('overflow-wrap:normal');
    }
  });

  it('c28 m4: the One report names its rung with no parenthesis inside another', () => {
    for (const id of VARIANTS) {
      for (const lang of LANGS) {
        const text = textOf(render(<SpecimenView sel={selOf(id)} />, lang));
        expect(text, `${id} ${lang}`).not.toMatch(/(drawn at|generado en) [^()]*\([^()]*\([^()]*\)\)/);
      }
    }
    expect(textOf(render(<SpecimenView sel={selOf('drift')} />, 'en'))).toContain('drawn at 0.2, on the ladder of mean shift (standard deviations)');
  });

  it('ruling 2: every row of the One report names the dataset it is computed on', () => {
    for (const id of VARIANTS) {
      const v = selOf(id).data.variant;
      const html = render(<SpecimenView sel={selOf(id)} />, 'es');
      const table = /<table[^>]*data-table="specimen"[\s\S]*?<\/table>/.exec(html)![0];
      const rows = [...table.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].slice(1);
      expect(rows.length, id).toBe(v.tests.length);
      for (const m of rows) expect(m[1], id).toMatch(/<td class="ct-text" data-segment="[^"]+"><code translate="no">[^<]+<\/code>/);
    }
  });

  it('c28 m8: the Spanish attribution joins its authors with "y" and writes "n.º"', () => {
    expect(attributionText('Yurdakul, B. and Naranjo, J. (2020). Statistical properties of the population stability index.', 'es'))
      .toBe('Yurdakul, B. y Naranjo, J. (2020). Statistical properties of the population stability index.');
    expect(attributionText('BCBS Working Paper No. 14. Bank for International Settlements.', 'es')).toBe('BCBS Working Paper n.º 14. Bank for International Settlements.');
    expect(attributionText('Yurdakul, B. and Naranjo, J. (2020).', 'en')).toBe('Yurdakul, B. and Naranjo, J. (2020).');
    const es = textOf(render(<C22ContextView sel={selOf('null')} />, 'es'));
    expect(es).toContain('Yurdakul, B. y Naranjo, J. (2020)');
    expect(es).not.toMatch(/Paper No\. 14/);
  });

  it('c28 m2, m3, m5, c29 N1, N4: the write-up in Spanish form, one citation each, G − 2 with a minus sign', () => {
    const en = render(<C22WriteUp />, 'en');
    const es = render(<C22WriteUp />, 'es');
    for (const html of [en, es]) {
      expect(textOf(html)).not.toContain('G - 2');
      expect(textOf(html)).toContain('G − 2');
      expect(html).not.toMatch(/<\/cite>\)?\s*\(?<cite/i);
    }
    expect(es).not.toContain('0.5 + c');
    expect(textOf(es)).not.toMatch(/\d%/);
    expect(es).toContain('al nivel de 5 %');
  });

  it('c29 N2: a curve past the seventh is not dashed as an exact curve', () => {
    expect(seriesStyle(0).dash).toBeUndefined();
    const late = seriesStyle(7).dash!;
    expect(late).toBeDefined();
    expect(late).not.toEqual([6, 4]);
    expect(late.length).toBe(4);
  });
});
