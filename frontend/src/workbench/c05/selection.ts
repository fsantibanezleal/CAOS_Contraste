// The C05 instrument's selection and its live computations (CT-209, CT-210). Every live number comes from the ports
// in engine/credit.ts on committed inputs; the replayed ones are read from the artifact as the pipeline wrote them.
import type { ShellToken } from '@fasl-work/caos-app-shell';
import { useMemo } from 'react';
import type { CaseData } from '../../api/artifacts';
import type { C05LdpOutputs, C05SpOutputs, ModelsArtifact, QuadratureDetails, Text, VariantArtifact } from '../../lib/contract.types';
import type { PolicyAlphas } from '../../lib/policy';
import { calibrate, irbCapital, mostPrudent, mostPrudentScaled, type Case1, type Quadrature, type Regime } from '../../engine/credit';

export type SpVariant = VariantArtifact<C05SpOutputs>;
export type LdpVariant = VariantArtifact<C05LdpOutputs>;

export interface C05Sel {
  data: CaseData;
  alphas: PolicyAlphas;
  /** sp variants: the case 1 approach the live calibration uses, and the forecast PD it calibrates to */
  approach: Case1;
  p1: number;
  /** ldp variants: the confidence level, the asset correlation and whether the bounds are scaled */
  gamma: number;
  rho: number;
  scaled: boolean;
  /** the capital assumptions of the Impact group */
  regime: Regime;
  lgd: number;
}

export const isSp = (v: VariantArtifact<unknown>): v is SpVariant => (v.outputs as { kind?: string }).kind === 'sp-calibration';
export const isLdp = (v: VariantArtifact<unknown>): v is LdpVariant => (v.outputs as { kind?: string }).kind === 'ldp';

export const CASE1: Case1[] = ['A1-idp', 'A2-iar', 'A3-spd', 'A4-slr'];

/** One colour per approach, and per grade of the low-default portfolio, the same in every view and its key. */
export const APPROACH_COLOR: Record<string, ShellToken> = {
  'A1-idp': '--color-accent',
  'A2-iar': '--color-accent-2',
  'A3-spd': '--color-warn',
  'A4-slr': '--color-good',
  'B1-ilr': '--color-magenta',
  'C1-ipc': '--color-fg-subtle',
  'C2-ls': '--color-bad',
  'C3-chi2': '--color-bad',
  'C4-ilr': '--color-magenta',
};
export const GRADE_COLOR: ShellToken[] = ['--color-accent', '--color-accent-2', '--color-warn'];

export const approachShort = (v: SpVariant, id: string): Text => v.model.find((m) => m.id === id)?.short_title ?? { en: id, es: id };

/** The 2009 estimation model the live calibrations start from, read from the variant's exact inputs. */
export function estimationModel(v: SpVariant) {
  const o = v.outputs;
  return { curve0: o.qmm0.curve, pd0: o.qmm0.pd, ar0: o.ar0, defaultProfile0: o.default_profile0 };
}

/** The live forecast curve at the selected approach and forecast PD. */
export function useLiveCurve(sel: C05Sel | null) {
  return useMemo(() => {
    const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
    if (!sel || !v || !isSp(v)) return null;
    try {
      const r = calibrate(sel.approach, estimationModel(v), v.outputs.profile1, sel.p1);
      return { ...r, approach: sel.approach, p1: sel.p1 };
    } catch (e) {
      return { curve: [] as number[], constant: null, improper: String((e as Error).message ?? e), approach: sel.approach, p1: sel.p1 };
    }
  }, [sel]);
}

export function quadrature(models: ModelsArtifact<unknown>): Quadrature | null {
  const d = models.model.find((m) => m.id === 'L0-methods')?.details as QuadratureDetails | undefined;
  return d ? d.quadrature : null;
}

/** The live most prudent bounds of the variant's observation at the selected level, correlation and scaling. */
export function useLiveBounds(sel: C05Sel | null) {
  return useMemo(() => {
    const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
    if (!sel || !v || !isLdp(v)) return null;
    const quad = quadrature(sel.data.models as ModelsArtifact<unknown>);
    if (!quad) return null;
    const o = v.outputs;
    if (sel.scaled) {
      const s = mostPrudentScaled(o.obligors, o.defaults, sel.gamma, sel.rho, quad);
      return { pd: s.pd, k: s.k as number | null, raw: s.raw };
    }
    const pd = mostPrudent(o.obligors, o.defaults, sel.gamma, sel.rho, quad);
    return { pd, k: null as number | null, raw: pd };
  }, [sel]);
}

/** The average risk weight (share of EAD) of a set of grade PDs with weights, under the selected regime and LGD. */
export function averageRiskWeight(pds: number[], weights: number[], regime: Regime, lgd: number, maturity: number): number {
  const total = weights.reduce((a, b) => a + b, 0);
  return pds.reduce((a, p, i) => a + weights[i] * irbCapital('corporate', p, lgd, { maturity, regime }).riskWeight, 0) / total;
}
