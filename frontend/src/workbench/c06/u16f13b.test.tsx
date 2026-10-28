// U16-F13b (fix round 6, the R5 capture review of C06 and C07, batches c08, c09 and c10 M1; R5 ruling 2): every row of the shared
// tests card names its segment, and a row whose document gives none says "whole portfolio" / "toda la cartera", on every committed
// variant of C06 and C07 in both languages.
import { afterEach, describe, expect, it } from 'vitest';
import type { VariantArtifact } from '../../lib/contract.types';
import { committedData, render, textOf, variantIds } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { provenanceOf } from '../model';
import { committedData as c07Data } from '../c08/spanish-testkit';
import { TablesView } from '../c07/ValidationViews';
import { defaultSel as c07Sel, type C07Sel } from '../c07/selection';
import { C06ContextView } from './C06Common';
import { StageSummaryView } from './ImpactViews';
import { NonLinearityView, SicrView } from './TermViews';
import { BacktestView, TestRowsCard } from './ValidationViews';
import { defaultSel, type C06Sel } from './selection';

const rowsOf = (markup: string) =>
  [...(markup.match(/<table[^>]*data-table="tests"[\s\S]*?<tbody>([\s\S]*?)<\/tbody>/)?.[1] ?? '').matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/g)].map((m) => m[1]);
// the first cell of a row: the test's name, then its segment line
const segmentLine = (row: string) => row.match(/^\s*<td[^>]*>[\s\S]*?<span class="ct-note"[^>]*data-segment[^>]*>([\s\S]*?)<\/span>/)?.[1];

describe('U16-R5 c08, c09 and c10 M1 on the committed C06 and C07 documents', () => {
  afterEach(() => setLang('en'));

  it('every tests row names its segment; a row of no segment names the whole portfolio', () => {
    let nulls = 0;
    for (const caseId of ['C06', 'C07']) {
      for (const id of variantIds(caseId)) {
        const v = committedData(caseId, id).variant as VariantArtifact;
        for (const lang of ['en', 'es'] as const) {
          const rows = rowsOf(render(<TestRowsCard variant={v} prov={provenanceOf(v.provenance.truth_status)} />, lang));
          expect(rows.length, `${caseId} ${id}`).toBe(v.tests.length);
          rows.forEach((r, i) => {
            const seg = segmentLine(r);
            expect(seg, `${caseId} ${id} ${lang} row ${i} ${v.tests[i].test_id}`).toBeTruthy();
            expect(textOf(seg!).trim(), `${caseId} ${id} ${lang} row ${i}`).not.toMatch(/^-?$/);
            if (v.tests[i].segment === null || v.tests[i].segment === undefined) {
              nulls += 1;
              expect(textOf(seg!).trim()).toBe(lang === 'en' ? 'whole portfolio' : 'toda la cartera');
            }
          });
        }
      }
    }
    // the review counted 8 null rows in each C06 document and 5 in each C07 one
    expect(nulls).toBeGreaterThan(0);
  });
});

describe('U16-R5 c08, c09 and c10 minors on the committed C06 and C07 documents', () => {
  afterEach(() => setLang('en'));
  const c06 = (id: string) => defaultSel(committedData('C06', id)) as C06Sel;
  const c07 = (file: string) => c07Sel(c07Data('C07', file, 'models-banco-andino.json', { en: 'Chile provisions trilogy', es: 'Trilogía de provisiones de Chile' })) as C07Sel;

  it('c09 n1: the backtest row names the observed side by its estimator, not as a rung', () => {
    for (const id of variantIds('C06')) {
      const en = textOf(render(<BacktestView sel={c06(id)} />, 'en'));
      const es = textOf(render(<BacktestView sel={c06(id)} />, 'es'));
      expect(en).toContain('observed by Kaplan-Meier');
      expect(es).toContain('observada por Kaplan-Meier');
    }
  });

  it('c09 n2: the stage cell of the stages table keeps one line', () => {
    const m = render(<StageSummaryView sel={c06(variantIds('C06')[0])} />, 'en');
    const row = m.match(/<tr[^>]*data-stage="[^"]+"[^>]*>\s*<td([^>]*)>/)?.[1] ?? '';
    expect(row).toContain('white-space:nowrap');
  });

  it('c08 n3, n4 and n5: one spelling of Nonlinearity; the SICR share is Participación; probation is the cure period', () => {
    const id = variantIds('C06')[0];
    expect(textOf(render(<NonLinearityView sel={c06(id)} />, 'en'))).not.toContain('Non-linearity');
    expect(textOf(render(<SicrView sel={c06(id)} />, 'es'))).not.toMatch(/\bParte\b/);
    expect(textOf(render(<SicrView sel={c06(id)} />, 'es'))).toContain('Participación');
    const es = textOf(render(<C06ContextView sel={c06(id)} />, 'es'));
    expect(es).toContain('el período de prueba de cura y la convención de descuento');
    expect(es).not.toContain('el piso, la prueba y');
  });

  it('c10 n1: the B-1 table captions are paragraphs as wide as the box, the tables keep them as their names', () => {
    for (const lang of ['en', 'es'] as const) {
      const m = render(<TablesView sel={c07('base.json')} />, lang);
      expect(m).not.toContain('<caption');
      const caps = [...m.matchAll(/<p class="ct-note" data-caption="([^"]+)">/g)].map((x) => x[1]);
      const tables = [...m.matchAll(/<table[^>]*(?:data-table-id|data-table)="([^"]+)"[^>]*aria-label="[^"]+"/g)].map((x) => x[1]);
      expect(caps.length).toBeGreaterThan(1);
      expect(tables).toEqual(caps);
    }
  });
});
