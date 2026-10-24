// U16-R2b (batch c10): each C09 sub-tab lists its own tests (B1: "By design and tests" listed none and the back-test all 32, since
// every C09 test id starts `lgd_ead.`), the models name their covariates in words (B3), the distribution states its totals above
// its table (M1), the interval is the bias's (m12), the colours have a legend (m5) and a level with no acceleration says none (m6).
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import { html, setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { ByDesignView, DistributionView } from './CcfViews';
import { BacktestView, ModelsView } from './EadViews';
import { defaultSel, type C09Sel } from './selection';

const data = committedData('C09', 'level-3.json', 'models-generator.json', { en: 'EAD and CCF for revolving lines', es: 'EAD y CCF de líneas rotativas' });
const sel = defaultSel(data) as C09Sel;
const testRows = (html: string, id: string) => (html.match(new RegExp(`data-test="${id.replace('.', '\\.')}"`, 'g')) ?? []).length;

describe('U16-R2b c10: the C09 sub-tabs', () => {
  afterEach(() => setLang('en'));

  it('B1: By design lists the estimator-bias tests of the design in focus, and no back-test row', () => {
    const markup = html(<ByDesignView sel={sel} />);
    expect(testRows(markup, 'lgd_ead.ccf_estimator_bias')).toBe(8);
    expect(testRows(markup, 'lgd_ead.ead_backtest_by_band')).toBe(0);
    expect(markup).not.toMatch(/ccf-fixed-horizon-[a-z-]+</);
  });

  it('B1: the back-test lists the EAD back-test rows only', () => {
    const markup = html(<BacktestView sel={sel} />);
    expect(testRows(markup, 'lgd_ead.ead_backtest_by_band')).toBe(8);
    expect(testRows(markup, 'lgd_ead.ccf_estimator_bias')).toBe(0);
  });

  it('B3: the models name their covariates in Spanish, never the ids', () => {
    setLang('es');
    const text = view(<ModelsView sel={sel} />);
    expect(text).toContain('utilización');
    expect(text).toContain('logaritmo del límite');
    expect(text).not.toMatch(/log_limit|credit_score/);
    expect(text).toContain('no aplica');
  });

  it('M1: the distribution states its totals above the table', () => {
    expect(view(<DistributionView sel={sel} />)).toMatch(/defaults in the design: [\d,]+ below 0 and [\d,]+ above 1, kept and not clipped/);
  });

  it('m12 and m5: the interval is the bias\'s, and the bar colours have a legend', () => {
    const markup = html(<ByDesignView sel={sel} />);
    expect(markup).toContain('Interval of the bias');
    // the BarChart draws its legend once mounted: the view passes one entry per tone it uses
    expect(readFileSync(new URL('./CcfViews.tsx', import.meta.url), 'utf8')).toMatch(/legend=\{\[[^\]]*Within the tolerance/);
  });
});
