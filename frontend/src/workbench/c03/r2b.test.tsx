// U16-R2b (batch c04, C03): the Context names the truth status and the data source in words (B1: "real-outcomes", "sba-7a"), and
// the reason a rung did not run reads in Spanish in the Spanish view (M2: the TabPFN reason in English).
import { afterEach, describe, expect, it } from 'vitest';
import { setLang } from './u6-testkit';
import { committed, committedData, view } from '../c08/spanish-testkit';
import { C03ContextView } from './C03Common';
import { defaultSel, reasonText, type C03Sel } from './selection';

const TITLE = { en: 'SME PD on vintages', es: 'PD pyme por cosechas' };

describe('U16-R2b c04: C03', () => {
  afterEach(() => setLang('en'));

  it('B1: the Context prints no raw truth status and no raw source id, in either language', () => {
    const sel = defaultSel(committedData('C03', 'fy2008-10.json', 'models-sba-7a.json', TITLE)) as C03Sel;
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const text = view(<C03ContextView sel={sel} />);
      expect(text).not.toMatch(/real-outcomes|\bsba-7a\b/);
    }
    setLang('es');
    expect(view(<C03ContextView sel={sel} />)).toContain('Resultados reales');
  });

  it('M2: every reason a committed document gives for a rung it did not run has its Spanish', () => {
    const reasons = new Set<string>();
    for (const f of ['fy2006-07.json', 'fy2008-10.json', 'fy2011-14.json', 'fy2015-17.json', 'fy2018-20.json']) {
      const o = committed<{ outputs: { rung_comparison: Array<{ reason: string | null }> } }>('C03', f).outputs;
      for (const r of o.rung_comparison) if (r.reason) reasons.add(r.reason);
    }
    expect(reasons.size).toBeGreaterThan(0);
    for (const r of reasons) expect(reasonText(r).es, r).not.toBe(r);
  });
});
