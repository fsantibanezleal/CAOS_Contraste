// U16-F9a: the shared Findings card prints every evidence key in words. Rendered over every committed variant document of every
// case, in both languages, it shows no raw key: no `test@model`, no `design:`, `rate:` or `contract:` prefix, and no test id the
// key cites (R2b: c01 B1, c03 B3, c12 B1, c14 B2, c15 B2, c16 B1, c17 B1 and c18 B-1 read raw keys in this card).
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';
import type { VariantArtifact } from '../../lib/contract.types';
import { setLang } from '../c03/u6-testkit';
import { FindingsCard } from '../c06/C06Common';

const derived = fileURLToPath(new URL('../../../../data/derived/', import.meta.url));
const variants: Array<{ file: string; v: VariantArtifact }> = readdirSync(derived)
  .filter((d) => /^C\d\d$/.test(d))
  .flatMap((c) =>
    readdirSync(derived + c)
      .filter((f) => f.endsWith('.json') && !f.startsWith('models'))
      .map((f) => ({ file: `${c}/${f}`, v: JSON.parse(readFileSync(`${derived}${c}/${f}`, 'utf8')) as VariantArtifact })),
  )
  .filter(({ v }) => Array.isArray(v.findings) && v.findings.some((f) => f.evidence.length > 0));
const plain = (markup: string) => markup.replace(/<[^>]*>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
afterEach(() => setLang('en'));

describe('the Findings card names every evidence key', () => {
  it('reads the variant documents of every case', () => {
    expect(new Set(variants.map((x) => x.file.slice(0, 3))).size).toBeGreaterThanOrEqual(20);
  });
  for (const lang of ['en', 'es'] as const) {
    it(`prints no raw key in ${lang}`, () => {
      setLang(lang);
      const bad: string[] = [];
      for (const { file, v } of variants) {
        // the evidence lists only: the titles are the producers' (a title that cites a test id is a per-case row, U16-F9b to F9d)
        const markup = renderToStaticMarkup(<MemoryRouter><FindingsCard variant={v} /></MemoryRouter>);
        const evidence = plain([...markup.matchAll(/<ul class="ct-evidence">(.*?)<\/ul>/g)].map((m) => m[1]).join(' '));
        if (!evidence.trim()) bad.push(`${file}: no evidence list rendered`);
        const ids = v.findings.flatMap((f) => f.evidence.map((e) => e.replace(/^(rate|design|contract):/, '').split('@')[0]));
        const leak = /\b[a-z0-9_]+\.[a-z0-9_]+@|\bdesign:|\brate:|\bcontract:/.exec(evidence)?.[0] ?? ids.find((id) => /[._]/.test(id) && evidence.includes(` ${id}`));
        if (leak) bad.push(`${file}: ${leak}`);
      }
      expect(bad.slice(0, 20)).toEqual([]);
    });
  }
});
