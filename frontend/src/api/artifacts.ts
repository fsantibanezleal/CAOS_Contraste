// The artifact layer (T3): every committed artifact is fetched from a root-absolute URL under the site's base, with
// ?v=VERSION so a new release never reads an old cached file, and must answer JSON: a static host answering a
// missing file with its HTML page would otherwise parse as an error far from the cause (failure classes 2, 9).
import { useEffect, useState } from 'react';
import type { CaseIndex, CaseManifest, Trace } from '../lib/contract.types';

export class ArtifactError extends Error {}

const DATA = `${import.meta.env.BASE_URL}data/`;

export async function getJSON<T>(rel: string, signal?: AbortSignal): Promise<T> {
  const url = `${DATA}${rel}?v=${encodeURIComponent(__APP_VERSION__)}`;
  const res = await fetch(url, { signal });
  if (!res.ok) throw new ArtifactError(`${rel}: HTTP ${res.status}`);
  const type = res.headers.get('content-type') ?? '';
  if (!type.includes('json')) throw new ArtifactError(`${rel}: answered ${type || 'no content type'}, not JSON`);
  return (await res.json()) as T;
}

export const loadIndex = (signal?: AbortSignal) => getJSON<CaseIndex>('manifests/index.json', signal);

export const loadManifest = (caseId: string, signal?: AbortSignal) => getJSON<CaseManifest>(`manifests/${caseId}.json`, signal);

export interface CaseData {
  manifest: CaseManifest;
  trace: Trace;
}

export async function loadCase(caseId: string, signal?: AbortSignal): Promise<CaseData> {
  const manifest = await loadManifest(caseId, signal);
  const trace = await getJSON<Trace>(manifest.artifact.path, signal);
  return { manifest, trace };
}

/** Every case's manifest and trace, for the cross-case pages (Experiments, Benchmark). */
export async function loadAllCases(signal?: AbortSignal): Promise<{ index: CaseIndex; cases: CaseData[] }> {
  const index = await loadIndex(signal);
  const cases = await Promise.all(index.cases.map((c) => loadCase(c.case_id, signal)));
  return { index, cases };
}

/** A loaded value with its declared state; views write `data-state` from it, and the gate waits on it. */
export type Loaded<T> = { state: 'loading' } | { state: 'ready'; data: T } | { state: 'error'; error: string };

export function useArtifact<T>(load: (signal: AbortSignal) => Promise<T>, deps: unknown[]): Loaded<T> {
  const [value, setValue] = useState<Loaded<T>>({ state: 'loading' });
  useEffect(() => {
    const ctl = new AbortController();
    setValue({ state: 'loading' });
    load(ctl.signal).then(
      (data) => {
        if (!ctl.signal.aborted) setValue({ state: 'ready', data });
      },
      (e: unknown) => {
        if (ctl.signal.aborted) return;
        console.error(`[artifacts] ${String(e)}`);
        setValue({ state: 'error', error: String(e) });
      },
    );
    return () => ctl.abort();
    // the caller names the dependencies of its loader
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return value;
}
