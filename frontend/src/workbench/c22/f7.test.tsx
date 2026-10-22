// U16-F7 (the U16-R2 capture review, batch b10, C22): the minors of the validator views, read on the committed documents.
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { COMMITTED } from '../../lib/policy';
import { html, setLang } from '../c03/u6-testkit';
import { visibleText } from '../c14/testkit';
import { START } from './instrument';
import type { C22Sel } from './selection';
import { LiveCalculatorView, PValuesView, RatesTableView, SizeView, SpecimenView } from './Views';

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C22.json');
const ids = manifest.artifacts.filter((a) => a.role === 'variant').map((a) => a.variant_id as string);
const selOf = (id: string): C22Sel => {
  const entry = manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === id)!;
  const data: CaseData = { manifest, variant: read<VariantArtifact>(entry.path), models: read<ModelsArtifact>(entry.models_ref as string) };
  return { data, alphas: COMMITTED, level: 0.05, portfolio: { ...START } };
};
const text = (el: React.ReactElement) => visibleText(html(el));

describe('U16-F7 C22 (b10 minors)', () => {
  afterEach(() => setLang('en'));

  it('m2: the Wilson interval is written "x to y", never "x - y"', () => {
    const t = text(<RatesTableView sel={selOf(ids[0])} />);
    expect(t).not.toMatch(/\d % - \d/);
    expect(t).toMatch(/\d % to \d/);
    setLang('es');
    expect(text(<RatesTableView sel={selOf(ids[0])} />)).toMatch(/\d % a \d/);
  });

  it('m8: the Spanish note groups four digits like the rest of the product (4.000, not 4000)', () => {
    setLang('es');
    for (const id of ids) {
      const t = text(<SizeView sel={selOf(id)} />);
      expect(t, id).not.toMatch(/\b\d{4,} repeticiones/);
    }
    const reps = selOf(ids[0]).data.variant as unknown as { outputs: { simulations: Array<{ n_rep: number }> } };
    if (reps.outputs.simulations[0]?.n_rep >= 1000) expect(text(<SizeView sel={selOf(ids[0])} />)).toMatch(/\d\.\d{3} repeticiones/);
  });

  it('m9: the one-report table names its tests in words', () => {
    let seen = 0;
    for (const id of ids) {
      const t = text(<SpecimenView sel={selOf(id)} />);
      if (/Hosmer/.test(t)) seen += 1;
      expect(t, id).not.toMatch(/pd\.hosmer_lemeshow/);
    }
    expect(seen, 'a variant with a specimen names Hosmer-Lemeshow').toBeGreaterThan(0);
  });

  it('m16: the p-value panels let the reader solo one series', () => {
    const markup = ids.map((id) => html(<PValuesView sel={selOf(id)} />)).join('');
    expect(markup).toContain('aria-pressed');
  });

  it('m7: the live calculator says the Jeffreys line lies over the Binomial one where they are equal', () => {
    expect(text(<LiveCalculatorView sel={selOf(ids[0])} />)).toContain('the Jeffreys line lies over the Binomial one');
    setLang('es');
    expect(text(<LiveCalculatorView sel={selOf(ids[0])} />)).toContain('la línea de Jeffreys cubre a la Binomial');
  });
});
