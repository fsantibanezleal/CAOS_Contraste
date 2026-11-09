// What the story tests share: the committed artifacts read from disk as the loaders would fetch them, and a server render of
// a view inside the linked-view store. Not a test file itself.
import { readFileSync } from 'node:fs';
import { LinkedViewProvider, useLangStore } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import type { CaseData } from '../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../lib/contract.types';
import type { GovFindings, GovInventory } from '../workbench/governance/model';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;

export const WINDOWS = ['equity-2007-09', 'equity-2020', 'rates-2022', 'fx-2008', 'mixed-2023', 'calm-2004-06'] as const;

export const inventory = (): GovInventory => read<GovInventory>('governance/inventory.json');
export const findings = (): GovFindings => read<GovFindings>('governance/findings.json');

/** The CaseData the workbench would load for a C11 window: the manifest, the window document and the models document. */
export function c11(windowId: string): CaseData {
  return {
    manifest: read<CaseManifest>('manifests/C11.json'),
    variant: read<VariantArtifact>(`C11/${windowId}.json`),
    models: read<ModelsArtifact>('C11/models-ladder.json'),
  };
}

export const setLang = (lang: 'en' | 'es') => {
  // a server render reads the store's initial state, so both are set (as the workbench tests do)
  (useLangStore.getInitialState() as { lang: string }).lang = lang;
  useLangStore.setState({ lang });
};

/** A view rendered on the server inside the linked-view store and a router. */
export const html = (el: ReactElement, initial?: { selectedId?: string; cursor?: number }) =>
  renderToStaticMarkup(
    <MemoryRouter>
      <LinkedViewProvider initial={initial}>{el}</LinkedViewProvider>
    </MemoryRouter>,
  );

/** The visible text of a markup. */
export const textOf = (markup: string) =>
  markup.replace(/<[^>]*>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
