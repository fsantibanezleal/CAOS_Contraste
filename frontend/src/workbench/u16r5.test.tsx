// U16-R5 (the fifth capture review): the Findings evidence of C01 reads the row a finding cites by its full id, so a grade row's p and
// light are its own, never the portfolio row's (R5 c01 B1, c02 B1: holdout P3 EBM G01 printed p 0.78 green where the document has 1e-7 red).
import { describe, expect, it } from 'vitest';
import { committedData } from './c03/u16f2-kit';
import { cited } from './FindingsView';

const sel = (v: string) => ({ data: committedData('C01', v) }) as never;

describe('U16-R5 C01 Findings evidence', () => {
  for (const v of ['holdout', 'small-sample', 'german-twin', 'drift-moderate', 'prior-shift']) {
    it(`${v}: every evidence id of a red-row finding resolves to its own row, and that row is red`, () => {
      const s = sel(v) as { data: { variant: { findings: Array<{ id: string; evidence: string[] }>; tests: Array<{ test_id: string; model_id: string | null; segment: string | null; light: string }> } } };
      const red = s.data.variant.findings.filter((f) => f.id.startsWith('F-RED-'));
      for (const f of red) {
        for (const e of f.evidence) {
          const row = cited(s as never, e);
          expect(row, `${v} ${e}`).toBeDefined();
          const [t, m, seg] = e.split('@');
          expect(row!.test_id).toBe(t);
          if (m && m !== '-') expect(row!.model_id).toBe(m);
          if (seg) expect(row!.segment).toBe(seg);
          expect(row!.light, `${v} ${e}`).toBe('red');
        }
      }
    });
  }
});
