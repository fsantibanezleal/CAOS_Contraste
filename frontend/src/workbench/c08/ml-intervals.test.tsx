// the S-5 benchmark beside its verdict. Each test cohort's document carries the loan-level bootstrap interval of the RMSE
// gain of the better of the random forest and the neural network against each of the six models before them and against the best of
// the six; the Models view prints each interval beside its difference and the count over the cohorts, in both languages, on the
// committed documents (the real bake). A model that was not fitted has no comparison, with its reason.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it } from 'vitest';
import { html, setLang } from '../c03/u6-testkit';
import { committedData } from './spanish-testkit';
import { RungsView } from './ModelViews';
import { defaultSel, outputsOf, type C08Sel } from './selection';

const TITLE = { en: 'LGD and downturn LGD', es: 'LGD y LGD de recesión' };
const COHORTS = ['dc-2003-06', 'dc-2007-08', 'dc-2009-10', 'dc-2011-13', 'dc-2014-19', 'dc-2020-23'];
const selOf = (c: string) => defaultSel(committedData('C08', `${c}.json`, `models-${c}.json`, TITLE)) as C08Sel;
const text = (m: string) => m.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');

describe('the S-5 intervals in the Models view', () => {
  afterEach(() => setLang('en'));

  it('every cohort carries the block, one interval per earlier model and one against the best, and the same count over the cohorts', () => {
    const overall = new Set<string>();
    for (const c of COHORTS) {
      const b = outputsOf(selOf(c))!.ml_benchmark;
      expect(b.against.length, c).toBe(6);
      expect(b.resampled_unit, c).toBe('default');
      expect(b.predictions_refit, c).toBe(false);
      expect(b.interval_excludes_zero, c).toBe(b.against_best.excludes_zero);
      overall.add(JSON.stringify(b.overall));
    }
    expect(overall.size).toBe(1);
  });

  it('the view prints each interval beside its difference in both languages, with the count and no raw id', () => {
    for (const c of COHORTS) {
      const sel = selOf(c);
      const b = outputsOf(sel)!.ml_benchmark;
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const markup = html(<RungsView sel={sel} />);
        const t = text(markup);
        expect(markup, `${c} ${lang}`).toContain('data-table="ml-intervals"');
        expect(markup, `${c} ${lang}`).toContain('data-ml-row="best"');
        for (const d of b.against) {
          expect(markup, `${c} ${lang}`).toContain(`data-ml-row="${d.rung_id}"`);
          if (d.difference !== null && d.lo !== null && d.hi !== null) {
            for (const v of [d.difference, d.lo, d.hi]) expect(t, `${c} ${lang} ${d.rung_id}`).toContain(formatNumber(v, lang, { decimals: 4 }));
          }
        }
        const o = b.overall;
        const count =
          lang === 'en'
            ? `in ${o.wins_excluding_zero} of those ${o.wins} the interval against the best of the six excludes zero`
            : `en ${o.wins_excluding_zero} de esas ${o.wins} el intervalo frente al mejor de los seis excluye el cero`;
        expect(t, `${c} ${lang}`).toContain(count);
        if (lang === 'es') for (const phrase of ['Excludes zero', 'RMSE gain of the better', '95% interval']) expect(t, `${c} ${phrase}`).not.toContain(phrase);
        expect(t, `${c} ${lang}`).not.toMatch(/NaN|undefined|against_best|interval_excludes/);
      }
    }
  });

  it('a model that was not fitted has no comparison, with its reason in both languages, never a number', () => {
    const sel = selOf('dc-2009-10');
    const o = outputsOf(sel)!;
    const reason = { en: 'rung L3-beta was not fitted: planted', es: 'la etapa L3-beta no se ajustó: plantado' };
    const against = o.ml_benchmark.against.map((d) => (d.rung_id === 'L3-beta' ? { ...d, difference: null, lo: null, hi: null, excludes_zero: null, n_valid: 0, reason } : d));
    const variant = { ...sel.data.variant, outputs: { ...o, ml_benchmark: { ...o.ml_benchmark, against } } };
    const planted = { ...sel, data: { ...sel.data, variant } } as unknown as C08Sel;
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      expect(text(html(<RungsView sel={planted} />)), lang).toContain(reason[lang]);
    }
  });
});
