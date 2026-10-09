// The C04 layouts of a screen under 1100 px tall (1280 x 800): where two cards share a column or a row only on a tall
// screen, a short one gives the first card the room (at 1280 x 800 the second card left the first a plot of 10 to 30 px
// or a table of one row). The server-rendered tests elsewhere render the tall layout, the hook's server default.
import { readFileSync } from 'node:fs';
import { pick, useLangStore } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { DefinitionsView } from './AgencyValidationViews';
import { C04FindingsView } from './C04Common';
import { DriftView } from './LiveViews';
import { ESMA_DEFINITIONS, makeSel } from './selection';

vi.mock('../../lib/useMedia', () => ({ useMedia: () => false, useFindingsShares: () => [2, 1] }));

type Lang = 'en' | 'es';
const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C04.json');
function dataOf(id: string): CaseData {
  const a = manifest.artifacts.find((x) => x.role === 'variant' && x.variant_id === id);
  if (!a) throw new Error(`no variant ${id}`);
  return { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) };
}
const langState = useLangStore.getInitialState() as { lang: Lang };
function html(el: ReactElement, lang: Lang = 'en'): string {
  const before = langState.lang;
  langState.lang = lang;
  try {
    return renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
  } finally {
    langState.lang = before;
  }
}
const unesc = (s: string) => s.replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&amp;/g, '&');
const titles = (markup: string) => [...markup.matchAll(/<figure class="caos-plot[^"]*" data-plot="([^"]*)"/g)].map((m) => unesc(m[1]));
const notes = (markup: string) => [...markup.matchAll(/<p class="caos-plot-note">([\s\S]*?)<\/p>/g)].map((m) => unesc(m[1]));

describe('C04 on a short screen', () => {
  it("Drift: the agency's projection alone in its row over the table; the mix and the table without ESMA's statement", () => {
    for (const lang of ['en', 'es'] as const) {
      const m = html(<DriftView sel={makeSel(dataOf('sp'))} />, lang);
      expect(m).toContain('<div class="caos-views-row" data-views="1">');
      const t = titles(m);
      expect(t, lang).toHaveLength(2);
      expect(t[0]).toMatch(lang === 'en' ? /^Projected default rate/ : /^Tasa proyectada/);
      const n = notes(m);
      expect(n[0]).toContain(pick(ESMA_DEFINITIONS, lang));
      expect(n[1]).not.toContain(pick(ESMA_DEFINITIONS, lang));
      expect(n[1]).toContain('Source: ESMA CEREP; tables transformed by Contraste');
    }
    // Moody's has no default column: the mix is its view, and it keeps the statement
    const moodys = html(<DriftView sel={makeSel(dataOf('moodys'))} />);
    expect(titles(moodys)[0]).toBe("The portfolio's mix by grade");
    expect(notes(moodys)[0]).toContain(pick(ESMA_DEFINITIONS, 'en'));
  });

  it('Definitions: the definitions alone beside the chart, and the chart points to By year for the cohorts', () => {
    const m = html(<DefinitionsView sel={makeSel(dataOf('sp'))} />);
    expect(m).not.toContain('data-table="tab2-cohorts"');
    expect(titles(m)).toHaveLength(2);
    expect(notes(m)[0]).toContain("the By year view gives each cohort's two counts");
    expect(notes(m)[0]).not.toContain('the cohorts beside');
    const es = html(<DefinitionsView sel={makeSel(dataOf('sp'))} />, 'es');
    expect(notes(es)[0]).toContain('la vista Por año da los dos conteos de cada cohorte');
  });

  it("Findings: the papers' short table beside its drawing, not over it", () => {
    const m = html(<C04FindingsView sel={makeSel(dataOf('published'))} />);
    expect(m).toMatch(/<div class="caos-views-row" data-views="2"><div class="caos-views-col" data-share="2"/);
    expect(m).toContain('data-series=');
  });
});
