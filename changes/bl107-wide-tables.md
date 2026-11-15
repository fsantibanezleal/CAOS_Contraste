- The table-heavy and bar-list views pass the shell gate's G6 floors at 2560 x 1440 (BL-107: a drawing under 30 % of its stage, the drawn
  views under 60 % of the viewport, in 23 views of C03, C04, C05, C06, C07, C09, C11, C12, C16 and C22 since 1.00.000). On a screen at least
  1100 px tall and 1280 px wide a card's table takes its stage: one table alone is the card body's own child, so the shell's rule for a
  full-height table gives it the body's height; a card with a list, a note or a second table shares the height among its tables in the
  scroll box, which still scrolls to its last row. C09's by-design bars fill their card, its floors card lets the drawing take the height
  the table leaves (no fixed 9 rem), and C11's verdict card fills its stage. Under that size (1280 x 800, 1600 x 900, 768, 390) every
  card keeps the layout it had. The shared box is `workbench/TableBox.tsx`; `ChartAbove` takes `grow` for the second.
