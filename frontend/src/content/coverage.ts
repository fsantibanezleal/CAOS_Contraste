// The coverage registry. `content/coverage/base.ts` holds the 22 cases of SDD section 5 and their categories; any other
// file of content/coverage/*.ts exports `CASES?: PlannedCase[]` and `CATEGORY_TITLES?: Record<string, BiText>`, and a
// later file (path order after base) replaces an entry of the same id, so the unit that builds a case updates its row
// by adding `content/coverage/<unit>.ts` and edits nothing else. Whether a case is built is read from the readiness
// and the committed index at run time, never typed here.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { PlannedCase } from './coverage/base';

export type { PlannedCase } from './coverage/base';

type CoverageFile = { CASES?: PlannedCase[]; CATEGORY_TITLES?: Record<string, BiText> };

/** The coverage of `files` (path to module): base first, the others in path order; the later entry of an id wins. */
export function mergeCoverage(files: Record<string, CoverageFile>): { CASES: PlannedCase[]; CATEGORY_TITLES: Record<string, BiText> } {
  const paths = Object.keys(files).sort((a, b) => Number(b.endsWith('/base.ts')) - Number(a.endsWith('/base.ts')) || a.localeCompare(b));
  const cases = new Map<string, PlannedCase>();
  const categories: Record<string, BiText> = {};
  for (const path of paths) {
    const file = files[path];
    if (!file || (file.CASES !== undefined && !Array.isArray(file.CASES))) throw new Error(`${path}: a coverage file exports CASES as an array`);
    for (const c of file.CASES ?? []) cases.set(c.id, c);
    Object.assign(categories, file.CATEGORY_TITLES ?? {});
  }
  return { CASES: [...cases.values()].sort((a, b) => a.id.localeCompare(b.id)), CATEGORY_TITLES: categories };
}

const merged = mergeCoverage(import.meta.glob('./coverage/*.ts', { eager: true }));
export const CASES: PlannedCase[] = merged.CASES;
export const CATEGORY_TITLES: Record<string, BiText> = merged.CATEGORY_TITLES;
