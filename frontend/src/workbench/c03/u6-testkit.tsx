// What the three U6 consumer tests share (C03, C08 and C09): reading a contract fixture, building the CaseData the
// workbench opens from it, rendering a view on the server, and finding the lane of every card. Not a test file itself.
import { readFileSync } from 'node:fs';
import { useLangStore } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';

export function readFixture<T>(dir: 'c03' | 'c08' | 'c09', rel: string): T {
  return JSON.parse(readFileSync(new URL(rel, new URL(`../../../../docs/contracts/fixtures/${dir}/`, import.meta.url)), 'utf8')) as T;
}

export const html = (el: ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);

/** The CaseData of a fixture pair, with a manifest that names the one variant. */
export function fixtureData(caseId: string, variant: VariantArtifact, models: ModelsArtifact, title: { en: string; es: string }): CaseData {
  const manifest = {
    schema: 'contraste.manifest/v1',
    case_id: caseId,
    title,
    category: { en: 'Fixture', es: 'Ejemplo' },
    question: { en: 'A question', es: 'Una pregunta' },
    sources: [],
    source_details: {},
    seed: 0,
    engine: { pipeline: 'fixture', riskvalidation: 'fixture' },
    default_variant: variant.variant_id,
    artifacts: [{ role: 'variant', variant_id: variant.variant_id, path: `${caseId}/fixture.json`, models_ref: `${caseId}/models.json`, truth_status: variant.provenance.truth_status, title: { en: 'The fixture variant', es: 'La variante de ejemplo' }, short_title: { en: 'Fixture', es: 'Ejemplo' } }],
    contract: {},
    expect: {},
  } as unknown as CaseManifest;
  return { manifest, variant, models };
}

/** The cards of a markup and whether each names its lane. */
export function cards(markup: string): Array<{ lane: boolean }> {
  return markup
    .split('class="caos-plot-head"')
    .slice(1)
    .map((rest) => ({ lane: /data-lane="(live|replay|offline)"/.test(rest.slice(0, rest.indexOf('</figcaption>'))) }));
}

export const setLang = (lang: 'en' | 'es') => {
  (useLangStore.getInitialState() as { lang: string }).lang = lang;
  useLangStore.setState({ lang });
};

export const escapeHtml = (t: string) => t.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#x27;');

/** A money amount written out in full, eight digits or more with separators: no rail may print one. */
export const RAW_AMOUNT = /\d{1,3}(?:[,. ]\d{3}){2,}/;
