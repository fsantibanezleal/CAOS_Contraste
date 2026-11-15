// The Introduction's technical view and the README name the concept DOI of every publication product.json declares (CAOS_MANAGE GUIDE
// R-C4; found missing by the GUIDE walk of 2026-11-14), with its current title, and never an internal claim id (R-B6).
import { readFileSync } from 'node:fs';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it } from 'vitest';
import product from '../../../product.json';
import { CITATIONS } from '../content/citations';
import { html, setLang } from '../workbench/c03/u6-testkit';
import { PUBLICATIONS, Publications } from './Publications';

const escape = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const markup = (lang: 'en' | 'es') => {
  setLang(lang);
  return html(
    <CitationsProvider items={CITATIONS}>
      <Publications />
    </CitationsProvider>,
  );
};

describe('the publications', () => {
  afterEach(() => setLang('en'));

  it('lists every manuscripts entry of product.json, the technical report first, each linked by its concept DOI with its title', () => {
    expect(PUBLICATIONS).toHaveLength(product.manuscripts.length);
    expect(PUBLICATIONS[0].kind).toBe('technical-report');
    for (const lang of ['en', 'es'] as const) {
      const m = markup(lang);
      for (const p of product.manuscripts) {
        expect(m, `${lang} ${p.concept_doi}`).toContain(`href="https://doi.org/${p.concept_doi}"`);
        expect(m, `${lang} ${p.concept_doi}`).toContain(escape(p.title));
      }
      expect(m).toContain(lang === 'es' ? 'Informe técnico' : 'Technical report');
    }
  });

  it('marks each title as English and not to be translated, and shows no internal claim id', () => {
    for (const lang of ['en', 'es'] as const) {
      const m = markup(lang);
      expect((m.match(/<span lang="en" translate="no">/g) ?? []).length).toBe(product.manuscripts.length);
      expect(m).not.toMatch(/\bBS-\d+/);
    }
  });

  it('the README names the same concept DOIs with the same titles', () => {
    const readme = readFileSync(new URL('../../../README.md', import.meta.url), 'utf8');
    for (const p of product.manuscripts) {
      expect(readme, p.concept_doi).toContain(`[${p.title}](https://doi.org/${p.concept_doi})`);
    }
  });
});
