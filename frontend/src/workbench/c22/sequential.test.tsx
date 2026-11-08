// BS-15 (unit D15) on the committed C22 documents: the other-families variant carries the e-process monitors against the fixed-window tests read
// every day, and its Validation group draws them in a Sequential tab, in both languages: the three hypotheses with their measured numbers and
// the verdict, the VaR-hit scenarios and the PD book. Every other variant carries a null block and draws no such tab.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { COMMITTED } from '../../lib/policy';
import { committedData, render, textOf, variantIds } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { START, useC22Instrument } from './instrument';
import { isC22, type C22Sel } from './selection';
import { SequentialView } from './SequentialView';

const sel = (data: CaseData): C22Sel => ({ data, alphas: COMMITTED, level: 0.05, portfolio: { ...START } });
const seqOf = (id: string) => {
  const v = committedData('C22', id).variant as VariantArtifact<unknown>;
  if (!isC22(v)) throw new Error('not a C22 variant');
  return v.outputs.sequential;
};
function Validation({ data }: { data: CaseData }) {
  const inst = useC22Instrument(data, () => undefined);
  return <div>{inst?.groups.find((g) => g.id === 'validation')?.content}</div>;
}

describe('BS-15 on the committed C22 documents', () => {
  afterEach(() => setLang('en'));

  it('only the other-families variant carries the block, and only it draws the Sequential tab', () => {
    for (const id of variantIds('C22')) {
      expect(seqOf(id) !== null, id).toBe(id === 'other-families');
      const tab = textOf(render(<Validation data={committedData('C22', id)} />, 'en'));
      expect(tab.includes('Sequential'), id).toBe(id === 'other-families');
    }
  });

  it('draws the three hypotheses with their verdict, every VaR-hit scenario and every PD scenario, in both languages', () => {
    const data = committedData('C22', 'other-families');
    const s = seqOf('other-families')!;
    for (const lang of ['en', 'es'] as const) {
      const markup = render(<SequentialView sel={sel(data)} />, lang);
      for (const h of s.hypotheses) {
        expect(markup).toContain(`data-hypothesis="${h.id}" data-holds="${h.holds ? 'yes' : 'no'}"`);
        expect(textOf(markup)).toContain(textOf(h.rule[lang]).slice(0, 40));
      }
      for (const x of s.hits.scenarios) expect(markup, x.id).toContain(`data-scenario="${x.id}"`);
      for (const x of s.pd_grades.scenarios) expect(markup, x.id).toContain(`data-scenario="${x.id}"`);
      expect(markup).toContain(`data-sequential-verdict="${s.verdict.holds ? 'holds' : 'refuted'}"`);
      expect(textOf(markup)).toContain(textOf(s.verdict.text[lang]).slice(0, 60));
      expect(textOf(markup)).not.toMatch(/NaN|undefined|Infinity/);
    }
    const es = textOf(render(<SequentialView sel={sel(data)} />, 'es'));
    expect(es).toContain('Monitores secuenciales');
    expect(es).not.toContain('Sequential monitors');
  });

  it('judges H2 and H3 on the 20-seed replication: the verdict is refuted, the replication table draws both factors and the note says which reading decides', () => {
    const data = committedData('C22', 'other-families');
    const s = seqOf('other-families')!;
    expect(s.verdict.holds).toBe(false);
    expect(s.replication.seeds).toBe(20);
    expect(s.hypotheses.map((h) => [h.id, h.holds])).toEqual([['H1', true], ['H2', false], ['H3', false]]);
    for (const lang of ['en', 'es'] as const) {
      const markup = render(<SequentialView sel={sel(data)} />, lang);
      expect(markup).toContain('data-sequential-verdict="refuted"');
      expect(markup).toContain('data-hypothesis="H2" data-holds="no"');
      expect(markup).toContain('data-table="sequential-replication"');
      expect(markup).toContain('data-sequential-replication-note');
      for (const f of s.replication.factors) {
        expect(markup).toContain(`data-replication="${f.id}"`);
        const text = textOf(markup);
        expect(text).toContain(formatNumber(f.pooled_median, lang, { decimals: 0 }));
        expect(text).toContain(formatNumber(100 * f.pooled_power_cost, lang, { decimals: 1 }));
      }
      const note = textOf(markup).split(lang === 'en' ? 'are judged on the replication' : 'se juzgan en la réplica')[1] ?? '';
      expect(note).toContain('20');
      expect(textOf(markup)).not.toMatch(/NaN|undefined|Infinity/);
    }
  });

  it('a median that is null (more than half never rejected) is told in words, not drawn as a day', () => {
    const s = seqOf('other-families')!;
    const never = s.hits.scenarios.find((x) => x.e_rate.median_day === null);
    expect(never, 'the null scenario never rejects in more than half of the series').toBeTruthy();
    expect(textOf(render(<SequentialView sel={sel(committedData('C22', 'other-families'))} />, 'en'))).toContain('not reached');
  });
});
