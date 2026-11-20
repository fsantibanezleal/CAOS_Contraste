// S-4 (method tiers plan): the PC-Hazard tab of C06 on the committed documents of the six reporting dates, in both languages: the
// rung is named by its short title, never its id; the numbers on screen are the ones the models document holds; a date whose
// follow-up has not reached a horizon says so; the Spanish view carries no English sentence of the tab.
import { afterEach, describe, expect, it } from 'vitest';
import { formatNumber } from '@fasl-work/caos-app-shell';
import { committedData, render, textOf, variantIds } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { PchView, bootstrapOf, pchRecords, sensitivityOf } from './PchView';
import { defaultSel, type C06Sel } from './selection';

const sel = (id: string) => defaultSel(committedData('C06', id)) as C06Sel;

describe('S-4 PC-Hazard view on the committed C06 documents', () => {
  afterEach(() => setLang('en'));

  it('every date has the rung, its evaluation and 30 decile cells in the models document', () => {
    for (const id of variantIds('C06')) {
      const { pch, cox } = pchRecords(sel(id));
      expect(pch?.details?.evaluated, id).toBe(true);
      expect(pch?.details?.decile_calibration?.length, id).toBe(30);
      expect(cox?.details?.decile_calibration?.length, id).toBe(30);
      expect(pch?.details?.evaluation?.comparator, id).toBe('L2-cox');
    }
  });

  it('the view names the rungs in words, shows the measured numbers and the verdict, with no raw id', () => {
    for (const id of variantIds('C06')) {
      const ev = pchRecords(sel(id)).pch!.details!.evaluation!;
      for (const lang of ['en', 'es'] as const) {
        const markup = render(<PchView sel={sel(id)} />, lang);
        const text = textOf(markup);
        expect(text, `${id} ${lang}`).toContain('PC-Hazard');
        expect(text, `${id} ${lang}`).toContain('Aalen-Johansen');
        expect(text, `${id} ${lang}`).not.toMatch(/L3-pch|L2-cox|aalen-johansen|kaplan-meier|NaN|undefined/);
        expect(markup, `${id} ${lang}`).toContain('data-table="pch-summary"');
        expect(markup, `${id} ${lang}`).toContain(`data-verdict="${String(ev.holds_at_date)}"`);
        // the integrated Brier of both rungs is printed (five digits), whatever the language's decimal mark
        const fmt = (v: number | null) => (v === null ? null : formatNumber(v, lang, { decimals: 5 }));
        if (ev.integrated_brier.pch !== null) expect(text, `${id} ${lang}`).toContain(fmt(ev.integrated_brier.pch));
        if (ev.integrated_brier.cox !== null) expect(text, `${id} ${lang}`).toContain(fmt(ev.integrated_brier.cox));
      }
    }
  });

  it('the Spanish view carries no sentence of the English one', () => {
    for (const id of variantIds('C06')) {
      const es = textOf(render(<PchView sel={sel(id)} />, 'es'));
      for (const phrase of ['Predicted minus observed', 'Concordance index', 'Integrated Brier score', 'Hypothesis', 'Accounts', 'Decile']) {
        expect(es, `${id} ${phrase}`).not.toContain(phrase);
      }
      expect(es, id).toContain('Brecha');
    }
  });

  it('a horizon the follow-up has not reached is not available, with its reason, never a number', () => {
    let unobserved = 0;
    for (const id of variantIds('C06')) {
      const rows = pchRecords(sel(id)).pch!.details!.decile_calibration!;
      for (const r of rows) {
        expect(r.observed_aalen_johansen === null, `${id} ${r.months}/${r.decile}`).toBe(r.reason !== null);
        if (r.reason) unobserved += 1;
      }
    }
    expect(unobserved).toBeGreaterThanOrEqual(0);
  });

  it('every date carries the bootstrap block, the view prints each interval beside its difference and the count, in both languages', () => {
    const overall = new Set<string>();
    for (const id of variantIds('C06')) {
      const boot = bootstrapOf(sel(id));
      expect(boot, id).not.toBeNull();
      expect(boot!.differences.map((d) => d.measure), id).toEqual(['integrated_brier', 'mean_decile_gap']);
      expect(boot!.predictions_refit, id).toBe(false);
      overall.add(JSON.stringify(boot!.overall));
      for (const lang of ['en', 'es'] as const) {
        const markup = render(<PchView sel={sel(id)} />, lang);
        const text = textOf(markup);
        expect(markup, `${id} ${lang}`).toContain('data-table="pch-interval"');
        expect(markup, `${id} ${lang}`).toContain('data-note="pch-bootstrap-count"');
        for (const d of boot!.differences) {
          expect(markup, `${id} ${lang} ${d.measure}`).toContain(`data-measure="interval-${d.measure}"`);
          expect(markup, `${id} ${lang} ${d.measure}`).toContain(`data-excludes-zero="${String(d.excludes_zero)}"`);
          if (d.measure === 'integrated_brier' && d.lo !== null && d.hi !== null && d.difference !== null) {
            for (const v of [d.difference, d.lo, d.hi]) expect(text, `${id} ${lang}`).toContain(formatNumber(v, lang, { decimals: 5 }));
          }
        }
        const o = boot!.overall;
        const count =
          lang === 'en'
            ? `at ${o.holds_excluding_zero} of those ${o.holds_at} both intervals exclude zero`
            : `en ${o.holds_excluding_zero} de esas ${o.holds_at} ambos intervalos excluyen el cero`;
        expect(text, `${id} ${lang}`).toContain(count);
        expect(text, `${id} ${lang}`).not.toMatch(/integrated_brier|mean_decile_gap|NaN|undefined/);
        if (lang === 'es') for (const phrase of ['Excludes zero', 'Difference, PC-Hazard minus Cox', '95% interval']) expect(text, `${id} ${phrase}`).not.toContain(phrase);
      }
    }
    expect(overall.size, 'one count over the dates, the same in every document').toBe(1);
  });

  it('a date with no interval says why in both languages and never prints a number for it', () => {
    const id = variantIds('C06')[0];
    const boot = bootstrapOf(sel(id))!;
    const why = { en: 'planted: fewer than 30 defaults', es: 'plantado: menos de 30 incumplimientos' };
    const none = {
      ...boot,
      evaluated: false,
      reason: why,
      both_exclude_zero: null,
      differences: boot.differences.map((d) => ({ ...d, difference: null, lo: null, hi: null, excludes_zero: null, n_valid: 0, reason: why })),
    };
    const base = sel(id);
    const models = base.data.models as unknown as { fit: object };
    const planted = { ...base, data: { ...base.data, models: { ...models, fit: { ...models.fit, s4_bootstrap: none } } } } as unknown as C06Sel;
    for (const lang of ['en', 'es'] as const) {
      const text = textOf(render(<PchView sel={planted} />, lang));
      expect(text, lang).toContain(why[lang]);
    }
  });

  it('every date carries the nine settings of the sweep, the default equal to the committed evaluation, and the view prints them with the count in both languages', () => {
    const overall = new Set<string>();
    for (const id of variantIds('C06')) {
      const sweep = sensitivityOf(sel(id));
      expect(sweep, id).not.toBeNull();
      expect(sweep!.selected_setting, id).toBeNull();
      expect(sweep!.covers_months, id).toBe(180);
      overall.add(JSON.stringify(sweep!.overall));
      const ev = pchRecords(sel(id)).pch!.details!.evaluation!;
      if (!sweep!.evaluated) continue;
      expect(sweep!.settings.map((s) => s.setting_id), id).toEqual([
        'default', 'width-1.5', 'width-6', 'hidden-16', 'hidden-64', 'weight-decay-1e-5', 'weight-decay-1e-3', 'learning-rate-0.003', 'learning-rate-0.03',
      ]);
      for (const s of sweep!.settings) expect(s.parameters.interval_months * s.parameters.intervals, `${id} ${s.setting_id}`).toBe(180);
      const d = sweep!.settings[0].evaluation!;
      expect(d.holds_at_date, id).toBe(ev.holds_at_date);
      expect(d.integrated_brier.pch!, id).toBeCloseTo(ev.integrated_brier.pch!, 8);
      for (const lang of ['en', 'es'] as const) {
        const markup = render(<PchView sel={sel(id)} />, lang);
        const text = textOf(markup);
        expect(markup, `${id} ${lang}`).toContain('data-table="pch-sensitivity"');
        for (const s of sweep!.settings) {
          expect(markup, `${id} ${lang} ${s.setting_id}`).toContain(`data-setting="${s.setting_id}"`);
          if (s.evaluation?.integrated_brier.pch != null) expect(text, `${id} ${lang} ${s.setting_id}`).toContain(formatNumber(s.evaluation.integrated_brier.pch, lang, { decimals: 5 }));
        }
        const o = sweep!.overall;
        const count = lang === 'en' ? `in ${o.agree} of ${o.settings_count} settings` : `en ${o.agree} de ${o.settings_count} configuraciones`;
        expect(text, `${id} ${lang}`).toContain(count);
        expect(text, `${id} ${lang}`).not.toMatch(/weight_decay|interval_width|hidden_layers|not_converged|NaN|undefined/);
        if (lang === 'es') for (const phrase of ['Setting', 'Agrees with the default', 'Verdict over all dates', 'stopped early']) expect(text, `${id} ${phrase}`).not.toContain(phrase);
      }
    }
    expect(overall.size, 'one count over the dates, the same in every document').toBe(1);
    const o = JSON.parse([...overall][0]) as { case_verdict: string | null; case_setting: string };
    const verdicts = new Set(variantIds('C06').map((id) => bootstrapOf(sel(id))!.overall.verdict));
    expect([...verdicts], 'the case verdict is the one of the S-4 block').toEqual([o.case_verdict]);
    expect(o.case_setting).toBe('default');
  });

  it('a setting whose fit failed or ran to the cap is listed with its status and reason, and a date with no sweep says why', () => {
    const id = variantIds('C06')[0];
    const base = sel(id);
    const sweep = sensitivityOf(base)!;
    const why = { en: 'planted: the fit raised', es: 'plantado: el ajuste falló' };
    const settings = sweep.settings.map((s, i) => (i === 2 ? { ...s, status: 'failed', reason: why, evaluation: null } : i === 3 ? { ...s, status: 'not_converged', reason: why } : s));
    const models = base.data.models as unknown as { fit: object };
    const plant = (block: unknown) => ({ ...base, data: { ...base.data, models: { ...models, fit: { ...models.fit, pch_sensitivity: block } } } }) as unknown as C06Sel;
    for (const lang of ['en', 'es'] as const) {
      const markup = render(<PchView sel={plant({ ...sweep, settings })} />, lang);
      expect(markup, lang).toContain('data-status="failed"');
      expect(markup, lang).toContain('data-status="not_converged"');
      expect(textOf(markup), lang).toContain(why[lang]);
      const none = plant({ ...sweep, evaluated: false, settings: [], reason: why });
      const text = textOf(render(<PchView sel={none} />, lang));
      expect(text, lang).toContain(why[lang]);
      expect(text, lang).not.toMatch(/NaN|undefined/);
    }
  });
});
