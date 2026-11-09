// The page bar of a long document of the Experiments design group (GATE-15B): the previous and next buttons and the
// position ("1 to 8 of 732", "3 of 12") of a list that is read a page at a time. The window and the words are the shell's
// (`deckWindow`, `deckPosition`, `DECK_TEXT`), the bar wears the shell's deck classes unchanged; the rows are the product's,
// because a table row is not a card (the CardDeck draws cards). Nothing is hidden without being counted: the position
// states the page and the total.
import { DECK_TEXT, deckPosition, deckWindow, useShellLang } from '@fasl-work/caos-app-shell';
import { ChevronLeft, ChevronRight } from 'lucide-react';

/** The page of `items` that `per` at a time show from `start`: the items and the window the shell computed. */
export function pageOf<T>(items: readonly T[], per: number, start: number): { items: T[]; start: number; end: number } {
  const w = deckWindow(items.length, per, start);
  return { items: items.slice(w.start, w.end), start: w.start, end: w.end };
}

/** The start of the previous page and of the next one (the window pulls the last page back so it is full). */
export function stepStart(n: number, per: number, start: number, dir: -1 | 1): number {
  const w = deckWindow(n, per, start);
  return dir < 0 ? deckWindow(n, per, Math.max(0, w.start - per)).start : deckWindow(n, per, w.end).start;
}

/** The bar: previous, the position, next. Drawn even for one page so the position is always stated; the buttons are disabled at the ends. */
export function RowPager({ n, per, start, onStart, label }: { n: number; per: number; start: number; onStart: (start: number) => void; label: string }) {
  const lang = useShellLang();
  const w = deckWindow(n, per, start);
  const shown = w.end - w.start;
  const atStart = w.start <= 0;
  const atEnd = w.end >= n;
  return (
    <div className="caos-deck-bar" role="group" aria-label={label} data-pager data-pager-n={n} data-pager-start={w.start} data-pager-end={w.end}>
      <button type="button" className="caos-deck-btn" data-pager-prev aria-label={DECK_TEXT.previous[lang]} aria-disabled={atStart} onClick={() => !atStart && onStart(stepStart(n, per, w.start, -1))}>
        <ChevronLeft size={18} aria-hidden="true" />
      </button>
      <span className="caos-deck-position" data-pager-position aria-live="polite">
        {n === 0 ? `0 ${DECK_TEXT.of[lang]} 0` : deckPosition(w.start, shown, n, lang)}
      </span>
      <button type="button" className="caos-deck-btn" data-pager-next aria-label={DECK_TEXT.next[lang]} aria-disabled={atEnd} onClick={() => !atEnd && onStart(stepStart(n, per, w.start, 1))}>
        <ChevronRight size={18} aria-hidden="true" />
      </button>
    </div>
  );
}
