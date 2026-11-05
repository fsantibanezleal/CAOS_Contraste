// U16-R2 (b04 B3, B5, B6, M2): the Spanish views of C08 say in Spanish what they print, and a year is never grouped. Reads the committed
// documents of the cohort 2011-13 (the 1.0 bake), the ones the capture review read.
import { afterEach, describe, expect, it } from 'vitest';
import { setLang } from '../c03/u6-testkit';
import { committedData, view } from './spanish-testkit';
import { C08ContextView } from './C08Common';
import { DownturnView, FloorsView, YEAR_FORMAT } from './DownturnViews';
import { ProxyView } from './SeverityViews';
import { YEAR_FORMAT as MODEL_YEAR_FORMAT } from './ModelViews';
import { defaultSel, type C08Sel } from './selection';

const data = committedData('C08', 'dc-2011-13.json', 'models-dc-2011-13.json', { en: 'LGD and downturn LGD', es: 'LGD y LGD de recesión' });
const sel = defaultSel(data) as C08Sel;

const ENGLISH = [/real-outcomes/, /sba-7a-chargeoff-twin/, /\bSME (revolver|term)\b/, /\bnot available\b/, /\bthe SBA file\b/, /charge-off rate of the SBA/, /owner's account/, /CRE32\.\d+ to /];

describe('the Spanish views of C08', () => {
  afterEach(() => setLang('en'));

  it('the context names the data, the truth status and the reasons in Spanish', () => {
    setLang('es');
    const markup = view(<C08ContextView sel={sel} />);
    for (const re of ENGLISH) expect(markup, String(re)).not.toMatch(re);
    expect(markup).toContain('Resultados reales');
    expect(markup).toContain('falta la cuenta del propietario');
    expect(markup).toContain('el archivo SBA no tiene flujos de recuperación');
    setLang('en');
    expect(view(<C08ContextView sel={sel} />)).toContain('account is missing; the SBA twin is published');
  });

  it('the downturn note writes the indicator and the macro source in Spanish', () => {
    setLang('es');
    const markup = view(<DownturnView sel={sel} />);
    expect(markup).toContain('tasa anual de castigos de la cartera SBA 7(a)');
    expect(markup).not.toMatch(/charge-off rate|no macro path/);
  });

  it('the floors name each segment with its term in Spanish and write the paragraph range in Spanish', () => {
    setLang('es');
    const markup = view(<FloorsView sel={sel} />);
    for (const re of ENGLISH) expect(markup, String(re)).not.toMatch(re);
    expect(markup).toContain('Línea rotativa pyme');
    expect(markup).toContain('Préstamo a plazo pyme, de 85 a 239 meses');
    expect(markup).toContain('CRE32.58 a CRE32.59');
    setLang('en');
    const en = view(<FloorsView sel={sel} />);
    expect(en).toContain('SME term loan, 85 to 239 months');
    expect(en).toContain('CRE32.58 to CRE32.59');
  });

  it('the proxy view names its data and nothing raw', () => {
    setLang('es');
    const markup = view(<ProxyView sel={sel} />);
    for (const re of ENGLISH) expect(markup, String(re)).not.toMatch(re);
  });

  it('the year axes do not group their digits (2009, not 2.009)', () => {
    expect(YEAR_FORMAT).toEqual({ decimals: 0, grouping: false });
    expect(MODEL_YEAR_FORMAT).toEqual({ decimals: 0, grouping: false });
  });
});
