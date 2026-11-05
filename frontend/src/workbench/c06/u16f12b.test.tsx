// U16-F12b (fix round 5, the R4 capture review of C06, batches c07 and c08 minors, and C07's c09 m8 on the shared tests card), on the
// committed documents in both languages: the correlation of the PIT conversion is named in words with its symbol (N-m3), the Spanish
// simplex note agrees with its subjects (N-m5), and a tests card whose rows carry no p-value drops the p column (c09 m8: at 390 the
// Light column sat right of the box behind eleven "not available" cells).
import { afterEach, describe, expect, it } from 'vitest';
import type { VariantArtifact } from '../../lib/contract.types';
import { committedData, render, textOf, variantIds } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { provenanceOf } from '../model';
import { WeightsView } from './ImpactViews';
import { LadderView, TestRowsCard } from './ValidationViews';
import { defaultSel, type C06Sel } from './selection';

const sel = (id: string) => defaultSel(committedData('C06', id)) as C06Sel;
const head = (markup: string) => [...(markup.match(/<thead>[\s\S]*?<\/thead>/)?.[0] ?? '').matchAll(/<th[^>]*>([\s\S]*?)<\/th>/g)].map((m) => m[1].replace(/<[^>]*>/g, ''));

describe('U16-R4 c07 and c08 minors on the committed C06 documents', () => {
  afterEach(() => setLang('en'));

  it('N-m3: the PIT conversion names its correlation in words, with the symbol, never "rho"', () => {
    for (const v of variantIds('C06')) {
      const en = textOf(render(<LadderView sel={sel(v)} />, 'en'));
      const es = textOf(render(<LadderView sel={sel(v)} />, 'es'));
      expect(en).not.toMatch(/\brho\b/);
      expect(es).not.toMatch(/\brho\b/);
      expect(en).toMatch(/; correlation ρ \d+ %/);
      expect(es).toMatch(/; correlación ρ \d+ %/);
    }
  });

  it('N-m5: the Spanish simplex note agrees with its subjects', () => {
    const es = textOf(render(<WeightsView sel={sel(variantIds('C06')[0])} />, 'es'));
    expect(es).not.toContain('Etapas recalculadas mueve cuentas');
    expect(es).toContain('Con etapas recalculadas, las cuentas se mueven entre etapas al cambiar los pesos; con etapas congeladas, las etapas se mantienen');
  });
});

describe('U16-R4 c09 m8 on the shared tests card', () => {
  afterEach(() => setLang('en'));

  it('drops the p column when no row of the document carries a p-value, and keeps it when one does', () => {
    for (const [caseId, file] of [['C07', 'base'], ['C06', variantIds('C06')[0]]] as const) {
      const v = committedData(caseId, file).variant as VariantArtifact;
      const anyP = v.tests.some((t) => t.p_value !== null && t.p_value !== undefined);
      for (const lang of ['en', 'es'] as const) {
        const cols = head(render(<TestRowsCard variant={v} prov={provenanceOf(v.provenance.truth_status)} />, lang));
        expect(cols.includes('p'), `${caseId} ${lang}`).toBe(anyP);
        expect(cols.some((c) => /Light|Luz/.test(c)), `${caseId} ${lang}`).toBe(true);
      }
    }
    // a C07 document has no p-value in any row (the review's eleven "not available" cells)
    expect((committedData('C07', 'base').variant as VariantArtifact).tests.every((t) => t.p_value === null)).toBe(true);
  });
});
