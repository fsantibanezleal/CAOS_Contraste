// The filters and the pages of the findings register (GATE-15B), as pure functions so the behaviour is tested without a
// browser: the severity filter, the question-family filter (the family of the finding's case, `families.ts`), the counts
// the chips show, and the page of the filtered rows. A filter never hides rows without saying how many (`hidden`), and the
// default filter (`all`, `all`) shows every row.
import type { BiText } from '@fasl-work/caos-app-shell';
import { sortRows, type FindingRow, type Severity } from '../../workbench/governance/model';
import { familyOf } from './families';
import { pageOf } from './RowPager';

export const ALL = 'all';
export const SEVERITIES: Severity[] = ['S1', 'S2', 'S3', 'S4'];

/** Rows per page of the register. A row is about 120 px tall, so a page holds the register's sized box (520 px) a few times, never the 70,000 px of the whole. */
export const REGISTER_PER_PAGE = 8;

export interface RegisterFilter {
  severity: string;
  family: string;
}

/** The rows that match the filter, by severity (S1 first) and then in the document's order: the order of the pages. */
export function filterRegister(rows: readonly FindingRow[], f: RegisterFilter): FindingRow[] {
  const kept = rows.filter((r) => (f.severity === ALL || r.severity === f.severity) && (f.family === ALL || familyOf(r.case_id).id === f.family));
  return sortRows(kept, 'severity', 'asc');
}

/** The families that hold at least one row, in the order of the first case, with their label and count (under the other filter, so a chip counts what choosing it would show). */
export function familyOptions(rows: readonly FindingRow[], severity: string): Array<{ id: string; label: BiText; count: number }> {
  const out: Array<{ id: string; label: BiText; count: number }> = [];
  for (const r of rows) {
    const fam = familyOf(r.case_id);
    let o = out.find((x) => x.id === fam.id);
    if (!o) {
      o = { id: fam.id, label: fam.label, count: 0 };
      out.push(o);
    }
    if (severity === ALL || r.severity === severity) o.count += 1;
  }
  return out;
}

/** The count of each severity under the family filter. */
export function severityCounts(rows: readonly FindingRow[], family: string): Record<Severity, number> {
  const c: Record<Severity, number> = { S1: 0, S2: 0, S3: 0, S4: 0 };
  for (const r of rows) if (family === ALL || familyOf(r.case_id).id === family) c[r.severity] += 1;
  return c;
}

export interface RegisterView {
  /** Rows matching the filter. */
  matching: number;
  /** Rows the filter hides. */
  hidden: number;
  /** The rows of the page. */
  page: FindingRow[];
  /** The window of the page, 0-based, `[start, end)`. */
  start: number;
  end: number;
}

/** The page of the register under a filter, from `start`: the window is the shell's (`deckWindow`), so the last page is full. */
export function registerView(rows: readonly FindingRow[], f: RegisterFilter, start: number, per = REGISTER_PER_PAGE): RegisterView {
  const matching = filterRegister(rows, f);
  const p = pageOf(matching, per, start);
  return { matching: matching.length, hidden: rows.length - matching.length, page: p.items, start: p.start, end: p.end };
}
