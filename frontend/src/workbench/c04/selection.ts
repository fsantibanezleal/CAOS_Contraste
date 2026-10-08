// The C04 instrument's selection, its shared look and its live computations (CT-410 to CT-412). The replayed numbers
// are read from the artifacts as the pipeline wrote them; the live ones are engine/transitions.ts on committed inputs
// (an agency's pooled one-year matrix and its cohort mix, a generator family's true one-year matrix and its cohort
// sizes), held to riskvalidation by the parity points of C04's models artifact.
import type { BiText, ShellColorToken } from '@fasl-work/caos-app-shell';
import { useMemo } from 'react';
import type { CaseData } from '../../api/artifacts';
import type { AssetClass, Regime } from '../../engine/credit';
import {
  effectiveN,
  pdAgrestiCoull,
  pdJeffreys,
  pdWald,
  portfolioRiskWeight,
  project,
  type PdInterval,
  type PortfolioRiskWeight,
  type Projection,
} from '../../engine/transitions';
import type { C04AgencyOutputs, C04FamilyOutputs, C04PublishedOutputs, VariantArtifact } from '../../lib/contract.types';
import type { MapScale } from './MatrixMap';

export type AgencyVariant = VariantArtifact<C04AgencyOutputs>;
export type FamilyVariant = VariantArtifact<C04FamilyOutputs>;
export type PublishedVariant = VariantArtifact<C04PublishedOutputs>;

const kindOf = (v: VariantArtifact<unknown>) => (v.outputs as { kind?: string }).kind;
export const isAgency = (v: VariantArtifact<unknown>): v is AgencyVariant => kindOf(v) === 'agency';
export const isFamily = (v: VariantArtifact<unknown>): v is FamilyVariant => kindOf(v) === 'generator';
export const isPublished = (v: VariantArtifact<unknown>): v is PublishedVariant => kindOf(v) === 'published';

/** The common scale's seven performing grades, best first; default is the eighth state. */
export const GRADES = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC-C'] as const;
export const N_GRADES = GRADES.length;
/** The x axis of a chart by grade: grades counted from the best, the axis title naming them. */
export const GRADE_AXIS: BiText = { en: 'Grade (1 AAA, 2 AA, 3 A, 4 BBB, 5 BB, 6 B, 7 CCC-C)', es: 'Grado (1 AAA, 2 AA, 3 A, 4 BBB, 5 BB, 6 B, 7 CCC-C)' };

/** The floor under which a p-value is drawn on a log axis, labelled as below it: a reading choice, since 1e-124 and
 * 1e-20 lead to the same decision and an axis of a hundred decades leaves the readable p-values a sliver (the shell
 * draws such an axis since 0.9.2, known shell defect 31; before it the chart was never drawn). The tables print the
 * exact value. C01's findings chart uses the same floor. */
export const P_FLOOR = 1e-16;

/** CEREP's default definitions (docs/cases/C04.md, "What CEREP counts"). */
export type Definition = 'd2' | 'd3' | 'd4' | 'keep';
export const DEFINITIONS: Definition[] = ['d2', 'd3', 'd4', 'keep'];
export const DEFINITION_LABEL: Record<Definition, BiText> = {
  d2: { en: 'D2 rated defaulters', es: 'D2 calificaciones incumplidas' },
  d3: { en: 'D3 default events', es: 'D3 eventos de incumplimiento' },
  d4: { en: 'D4 matrix column', es: 'D4 columna de la matriz' },
  keep: { en: 'Keep withdrawals', es: 'Con retiros' },
};
export const DEFINITION_HINT: Record<Definition, BiText> = {
  d2: {
    en: "CEREP's default-rate page: the distinct ratings of the cohort with at least one default event, over that page's own cohort, withdrawals included (EBA/GL/2017/16 paragraph 76 keeps closed obligations in the denominator).",
    es: 'La página de tasas de incumplimiento de CEREP: las calificaciones distintas de la cohorte con al menos un evento de incumplimiento, sobre la propia cohorte de esa página, con los retiros (el párrafo 76 de EBA/GL/2017/16 mantiene las obligaciones cerradas en el denominador).',
  },
  d3: {
    en: "CEREP's defaults page: every default event of the cohort, over the cohort of the transition page. In CEREP's data it counts the same defaults as D2; only the cohort differs.",
    es: 'La página de incumplimientos de CEREP: cada evento de incumplimiento de la cohorte, sobre la cohorte de la página de transiciones. En los datos de CEREP cuenta los mismos incumplimientos que D2; solo cambia la cohorte.',
  },
  d4: {
    en: "The transition page's default column over the cohort less its withdrawals: a rating that defaulted and was withdrawn by the end of the year is not counted. Moody's page has no default category.",
    es: 'La columna de incumplimiento de la página de transiciones sobre la cohorte menos sus retiros: una calificación que incumplió y fue retirada antes del fin del año no se cuenta. La página de Moody\'s no tiene categoría de incumplimiento.',
  },
  keep: {
    en: "The transition page's default column over the whole cohort, withdrawals kept in the denominator.",
    es: 'La columna de incumplimiento de la página de transiciones sobre toda la cohorte, con los retiros en el denominador.',
  },
};
/** ESMA's statement, which every PD view repeats (CEREP help file, ESMA65-8-10634). */
export const ESMA_DEFINITIONS: BiText = {
  en: '"For the purposes of reporting into the CEREP, no deterministic definition of a default event has been set up. Therefore, the definitions might differ for various CRAs" (ESMA).',
  es: '"Para efectos del reporte a CEREP, no se ha establecido una definición determinista de un evento de incumplimiento. Por lo tanto, las definiciones pueden diferir entre agencias" (ESMA).',
};

/** The estimators the Markov family compares with the truth. */
export type Estimator = 'cohort' | 'duration' | 'em' | 'diagonal' | 'weighted' | 'jlt';
export const ESTIMATORS: Estimator[] = ['cohort', 'duration', 'em', 'diagonal', 'weighted', 'jlt'];
export const ESTIMATOR_LABEL: Record<Estimator, BiText> = {
  cohort: { en: 'Cohort', es: 'Cohortes' },
  duration: { en: 'Duration', es: 'Duración' },
  em: { en: 'EM', es: 'EM' },
  diagonal: { en: 'Diagonal', es: 'Diagonal' },
  weighted: { en: 'Weighted', es: 'Ponderado' },
  jlt: { en: 'JLT', es: 'JLT' },
};

/** The generators an agency variant carries, beside the pooled matrix itself. */
export type GeneratorKey = 'em' | 'diagonal' | 'weighted' | 'jlt';
export const GENERATOR_KEYS: GeneratorKey[] = ['em', 'diagonal', 'weighted', 'jlt'];

/** The starting portfolios of the live projection. */
export type StartPortfolio = 'best' | 'origination' | 'uniform' | 'speculative';
export const STARTS: StartPortfolio[] = ['origination', 'best', 'uniform', 'speculative'];
export const START_LABEL: Record<StartPortfolio, BiText> = {
  origination: { en: 'Origination', es: 'Originación' },
  best: { en: 'All AAA', es: 'Todo AAA' },
  uniform: { en: 'Uniform', es: 'Uniforme' },
  speculative: { en: 'Speculative', es: 'Especulativa' },
};
export const LEVELS = [0.9, 0.95, 0.99] as const;

/** One colour per definition, estimator, generator and grade, the same in every view and its key. The definitions and
 * the four generators meet in one chart (the generators' PDs, the capital by PD source), so no generator shares a
 * definition's colour; Keep (magenta) never meets a generator, and the cohort and duration estimators appear only in
 * the families' charts, which draw no definition. */
export const DEFINITION_COLOR: Record<Definition, ShellColorToken> = { d2: '--color-accent', d3: '--color-accent-2', d4: '--color-warn', keep: '--color-magenta' };
export const ESTIMATOR_COLOR: Record<Estimator, ShellColorToken> = {
  cohort: '--color-fg-subtle',
  duration: '--color-accent',
  em: '--color-magenta',
  diagonal: '--color-good',
  weighted: '--color-fg',
  jlt: '--color-bad',
};
export const GRADE_COLOR: ShellColorToken[] = ['--color-accent', '--color-accent-2', '--color-good', '--color-warn', '--color-magenta', '--color-bad', '--color-fg-subtle'];

export interface C04Actions {
  setGrade: (g: number) => void;
  setCohort: (k: number | null) => void;
  setMapScale: (s: MapScale) => void;
  setLgd: (l: number) => void;
}

export interface C04Sel {
  data: CaseData;
  /** the chosen grade, 0 (AAA) to 6 (CCC-C) */
  grade: number;
  /** agency variants: the default definition */
  definition: Definition;
  /** generator variants: the estimator the Markov family highlights */
  estimator: Estimator;
  /** the matrix view: null for the pooled matrix, else the index of an annual cohort */
  cohort: number | null;
  mapScale: MapScale;
  /** the live projection: its starting portfolio and horizon in years */
  start: StartPortfolio;
  horizon: number;
  /** the live intervals: the default correlation and the level */
  rho: number;
  level: number;
  /** the live capital: the LGD */
  lgd: number;
  act: C04Actions;
}

const NOOP: C04Actions = { setGrade: () => undefined, setCohort: () => undefined, setMapScale: () => undefined, setLgd: () => undefined };

/** The instrument's starting selection (and the tests'): the speculative CCC to C grade, where the definitions differ
 * most; the default-rate page's definition; the EM estimator; the pooled matrix with the migrations scale; the
 * origination mix over 20 years; independent defaults at 95%; the F-IRB LGD of 45%. */
export function makeSel(data: CaseData, over: Partial<C04Sel> = {}): C04Sel {
  return {
    data,
    grade: 6,
    definition: 'd2',
    estimator: 'em',
    cohort: null,
    mapScale: 'migrations',
    start: 'origination',
    horizon: 20,
    rho: 0,
    level: 0.95,
    lgd: 0.45,
    act: NOOP,
    ...over,
  };
}

/** The definitions an agency's pages give: Moody's transition page has no default category, so D4 and Keep do not
 * exist for it. */
export function definitionsOf(o: C04AgencyOutputs): Definition[] {
  return DEFINITIONS.filter((d) => o.pd[d] !== null);
}

const sum = (a: readonly number[]) => a.reduce((s, x) => s + x, 0);

/** The one-year matrix and origination of the live projection: an agency's pooled matrix (withdrawals removed, the
 * industry treatment) and its pooled cohort mix; a family's true one-year matrix and its cohort sizes as the mix.
 * Null where no grade reaches default (Moody's), since Engelmann's propagation then never defaults. */
export function liveChain(v: VariantArtifact<unknown>): { matrix: number[][]; origination: number[] } | null {
  if (isAgency(v)) {
    const m = v.outputs.pooled.matrix;
    return m.slice(0, N_GRADES).some((row) => row[N_GRADES] > 0) ? { matrix: m, origination: v.outputs.origination } : null;
  }
  if (isFamily(v)) {
    const g = v.outputs.generator;
    const total = sum(g.obligors);
    return { matrix: g.one_year_matrix, origination: [...g.obligors.map((n) => n / total), 0] };
  }
  return null;
}

/** A starting portfolio over the eight states (default last, 0). */
export function startPortfolio(kind: StartPortfolio, origination: readonly number[]): number[] {
  const w = new Array<number>(N_GRADES + 1).fill(0);
  if (kind === 'best') w[0] = 1;
  else if (kind === 'uniform') w.fill(1 / N_GRADES, 0, N_GRADES);
  else if (kind === 'speculative') w.fill(1 / 3, 4, N_GRADES);
  else return [...origination];
  return w;
}

/** The live projection at the selection's start and horizon (Engelmann's (9) and his TTC portfolio (10)); null where
 * the variant has no chain, an error message where the port refuses its inputs. */
export function useProjection(sel: C04Sel | null): { projection: Projection; w0: number[] } | { error: string } | null {
  return useMemo(() => {
    const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
    if (!sel || !v) return null;
    const chain = liveChain(v);
    if (!chain) return null;
    const w0 = startPortfolio(sel.start, chain.origination);
    try {
      return { projection: project(chain.matrix, w0, chain.origination, sel.horizon), w0 };
    } catch (e) {
      return { error: String((e as Error).message ?? e) };
    }
  }, [sel]);
}

/** A grade's pooled counts for the live intervals: an agency's under the chosen definition (its long-run average's
 * defaults and n), a family's design (the obligor-years of its cohorts, or the thin family's smallest cohort, and the
 * expected defaults at the true PD, rounded), the published variant's Table 5 cell (15 defaults of 531). Null where
 * the definition gives none. */
export function gradeCounts(v: VariantArtifact<unknown>, definition: Definition, g: number): { defaults: number; n: number } | null {
  if (isAgency(v)) {
    const o = v.outputs;
    if (definition === 'keep') {
      // the transition page's defaults over the whole pooled cohort, withdrawals kept in the denominator
      const d4 = o.lra.d4;
      const n = sum(o.cohorts.map((c) => c.size[g]));
      return d4 && n > 0 ? { defaults: d4.defaults[g], n } : null;
    }
    const lra = o.lra[definition];
    if (!lra) return null;
    const n = lra.n[g];
    return n > 0 ? { defaults: lra.defaults[g], n } : null;
  }
  if (isFamily(v)) {
    const o = v.outputs;
    // the thin family's cohorts are its ladder's sizes, the smallest first (the rung the grade read-out describes)
    const n = o.family === 'thin' && o.ladder ? o.ladder.values[0] : Math.round(o.generator.obligors[g] * o.design.years);
    return n > 0 ? { defaults: Math.round(n * o.generator.pd_1y[g]), n } : null;
  }
  if (isPublished(v)) return { defaults: v.outputs.sr190.defaults, n: v.outputs.sr190.n };
  return null;
}

export interface GradeIntervals {
  grade: number;
  defaults: number;
  n: number;
  nEffective: number;
  wald: PdInterval;
  agrestiCoull: PdInterval;
  jeffreys: PdInterval;
}

/** The three intervals of every grade with counts, at the selection's level and correlation (Jeffreys has no
 * correlation correction: it is the posterior of independent trials). */
export function useIntervals(sel: C04Sel | null): GradeIntervals[] {
  return useMemo(() => {
    const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
    if (!sel || !v) return [];
    const out: GradeIntervals[] = [];
    for (let g = 0; g < N_GRADES; g++) {
      const c = gradeCounts(v, sel.definition, g);
      if (!c) continue;
      const opts = { level: sel.level, rho: sel.rho };
      out.push({
        grade: g,
        ...c,
        nEffective: effectiveN(c.n, sel.rho),
        wald: pdWald(c.defaults, c.n, opts),
        agrestiCoull: pdAgrestiCoull(c.defaults, c.n, opts),
        jeffreys: pdJeffreys(c.defaults, c.n, { level: sel.level }),
      });
    }
    return out;
  }, [sel]);
}

export interface CapitalRow {
  key: string;
  label: BiText;
  pds: (number | null)[];
  result: PortfolioRiskWeight | null;
  error: string | null;
}

/** The IRB risk weight of the variant's portfolio by grade (an agency's pooled cohort mix, a family's cohort sizes)
 * with the PDs of each definition (agency: long-run averages) and each generator's one-year PD, at the selection's LGD
 * under the case's convention (outputs.irb on agencies; C05's on families, the same values). */
export function useCapital(sel: C04Sel | null): CapitalRow[] {
  return useMemo(() => {
    const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
    if (!sel || !v) return [];
    const irb = { assetClass: 'corporate' as AssetClass, lgd: sel.lgd, maturity: 2.5, regime: 'basel3' as Regime };
    const rows: Array<{ key: string; label: BiText; pds: (number | null)[] }> = [];
    let exposure: number[] = [];
    if (isAgency(v)) {
      const o = v.outputs;
      Object.assign(irb, { assetClass: o.irb.asset_class as AssetClass, maturity: o.irb.maturity, regime: o.irb.regime as Regime });
      exposure = o.origination.slice(0, N_GRADES);
      for (const d of definitionsOf(o)) {
        const lra = o.lra[d === 'keep' ? 'd4' : d];
        if (d !== 'keep' && lra) rows.push({ key: d, label: DEFINITION_LABEL[d], pds: lra.rate });
      }
      for (const k of GENERATOR_KEYS) {
        const gen = o.generators[k];
        if (gen && gen.pd_1y) rows.push({ key: k, label: ESTIMATOR_LABEL[k], pds: gen.pd_1y });
      }
    } else if (isFamily(v)) {
      const g = v.outputs.generator;
      exposure = [...g.obligors];
      rows.push({ key: 'truth', label: { en: 'True one-year PD', es: 'PD anual verdadera' }, pds: g.pd_1y });
    } else {
      return [];
    }
    return rows.map((r) => {
      try {
        return { ...r, result: portfolioRiskWeight(r.pds, exposure, irb), error: null };
      } catch (e) {
        return { ...r, result: null, error: String((e as Error).message ?? e) };
      }
    });
  }, [sel]);
}
