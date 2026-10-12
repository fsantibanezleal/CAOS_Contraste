// The Methodology registry. A unit that adds a method writes `pages/methodology/<name>.tsx` exporting
// `methodologySection: { id, group, order, title, Body }`; this module collects every such file (eager glob) and
// Methodology.tsx appends each one as a tab of the top-level group named by `group`, after the page's own tabs and in
// `order`. The groups are the page's existing ones (ADR-0071 rule 5: at most six); a section naming another group, a
// duplicate id or a file without the export fails at load, naming the file.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';

/** The top-level groups of the Methodology page that a registered section may join. */
export const METHODOLOGY_GROUPS = ['models', 'tests'] as const;
export type MethodologyGroup = (typeof METHODOLOGY_GROUPS)[number];

export interface MethodologySection {
  id: string;
  group: MethodologyGroup;
  order: number;
  title: BiText;
  Body: () => ReactElement;
}

/** The sections of `modules` (path to module), in `order` then id; an unknown group, a duplicate id or a missing export throws. */
export function collectSections(modules: Record<string, unknown>, groups: readonly string[]): MethodologySection[] {
  const seen = new Map<string, string>();
  const out: MethodologySection[] = [];
  for (const path of Object.keys(modules).sort()) {
    const s = (modules[path] as { methodologySection?: MethodologySection } | undefined)?.methodologySection;
    if (!s || typeof s.id !== 'string' || typeof s.Body !== 'function') throw new Error(`${path}: a Methodology file must export methodologySection { id, group, order, title, Body }`);
    if (!groups.includes(s.group)) throw new Error(`${path}: section "${s.id}" names unknown group "${s.group}"; the groups are ${groups.join(', ')}`);
    const first = seen.get(s.id);
    if (first) throw new Error(`${path}: duplicate Methodology section id "${s.id}" (also in ${first})`);
    seen.set(s.id, path);
    out.push(s);
  }
  return out.sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
}

export const REGISTERED_SECTIONS: MethodologySection[] = collectSections(import.meta.glob('./methodology/*.tsx', { eager: true }), METHODOLOGY_GROUPS);
