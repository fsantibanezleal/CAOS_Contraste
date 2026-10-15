// A short list of facts as a two-column table, for the places under a drawing where a definition list would take the
// card's height (the card scrolls its tables, not its drawing). Each row names its fact in both languages; a value that
// the document does not carry says "not available" with its reason, written by the caller.
import { pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';

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
    <table className="caos-table ct-wrap-head" data-table={table}>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} data-row={r.id}>
            <th scope="row" className="ct-text" style={{ minWidth: '11rem', fontWeight: 600 }}>{pick(r.label, lang)}</th>
            <td className="ct-text" {...r.attrs}>{r.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
