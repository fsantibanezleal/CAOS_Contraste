// The C04 rail at 1280 x 800 in Spanish (ADR-0071 rule 6, gate G5/ADR-0071.6): the Retiros definition chip is one short label,
// and the starting portfolio of the Projection section is one select, so neither section scrolls the rail.
import { readFileSync } from 'node:fs';
import { useLangStore } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { useInstrument } from './instrument';

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C04.json');
const a = manifest.artifacts.find((x) => x.role === 'variant' && x.variant_id === 'sp');
if (!a) throw new Error('no S&P variant');
const data: CaseData = { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) };
const langState = useLangStore.getInitialState() as { lang: 'en' | 'es' };

function Section({ id }: { id: string }) {
  const inst = useInstrument(data, () => undefined);
  const s = inst?.rail.find((r) => r.id === id);
  return <div>{s ? s.content : null}</div>;
}
const rail = (id: string, lang: 'en' | 'es') => {
  const before = langState.lang;
  langState.lang = lang;
  try {
    return renderToStaticMarkup(<MemoryRouter><Section id={id} /></MemoryRouter>);
  } finally {
    langState.lang = before;
  }
};

describe('the C04 rail fits 1280 x 800', () => {
  it('names the definition that keeps withdrawals with a short chip in Spanish and keeps the English word', () => {
    const es = rail('grade', 'es');
    expect(es).toMatch(/<button[^>]*>Con W<\/button>/);
    expect(es).not.toContain('>Con retiros<');
    expect(rail('grade', 'en')).toMatch(/<button[^>]*>Keep<\/button>/);
  });

  it('gives the four starting portfolios as one select, each option reachable', () => {
    for (const lang of ['en', 'es'] as const) {
      const m = rail('projection', lang);
      expect(m).toMatch(/data-control="c04-start"[^>]*><label[^>]*>[^<]+<\/label><select/);
      expect(m.match(/<option/g)?.length, lang).toBe(4);
    }
  });
});
