// The question families of the cases (ADR-0071 rule 5), shared by the Experiments case tabs, the governance register's
// filter and the Benchmark sub-tabs, so one case sits in the same family on all three. Moved out of Experiments.tsx
// unchanged (GATE-15B); the family of a case is the family of its category in the coverage registry.
import type { BiText } from '@fasl-work/caos-app-shell';
import { CASES, CATEGORY_TITLES } from '../../content/coverage';

/** The question families the case tabs are grouped by (ADR-0071 rule 5: at most six peer tabs, then group by the question), keyed by the category of the coverage registry; a category without a family keeps its own title. */
export const FAMILY: Record<string, { id: string; label: BiText }> = {
  'credit-scoring': { id: 'pd', label: { en: 'Credit scoring and PD', es: 'Calificación crediticia y PD' } },
  'ratings-calibration': { id: 'pd', label: { en: 'Credit scoring and PD', es: 'Calificación crediticia y PD' } },
  provisions: { id: 'credit-losses', label: { en: 'Credit losses: provisions, severity and exposure', es: 'Pérdidas de crédito: provisiones, severidad y exposición' } },
  'lgd-ead': { id: 'credit-losses', label: { en: 'Credit losses: provisions, severity and exposure', es: 'Pérdidas de crédito: provisiones, severidad y exposición' } },
  'portfolio-capital': { id: 'capital', label: { en: 'Capital, aggregation and stress', es: 'Capital, agregación y estrés' } },
  operational: { id: 'capital', label: { en: 'Capital, aggregation and stress', es: 'Capital, agregación y estrés' } },
  'capital-stress': { id: 'capital', label: { en: 'Capital, aggregation and stress', es: 'Capital, agregación y estrés' } },
  'ml-ai-risk': { id: 'ml-ai-risk', label: { en: 'ML and AI risk', es: 'Riesgo de ML e IA' } },
  'market-ccr': { id: 'market-balance', label: { en: 'Market and balance-sheet risk', es: 'Riesgo de mercado y de balance' } },
  'balance-sheet': { id: 'market-balance', label: { en: 'Market and balance-sheet risk', es: 'Riesgo de mercado y de balance' } },
};

/** The family of a case by its id (`C04`, case-insensitive): a category without a family keeps its own title, a case outside the registry is "Other cases". */
export function familyOf(caseId: string): { id: string; label: BiText } {
  const category = CASES.find((c) => c.id.toLowerCase() === caseId.toLowerCase())?.category ?? 'other';
  return FAMILY[category] ?? { id: category, label: CATEGORY_TITLES[category] ?? { en: 'Other cases', es: 'Otros casos' } };
}
