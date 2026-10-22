// The C05 instrument's selection and its live computations (CT-209, CT-210). Every live number comes from the ports
// in engine/credit.ts on committed inputs; the replayed ones are read from the artifact as the pipeline wrote them.
import type { ShellColorToken } from '@fasl-work/caos-app-shell';
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

/** The words for a variant's truth status (the document's id is never printed in a sentence, U16-R2 b03 B1). */
export const TRUTH_STATUS_TEXT: Record<string, Text> = {
  'real-outcomes': { en: 'real outcomes', es: 'resultados reales' },
  'synthetic-known-truth': { en: 'synthetic, known truth', es: 'sintético, verdad conocida' },
  'synthetic-calibrated': { en: 'synthetic, calibrated', es: 'sintético, calibrado' },
  'published-answer': { en: 'published answer', es: 'respuesta publicada' },
};
export const truthStatusText = (id: string): Text => TRUTH_STATUS_TEXT[id] ?? { en: id, es: id };

/** The Spanish of the descriptive part of a source's licence and attribution (names, URLs and the citation stay verbatim), kept with the
 * English it translates: a registry wording that has moved on is shown as declared, never as a stale translation. */
export const SOURCE_TEXT_ES: Record<string, { licence: [string, string]; attribution: [string, string] }> = {
  'tasche-2013': {
    licence: [
      'arXiv.org perpetual, non-exclusive license to distribute (http://arxiv.org/licenses/nonexclusive-distrib/1.0/); Table 2 quotes the S&P annual global corporate default studies for 2009 to 2011 (S&P 2010, 2011, 2012)',
      'Licencia de arXiv.org perpetua y no exclusiva para distribuir (http://arxiv.org/licenses/nonexclusive-distrib/1.0/); la Tabla 2 cita los estudios anuales de incumplimiento corporativo global de S&P de 2009 a 2011 (S&P 2010, 2011, 2012)',
    ],
    attribution: [
      'Tasche, D. (2013). The art of probability-of-default curve calibration. Journal of Credit Risk 9(4):63-103. https://doi.org/10.21314/jcr.2013.169. Table 2 data: S&P annual global corporate default studies 2009 to 2011.',
      'Tasche, D. (2013). The art of probability-of-default curve calibration. Journal of Credit Risk 9(4):63-103. https://doi.org/10.21314/jcr.2013.169. Datos de la Tabla 2: estudios anuales de incumplimiento corporativo global de S&P, 2009 a 2011.',
    ],
  },
  'pluto-tasche-2005': {
    licence: [
      "arXiv assumed license, 1991-2003 (http://arxiv.org/licenses/assumed-1991-2003/): distribution by arXiv; the tables are the paper's own computations on a hypothetical portfolio",
      'Licencia supuesta de arXiv, 1991-2003 (http://arxiv.org/licenses/assumed-1991-2003/): distribución por arXiv; las tablas son los cálculos propios del artículo sobre una cartera hipotética',
    ],
    attribution: [
      'Pluto, K. and Tasche, D. (2005). Estimating probabilities of default for low default portfolios. arXiv:cond-mat/0411699v3. https://doi.org/10.48550/arXiv.cond-mat/0411699',
      'Pluto, K. y Tasche, D. (2005). Estimating probabilities of default for low default portfolios. arXiv:cond-mat/0411699v3. https://doi.org/10.48550/arXiv.cond-mat/0411699',
    ],
  },
};
/** A source's licence or attribution in the language: the Spanish of the known wording, else the wording as declared. */
export function sourceText(id: string, field: 'licence' | 'attribution', declared: string, l: 'en' | 'es'): string {
  const known = SOURCE_TEXT_ES[id]?.[field];
  return l === 'es' && known && known[0] === declared ? known[1] : declared;
}

export const isSp = (v: VariantArtifact<unknown>): v is SpVariant => (v.outputs as { kind?: string }).kind === 'sp-calibration';
export const isLdp = (v: VariantArtifact<unknown>): v is LdpVariant => (v.outputs as { kind?: string }).kind === 'ldp';

export const CASE1: Case1[] = ['A1-idp', 'A2-iar', 'A3-spd', 'A4-slr'];

/** One colour per approach, and per grade of the low-default portfolio, the same in every view and its key. */
export const APPROACH_COLOR: Record<string, ShellColorToken> = {
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
export const GRADE_COLOR: ShellColorToken[] = ['--color-accent', '--color-accent-2', '--color-warn'];

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
