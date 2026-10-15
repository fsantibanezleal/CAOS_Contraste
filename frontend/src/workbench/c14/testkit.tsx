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
