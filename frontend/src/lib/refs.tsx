// Reference identifiers inside running text: a paragraph, section, table or equation number, an arXiv id, a software or licence
// version ("sección 4.2", "Tablas 3.2 y 3.3", "IFRS 9 5.5", "arXiv 0708.2542", "QuantLib 1.44"). A Spanish page writes a decimal
// with a comma, so the gate's Spanish-number check (G11) reads a dotted number as a decimal written the English way; an identifier
// is marked translate="no", which the gate and the translators read as "not a number to localise".
//
// An identifier is recognised by its context only: the number that follows a reference word or name, and the further numbers of the
// list that word starts. A dotted number with no such context is never marked, so a decimal written with a point in Spanish prose
// is still seen by the gate. Data documents are never touched: this renders a text, it does not rewrite one.
import { Fragment, type ReactNode } from 'react';

type Lang = 'en' | 'es';

// A reference word; the number may be undotted ("línea 237", "paras 114 to 118").
const WORDS = [
  'secci[oó]n', 'secciones', 'sections?',
  'tablas?', 'tables?', 'cuadros?',
  'p[aá]rrafos?', 'paragraphs?',
  'cap[ií]tulos?', 'chapters?', 'apartados?',
  'notas?', 'notes?',
  'ecuaci[oó]n', 'ecuaciones', 'equations?',
  'l[ií]neas?', 'lines?',
  'principios?', 'principles?',
  'filas?', 'rows?',
  'anexos?', 'annex(?:es)?',
  'art[ií]culos?', 'articles?',
  'teoremas?', 'theorems?', 'lemas?', 'lemmas?',
  'figuras?', 'figures?',
  'ap[eé]ndices?', 'appendix', 'appendices',
  'versi[oó]n', 'versiones', 'versions?',
];
// "para" is an English abbreviation of "paragraph" and a Spanish preposition ("para 2.5 millones"): a reference word in English only.
const WORDS_EN_ONLY = ['paras?'];
// A name that carries a dotted number of its own: a standard's paragraph, or the version of a package or a licence.
const NAMES = [
  String.raw`IFRS\s*\d+`, String.raw`NIIF\s*\d+`, String.raw`IAS(?:\s*\d+)?`, String.raw`NIC(?:\s*\d+)?`,
  'QuantLib', 'Python', 'NumPy', 'SciPy', 'pandas', 'scikit-learn', 'statsmodels', 'PyTorch', 'TensorFlow', 'XGBoost', 'LightGBM', String.raw`Node(?:\.js)?`,
  'CC0', 'CC[- ]BY(?:-[A-Z]{2})?', 'Apache', 'GPL', 'LGPL', 'AGPL',
];

const ITEM = String.raw`\d+(?:\.\d+)*(?:\([a-z]{1,4}\))*`;
// A further item continues a list only where the list can go on: before punctuation, the end, another joiner or "de/of".
const JOINER = '(?:y|and|e|o|or|a|to)';
const CONTINUE = String.raw`(?:,\s*|\s+${JOINER}\s+|\s*[–-]\s*)${ITEM}(?!\.?\d)(?=\s*(?:[,;:.)]|$)|\s+${JOINER}\s+\d|\s+(?:de|del|of|in|en|on)\b)`;
const LIST = `(?<list>${ITEM}(?:${CONTINUE})*)`;

const build = (lang: Lang): RegExp => {
  const words = (lang === 'en' ? [...WORDS, ...WORDS_EN_ONLY] : WORDS).join('|');
  const before = String.raw`(?<![\p{L}\p{N}_])`;
  const dotted = String.raw`(?=\d+\.\d)`;
  const lead = [
    String.raw`(?:${words})\s+\(?`, // a reference word, the number possibly in parentheses ("ecuación (10)")
    String.raw`arXiv:?\s*`, // an arXiv id
    String.raw`§\s*`,
    String.raw`(?:${NAMES.join('|')})\s+${dotted}`, // a name followed by its dotted number
    `v${dotted}`, // v0.05
  ].join('|');
  return new RegExp(`${before}(?:${lead})${LIST}`, 'giu');
};
const RE: Record<Lang, RegExp> = { en: build('en'), es: build('es') };
const ITEM_RE = new RegExp(ITEM, 'g');
const dots = (s: string): number => s.replace(/\(.*$/, '').split('.').length - 1;

/** The part of a matched list that is one list: the first item and every following item of the same shape (the same number of
 * dots), so "Tablas 3.2 y 3.3" is one identifier and the "7.5 million" after "paras 114 to 118 and" is not part of it. A single
 * whole number ("línea 237", "Annex 3") is not marked: only a dotted number can be read as a decimal, so it has nothing to be
 * read as an identifier for. */
function listEnd(list: string): number | null {
  const items = [...list.matchAll(ITEM_RE)];
  const shape = dots(items[0][0]);
  let end = items[0].index! + items[0][0].length;
  let count = 1;
  for (const it of items.slice(1)) {
    if (dots(it[0]) !== shape) break;
    end = it.index! + it[0].length;
    count++;
  }
  return shape === 0 && count < 2 ? null : end;
}

/** A text with each reference identifier wrapped in `<span translate="no">`; the text itself when it has none (no extra span),
 * and an empty string for an empty or missing text. */
export function markRefs(text: string | null | undefined, lang: Lang = 'en'): ReactNode {
  if (!text) return '';
  const out: ReactNode[] = [];
  let at = 0;
  for (const m of text.matchAll(new RegExp(RE[lang].source, RE[lang].flags))) {
    const list = m.groups!.list;
    const start = m.index! + m[0].length - list.length;
    if (start < at) continue;
    const length = listEnd(list);
    if (length === null) continue;
    const end = start + length;
    out.push(<Fragment key={`t${start}`}>{text.slice(at, start)}</Fragment>, <span key={start} translate="no">{text.slice(start, end)}</span>);
    at = end;
  }
  if (!out.length) return text;
  out.push(<Fragment key="tail">{text.slice(at)}</Fragment>);
  return out;
}
