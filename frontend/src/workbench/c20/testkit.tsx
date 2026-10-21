// What the U14 consumer tests share (C02, C20 and C21): reading a contract fixture of docs/contracts/fixtures/c02, c20 or
// c21, on top of the U6 test kit (rendering a view on the server, the CaseData a fixture pair opens as, the lane of
// every card). Not a test file itself.
import { readFileSync } from 'node:fs';
import type { Bi } from '../c03/U6Shared';

export { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, setLang } from '../c03/u6-testkit';

export function readU14Fixture<T>(dir: 'c02' | 'c20' | 'c21', rel: string): T {
  return JSON.parse(readFileSync(new URL(rel, new URL(`../../../../docs/contracts/fixtures/${dir}/`, import.meta.url)), 'utf8')) as T;
}

/** The text of a bilingual label in one language. */
export const en = (t: Bi) => t.en;

/** The numbers a markup prints, as the tests read them: digits with an optional decimal part in either notation. */
export const printed = (markup: string): string[] => [...markup.replace(/<[^>]*>/g, ' ').matchAll(/\d+(?:[.,]\d+)?/g)].map((m) => m[0]);
