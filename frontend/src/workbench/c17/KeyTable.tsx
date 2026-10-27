// A short list of facts as a two-column table, for the places under a drawing where a definition list would take the
// card's height (the card scrolls its tables, not its drawing). Each row names its fact in both languages; a value that
// the document does not carry says "not available" with its reason, written by the caller.
import { pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { Fragment, type ReactNode } from 'react';

export interface KeyRow {
  id: string;
  label: BiText;
  value: ReactNode;
  /** Attributes the gate and the tests read from the value cell (`data-mean`, `data-golden`). */
  attrs?: Record<string, string>;
}

export function KeyTable({ table, rows }: { table: string; rows: KeyRow[] }) {
  const lang = useShellLang();
  return (
    <table className="caos-table ct-wrap-head" data-table={table} style={{ width: '100%' }}>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} data-row={r.id}>
            <th scope="row" className="ct-text" style={{ minWidth: 'min(11rem, 34vw)', fontWeight: 600 }}>{pick(r.label, lang)}</th>
            <td className="ct-text" {...r.attrs}>{r.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** A text whose ISO dates never break at their hyphens (U16-R4 c21 m11: "2024-07-" and "05" on two lines at 390). */
export function keepDates(text: string): ReactNode {
  const parts = text.split(/(\d{4}-\d{2}-\d{2})/);
  return parts.map((p, i) => (i % 2 === 1 ? <span key={i} style={{ whiteSpace: 'nowrap' }}>{p}</span> : <Fragment key={i}>{p}</Fragment>));
}
