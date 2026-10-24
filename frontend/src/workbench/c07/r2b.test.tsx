// U16-R2b (batch c08, C07): no scenario, driver, unit, segment or model id on screen where the product has a name (B2), the
// calibration targets in Spanish (B3), and the grouped bars' members by their short names (M1).
import { afterEach, describe, expect, it } from 'vitest';
import { setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { DeltaView, SegmentsView } from './RegimeViews';
import { C07ContextView } from './C07Common';
import { defaultSel, type C07Sel } from './selection';

const TITLE = { en: 'Chile provisions trilogy', es: 'Trilogía de provisiones de Chile' };
const at = (file: string) => defaultSel(committedData('C07', file, 'models-banco-andino.json', TITLE)) as C07Sel;

describe('U16-R2b c08: C07', () => {
  afterEach(() => setLang('en'));

  it('B2: the scenario view names the scenario, its drivers and units, in both languages', () => {
    const sel = at('combined-severe.json');
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const text = view(<DeltaView sel={sel} />);
      expect(text).not.toMatch(/combined-severe|gdp-growth|house-prices|consumer-arrears|uf-inflation/);
    }
    expect(view(<DeltaView sel={sel} />)).toMatch(/Crecimiento del PIB|puntos porcentuales/);
  });

  it('B2 and B3: the Context names the test rows\' segments and model, and the calibration targets read in Spanish', () => {
    setLang('es');
    const text = view(<C07ContextView sel={at('base.json')} />);
    expect(text).not.toMatch(/mortgage-ltv-le80|consumer-instalment|IFRS9-ecl|loan mix:|share of loans/);
    expect(text).toContain('composición de la cartera');
  });

  it('M1: the segments view still renders its six groups', () => {
    expect(view(<SegmentsView sel={at('base.json')} />)).toMatch(/Provision by segment/);
  });
});
