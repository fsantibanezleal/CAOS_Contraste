// What the C14 and C15 consumer tests share: reading a contract fixture of docs/contracts/fixtures/c14 or c15, on top of
// the U6 test kit (rendering a view on the server, the CaseData a fixture pair opens as, the lane of every card). Not a
// test file itself.
import { readFileSync } from 'node:fs';
import type { Bi } from '../c03/U6Shared';

export { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, setLang } from '../c03/u6-testkit';

export function readIrrbbFixture<T>(dir: 'c14' | 'c15', rel: string): T {
  return JSON.parse(readFileSync(new URL(rel, new URL(`../../../../docs/contracts/fixtures/${dir}/`, import.meta.url)), 'utf8')) as T;
}

/** The text of a bilingual label in one language. */
export const en = (t: Bi) => t.en;

// --- the committed documents, for the U16-R2 Spanish checks (c14 to c22 share them) -------------------------------------

/** A committed document of data/derived/<case>/<name>.json. */
export function committedDoc<T = Record<string, any>>(caseId: string, name: string): T {
  return JSON.parse(readFileSync(new URL(`../../../../data/derived/${caseId}/${name}.json`, import.meta.url), 'utf8')) as T;
}

/** The markup without the elements marked lang="en": a quotation the reader finds as the source writes it (nested elements of the same name are matched). */
function withoutEnglishQuotes(markup: string): string {
  let out = '';
  let i = 0;
  const tag = /<(\/?)(\w+)([^>]*)>/g;
  let skip: { name: string; depth: number } | null = null;
  for (let m = tag.exec(markup); m !== null; m = tag.exec(markup)) {
    if (skip === null) {
      out += markup.slice(i, m.index);
      if (m[1] === '' && /lang="en"/.test(m[3]) && !m[3].trimEnd().endsWith('/')) skip = { name: m[2], depth: 1 };
      else out += m[0];
    } else if (m[2] === skip.name) {
      skip.depth += m[1] === '' ? 1 : -1;
      if (skip.depth === 0) { skip = null; out += ' '; }
    }
    i = m.index + m[0].length;
  }
  return skip === null ? out + markup.slice(i) : out;
}

/** The text a reader sees in a server-rendered markup: tags dropped, entities decoded, white space folded. */
export function visibleText(markup: string): string {
  return withoutEnglishQuotes(markup)
    .replace(/<(script|style)[\s\S]*?<\/\1>/g, ' ')
    // a quotation the reader finds in its own language (lang="en") is kept as the source writes it
    .replace(/<(\w+)[^>]*\blang="en"[^>]*>[\s\S]*?<\/\1>/g, ' ')
    .replace(/<[^>]*>/g, ' ')
    .replaceAll('&amp;', '&').replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&quot;', '"').replaceAll('&#x27;', "'")
    .replace(/\s+/g, ' ');
}

/** English function words that no Spanish sentence of the product contains: a hit in a Spanish capture is untranslated prose. */
const ENGLISH_WORDS = /(?<![\p{L}\p{N}_])(the|of|and|with|from|for|are|was|were|not|which|that|this|than|over|under|used|uses|applied|stated|fitted|by|on|is|per|has|have|its|their|these|those|when|each|only|all)(?![\p{L}\p{N}_])/gu;

/** The English words left in a Spanish text once the verbatim citations (strings that a reader must find as they are) are removed, each with its context. */
export function englishLeaks(text: string, verbatim: ReadonlyArray<string | RegExp> = []): string[] {
  let t = text.replace(/https?:\/\/\S+/g, ' ').replace(/[a-z]+(?:-[a-z]+){2,}/g, ' ');
  for (const v of verbatim) t = typeof v === 'string' ? t.split(v).join(' ') : t.replace(v, ' ');
  const found = new Map<string, string>();
  for (const m of t.matchAll(ENGLISH_WORDS)) {
    const at = m.index ?? 0;
    if (!found.has(m[0])) found.set(m[0], `${m[0]}: ...${t.slice(Math.max(0, at - 30), at + 40)}...`);
  }
  return [...found.values()].sort();
}
