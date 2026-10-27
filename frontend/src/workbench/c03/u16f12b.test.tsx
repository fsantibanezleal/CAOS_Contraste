// U16-F12b (fix round 5, the R4 capture review of C03, batch c04 minors of the C03 views), on the committed C03 documents in both
// languages and on the view sources where the value is a chart option the server render does not print: the rungs' bar labels and the
// parity chart keep fixed decimals (m2), the curves' data table keeps the curve's start (n2: 0.044 % read "0.0 %"), the bars' notes
// do not repeat their labels (n4), and the training windows and the variants' cohorts stay whole at 390 (m5).
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import { C03VariantsTable } from './C03Common';
import { TrainingView } from './ModelViews';
import { committedData, render, variantIds } from './u16f2-kit';
import { setLang } from './u6-testkit';
import { defaultSel, type C03Sel } from './selection';
import type { VariantArtifact } from '../../lib/contract.types';

const selOf = (id: string) => defaultSel(committedData('C03', id)) as C03Sel;
const src = (rel: string) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const LANGS = ['en', 'es'] as const;
const rows = (markup: string, table: string) => {
  const t = markup.match(new RegExp(String.raw`<table[^>]*data-table="${table}"[\s\S]*?</table>`))?.[0] ?? '';
  return [...t.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/g)].map((m) => [...m[1].matchAll(/<td([^>]*)>([\s\S]*?)<\/td>/g)].map((c) => ({ attrs: c[1], text: c[2].replace(/<[^>]*>/g, '') }))).filter((r) => r.length);
};

describe('U16-R4 c04 minors on the committed C03 documents', () => {
  afterEach(() => setLang('en'));

  it('m2: the rungs axis prints three fixed decimals and the parity axes two', () => {
    const s = src('./ModelViews.tsx');
    expect(s).toMatch(/label: \{ en: 'AUC \(higher is better\)', es: 'AUC \(más alto es mejor\)' \}, format: \{ decimals: 3 \}/);
    expect(s).toMatch(/label: \{ en: 'Predicted PD', es: 'PD predicha' \}, format: \{ percent: true, decimals: 2 \}/);
    expect(s).toMatch(/label: \{ en: 'Observed rate', es: 'Tasa observada' \}, format: \{ percent: true, decimals: 2 \}/);
  });

  it('n2: the curves keep two decimals of percent, so the curve\'s start (0.044 %) does not read 0.0 %', () => {
    expect(src('./VintageViews.tsx')).toMatch(/label: \{ en: 'Cumulative PD', es: 'PD acumulada' \}, format: \{ percent: true, decimals: 2 \}/);
  });

  it('n4: a bar of the rungs chart has no note that repeats its label', () => {
    expect(src('./ModelViews.tsx')).not.toMatch(/hint: label\(r\.rung_id\)/);
  });

  it('m5: the training windows keep the cut-off, the window and the cohort on one line', () => {
    for (const lang of LANGS) {
      const r = rows(render(<TrainingView sel={selOf(variantIds('C03')[0])} />, lang), 'training-windows');
      expect(r.length).toBeGreaterThan(0);
      for (const row of r) for (const k of [0, 1, 2]) expect(row[k].attrs, `${lang} ${row[k].text}`).toContain('white-space:nowrap');
    }
  });

  it('m5: the variants table keeps the cohort and the training window on one line', () => {
    const variants = variantIds('C03').map((id) => ({ id, title: { en: id, es: id }, v: committedData('C03', id).variant as VariantArtifact<never> }));
    for (const lang of LANGS) {
      const r = rows(render(<C03VariantsTable variants={variants as never} onPick={() => undefined} current={variants[0].id} />, lang), 'variants-c03');
      expect(r.length).toBe(variants.length);
      for (const row of r) expect(row[1].attrs, `${lang} ${row[1].text}`).toContain('white-space:nowrap');
    }
  });
});
