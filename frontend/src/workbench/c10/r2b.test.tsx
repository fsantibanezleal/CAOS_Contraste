// U16-R2b (batch c11): the correlation note counts the years the fit used (B3: "With 22 years" on the commercial real estate and
// residential fits, which used 16), and the ladder's Scenarios cell wraps its reason (M1: a nowrap sentence pushed four columns past
// the card at 1280).
import { afterEach, describe, expect, it } from 'vitest';
import { html, setLang } from '../c03/u6-testkit';
import { committed, committedData, view } from '../c08/spanish-testkit';
import { CorrelationView } from './FitViews';
import { LadderView } from './ModelViews';
import { defaultSel, type C10Sel } from './selection';

const TITLE = { en: 'Portfolio credit risk', es: 'Riesgo de crédito de cartera' };

describe('U16-R2b c11: C10', () => {
  afterEach(() => setLang('en'));

  for (const file of ['commercial-real-estate.json', 'residential.json', 'credit-cards.json']) {
    it(`B3: the correlation note counts the years ${file} used`, () => {
      const years = committed<{ outputs: { fit: { n_years_used: number } } }>('C10', file).outputs.fit.n_years_used;
      const sel = defaultSel(committedData('C10', file, 'models-c10.json', TITLE)) as C10Sel;
      expect(view(<CorrelationView sel={sel} />)).toContain(`With ${years} years the interval is wide`);
      setLang('es');
      expect(view(<CorrelationView sel={sel} />)).toContain(`Con ${years} años el intervalo es ancho`);
    });
  }

  it('M1: the Scenarios cell of the ladder wraps its reason', () => {
    const sel = defaultSel(committedData('C10', 'commercial-industrial.json', 'models-c10.json', TITLE)) as C10Sel;
    expect(html(<LadderView sel={sel} />)).toMatch(/<td class="ct-text ct-wide-only" data-na="true">/);
  });
});
