// U16-F12e (fix round 5, the fourth capture review R4, batch c25: the small, local minors of C21), on the committed pair documents in
// both languages: the Pair cell names the pair once, the licence status is said once, the Spanish names the pairwise tests one way, and
// the data codes NA, Exempt, Yes and No are marked as codes in the Spanish prose.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { C21ContextView, C21VariantsTable } from './C21Common';
import { defaultSel, type C21Sel } from './selection';

const PAIRS = ['pair-2018-19', 'pair-2019-20', 'pair-2020-21', 'pair-2021-22', 'pair-2022-23', 'pair-2023-24'] as const;
const models = committedDoc<ModelsArtifact>('C21', 'models-hmda-de-2018-2023');
const title = { en: 'Fair lending', es: 'Préstamos justos' };
const selOf = (name: string): C21Sel => defaultSel(fixtureData('C21', committedDoc<VariantArtifact>('C21', name), models, title)) as C21Sel;
const LANGS = ['en', 'es'] as const;

describe('U16-F12e C21', () => {
  afterEach(() => setLang('en'));

  it('c25 n2: the Pair cell names the pair once ("2018-19", never "2018-19 2018 - 2019")', () => {
    const v = committedDoc<VariantArtifact>('C21', 'pair-2018-19');
    for (const lang of LANGS) {
      const html = render(<C21VariantsTable variants={[{ id: v.variant_id, title: { en: '2018-19', es: '2018-19' }, v: v as never }]} onPick={() => undefined} current={v.variant_id} field="derived_sex" />, lang);
      const row = textOf(/<tr[^>]*data-variant="pair-2018-19"[\s\S]*?<\/tr>/.exec(html)![0]);
      expect(row, lang).not.toMatch(/2018 - 2019/);
    }
  });

  it('c25 n3: the licence status is said once', () => {
    for (const name of PAIRS) {
      const en = textOf(render(<C21ContextView sel={selOf(name)} />, 'en'));
      const es = textOf(render(<C21ContextView sel={selOf(name)} />, 'es'));
      expect(en, name).not.toMatch(/UNVERIFIED: The HMDA data licence sentence is UNVERIFIED/);
      expect(es, name).not.toMatch(/UNVERIFIED: La frase de licencia/);
    }
  });

  it('c25 m5: the Spanish names the pairwise tests one way ("por pares")', () => {
    const es = textOf(render(<C21ContextView sel={selOf('pair-2018-19')} />, 'es'));
    expect(es).not.toContain('de a pares');
    expect(es).toContain('Grupos fuera de las pruebas por pares');
  });

  it('c25 m7: the data codes NA and Exempt are marked as codes in the Spanish Context', () => {
    const html = render(<C21ContextView sel={selOf('pair-2018-19')} />, 'es');
    expect(html).toContain('<code translate="no" lang="en">NA</code>');
    expect(html).toContain('<code translate="no" lang="en">Exempt</code>');
    expect(html).not.toMatch(/marcadores NA y Exempt/);
  });
});
