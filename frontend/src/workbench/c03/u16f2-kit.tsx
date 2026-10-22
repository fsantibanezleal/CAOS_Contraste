// What the U16-F2 tests of C03 to C07 share: the committed documents of a case as the workbench opens them (the real bake, not a
// fixture), the markup of a view in a language, and the words an English sentence is made of. Not a test file itself.
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { setLang } from './u6-testkit';

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;

export type Lang = 'en' | 'es';

/** The manifest of a case as committed. */
export const manifestOf = (caseId: string): CaseManifest => read<CaseManifest>(`manifests/${caseId}.json`);

/** The CaseData of one committed variant (the default one when none is named), with its models artifact. */
export function committedData(caseId: string, variantId?: string): CaseData {
  const manifest = manifestOf(caseId);
  const entry = manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === (variantId ?? manifest.default_variant));
  if (!entry) throw new Error(`${caseId}: no variant ${variantId}`);
  return { manifest, variant: read<VariantArtifact>(entry.path), models: read<ModelsArtifact>(entry.models_ref as string) };
}

/** The ids of the variants of a case, in the manifest's order. */
export const variantIds = (caseId: string): string[] => manifestOf(caseId).artifacts.filter((a) => a.role === 'variant').map((a) => a.variant_id);

/** The markup of a view in a language (the shell's language store is global: the caller resets it). */
export function render(el: ReactElement, lang: Lang): string {
  setLang(lang);
  return renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
}

/** The text of a markup: tags dropped, entities of the markup decoded, blanks collapsed. */
export const textOf = (markup: string): string =>
  markup.replace(/<[^>]*>/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, ' ');

/** An English number form inside Spanish text: a thousands comma ('413,083') or a decimal point after a zero ('0.0694'; a Spanish thousands dot, '330.682', is not one). */
export const ENGLISH_NUMBER = /\d,\d{3}\b|\b0\.\d{2,}\b/;
