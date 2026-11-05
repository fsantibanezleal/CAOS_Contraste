// U16-R2 (b06 B3, B4): the Spanish views of C13 name the truth status, the parameters, the units and the paragraph ranges in Spanish, and the
// findings box keeps a readable height on a phone. Reads the committed documents (the 1.0 bake the review read).
import { afterEach, describe, expect, it } from 'vitest';
import { setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { C13ContextView, FINDINGS_MIN_HEIGHT, C13FindingsView } from './C13Common';
import { DeskView } from './DeskViews';
import { defaultSel } from './selection';

const title = { en: 'Trading desk P&L attribution', es: 'Atribución de P&L de la mesa' };
const data = committedData('C13', 'omitted-factor.json', 'models-generator.json', title);
const ENGLISH = [/synthetic-known-truth/, /loading_\d/, /decimal-per-sd/, /share-of-hpl-sd/, /omitted_loading_share/, /MAR32\.\d+ to MAR/, /\bdays\b/, /desk-pnl-generator/, /per-day|log-points/];

describe('the Spanish views of C13', () => {
  afterEach(() => setLang('en'));

  it('the context and the desk view are in Spanish', () => {
    setLang('es');
    for (const V of [C13ContextView, DeskView]) {
      const text = view(<V sel={defaultSel(data)} />);
      for (const re of ENGLISH) expect(text, `${V.name} ${re}`).not.toMatch(re);
    }
    expect(view(<DeskView sel={defaultSel(data)} />)).toContain('MAR32.18 a MAR32.19');
    expect(view(<C13ContextView sel={defaultSel(data)} />)).toContain('Sintético, con una verdad conocida');
  });

  it('the findings box has a floor height so the card is reachable on a phone', () => {
    setLang('es');
    expect(FINDINGS_MIN_HEIGHT).toBe('min(70vh, 36rem)');
    // the floor is the stylesheet's, below 900 px only: at 1280 the box fills the instrument (R2b c14 M1)
    expect(view(<C13FindingsView sel={defaultSel(data)} />)).not.toBe('');
    expect(view(<C13FindingsView sel={defaultSel(data)} />)).toContain('Deficiencia conocida');
  });
});
