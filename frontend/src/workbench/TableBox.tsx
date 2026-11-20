// The numbers of a card that has no drawing (or a drawing beside it) on a tall desktop (BL-107, ADR-0071 rule 8, ADR-0082): a table takes its
// stage. The shell's own rule does it for a table that is the card body's child (`.caos-plot.fill > .caos-plot-body > .caos-table
// { height: 100% }`, taller rows from 2400 x 1200: "a full-height table is a plotted view too"), and the gate measures a table's painted
// box against the whole body, so a table at its natural height in a body that grows with the screen painted under 30 % of it at 2560 x 1440.
// Below that height the card keeps its scroll box (a long table scrolls under the 400 px a 1280 x 800 body leaves it).
import { Children, Fragment, cloneElement, isValidElement, type ReactElement, type ReactNode } from 'react';
import { useMedia } from '../lib/useMedia';

/** A desktop tall enough that a filling card's body holds a table's rows with room over (1280 x 800 and 1600 x 900 are under it, 2560 x 1440
 * over it); the width keeps a tall tablet on the flowing layout the shell gives a phone. */
export const TALL_QUERY = '(min-height: 1100px) and (min-width: 1280px)';

/** Whether the screen is tall. Where there is no window (the server-rendered tests) the screen is the short one: the layout every view had before BL-107. */
export function useTall(): boolean {
  return useMedia(TALL_QUERY, false);
}

type Marks = Record<string, string>;

/** The children as a flat list: a fragment is opened (its children are the box's own), a null or a boolean is dropped. */
function flat(children: ReactNode): ReactNode[] {
  return Children.toArray(children).flatMap((c) => (isValidElement(c) && c.type === Fragment ? flat((c.props as { children?: ReactNode }).children) : [c]));
}

/** The one `<table>` a card holds, or null (a table beside a paragraph, a list or another table is not alone). */
function soloTable(children: ReactNode): ReactElement<Record<string, unknown>> | null {
  const items = flat(children);
  if (items.length !== 1) return null;
  const only = items[0];
  return isValidElement(only) && only.type === 'table' ? (only as ReactElement<Record<string, unknown>>) : null;
}

/**
 * The body of a filling card whose content is tables. A card that is `fill` takes its stage's height; its tables take it too.
 *
 * - From a tall desktop, one table alone is the body's own child, so the shell's rule gives it the body's height and its rows share
 *   it; `block` is then marked on the table.
 * - From a tall desktop, tables with a list, a note or another table beside them (a body holds one `height: 100%` child) stay in the
 *   card's scroll box, a flex column whose tables each take their share of the height and keep their rows' own height at the least,
 *   so a box that holds more than the card shows scrolls to its last row.
 * - Under a tall desktop the box is the scroll box it always was: the tables keep their own height and scroll inside the card.
 *   `natural`: a card that does not fill below a tall desktop (its box is a plain `div` at its content's height, not a scroll box),
 *   and `attrs`: the data attributes the box carries.
 */
export function TableBox({ children, block, lone = false, natural = false, attrs }: { children: ReactNode; block?: string; lone?: boolean; natural?: boolean; attrs?: Record<string, string> }) {
  const tall = useTall();
  const marks: Marks = { ...(block ? { 'data-block': block } : {}), ...attrs };
  if (!tall) return natural ? <div {...marks}>{children}</div> : <div className="ct-scroll" data-caos-flow="" {...marks}>{children}</div>;
  // `lone`: the child is a component that renders one table and nothing else, so it is the body's child as a table would be
  if (lone) return <>{children}</>;
  const solo = soloTable(children);
  if (solo) return cloneElement(solo, marks);
  return (
    <div className="ct-scroll ct-tall-tables" data-caos-flow="" {...marks}>
      {flat(children).map((child) =>
        isValidElement(child) && child.type === 'table'
          ? cloneElement(child as ReactElement<{ className?: string }>, { className: `${(child.props as { className?: string }).className ?? ''} ct-fill-table`.trim() })
          : child,
      )}
    </div>
  );
}
