// S-2 of the method tiers, on the committed documents in both languages: the VAR conditional forecast and the growth-at-risk views draw
// what the models artifact's two sota records hold (the bake's numbers, none computed here), name every loan type, episode and term in
// words (no raw id), and write a result that does not improve on the OLS satellite like one that does.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { GAR_MODEL_ID, GarRungView, VAR_MODEL_ID, VarRungView, detailsOf, joinWindows, type GarDetails, type VarDetails } from './RungViews';
import { defaultSel, type C18Sel } from './selection';

const models = committedDoc<ModelsArtifact>('C18', 'models-banco-andino');
const title = { en: 'ICAAP and IAPE capital aggregation under macro scenarios', es: 'Agregación de capital ICAAP e IAPE bajo escenarios macro' };
const variant = committedDoc<VariantArtifact>('C18', 'fed-2026-severely-adverse');
const base = defaultSel(fixtureData('C18', variant, models, title)) as C18Sel;
const sel = (loan: C18Sel['loan']): C18Sel => ({ ...base, loan });
const LANGS = ['en', 'es'] as const;
const IDS = ['commercial-industrial', 'commercial-real-estate', 'credit-cards', 'other-consumer', 'gfc-2008-09', 'pandemic-2020', 'real_gdp_growth', 'term_spread', 'unemployment_rate_lag1', 'c18-var-conditional-forecast'];

describe('S-2 C18 stress rungs', () => {
  afterEach(() => setLang('en'));
  const v = detailsOf<VarDetails>(base, VAR_MODEL_ID)!.details;
  const g = detailsOf<GarDetails>(base, GAR_MODEL_ID)!.details;

  it('the models artifact carries both sota records and the acceptance criterion is met on the measured run', () => {
    expect(v.tier).toBe('sota');
    expect(g.tier).toBe('sota');
    expect(v.acceptance.met).toBe(true);
    expect(v.var.windows.map((w) => w.window_id)).toEqual(['gfc-2008-09', 'pandemic-2020']);
    expect(g.growth_at_risk.windows).toHaveLength(2);
  });

  it('the VAR view writes the two episodes of the loan type in focus, the error of each rung and the verdict, in both languages', () => {
    for (const lang of LANGS) {
      for (const l of ['commercial-industrial', 'credit-cards'] as const) {
        const html = render(<VarRungView sel={sel(l)} />, lang);
        const rows = [...html.matchAll(/<tr data-window="([^"]+)" data-closer="([^"]+)"/g)];
        expect(rows.map((m) => m[1])).toEqual(['gfc-2008-09', 'pandemic-2020']);
        v.var.windows.forEach((w, i) => expect(rows[i][2], `${lang} ${l}`).toBe(w.per_loan_type.find((r) => r.fed_loan_type === l)!.closer));
        const t = textOf(html);
        expect(t).toContain(lang === 'en' ? 'The VAR conditional forecast beside the OLS satellite' : 'El pronóstico condicional VAR junto al satélite MCO');
        expect(html).toContain('data-table="c18-var-coefficients"');
        for (const id of IDS) expect(t, `${lang} ${l} shows the raw id ${id}`).not.toContain(id);
      }
    }
  });

  it('a result where the OLS satellite is closer is written as it is, not hidden', () => {
    const worse = v.var.windows.flatMap((w) => w.per_loan_type.filter((r) => r.closer === 'ols'));
    expect(worse.length).toBeGreaterThan(0);
    const r = worse[0];
    const html = render(<VarRungView sel={sel(r.fed_loan_type as C18Sel['loan'])} />, 'en');
    expect(html).toContain('data-closer="ols"');
    expect(textOf(html)).toContain('OLS satellite');
  });

  it('the summary row counts are the document\'s counts', () => {
    const html = render(<VarRungView sel={sel('commercial-industrial')} />, 'en');
    const table = /<table[^>]*data-table="c18-var-summary"[\s\S]*?<\/table>/.exec(html)![0];
    v.var.summary.forEach((s) => expect(textOf(table)).toContain(`${s.var_closer} of ${s.loan_types}`));
  });

  it('the growth-at-risk view lists each episode with its origins, coverage and pinball ratio, and names the spread in words', () => {
    for (const lang of LANGS) {
      const html = render(<GarRungView sel={base} />, lang);
      const rows = [...html.matchAll(/<tr data-window="([^"]+)" data-pinball-ratio="([^"]+)"/g)];
      expect(rows.map((m) => m[1])).toEqual(['gfc-2008-09', 'pandemic-2020']);
      g.growth_at_risk.windows.forEach((w, i) => expect(Number(rows[i][2])).toBeCloseTo(w.mean_pinball_ratio, 9));
      const coefRows = [...html.matchAll(/<tr data-window="[^"]+" data-tau="([^"]+)"/g)];
      expect(coefRows).toHaveLength(2 * 5);
      const t = textOf(html);
      expect(t).toContain(lang === 'en' ? 'Term spread' : 'Pendiente');
      for (const id of IDS) expect(t, `${lang} shows the raw id ${id}`).not.toContain(id);
    }
  });

  it('two episodes share one axis with a gap between them', () => {
    expect(joinWindows([[1, 2], [3]])).toEqual([1, 2, null, 3]);
    expect(joinWindows([[1]])).toEqual([1]);
  });

  it('a models artifact without the records shows the not-available state, never an empty chart', () => {
    const bare = { ...base, data: { ...base.data, models: { ...(base.data.models as object), model: [] } } } as unknown as C18Sel;
    for (const lang of LANGS) {
      const html = render(<VarRungView sel={bare} />, lang);
      expect(html).toContain('data-state="unavailable"');
      expect(render(<GarRungView sel={bare} />, lang)).toContain('data-state="unavailable"');
    }
  });
});
