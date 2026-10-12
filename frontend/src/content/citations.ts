// The citation registry. Every file of content/citations/*.ts exports `CITATIONS: Citation[]`; this module merges
// them, `base.ts` first and the others in path order, so a unit that cites new references adds
// `content/citations/<unit>.ts` and edits nothing else. A citation id defined in two files is an error that names both
// files: two units must not silently disagree about one reference.
import type { Citation } from '@fasl-work/caos-app-shell';

type CitationFile = { CITATIONS?: Citation[] };

/** The citations of `files` (path to module) merged in registry order; a duplicate id throws. */
export function mergeCitations(files: Record<string, CitationFile>): Citation[] {
  const paths = Object.keys(files).sort((a, b) => Number(b.endsWith('/base.ts')) - Number(a.endsWith('/base.ts')) || a.localeCompare(b));
  const seen = new Map<string, string>();
  const merged: Citation[] = [];
  for (const path of paths) {
    const list = files[path]?.CITATIONS;
    if (!Array.isArray(list)) throw new Error(`${path}: a citation file must export CITATIONS: Citation[]`);
    for (const c of list) {
      const first = seen.get(c.id);
      if (first) throw new Error(`citation "${c.id}" is defined twice: ${first} and ${path}`);
      seen.set(c.id, path);
      merged.push(c);
    }
  }
  return merged;
}

export const CITATIONS: Citation[] = mergeCitations(import.meta.glob('./citations/*.ts', { eager: true }));
