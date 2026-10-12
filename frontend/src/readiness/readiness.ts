// The readiness document on the web side (catalog: Missing-data states, ADR-0080 decisions 3 and 4). The pipeline
// declares, per catalog row, whether it is available, partial, stale, provided by a provider, training or missing;
// the views never decide that themselves, they read it here. Pure functions over the document, and one cached fetch.
import { getJSON } from '../api/artifacts';
import type { Text } from '../lib/contract.types';
import type { ContractState, Provenance, Readiness, ReadinessEntry } from './types';

export const READINESS_URL = 'readiness.json';

/** The most severe state first: the order in which a view's rows are reduced to one note. */
export const SEVERITY: ContractState[] = ['missing', 'partial', 'training', 'provider', 'stale', 'available'];

/** What the frontend does with a state (the catalog's table "What each surface does"). */
export function behavior(state: ContractState): { showsResult: boolean; note: boolean } {
  return { showsResult: state !== 'missing', note: state !== 'available' };
}

export interface ViewRow {
  id: string;
  state: ContractState;
  provenance: Provenance | null;
  reason: Text | null;
}

/** The readiness of one view: `unknown` when the document is absent or names none of the view's rows. */
export type ViewState = { state: 'unknown' } | { state: ContractState; rows: ViewRow[] };

export const entryFor = (doc: Readiness | null, id: string): ReadinessEntry | undefined => doc?.contracts.find((c) => c.id === id);

/** The most severe state among the rows `ids` names, with each non-available row and its reason. */
export function viewState(doc: Readiness | null, ids: string[]): ViewState {
  const found = ids.map((id) => entryFor(doc, id)).filter((e): e is ReadinessEntry => !!e);
  if (!found.length) return { state: 'unknown' };
  const state = SEVERITY.find((s) => found.some((e) => e.state === s)) ?? 'available';
  const rows = found.filter((e) => e.state !== 'available').map((e) => ({ id: e.id, state: e.state, provenance: e.provenance, reason: e.reason }));
  return { state, rows };
}

/** Why `path` (relative to data/) is not available, or null: a row lists it in `missing`, or the case index is missing. */
export function unavailableRow(doc: Readiness | null, path: string): ReadinessEntry | null {
  if (!doc) return null;
  const listed = doc.contracts.find((c) => c.missing.includes(path));
  if (listed) return listed;
  const index = entryFor(doc, 'case-index');
  return index?.state === 'missing' ? index : null;
}

export const isUnavailable = (doc: Readiness | null, path: string): boolean => unavailableRow(doc, path) !== null;

let cached: Promise<Readiness | null> | null = null;

/** Forgets the fetched document (a test starts clean; a page load never needs it). */
export function resetReadiness(): void {
  cached = null;
}

/**
 * The readiness document, fetched once per page load through `getJSON`. A missing or unreadable document resolves to
 * null (every view then says readiness unknown) and names the cause on the console: it never breaks a view. The
 * fetch is shared by every view, so no single view's abort signal cancels it.
 */
export function loadReadiness(_signal?: AbortSignal): Promise<Readiness | null> {
  cached ??= getJSON<Readiness>(READINESS_URL).then(
    (doc) => {
      if (!doc || !Array.isArray(doc.contracts)) {
        console.error(`[readiness] ${READINESS_URL}: no contracts list; every view says readiness unknown`);
        return null;
      }
      return doc;
    },
    (e: unknown) => {
      console.error(`[readiness] ${String(e)}; every view says readiness unknown`);
      return null;
    },
  );
  return cached;
}

/** The rows a case's views consume: the shared ones, and every row named for the case (`c04-agency` for C04). */
const SHARED_ROWS = ['case-index', 'case-manifest', 'variant-envelope', 'models-envelope', 'test-result'];
export function rowsForCase(doc: Readiness | null, caseId: string): string[] {
  if (!doc) return [];
  const prefix = `${caseId.toLowerCase()}-`;
  const ids = doc.contracts.map((c) => c.id);
  return [...SHARED_ROWS.filter((id) => ids.includes(id)), ...ids.filter((id) => id.startsWith(prefix))];
}

/** The part of the case index the planned-case rule reads. */
export interface PlannableEntry {
  case_id: string;
  manifest_path: string;
}

/**
 * A planned case: an index entry whose manifest path is in the `missing` of the `case-manifest` readiness row while
 * that row is partial (the pipeline declares the case planned and not built). False when the readiness is unknown.
 */
export function isPlanned(doc: Readiness | null, entry: PlannableEntry): boolean {
  const row = entryFor(doc, 'case-manifest');
  return !!row && row.state === 'partial' && row.missing.includes(entry.manifest_path);
}

export const plannedCaseIds = (doc: Readiness | null, index: { cases: PlannableEntry[] }): string[] =>
  index.cases.filter((c) => isPlanned(doc, c)).map((c) => c.case_id);
