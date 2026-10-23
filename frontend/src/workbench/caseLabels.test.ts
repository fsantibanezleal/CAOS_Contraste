// The rail's short case names fit one line of the case select in both languages (ADR-0071 rule 6): the shell sizes the
// select to the longest name of the list, so one long name makes every rail's head taller (the C18 and C22 rails scrolled in
// Spanish at 1280 x 800 while the Spanish names took two lines; U16, 2026-10-22).
import { describe, expect, it } from 'vitest';
import { CASE_LABEL, caseLabel } from './caseLabels';

const MAX = 26; // the longest English name, which fits one line of the 182 px select

describe('the short case names of the rail', () => {
  it('every name fits one line in both languages', () => {
    for (const [id, l] of Object.entries(CASE_LABEL)) {
      expect(l.en.length, `${id} en: ${l.en}`).toBeLessThanOrEqual(MAX);
      expect(l.es.length, `${id} es: ${l.es}`).toBeLessThanOrEqual(MAX);
    }
  });

  it('no two cases share a name in either language', () => {
    for (const lang of ['en', 'es'] as const) {
      const names = Object.values(CASE_LABEL).map((l) => l[lang]);
      expect(new Set(names).size, lang).toBe(names.length);
    }
  });

  it('a case with no entry shows its baked title', () => {
    expect(caseLabel('C99', { en: 'A later case', es: 'Un caso posterior' }, 'es')).toBe('Un caso posterior');
  });
});
