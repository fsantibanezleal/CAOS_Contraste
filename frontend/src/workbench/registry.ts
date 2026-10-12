// The instrument registry. A case's instrument lives in workbench/cNN/instrument.tsx and exports
// `useInstrument(data, setVariantId)`: the hook that returns the case's rail, groups, variants view, context and
// control values when `data` is that case's, and null for any other case. This module collects every such file at
// build time (`import.meta.glob`, eager), so a unit that builds a case adds `workbench/c06/instrument.tsx` and edits
// nothing else. C01's instrument is built in Workbench.tsx and is not part of the registry.
//
// Rules of hooks: the set of files is fixed when the bundle is built and the order is the sorted path, so every render
// calls the same hooks in the same order. A file that does not export `useInstrument` fails at load, naming the file.
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

export interface RegisteredInstrument {
  path: string;
  useInstrument: InstrumentHook;
}

/** The registered instruments of `modules` (path to module), sorted by path; a module without the hook fails. */
export function collectInstruments(modules: Record<string, unknown>): RegisteredInstrument[] {
  return Object.keys(modules)
    .sort()
    .map((path) => {
      const hook = (modules[path] as { useInstrument?: unknown } | undefined)?.useInstrument;
      if (typeof hook !== 'function') throw new Error(`${path}: an instrument file must export useInstrument(data, setVariantId)`);
      return { path, useInstrument: hook as InstrumentHook };
    });
}

export const INSTRUMENTS: RegisteredInstrument[] = collectInstruments(import.meta.glob('./c[0-9][0-9]/instrument.tsx', { eager: true }));

/** Calls every registered hook, in path order, on every render, and returns the first instrument that is not null. */
export function useRegisteredInstrument(data: CaseData | null, setVariantId: (id: string) => void): Instrument | null {
  let found: Instrument | null = null;
  for (const { useInstrument } of INSTRUMENTS) {
    // eslint-disable-next-line react-hooks/rules-of-hooks -- a fixed list, in a fixed order, fixed at build time
    const inst = useInstrument(data, setVariantId);
    found ??= inst;
  }
  return found;
}
