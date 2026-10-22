// What the Spanish-view tests of C08 to C13 share (U16-R2): reading a committed document, and the text a reader sees. Not a test file.
import { readFileSync } from 'node:fs';
import type { ReactElement } from 'react';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { fixtureData, html } from '../c03/u6-testkit';

/** A committed document of a case (`data/derived/<case>/<rel>`), the 1.0 bake the capture review read. */
export const committed = <T,>(caseId: string, rel: string): T => JSON.parse(readFileSync(new URL(`../../../../data/derived/${caseId}/${rel}`, import.meta.url), 'utf8')) as T;

/** The CaseData of a committed variant and its models document. */
export function committedData(caseId: string, variantFile: string, modelsFile: string, title: { en: string; es: string }) {
  return fixtureData(caseId, committed<VariantArtifact>(caseId, variantFile), committed<ModelsArtifact>(caseId, modelsFile), title);
}

/** The text a reader sees: the markup without its tags and attributes. */
export const view = (el: ReactElement) => html(el).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');
