// The C22 instrument's selection and its live computation (CT-308, CT-309). The replayed numbers are the harness's
// rejection rates as the pipeline wrote them; the live ones are the exact size and power of the three count tests,
// from the ports in engine/sizepower.ts on the quadrature committed in C22's models artifact.
import type { ShellToken } from '@fasl-work/caos-app-shell';
import { useMemo } from 'react';
import type { CaseData } from '../../api/artifacts';
import type { C22Outputs, C22Simulation, Text, VariantArtifact } from '../../lib/contract.types';
import type { PolicyAlphas } from '../../lib/policy';
import type { Quadrature } from '../../engine/credit';
import { countTail, criticalCount, rejectionProbability, type CountTest } from '../../engine/sizepower';

export type C22Variant = VariantArtifact<C22Outputs>;

export interface Portfolio {
  /** obligors in the grade or portfolio */
  n: number;
  /** the PD applied (the model's) */
  pd: number;
  /** the true PD over the PD applied: 1 is the null, above 1 an underestimation */
  ratio: number;
  /** the true asset correlation of the defaults */
  rhoTrue: number;
  /** the correlation the Vasicek-corrected test assumes */
  rhoAssumed: number;
}

export interface C22Sel {
  data: CaseData;
  alphas: PolicyAlphas;
  /** the level the replayed views read: 0.05 or 0.01 */
  level: number;
  portfolio: Portfolio;
}

export const isC22 = (v: VariantArtifact<unknown>): v is C22Variant => (v.outputs as { kind?: string }).kind === 'validator';

export const COUNT_TESTS: Array<{ id: CountTest; label: Text; color: ShellToken }> = [
  { id: 'pd.binomial', label: { en: 'Binomial', es: 'Binomial' }, color: '--color-accent' },
  { id: 'pd.jeffreys', label: { en: 'Jeffreys', es: 'Jeffreys' }, color: '--color-magenta' },
  { id: 'pd.binomial_vasicek', label: { en: 'Vasicek-corrected', es: 'Corregida de Vasicek' }, color: '--color-good' },
];

/** One colour per test, the same in every view. */
export const TEST_COLOR: Record<string, ShellToken> = {
  'pd.binomial': '--color-accent',
  'pd.jeffreys': '--color-magenta',
  'pd.binomial_vasicek': '--color-good',
  'pd.chi2_grades': '--color-warn',
  'pd.default_profile': '--color-accent-2',
  'pd.hosmer_lemeshow': '--color-bad',
  'pd.spiegelhalter': '--color-accent-2',
  'pd.normal_multiperiod': '--color-warn',
  'pd.traffic_lights': '--color-accent',
  'disc.auc_vs_initial': '--color-accent',
  'disc.delong': '--color-magenta',
  'stability.psi': '--color-accent',
  'stability.csi': '--color-accent-2',
  'stability.chi2': '--color-good',
  'stability.ks': '--color-magenta',
  'rating.migration_ztests': '--color-accent',
  'rating.hhi': '--color-bad',
};

export const rule = (level: number) => `p<${level}`;

/** The rate of a simulation at the selected level (or a named rule), and its exact value where one exists. */
export function rateOf(s: C22Simulation, ruleKey: string) {
  const r = s.rates[ruleKey];
  return { rate: r?.rate ?? null, se: r?.se ?? null, lo: r?.wilson_low ?? null, hi: r?.wilson_high ?? null, exact: s.exact?.[ruleKey] ?? null };
}

/** The simulations of one panel grouped by test (one curve per test), each ordered by severity. */
export function curves(v: C22Variant, panel: string) {
  const by = new Map<string, C22Simulation[]>();
  for (const s of v.outputs.simulations) {
    if (s.panel !== panel) continue;
    const key = s.label.en === s.test_id ? s.test_id : `${s.test_id}|${s.label.en}`;
    by.set(key, [...(by.get(key) ?? []), s]);
  }
  return [...by.entries()].map(([key, rows]) => ({ key, rows: rows.sort((a, b) => a.severity - b.severity) }));
}

export function quadrature(data: CaseData): Quadrature | null {
  const x = data.models.model.find((m) => m.id === 'X1-exact')?.details as { quadrature?: Quadrature } | undefined;
  return x?.quadrature ?? null;
}

/** The live exact rejection probability of the three count tests for the rail's portfolio, at 5% and 1%. */
export function useLivePortfolio(sel: C22Sel | null) {
  return useMemo(() => {
    if (!sel) return null;
    const quad = quadrature(sel.data);
    if (!quad) return null;
    const p = sel.portfolio;
    return COUNT_TESTS.map((t) => {
      const at = (alpha: number) =>
        rejectionProbability(t.id, p.n, p.pd, alpha, Math.min(p.pd * p.ratio, 0.999), p.rhoTrue, p.rhoAssumed, quad);
      return { ...t, at5: at(0.05), at1: at(0.01) };
    });
  }, [sel]);
}

/** The live curves: rejection probability against the ratio (at the rail's correlation) and against the true
 * correlation (at the rail's ratio), for the three count tests at the selected level. */
export function useLiveCurves(sel: C22Sel | null) {
  return useMemo(() => {
    if (!sel) return null;
    const quad = quadrature(sel.data);
    if (!quad) return null;
    const p = sel.portfolio;
    const ratios = Array.from({ length: 21 }, (_, i) => 1 + i * 0.1);
    const rhos = Array.from({ length: 21 }, (_, i) => i * 0.015);
    // the critical count depends on the obligors, the PD applied, the level and the assumed correlation only: once
    // per test, then one tail of the true distribution per point
    const tail = (k: number | null, ratio: number, rho: number) => (k === null ? 0 : countTail(k, p.n, Math.min(p.pd * ratio, 0.999), rho, quad));
    return {
      ratios,
      rhos,
      byRatio: COUNT_TESTS.map((t) => {
        const k = criticalCount(t.id, p.n, p.pd, sel.level, p.rhoAssumed, quad);
        return { ...t, values: ratios.map((r) => tail(k, r, p.rhoTrue)) };
      }),
      byRho: COUNT_TESTS.map((t) => {
        const k = criticalCount(t.id, p.n, p.pd, sel.level, p.rhoAssumed, quad);
        return { ...t, values: rhos.map((r) => tail(k, p.ratio, r)) };
      }),
    };
  }, [sel]);
}
