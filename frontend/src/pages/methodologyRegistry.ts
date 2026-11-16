// The Methodology registry. A unit that adds a method writes two files in `pages/methodology/`: `<name>.meta.ts`
// exporting `methodologyMeta: { id, group, order, title }` (eager: the tab list is built from it) and `<name>.tsx`
// exporting `methodologySection: { ...methodologyMeta, Body }` (lazy: loaded when its tab opens, BL-102). This module
// pairs the two by stem and Methodology.tsx appends each section as a tab of the top-level group named by `group`, after
// the page's own tabs and in `order`. The groups are the page's existing ones (ADR-0071 rule 5: at most six); a section
// naming another group, a duplicate id, a metadata file without a body, a body without a metadata file or a body file
// without the export fails, naming the file.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';

/** The top-level groups of the Methodology page that a registered section may join. */
// grouped by the question family, as the App and Experiments group their cases (wave 2 integration, 2026-10-14)
export const METHODOLOGY_GROUPS = ['models', 'tests', 'loss', 'capital', 'market', 'balance'] as const;
export type MethodologyGroup = (typeof METHODOLOGY_GROUPS)[number];

/** What the tab list needs of a section, without loading its body. */
export interface MethodologySectionMeta {
  id: string;
  group: MethodologyGroup;
  order: number;
  title: BiText;
}

/** What a section's body file exports. */
export interface MethodologySection extends MethodologySectionMeta {
  Body: () => ReactElement;
}

/** A registered section: its metadata and the loader of its body. */
export interface RegisteredSection extends MethodologySectionMeta {
  /** The body file's path, for the messages that name it. */
  path: string;
  /** Imports the body file and resolves its `Body`; a file without `methodologySection` fails, naming it. */
  load: () => Promise<MethodologySection['Body']>;
}

const stemOf = (path: string, ext: string): string => path.slice(path.lastIndexOf('/') + 1, -ext.length);

/**
 * The sections of the metadata modules (path to module) paired by stem with the body loaders (path to lazy import), in
 * `order` then id; an unknown group, a duplicate id, a missing export or an orphan on either side throws.
 */
export function collectSections(metaModules: Record<string, unknown>, bodyLoaders: Record<string, () => Promise<unknown>>, groups: readonly string[]): RegisteredSection[] {
  const bodyByStem = new Map<string, string>();
  for (const path of Object.keys(bodyLoaders)) bodyByStem.set(stemOf(path, '.tsx'), path);
  const metaStems = new Set<string>();
  const seen = new Map<string, string>();
  const out: RegisteredSection[] = [];
  for (const path of Object.keys(metaModules).sort()) {
    const stem = stemOf(path, '.meta.ts');
    metaStems.add(stem);
    const m = (metaModules[path] as { methodologyMeta?: MethodologySectionMeta } | undefined)?.methodologyMeta;
    if (!m || typeof m.id !== 'string') throw new Error(`${path}: a Methodology metadata file must export methodologyMeta { id, group, order, title }`);
    if (!groups.includes(m.group)) throw new Error(`${path}: section "${m.id}" names unknown group "${m.group}"; the groups are ${groups.join(', ')}`);
    const bodyPath = bodyByStem.get(stem);
    if (!bodyPath) throw new Error(`${path}: this metadata file has no body file (${stem}.tsx beside it)`);
    const first = seen.get(m.id);
    if (first) throw new Error(`${path}: duplicate Methodology section id "${m.id}" (also in ${first})`);
    seen.set(m.id, path);
    const importBody = bodyLoaders[bodyPath];
    out.push({
      id: m.id,
      group: m.group,
      order: m.order,
      title: m.title,
      path: bodyPath,
      load: () =>
        importBody().then((mod) => {
          const body = (mod as { methodologySection?: MethodologySection } | undefined)?.methodologySection?.Body;
          if (typeof body !== 'function') throw new Error(`${bodyPath}: a Methodology body file must export methodologySection { ...methodologyMeta, Body }`);
          return body;
        }),
    });
  }
  for (const [stem, path] of bodyByStem) if (!metaStems.has(stem)) throw new Error(`${path}: this body file has no metadata file (${stem}.meta.ts beside it)`);
  return out.sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
}

export const REGISTERED_SECTIONS: RegisteredSection[] = collectSections(
  import.meta.glob('./methodology/*.meta.ts', { eager: true }),
  import.meta.glob('./methodology/*.tsx'),
  METHODOLOGY_GROUPS,
);
