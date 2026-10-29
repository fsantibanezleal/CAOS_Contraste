// U16-F10b (fix round 4, the R3 capture review of C06, batch c07), on the committed C06 documents in both languages: the
// non-linearity note follows the sign of the committed index (B1), the ladder note says what each rung is (B2), the covariates by
// their codebook names (B3), the cohort and movement ids in words (B4, B5), the percent axes at a resolution that prints their
// ticks (M2), the backtest table's columns in reach at 1280 (M1), and the minors of the views.
import { afterEach, describe, expect, it } from 'vitest';
import { committedData, render, textOf, variantIds } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { C06ContextView } from './C06Common';
import { NonLinearityView } from './TermViews';
import { BacktestView, LadderView, PCT_AXIS, TestRowsCard } from './ValidationViews';
import { covariateText, defaultSel, movementText, type C06Sel } from './selection';

const sel = (id: string) => defaultSel(committedData('C06', id)) as C06Sel;
const RAW_COVARIATE = /\b(?:size_\w+|term_\d+_\w+|term_over_\d+|sector_[\w-]+|age_q_\w+|unemployment_rate|real_gdp_growth|prime_rate)\b/;
const LANGS = ['en', 'es'] as const;

describe('U16-R3 c07 on the committed C06 documents', () => {
  afterEach(() => setLang('en'));

  it('B1: the non-linearity note follows the sign of the committed index (Dec 2010 overstates, every other date understates)', () => {
    for (const v of variantIds('C06')) {
      const index = (sel(v).data.variant.outputs as unknown as { non_linearity: { index: number } }).non_linearity.index;
      const en = textOf(render(<NonLinearityView sel={sel(v)} />, 'en'));
      const es = textOf(render(<NonLinearityView sel={sel(v)} />, 'es'));
      if (index < 0) {
        expect(en, v).toContain('averaging the scenarios first would overstate the loss');
        expect(es, v).toContain('promediar primero los escenarios sobrestimaría la pérdida');
        expect(en, v).not.toContain('understate');
      } else {
        expect(en, v).toContain('averaging the scenarios first would understate the loss');
        expect(es, v).toContain('promediar primero los escenarios subestimaría la pérdida');
        expect(en, v).not.toContain('overstate');
      }
    }
    expect((sel('rd-2010-12').data.variant.outputs as unknown as { non_linearity: { index: number } }).non_linearity.index).toBeLessThan(0);
  });

  it('B2: the ladder note says what each rung is and that prepayment is censored in all four, as the table shows', () => {
    for (const v of variantIds('C06')) {
      const en = textOf(render(<LadderView sel={sel(v)} />, 'en'));
      const es = textOf(render(<LadderView sel={sel(v)} />, 'es'));
      expect(en).not.toContain('each rung adds a piece');
      expect(en).not.toContain('competing prepayment');
      expect(en).toContain('prepayment is censored in all four');
      expect(es).toContain('el prepago se censura en los cuatro');
      expect(es).not.toContain('cada peldaño agrega una pieza');
    }
  });

  it('B3: the covariates of a rung by their names, never the fit codes, in both languages', () => {
    for (const lang of LANGS) {
      for (const v of variantIds('C06')) {
        const t = textOf(render(<LadderView sel={sel(v)} />, lang));
        expect(t, `${lang} ${v}`).not.toMatch(RAW_COVARIATE);
      }
    }
    expect(covariateText('size_50k_150k')).toEqual({ en: 'Size USD 50,000 to 150,000', es: 'Monto USD 50.000 a 150.000' });
    expect(covariateText('size_over_350k')).toEqual({ en: 'Size above USD 350,000', es: 'Monto sobre USD 350.000' });
    expect(covariateText('term_61_120')).toEqual({ en: 'Term 61 to 120 months', es: 'Plazo de 61 a 120 meses' });
    expect(covariateText('term_over_240')).toEqual({ en: 'Term over 240 months', es: 'Plazo sobre 240 meses' });
    expect(covariateText('sector_mining-utilities-construction')).toEqual({ en: 'Mining, utilities and construction', es: 'Minería, servicios básicos y construcción' });
    expect(covariateText('age_q_2_3')).toEqual({ en: 'Loan age 2 to 3 quarters', es: 'Antigüedad de 2 a 3 trimestres' });
    expect(covariateText('age_q_40_plus')).toEqual({ en: 'Loan age 40 quarters or more', es: 'Antigüedad de 40 trimestres o más' });
    expect(covariateText('unemployment_rate').es).toBe('Tasa de desempleo');
    expect(covariateText('revolver')).toEqual({ en: 'Revolving line', es: 'Línea revolvente' });
  });

  it('B4 and B5: the Spanish Context prints the cohorts and the repayments in words', () => {
    for (const v of variantIds('C06')) {
      const t = textOf(render(<C06ContextView sel={sel(v)} />, 'es'));
      expect(t, v).not.toMatch(/\b(?:all|older|repayments)\b/);
    }
    expect(movementText('repayments')).toEqual({ en: 'repayments', es: 'amortizaciones' });
  });

  it('M1: the backtest table has the room of half the row, its Estimator under the cohort, at 1280', () => {
    for (const lang of LANGS) {
      const markup = render(<BacktestView sel={sel('rd-2008-12')} />, lang);
      const head = markup.match(/<table[^>]*data-table="lifetime-backtest"[\s\S]*?<\/thead>/)?.[0] ?? '';
      expect([...head.matchAll(/<th[\s>]/g)].length).toBe(6); // the estimator moved under the cohort: six columns, not seven
      expect(head).not.toMatch(/Estimator|Estimador/);
      expect(markup).toMatch(/ct-row-detail">(?:observed by|observada por) (?:Kaplan-Meier|Aalen-Johansen)/);
    }
  });

  it('M2: every percent axis of the views prints its ticks with one decimal, never two significant digits', () => {
    expect(PCT_AXIS).toEqual({ percent: true, decimals: 1 });
  });

  it('m1: a p-value the engine returns as 0 prints as below the smallest shown, never "0"', () => {
    const v = structuredClone(sel('rd-2008-12').data.variant);
    v.tests = [{ ...v.tests[0], p_value: 0 }];
    for (const lang of LANGS) {
      const t = textOf(render(<TestRowsCard variant={v} prov="real" />, lang));
      expect(t).toContain(lang === 'en' ? '< 0.0001' : '< 0,0001');
    }
  });

  it('m4: a movement reads with a colon before its amount', () => {
    const t = textOf(render(<C06ContextView sel={sel('rd-2008-12')} />, 'es'));
    expect(t).toMatch(/traspaso de 2 a 3: [\d.]+,\d{2}/);
  });

  it('m7 and m11: one spelling of "período", and the EIR basis reads as policy', () => {
    for (const v of variantIds('C06')) {
      expect(textOf(render(<C06ContextView sel={sel(v)} />, 'es'))).not.toMatch(/\bperiodo\b/);
      expect(textOf(render(<LadderView sel={sel(v)} />, 'es'))).not.toMatch(/\bperiodo\b/);
      const en = textOf(render(<C06ContextView sel={sel(v)} />, 'en'));
      expect(en).not.toContain('EIR basis original');
      expect(en).toContain('original EIR basis');
    }
  });

  it('the Spanish texts of these views carry no ruled English word', () => {
    for (const v of variantIds('C06')) {
      for (const el of [<LadderView sel={sel(v)} />, <BacktestView sel={sel(v)} />, <C06ContextView sel={sel(v)} />]) {
        expect(textOf(render(el, 'es'))).not.toMatch(/\b(?:backtest|Backtest|hazard|proxy)\b/);
      }
    }
  });
});
