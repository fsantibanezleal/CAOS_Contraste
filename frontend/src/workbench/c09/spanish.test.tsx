// U16-R2 (b04 B3, B7): the Spanish views of C09 name their data, their facility classes and their items in Spanish. Reads the committed
// documents of the level 2 (the 1.0 bake), the ones the capture review read.
import { afterEach, describe, expect, it } from 'vitest';
import { setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { C09ContextView } from './C09Common';
import { FloorsView } from './EadViews';
import { defaultSel, type C09Sel } from './selection';

const data = committedData('C09', 'level-2.json', 'models-generator.json', { en: 'EAD and CCF for revolving lines', es: 'EAD y CCF de líneas rotativas' });
const sel = defaultSel(data) as C09Sel;
const ENGLISH = [/real-outcomes/, /synthetic-known-truth/, /fed-2025/, /\bUnconditionally\b/, /\bNifs\b/, /\bcommitments\b/i, /\bon-balance\b/, /CRE\d+\.\d+ to /, /Direct credit substitutes/i];

describe('the Spanish views of C09', () => {
  afterEach(() => setLang('en'));

  it('the context names the truth status and the generator source in Spanish', () => {
    setLang('es');
    const text = view(<C09ContextView sel={sel} />);
    for (const re of ENGLISH) expect(text, String(re)).not.toMatch(re);
    expect(text).toContain('Sintético, con una verdad conocida');
    expect(text).toContain('carteras hipotéticas de tarjetas de crédito');
    setLang('en');
    expect(view(<C09ContextView sel={sel} />)).toContain('Synthetic, with a known truth');
  });

  it('the floors name each facility class and supervisory item in Spanish, and the rule too', () => {
    setLang('es');
    const text = view(<FloorsView sel={sel} />);
    for (const re of ENGLISH) expect(text, String(re)).not.toMatch(re);
    expect(text).toContain('Cancelable sin condiciones');
    expect(text).toContain('Compromisos');
    expect(text).toContain('Contingentes relacionados con transacciones (NIF y RUF)');
    expect(text).toContain('Monto en balance + 50');
    expect(text).toContain('CRE20.94 a CRE20.101');
    setLang('en');
    const en = view(<FloorsView sel={sel} />);
    expect(en).toContain('Unconditionally cancellable');
    expect(en).toContain('On-balance amount + 50');
  });
});
