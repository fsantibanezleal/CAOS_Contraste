// The artifact layer (T3): every committed artifact is fetched from a root-absolute URL under the site's base, with
// ?v=VERSION so a new release never reads an old cached file, and must answer JSON: a static host answering a
// missing file with its HTML page would otherwise parse as an error far from the cause (failure classes 2, 9).
import { useEffect, useState } from 'react';
import type { CaseIndex, CaseManifest, ModelsArtifact, VariantArtifact } from '../lib/contract.types';

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

// Artifacts are immutable within a release, so each path is fetched once and shared by every view that reads it. The
// shared fetch takes no caller's abort signal: one view leaving must not cancel the load another view is waiting on.
const cache = new Map<string, Promise<unknown>>();

function cached<T>(rel: string): Promise<T> {
  let hit = cache.get(rel) as Promise<T> | undefined;
  if (!hit) {
    hit = getJSON<T>(rel);
    cache.set(rel, hit);
    hit.catch(() => cache.delete(rel));
  }
  return hit;
}

export const loadVariant = (path: string, _signal?: AbortSignal) => cached<VariantArtifact>(path);

export const loadModels = (path: string, _signal?: AbortSignal) => cached<ModelsArtifact>(path);

/** One case as the workbench opens it: its manifest, the chosen variant and the models that variant was scored by. */
export interface CaseData {
  manifest: CaseManifest;
  variant: VariantArtifact;
  models: ModelsArtifact;
}

export async function loadCase(caseId: string, variantId: string | null, signal?: AbortSignal): Promise<CaseData> {
  const manifest = await loadManifest(caseId, signal);
  const id = variantId ?? manifest.default_variant;
  const entry = manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === id) ??
    manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === manifest.default_variant);
  if (!entry || !entry.models_ref) throw new ArtifactError(`${caseId}: no variant ${id}`);
  const [variant, models] = await Promise.all([loadVariant(entry.path, signal), loadModels(entry.models_ref, signal)]);
  return { manifest, variant, models };
}

/** Every variant of a case, for the comparison across variants. */
export async function loadAllVariants(manifest: CaseManifest, signal?: AbortSignal): Promise<VariantArtifact[]> {
  const entries = manifest.artifacts.filter((a) => a.role === 'variant');
  return Promise.all(entries.map((e) => loadVariant(e.path, signal)));
}

/** Every case's manifest, for the cross-case pages (Experiments, Benchmark). */
export async function loadAllManifests(signal?: AbortSignal): Promise<{ index: CaseIndex; manifests: CaseManifest[] }> {
  const index = await loadIndex(signal);
  const manifests = await Promise.all(index.cases.map((c) => loadManifest(c.case_id, signal)));
  return { index, manifests };
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
