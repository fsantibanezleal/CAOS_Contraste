// A code identifier printed in a narrow cell (a generator, a class, a data field): it breaks only after its separators, never
// inside a word. The `<wbr>` after each separator are its only break points; the inline `overflow-wrap: normal` keeps the shared
// text-cell rule (`.caos-table td.ct-text :is(a, code) { overflow-wrap: anywhere }`, for a DOI or a URL) from breaking it anywhere
// else (U16-R4 c27 n5, U16-R5 c28 m1, c29 n5: "logistic / _ / portfoli / o"; c27 n4: "action_t / aken").
import type { CSSProperties, ReactNode } from 'react';

/** The parts of an identifier with a `<wbr>` after each ".", "_" or "-". */
export function codeBreaks(id: string): ReactNode[] {
  return id.split(/(?<=[._-])/).flatMap((part, i) => (i === 0 ? [part] : [<wbr key={i} />, part]));
}

/** The style of a code that breaks at its separators only. */
export const CODE_BREAKS_STYLE: CSSProperties = { overflowWrap: 'normal' };

/** A code identifier, not to be translated, that breaks only at its separators. */
export function BreakingCode({ id, lang }: { id: string; lang?: string }) {
  return (
    <code translate="no" lang={lang} style={CODE_BREAKS_STYLE}>
      {codeBreaks(id)}
    </code>
  );
}
