// SHOW-1: every number the story shows equals the committed artifact it cites. The flow of the bank against the governance
// documents; the trailing 250-day tally against the document's own traffic light, for every model and every window; the
// recalibration against the conformal block; the decision against the comparison block and the impact; the Wilson interval
// against a known value.
import { describe, expect, it } from 'vitest';
import { outputsOf, rollingCounts } from '../workbench/c11/selection';
import {
  CASE_FLOW, DEFAULT_WINDOW, buildFlow, clampCursor, decision, defaultCursor, elementOf, findingsOfFamily, groupByElement, recalibration, stressSpan, tally,
  trailingCounts, varEnvelope, wilson, windowModel, wrappedModels, zoneOf,
} from './model';
import { WINDOWS, c11, findings, inventory } from './testkit';

const inv = inventory();
const fin = findings();
const flow = buildFlow(inv, fin);

describe('V1: the flow of the bank is placed by a convention and counted from the documents', () => {
  it('places every inventory entry and loses none', () => {
    expect(flow.unmapped).toEqual([]);
    expect(flow.entries).toBe(inv.entries.length);
    expect(flow.entries).toBe(34);
    expect(Object.keys(CASE_FLOW).sort()).toEqual([...new Set(inv.entries.map((e) => e.case_id))].sort());
  });

  it('the findings of the flow are the findings of the document, in total and by severity', () => {
    expect(flow.total).toBe(fin.counts.total);
    expect(flow.sev).toEqual(fin.counts.by_severity);
    expect(flow.families.reduce((a, f) => a + f.total, 0)).toBe(fin.counts.total);
    expect(flow.exposures.reduce((a, f) => a + f.total, 0)).toBe(fin.counts.total);
  });

  it('each family holds the findings its cases hold in counts.by_case', () => {
    for (const fam of flow.families) {
      const cases = Object.entries(CASE_FLOW).filter(([, p]) => p.family === fam.id).map(([c]) => c);
      const expected = fin.counts.by_case.filter((c) => cases.includes(c.case_id)).reduce((a, c) => a + c.total, 0);
      expect(fam.total, fam.id).toBe(expected);
    }
  });

  it('the findings of a family are sorted by severity and belong to it', () => {
    const rows = findingsOfFamily(flow, fin, 'market');
    expect(rows.length).toBe(flow.families.find((f) => f.id === 'market')!.total);
    expect(rows.every((r) => flow.familyOfEntry.get(r.entry_key) === 'market')).toBe(true);
    const sev = rows.map((r) => r.severity);
    expect([...sev].sort()).toEqual(sev);
  });

  it('every evidence id of the register has an element of SR 11-7, none is left over', () => {
    const left = new Set<string>();
    for (const r of fin.rows) for (const e of r.evidence) if (!elementOf(e)) left.add(e.split('@')[0]!.split(/[.:]/)[0]!);
    expect([...left]).toEqual([]);
    const groups = groupByElement(findingsOfFamily(flow, fin, 'scoring'));
    expect(groups.other).toEqual([]);
    expect(groups.conceptual.length + groups.monitoring.length + groups.outcomes.length).toBe(flow.families.find((f) => f.id === 'scoring')!.total);
  });
});

describe('V3: the trailing 250-day tally is the Basel traffic light of the document', () => {
  it('counts the days so far before the window is full and the Basel count from day 249', () => {
    const t = trailingCounts([0, 1, 2, 300], 400);
    expect(t[2]).toBe(3);
    expect(t[249]).toBe(3);
    expect(t[250]).toBe(2);
    expect(t[300]).toBe(1);
    expect(t.slice(249)).toEqual(rollingCounts([0, 1, 2, 300], 400));
  });

  it('cuts the zones at the MAR32.9 table of the models document', () => {
    const w = windowModel(c11('equity-2007-09'))!;
    expect(w.cuts).toEqual({ amberStart: 5, redStart: 10 });
    expect([0, 4, 5, 9, 10, 40].map((n) => zoneOf(n, w.cuts))).toEqual(['green', 'green', 'amber', 'amber', 'red', 'red']);
  });

  it('the maximum, the final count and the days per zone of every model equal the document in every window', () => {
    for (const id of WINDOWS) {
      const w = windowModel(c11(id))!;
      expect(w.models, id).toHaveLength(18);
      expect(w.n, id).toBe(outputsOf({ data: c11(id) })!.window.n_forecast_days);
      for (const m of w.models) {
        if (!w.evaluated) {
          expect(m.light, `${id} ${m.id}`).toBeNull();
          expect(m.computed).toBeNull();
          continue;
        }
        expect(m.computed, `${id} ${m.id}`).not.toBeNull();
        expect(m.light, `${id} ${m.id}`).not.toBeNull();
        expect(m.computed!.max, `${id} ${m.id}`).toBe(m.light!.max);
        expect(m.computed!.final, `${id} ${m.id}`).toBe(m.light!.final);
        expect(zoneOf(m.computed!.final, w.cuts), `${id} ${m.id}`).toBe(m.light!.zone);
        expect([m.computed!.green, m.computed!.amber, m.computed!.red], `${id} ${m.id}`).toEqual([m.light!.green, m.light!.amber, m.light!.red]);
      }
    }
  });

  it('a window shorter than 250 days says why the light is not evaluated', () => {
    const w = windowModel(c11('mixed-2023'))!;
    expect(w.evaluated).toBe(false);
    expect(w.notEvaluatedReason).toMatch(/fewer than 250 forecast days \(64\)/);
    const quiet = w.models.find((m) => m.exceedances.length === 0)!;
    expect(quiet.trailing.every((c) => c === 0)).toBe(true);
    expect(Math.max(...w.models.map((m) => m.trailing.at(-1)!))).toBeGreaterThan(0);
  });

  it('the realised loss is drawn only where the document commits it', () => {
    expect(windowModel(c11('equity-2007-09'))!.loss).toBeNull();
    expect(windowModel(c11('equity-2007-09'))!.lossReason).toMatch(/derived-only/);
    const fx = windowModel(c11('fx-2008'))!;
    expect(fx.loss).toHaveLength(fx.n);
  });

  it('opens on the worst day of the model, and the cursor stays inside the window', () => {
    const w = windowModel(c11('equity-2007-09'))!;
    const hs = w.models.find((m) => m.id === 'hs-250')!;
    const day = defaultCursor(hs, w.n);
    expect(hs.trailing[day]).toBe(hs.light!.max);
    expect(clampCursor(9999, 100, 5)).toBe(99);
    expect(clampCursor(null, 100, 5)).toBe(5);
    expect(clampCursor(-3, 100, 5)).toBe(0);
    expect(stressSpan(hs, w.cuts)).not.toBeNull();
    const env = varEnvelope(w.models, w.n);
    expect(env.lo.every((v, i) => v <= env.hi[i]!)).toBe(true);
  });

  it('a window without exceptions stays in the green zone at zero', () => {
    const w = windowModel(c11('mixed-2023'))!;
    const m = w.models.find((x) => x.exceedances.length === 0)!;
    expect(Math.max(...m.trailing)).toBe(0);
    expect(zoneOf(0, w.cuts)).toBe('green');
    expect(stressSpan(m, w.cuts)).toBeNull();
    expect(tally([], w.cuts)).toBeNull();
  });
});

describe('V5: the recalibration is the conformal block of the document', () => {
  it('draws the raw and the recalibrated paths of every wrapped model with the document counts', () => {
    const data = c11(DEFAULT_WINDOW);
    const o = outputsOf({ data })!;
    const w = windowModel(data)!;
    expect(wrappedModels(o)).toEqual(['hs-250', 'garch-t', 'fhs']);
    for (const id of wrappedModels(o)) {
      const r = recalibration(data, id)!;
      const raw = w.models.find((m) => m.id === id)!;
      const row = o.conformal!.rows.find((x) => x.model_id === id && x.alpha === 0.01)!;
      expect(r.var).toEqual(row.series.var);
      expect(r.var).toHaveLength(w.n);
      expect(r.wrappedExceptions).toBe(row.wrapped.n_exceedances);
      expect(r.exceedances).toHaveLength(r.wrappedExceptions);
      expect(r.rawExceptions).toBe(raw.exceedances.length);
      expect(r.tally!.final).toBe(r.trailing.at(-1));
    }
    expect(recalibration(data, 'ewma')).toBeNull();
  });
});

describe('V6: the decision is the comparison block, the gates and the impact of the document', () => {
  it('the Wilson interval matches a known value and brackets the rate', () => {
    const [lo, hi] = wilson(0, 10);
    expect(lo).toBe(0);
    expect(hi).toBeCloseTo(0.2775, 4);
    const [l2, h2] = wilson(10, 250);
    expect(l2).toBeLessThan(0.04);
    expect(h2).toBeGreaterThan(0.04);
    expect(wilson(0, 0)).toEqual([0, 1]);
  });

  it('the eligible count is the impact of the document, the set and the champion are its comparison, in every window', () => {
    for (const id of WINDOWS) {
      const data = c11(id);
      const d = decision(data, windowModel(data))!;
      expect(d.total, id).toBe(18);
      expect(d.eligible, id).toBe((data.variant as unknown as { impact: { eligible_models: { value: number } } }).impact.eligible_models.value);
      const o = outputsOf({ data })!;
      const mcs = o.comparison.mcs.find((s) => s.alpha === 0.01);
      expect(d.setSize, id).toBe(mcs ? mcs.members.filter((m) => m.in_set).length : null);
      expect(d.champion, id).toBe(o.comparison.champions.find((c) => c.alpha === 0.01)!.model_id);
      if (!d.champion) expect(d.championReason, id).toBeTruthy();
      for (const r of d.rows) {
        expect(r.lo, id).toBeLessThanOrEqual(r.rate);
        expect(r.hi, id).toBeGreaterThanOrEqual(r.rate);
      }
    }
  });
});

describe('adversarial: what is planted must be found', () => {
  it('adversarial: an inventory entry of a case the flow does not place is reported, never dropped into a family', () => {
    const planted = { ...inv, entries: [...inv.entries, { ...inv.entries[0]!, key: 'C99/planted', case_id: 'C99' }] };
    const f = buildFlow(planted, fin);
    expect(f.unmapped).toEqual(['C99/planted']);
    expect(f.families.reduce((a, x) => a + x.entries.length, 0)).toBe(34);
    expect(f.entries).toBe(35);
  });

  it('adversarial: a finding added to the register changes the counts of its family and of the flow', () => {
    const extra = { ...fin.rows[0]!, key: 'planted', severity: 'S1' as const };
    const f = buildFlow(inv, { ...fin, rows: [...fin.rows, extra] });
    expect(f.total).toBe(fin.counts.total + 1);
    expect(f.sev.S1).toBe(fin.counts.by_severity.S1 + 1);
    expect(f.total).not.toBe(fin.counts.total);
  });

  it('adversarial: one exceedance day moved changes the tally, so the comparison with the document is not vacuous', () => {
    const w = windowModel(c11('equity-2007-09'))!;
    const hs = w.models.find((m) => m.id === 'hs-250')!;
    const moved = hs.exceedances.map((d, i) => (i === 0 ? d + 240 : d));
    const t = tally(trailingCounts(moved, w.n), w.cuts)!;
    expect([t.max, t.final, t.green, t.amber, t.red]).not.toEqual([hs.light!.max, hs.light!.final, hs.light!.green, hs.light!.amber, hs.light!.red]);
    expect(trailingCounts([], w.n).every((c) => c === 0)).toBe(true);
  });

  it('adversarial: a window document whose realised loss is removed yields no loss series and keeps its reason', () => {
    const data = c11('fx-2008');
    const o = outputsOf({ data })! as unknown as { grid: { realised_loss: { status: string; loss: number[] | null; reason: string | null } } };
    o.grid.realised_loss = { status: 'withheld-derived-only', loss: null, reason: 'planted' };
    const w = windowModel(data)!;
    expect(w.loss).toBeNull();
    expect(w.lossReason).toBe('planted');
  });

  it('adversarial: a cursor from a longer window is clamped and never indexes past the shorter one', () => {
    for (const bad of [9999, -5, Number.NaN, Infinity]) {
      const i = clampCursor(bad, 64, 7);
      expect(i).toBeGreaterThanOrEqual(0);
      expect(i).toBeLessThanOrEqual(63);
    }
  });

  it('adversarial: a comparison block with no champion and no reason yields a champion of none and invents no reason', () => {
    const data = c11('equity-2007-09');
    const o = outputsOf({ data })!;
    o.comparison.champions = o.comparison.champions.map((c) => ({ ...c, model_id: null, reason: null })) as unknown as typeof o.comparison.champions;
    const d = decision(data, windowModel(data))!;
    expect(d.champion).toBeNull();
    expect(d.championReason).toBeNull();
  });

  it('adversarial: the Wilson interval of a changed count moves, so an interval typed in place of it is found', () => {
    expect(wilson(19, 504)).not.toEqual(wilson(11, 504));
    expect(wilson(19, 504)[0]).toBeLessThan(19 / 504);
    expect(wilson(19, 504)[1]).toBeGreaterThan(19 / 504);
  });
});
