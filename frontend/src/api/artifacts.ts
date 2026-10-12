// The artifact layer (T3): every committed artifact is fetched from a root-absolute URL under the site's base, with
// ?v=VERSION so a new release never reads an old cached file, and must answer JSON: a static host answering a
// missing file with its HTML page would otherwise parse as an error far from the cause (failure classes 2, 9).
import { useEffect, useState } from 'react';
import type { CaseIndex, CaseManifest, ModelsArtifact, Text, VariantArtifact } from '../lib/contract.types';
import { loadReadiness, unavailableRow } from '../readiness/readiness';

export class ArtifactError extends Error {}

/** The readiness document lists this artifact as absent: the view says not available yet, with the reason. */
export class ArtifactUnavailable extends Error {
  constructor(
    readonly path: string,
    readonly reason: Text,
  ) {
    super(`${path}: not available yet (${reason.en})`);
  }
}

/** Throws ArtifactUnavailable when the readiness document marks `path` absent; an unreadable document never does. */
async function requireAvailable(path: string): Promise<void> {
  const row = unavailableRow(await loadReadiness(), path);
  if (!row) return;
  const why = row.reason ?? { en: 'the pipeline did not write it', es: 'el pipeline no lo escribió' };
  throw new ArtifactUnavailable(path, {
    en: `${path} is not available yet: ${why.en}`,
    es: `${path} aún no está disponible: ${why.es}`,
  });
}

const DATA = `${import.meta.env.BASE_URL}data/`;

export async function getJSON<T>(rel: string, signal?: AbortSignal): Promise<T> {
  const url = `${DATA}${rel}?v=${encodeURIComponent(__APP_VERSION__)}`;
  const res = await fetch(url, { signal });
  if (!res.ok) throw new ArtifactError(`${rel}: HTTP ${res.status}`);
  const type = res.headers.get('content-type') ?? '';
  if (!type.includes('json')) throw new ArtifactError(`${rel}: answered ${type || 'no content type'}, not JSON`);
  return (await res.json()) as T;
}

const INDEX_PATH = 'manifests/index.json';

export async function loadIndex(signal?: AbortSignal): Promise<CaseIndex> {
  await requireAvailable(INDEX_PATH);
  return getJSON<CaseIndex>(INDEX_PATH, signal);
}

export async function loadManifest(caseId: string, signal?: AbortSignal): Promise<CaseManifest> {
  const path = `manifests/${caseId}.json`;
  await requireAvailable(path);
  return getJSON<CaseManifest>(path, signal);
}

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

export interface AbsentCase {
  caseId: string;
  title: Text;
  reason: Text;
}

/**
 * Every built case's manifest, for the cross-case pages (Experiments, Benchmark). A case the readiness document lists
 * as absent (a planned case) is not in `manifests`: it is in `absent`, with its reason, and the others still load.
 */
export async function loadAllManifests(signal?: AbortSignal): Promise<{ index: CaseIndex; manifests: CaseManifest[]; absent: AbsentCase[] }> {
  const index = await loadIndex(signal);
  const settled = await Promise.all(
    index.cases.map((c) =>
      loadManifest(c.case_id, signal).then(
        (manifest) => ({ manifest }),
        (e: unknown) => {
          if (e instanceof ArtifactUnavailable) return { absent: { caseId: c.case_id, title: c.title, reason: e.reason } };
          throw e;
        },
      ),
    ),
  );
  return {
    index,
    manifests: settled.flatMap((r) => ('manifest' in r ? [r.manifest] : [])),
    absent: settled.flatMap((r) => ('absent' in r ? [r.absent] : [])),
  };
}

/** A loaded value with its declared state; views write `data-state` from it, and the gate waits on it. */
export type Loaded<T> = { state: 'loading' } | { state: 'ready'; data: T } | { state: 'error'; error: string };

/** A loaded value of a view that also says "not available yet": the readiness lists the artifact as absent (ADR-0080). */
export type LoadedDeclared<T> = Loaded<T> | { state: 'unavailable'; reason: Text };

/**
 * Loads `load` and holds its declared state. A view that can say "not available yet" itself passes
 * `{ unavailable: true }` and handles the `unavailable` state; every other view gets an absent artifact as `error`.
 */
export function useArtifact<T>(load: (signal: AbortSignal) => Promise<T>, deps: unknown[], opts: { unavailable: true }): LoadedDeclared<T>;
export function useArtifact<T>(load: (signal: AbortSignal) => Promise<T>, deps: unknown[]): Loaded<T>;
export function useArtifact<T>(load: (signal: AbortSignal) => Promise<T>, deps: unknown[], opts?: { unavailable: true }): LoadedDeclared<T> {
  const [value, setValue] = useState<LoadedDeclared<T>>({ state: 'loading' });
  useEffect(() => {
    const ctl = new AbortController();
    setValue({ state: 'loading' });
    load(ctl.signal).then(
      (data) => {
        if (!ctl.signal.aborted) setValue({ state: 'ready', data });
      },
      (e: unknown) => {
        if (ctl.signal.aborted) return;
        if (e instanceof ArtifactUnavailable && opts?.unavailable) {
          setValue({ state: 'unavailable', reason: e.reason });
          return;
        }
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
