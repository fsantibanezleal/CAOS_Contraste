// The host of a case's instrument (BL-102). A case's `useInstrument` hook is loaded on demand (registry.ts), so the
// workbench cannot call every case's hook on every render any more. Instead one `InstrumentRunner`, keyed by the case id,
// calls the hook of the selected case: a case change unmounts the runner of the old case and mounts one for the new
// case, so each mount calls one hook for its whole life and no hook of another case ever runs (rules of hooks kept).
// The runner draws nothing; it hands the instrument it built to the workbench, which keeps CaseWorkbench mounted across
// cases (Focus mode, the selected tab and the deep link survive a case change).
import { memo, useCallback, useEffect, useLayoutEffect, useReducer, useState, type ReactElement } from 'react';
import type { CaseData } from '../api/artifacts';
import type { CaseIndex, Text } from '../lib/contract.types';
import { absentInstrument, type AbsentInstrument } from '../readiness/Planned';
import { Pending } from './Pending';
import { hasInstrument, instrumentOf, loadInstrument, type createInstrumentLoader, type Instrument, type InstrumentHook } from './registry';

type IndexEntry = CaseIndex['cases'][number];
type InstrumentLoader = ReturnType<typeof createInstrumentLoader>;

// useLayoutEffect warns on a server render in older React; the runner only publishes in the browser
const useIsoLayoutEffect = typeof window === 'undefined' ? useEffect : useLayoutEffect;

export interface RunnerProps {
  caseId: string;
  hook: InstrumentHook;
  data: CaseData | null;
  setVariantId: (id: string) => void;
  /** Called after every render of the runner with the instrument it built (null for data that is not the case's). */
  onInstrument: (caseId: string, instrument: Instrument | null) => void;
}

/** Calls the hook of one case (the only hook this component ever calls) and hands the result to the workbench. */
export const InstrumentRunner = memo(function InstrumentRunner({ caseId, hook, data, setVariantId, onInstrument }: RunnerProps) {
  const instrument = hook(data, setVariantId);
  useIsoLayoutEffect(() => {
    onInstrument(caseId, instrument);
  });
  return null;
});

/** The runner element of a case, keyed by the case id: another case is another mount. */
export function instrumentSlot(props: RunnerProps): ReactElement {
  return <InstrumentRunner key={props.caseId} {...props} />;
}

export type InstrumentStatus = { state: 'none' } | { state: 'loading' } | { state: 'ready' } | { state: 'failed'; message: string };

/** The state of a case's instrument module: none (C01, no case, no file), loading, ready or failed (its own failure only). */
export function instrumentStatus(loader: Pick<InstrumentLoader, 'has' | 'peek'>, caseId: string | null, failed: { caseId: string; message: string } | null): InstrumentStatus {
  if (!caseId || !loader.has(caseId)) return { state: 'none' };
  if (loader.peek(caseId)) return { state: 'ready' };
  if (failed && failed.caseId === caseId) return { state: 'failed', message: failed.message };
  return { state: 'loading' };
}

/** Starts loading the selected case's module as soon as the case is known and reports its state; a loaded module is kept. */
export function useInstrumentModule(caseId: string | null): { status: InstrumentStatus; hook: InstrumentHook | null } {
  const [, rerender] = useReducer((n: number) => n + 1, 0);
  const [failed, setFailed] = useState<{ caseId: string; message: string } | null>(null);
  useEffect(() => {
    if (!caseId || !hasInstrument(caseId) || instrumentOf(caseId)) return;
    let live = true;
    loadInstrument(caseId).then(
      () => live && rerender(),
      (e: unknown) => live && setFailed({ caseId, message: e instanceof Error ? e.message : String(e) }),
    );
    return () => {
      live = false;
    };
  }, [caseId]);
  const status = instrumentStatus({ has: hasInstrument, peek: instrumentOf }, caseId, failed);
  return { status, hook: caseId ? instrumentOf(caseId) : null };
}

/** What the workbench keeps of the instrument its runner built: the case it is for, so another case's is never shown. */
export function useInstrumentPublication(selected: string | null): { published: Instrument | null; publish: RunnerProps['onInstrument'] } {
  const [held, setHeld] = useState<{ caseId: string; instrument: Instrument | null } | null>(null);
  const publish = useCallback((caseId: string, instrument: Instrument | null) => setHeld({ caseId, instrument }), []);
  return { published: held && held.caseId === selected ? held.instrument : null, publish };
}

const providedBy = (entry: IndexEntry | null): 'real' | 'synthetic' => (entry?.kind === 'synthetic' ? 'synthetic' : 'real');

/** The instrument shown while a case's module is on its way: the shell's pending state in every view, the gate waits on it. */
export function pendingInstrument(entry: IndexEntry | null): AbsentInstrument {
  const provenance = providedBy(entry);
  const wait = <Pending label={{ en: 'Loading the instrument of this case', es: 'Cargando el instrumento de este caso' }} />;
  return {
    sel: null,
    rail: [],
    groups: [
      { id: 'model', label: { en: 'Model', es: 'Modelo' }, lane: 'replay', provenance, content: wait },
      { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'replay', provenance, content: wait },
      { id: 'impact', label: { en: 'Impact', es: 'Impacto' }, lane: 'live', provenance, content: wait },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance, content: wait },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance, content: wait },
    context: { content: wait },
    controls: {},
  };
}

/** The instrument of a case whose module could not be loaded (an offline reader, a stale deploy): the absent one, with the reason. */
export function failedInstrument(caseId: string, message: string, entry: IndexEntry | null): AbsentInstrument {
  const reason: Text = {
    en: `The instrument of ${caseId} could not be loaded (${message}). Reload the page; if it persists the deployed build may be stale.`,
    es: `No se pudo cargar el instrumento de ${caseId} (${message}). Recargue la página; si persiste, la versión desplegada puede estar desactualizada.`,
  };
  return absentInstrument(reason, entry);
}
