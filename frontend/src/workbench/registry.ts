// The instrument registry. A case's instrument lives in workbench/cNN/instrument.tsx and exports
// `useInstrument(data, setVariantId)`: the hook that returns the case's rail, groups, variants view, context and
// control values when `data` is that case's, and null for any other case. This module collects every such file at
// build time (`import.meta.glob`, lazy), keyed by case id, so a unit that builds a case adds `workbench/c06/instrument.tsx`
// and edits nothing else. Only the selected case's module is fetched (BL-102: the eager glob put every case in one 1.6 MB
// chunk); a loaded module is kept. C01's instrument is built in Workbench.tsx and is not part of the registry.
//
// Rules of hooks: the host component (instrumentHost.tsx) that calls a case's hook is keyed by the case id, so each mount
// calls one hook for its whole life. A file that does not export `useInstrument` fails at load, naming the file.
import type { BiText, RailSection } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import type { CaseData } from '../api/artifacts';
import type { provenanceOf } from './model';

/** What every case's instrument gives the workbench. */
export interface Instrument {
  sel: unknown;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export type InstrumentHook = (data: CaseData | null, setVariantId: (id: string) => void) => Instrument | null;

export interface InstrumentLoaders {
  [caseId: string]: { path: string; import: () => Promise<unknown> };
}

/** The loaders of `modules` (path to lazy import), keyed by case id read from the path (`./c11/instrument.tsx` is C11). */
export function instrumentLoaders(modules: Record<string, () => Promise<unknown>>): InstrumentLoaders {
  const out: InstrumentLoaders = {};
  for (const path of Object.keys(modules).sort()) {
    const m = /(?:^|\/)c(\d\d)\/instrument\.tsx$/i.exec(path);
    if (!m) throw new Error(`${path}: an instrument file must be workbench/cNN/instrument.tsx`);
    const caseId = `C${m[1]}`;
    if (out[caseId]) throw new Error(`${path}: case ${caseId} has its instrument twice (also ${out[caseId].path})`);
    out[caseId] = { path, import: modules[path] };
  }
  return out;
}

/** The loading side of a set of loaders: `load` imports a case's module once and keeps its hook; a failed import is not kept. */
export function createInstrumentLoader(loaders: InstrumentLoaders) {
  const hooks = new Map<string, InstrumentHook>();
  const pending = new Map<string, Promise<InstrumentHook>>();
  return {
    /** Whether the case has an instrument file. */
    has: (caseId: string): boolean => caseId in loaders,
    /** The hook of a case whose module is loaded, else null. */
    peek: (caseId: string): InstrumentHook | null => hooks.get(caseId) ?? null,
    /** Imports the case's module (once), checks it exports `useInstrument`, and resolves its hook. */
    load(caseId: string): Promise<InstrumentHook> {
      const loaded = hooks.get(caseId);
      if (loaded) return Promise.resolve(loaded);
      const inflight = pending.get(caseId);
      if (inflight) return inflight;
      const entry = loaders[caseId];
      if (!entry) return Promise.reject(new Error(`${caseId}: this case has no instrument file (workbench/cNN/instrument.tsx)`));
      const p = entry
        .import()
        .then((mod) => {
          const hook = (mod as { useInstrument?: unknown } | undefined)?.useInstrument;
          if (typeof hook !== 'function') throw new Error(`${entry.path}: an instrument file must export useInstrument(data, setVariantId)`);
          hooks.set(caseId, hook as InstrumentHook);
          return hook as InstrumentHook;
        })
        .finally(() => pending.delete(caseId));
      pending.set(caseId, p);
      return p;
    },
  };
}

export const INSTRUMENT_LOADERS: InstrumentLoaders = instrumentLoaders(import.meta.glob('./c[0-9][0-9]/instrument.tsx'));

const registry = createInstrumentLoader(INSTRUMENT_LOADERS);
export const hasInstrument = registry.has;
export const instrumentOf = registry.peek;
export const loadInstrument = registry.load;
