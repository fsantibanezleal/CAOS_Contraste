// U16-R2 (b06 B1, B3, M2, M3): the Spanish views of C12 translate the engine notes, the ORE platform and the paragraph ranges, and the charts
// carry short axis titles. Reads the committed documents of the netting set (the 1.0 bake the review read).
import { afterEach, describe, expect, it } from 'vitest';
import { setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { C12ContextView, C12TestsView } from './C12Common';
import { CvaView } from './CreditViews';
import { ProfileView } from './ExposureViews';
import { ComparisonView, GirrView } from './RegulatoryViews';
import { defaultSel } from './selection';
import { platformText } from '../c08/notes';

const title = { en: 'Counterparty credit risk', es: 'Riesgo de crédito de contraparte' };
const nettingData = committedData('C12', 'netting-set.json', 'models-hw1f-treasury-2000-2025.json', title);
const wwrData = committedData('C12', 'wrong-way-risk.json', 'models-hw1f-treasury-2000-2025.json', title);
const ENGLISH = [/critical value the/, /secondary row/, /\d wheel,/, /MAR\d+ to MAR/, /combined standard errors(?! *;)(?<![a-z] errores)/, /native \(no WSL\)/, /\bsamples, antithetic\b/, /exceedances in \d+ dates/];

describe('the Spanish views of C12', () => {
  afterEach(() => setLang('en'));

  it('the tests table translates the engine notes', () => {
    setLang('es');
    const text = view(<C12TestsView sel={defaultSel(nettingData)} />);
    for (const re of ENGLISH) expect(text, String(re)).not.toMatch(re);
    // R3 c13 m4 (U16-F10a): the statistic written W², the horizon in words
    expect(text).toMatch(/W² supera el valor crítico simulado/);
  });

  it('the profile and the comparison write the ORE platform and the paragraph ranges in Spanish', () => {
    setLang('es');
    for (const V of [ProfileView, ComparisonView, C12ContextView, GirrView, CvaView]) {
      for (const data of [nettingData, wwrData]) {
        const text = view(<V sel={defaultSel(data)} />);
        for (const re of ENGLISH) expect(text, `${V.name} ${re}`).not.toMatch(re);
      }
    }
    expect(view(<ProfileView sel={defaultSel(nettingData)} />)).toContain('nativo (sin WSL)');
    expect(view(<ComparisonView sel={defaultSel(nettingData)} />)).toMatch(/CRE53\.7 y CRE53\.51/);
    expect(view(<ComparisonView sel={defaultSel(nettingData)} />)).not.toMatch(/CRE53\.7 and CRE53\.51/);
  });

  it('the platform string keeps its machine fields and translates its words', () => {
    const p = 'open-source-risk-engine 1.8.17.0 wheel, CPython 3.13.5, Windows 11 AMD64, native (no WSL); 10000 samples, antithetic';
    expect(platformText(p, 'en')).toBe(p);
    expect(platformText(p, 'es')).toBe('open-source-risk-engine 1.8.17.0 paquete, CPython 3.13.5, Windows 11 AMD64, nativo (sin WSL); 10.000 muestras, antitéticas');
  });
});
