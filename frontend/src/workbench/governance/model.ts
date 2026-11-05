// What the governance views share (U15-W): the types of the four governance documents, how a document is loaded and what
// the view says when the bake has not written it, the labels (every severity beside its ECB F equivalent, every status,
// every convention tag) and the small pure functions the views draw from. Nothing here computes a model quantity: the
// engine's governance package does (riskvalidation.governance), the bake writes the documents, and a view reads them.
// The tier matrix below is the rule of dossier 06 B.3 (a stated convention, item 30), shown beside the counts and
// checked against every entry of the documents in governance.test.tsx.
import { ArtifactUnavailable, getJSON, useArtifact, type LoadedDeclared } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import type { Text } from '../../lib/contract.types';
import { entryText } from '../names';

export type GovInventory = components['schemas']['governance-governance-inventory'];
export type GovFindings = components['schemas']['governance-governance-findings'];
export type GovReport = components['schemas']['governance-governance-report'];
export type GovAppetite = components['schemas']['governance-governance-appetite'];
export type InvEntry = GovInventory['entries'][number];
export type FindingRow = GovFindings['rows'][number];
export type AppetiteMetric = GovAppetite['metrics'][number];
export type ReportSection = GovReport['sections'][number];
export type Severity = FindingRow['severity'];
export type Tier = 1 | 2 | 3 | 4;

/** Where the governance bake writes each document, relative to data/ (U15-P; the fixtures of docs/contracts/fixtures/governance stand in until it runs). */
export const GOVERNANCE_FILES = {
  inventory: 'governance/inventory.json',
  findings: 'governance/findings.json',
  appetite: 'governance/appetite.json',
} as const;

/** The file of the validation report of an inventory entry (`case_id/fit_id`): governance/reports/<case>-<fit>.json. */
export const reportFile = (entryKey: string): string => `governance/reports/${entryKey.replace('/', '-')}.json`;

/** The reason a governance view gives when the bake has not written a document: never an empty chart. */
export const notWritten = (file: string): Text => ({
  en: `The governance bake has not written ${file}.`,
  es: `La generación de gobernanza aún no ha escrito ${file}.`,
});

const cache = new Map<string, Promise<unknown>>();

/** One governance document, fetched once. An absent or non-JSON answer is the declared "not available yet" state, with its reason. */
export function loadGovernance<T>(file: string): Promise<T> {
  let hit = cache.get(file) as Promise<T> | undefined;
  if (!hit) {
    hit = getJSON<T>(file).catch((e: unknown) => {
      cache.delete(file);
      // getJSON throws ArtifactError for an HTTP error or a non-JSON answer (a static host's HTML page): the file is not there
      if (e instanceof Error && e.name !== 'AbortError' && /HTTP \d+|not JSON/.test(e.message)) throw new ArtifactUnavailable(file, notWritten(file));
      throw e;
    });
    cache.set(file, hit);
  }
  return hit;
}

/** Forgets the fetched documents (a test starts clean; a page load never needs it). */
export function resetGovernance(): void {
  cache.clear();
}

/** A governance document with its declared state; `null` as the file waits for a choice (the report reader before an entry is picked). */
export function useGovernance<T>(file: string | null): LoadedDeclared<T> {
  return useArtifact<T>(() => (file ? loadGovernance<T>(file) : new Promise<T>(() => undefined)), [file], { unavailable: true });
}

// --- labels ------------------------------------------------------------------------------------------------------

export const SEVERITY_NAME: Record<Severity, Text> = {
  S1: { en: 'critical', es: 'crítico' },
  S2: { en: 'significant', es: 'significativo' },
  S3: { en: 'moderate', es: 'moderado' },
  S4: { en: 'minor', es: 'menor' },
};

/** The stated mapping of the product's severity to the ECB F scale (decision W15-2): S1 is F4 (very high), S2 F3, S3 F2, S4 F1 (low). */
export const ECB_F_OF: Record<Severity, string> = { S1: 'F4', S2: 'F3', S3: 'F2', S4: 'F1' };

/** The ECB F scale of the TRIM report: F1 a low impact, F4 a very high one (dossier 06 B.7); F2 and F3 are the steps between. */
export const ECB_F_NAME: Record<string, Text> = {
  F1: { en: 'low impact', es: 'impacto bajo' },
  F2: { en: 'F2', es: 'F2' },
  F3: { en: 'F3', es: 'F3' },
  F4: { en: 'very high impact', es: 'impacto muy alto' },
};

/** A severity written with its ECB F equivalent beside it (decision W15-2): "S1 critical, ECB F4". */
export const severityText = (s: Severity, ecbF: string, lang: 'en' | 'es'): string =>
  `${s} ${SEVERITY_NAME[s][lang]}, ${lang === 'es' ? 'BCE' : 'ECB'} ${ecbF}`;

export const STATUS_NAME: Record<string, Text> = {
  open: { en: 'open', es: 'abierto' },
  action_plan_agreed: { en: 'action plan agreed', es: 'plan de acción acordado' },
  in_progress: { en: 'in progress', es: 'en curso' },
  submitted_for_closure: { en: 'submitted for closure', es: 'enviado a cierre' },
  validated_closed: { en: 'validated and closed', es: 'validado y cerrado' },
  overdue: { en: 'overdue', es: 'vencido' },
  risk_accepted: { en: 'risk accepted (a stated limit)', es: 'riesgo aceptado (un límite declarado)' },
};

/** The product's own three statuses, which the register maps to the seven of B.7 (decision W15-5). */
export const PRODUCT_STATUS_NAME: Record<string, Text> = {
  open: { en: 'open', es: 'abierto' },
  accepted: { en: 'accepted', es: 'aceptado' },
  closed: { en: 'closed', es: 'cerrado' },
};

export const TAG_NAME: Record<string, Text> = {
  convention: { en: 'convention', es: 'convención' },
  doc: { en: 'read from a document', es: 'leído de un documento' },
};

/** The label every convention, threshold and tier count carries: none is a regulatory value (dossier 06 UNVERIFIED item 30). */
export const CONVENTION_NOTE: Text = {
  en: 'Every tier count, band, deadline, frequency and threshold on this page is a stated convention of Contraste, never a regulatory value.',
  es: 'Cada conteo por nivel, banda, plazo, frecuencia y umbral de esta página es una convención declarada de Contraste, nunca un valor regulatorio.',
};

/** The label of an opinion and of its recommendation (decisions W15-7 and W15-11). */
export const RULE_OUTPUT_LABEL: Text = {
  en: "the rule's output on the evidence; Contraste approves no model",
  es: 'el resultado de la regla sobre la evidencia; Contraste no aprueba ningún modelo',
};

export const OPINION_NAME: Record<number, Text> = {
  1: { en: 'adequate, no deficiencies', es: 'adecuado, sin deficiencias' },
  2: { en: 'adequate, minor deficiencies', es: 'adecuado, deficiencias menores' },
  3: { en: 'major deficiencies', es: 'deficiencias mayores' },
  4: { en: 'severe deficiencies', es: 'deficiencias severas' },
};

export const RECOMMENDATION_NAME: Record<string, Text> = {
  approve: { en: 'approve', es: 'aprobar' },
  'approve with conditions': { en: 'approve with conditions', es: 'aprobar con condiciones' },
  'remediate before use': { en: 'remediate before use', es: 'remediar antes del uso' },
};

export const tierName = (tier: number, lang: 'en' | 'es'): string => `${lang === 'es' ? 'Nivel' : 'Tier'} ${tier}`;

// --- the tier matrix (dossier 06 B.3, l.571-574) ----------------------------------------------------------------

/** The tier of a materiality and a complexity score: Tier 1 if M = 4 or (M = 3 and C >= 3); Tier 2 if M = 3 or (M = 2 and C >= 3); Tier 3 if M = 2 or (M = 1 and C >= 3); else Tier 4. */
export function tierOf(m: number, c: number): Tier {
  if (m === 4 || (m === 3 && c >= 3)) return 1;
  if (m === 3 || (m === 2 && c >= 3)) return 2;
  if (m === 2 || (m === 1 && c >= 3)) return 3;
  return 4;
}

export const TIER_RULE_TEX =
  '\\mathrm{Tier}=\\begin{cases}1&M=4\\ \\text{or}\\ (M=3\\ \\text{and}\\ C\\ge 3)\\\\2&M=3\\ \\text{or}\\ (M=2\\ \\text{and}\\ C\\ge 3)\\\\3&M=2\\ \\text{or}\\ (M=1\\ \\text{and}\\ C\\ge 3)\\\\4&\\text{otherwise}\\end{cases}';

/** The (M, C) the entry holds under the adopted reading, read from its sensitivity table. */
export function adoptedCell(entry: InvEntry): { m: number; c: number } | null {
  const row = entry.tier_block.tier_sensitivity.find((r) => r.reading === entry.tier_block.adopted_reading);
  return row ? { m: row.m, c: row.c } : null;
}

/** The count of entries in each (materiality, complexity) cell under their adopted reading; `keys[m][c]` lists them. */
export function matrixCells(entries: InvEntry[]): { counts: number[][]; keys: string[][][] } {
  const counts = [0, 1, 2, 3, 4].map(() => [0, 0, 0, 0, 0]);
  const keys = [0, 1, 2, 3, 4].map(() => [0, 1, 2, 3, 4].map(() => [] as string[]));
  for (const e of entries) {
    const cell = adoptedCell(e);
    if (!cell) continue;
    counts[cell.m][cell.c] += 1;
    keys[cell.m][cell.c].push(e.key);
  }
  return { counts, keys };
}

/** The worst severity among an entry's open findings (attribute A37), or null with none. */
export function worstOpen(entry: InvEntry): Severity | null {
  const v = entry.attributes.A37.value as Partial<Record<Severity, number>> | null;
  if (!v) return null;
  return (['S1', 'S2', 'S3', 'S4'] as Severity[]).find((s) => (v[s] ?? 0) > 0) ?? null;
}

/** The entries by generation of the map, each generation ordered by the bake's y (the layered layout of the dependency map). */
export function layers(entries: InvEntry[]): InvEntry[][] {
  const depth = Math.max(0, ...entries.map((e) => e.map.generation));
  return Array.from({ length: depth + 1 }, (_, g) => entries.filter((e) => e.map.generation === g).sort((a, b) => a.map.y - b.map.y || a.key.localeCompare(b.key)));
}

// --- the register ------------------------------------------------------------------------------------------------

export type SortKey = 'entry' | 'severity' | 'status' | 'anchor' | 'due' | 'ageing';

const SEVERITY_ORDER: Record<Severity, number> = { S1: 0, S2: 1, S3: 2, S4: 3 };

/** The rows sorted by a column; ties keep the document's order, so a sort is stable and reproducible. */
export function sortRows(rows: FindingRow[], key: SortKey, dir: 'asc' | 'desc'): FindingRow[] {
  const val = (r: FindingRow): string | number => {
    if (key === 'entry') return r.entry_key;
    if (key === 'severity') return SEVERITY_ORDER[r.severity];
    if (key === 'status') return r.status;
    if (key === 'anchor') return r.anchor ? r.anchor.value : Number.POSITIVE_INFINITY;
    if (key === 'due') return r.due;
    return r.ageing_days;
  };
  const sign = dir === 'asc' ? 1 : -1;
  return rows
    .map((r, i) => ({ r, i }))
    .sort((a, b) => {
      const x = val(a.r);
      const y = val(b.r);
      const c = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y));
      return c !== 0 ? sign * c : a.i - b.i;
    })
    .map((x) => x.r);
}

/** The rows by severity and status (the stacked bars): `[severity][status]` counts. */
export function severityByStatus(rows: FindingRow[]): Array<{ severity: Severity; total: number; byStatus: Record<string, number> }> {
  return (['S1', 'S2', 'S3', 'S4'] as Severity[]).map((severity) => {
    const mine = rows.filter((r) => r.severity === severity);
    const byStatus: Record<string, number> = {};
    for (const r of mine) byStatus[r.status] = (byStatus[r.status] ?? 0) + 1;
    return { severity, total: mine.length, byStatus };
  });
}

/** The age, in days, of the rows that are not closed, in bins of `width` days; the last bin holds the oldest. */
export function ageingBins(rows: FindingRow[], width = 30): Array<{ from: number; to: number; count: number; overdue: number }> {
  const live = rows.filter((r) => r.status !== 'validated_closed');
  if (!live.length) return [];
  const top = Math.max(...live.map((r) => r.ageing_days));
  const n = Math.floor(top / width) + 1;
  return Array.from({ length: n }, (_, i) => {
    const mine = live.filter((r) => Math.floor(r.ageing_days / width) === i);
    return { from: i * width, to: (i + 1) * width - 1, count: mine.length, overdue: mine.filter((r) => r.overdue).length };
  });
}

/** The entry key of a report file name's parts, for the reader's select: `C07/banco-andino`. */
// the entry in words (the R2b page review: the select printed `C01/german`); the case title is the report's header, so a plain
// select keeps a text that fits its room at 390 px (gate G5)
export const entryLabel = (e: InvEntry, lang: 'en' | 'es'): string => entryText(e.key)[lang];

/** The three states of a tab's one document, shown as the reason a reader can read. */
export const NOT_YET: Text = { en: 'Not available yet', es: 'Aún no disponible' };
