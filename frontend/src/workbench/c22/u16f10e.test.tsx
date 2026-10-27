// U16-F10e (fix round 4, the third capture review R3, batch c22), on the committed documents in both languages: the One report
// note gives the severity the data were drawn at (the rung, not its index), a descriptive metric is not printed as a p-value, the
// Spanish Context glosses the licences and the source descriptions in Spanish with the original marked, the leakage designs table keeps
// its rate column, the small multiples keep a floor for their plot, and the minors (no -0, no floating-point noise, a 1.5 % step axis).
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { COMMITTED } from '../../lib/policy';
import { render, textOf } from '../c03/u16f2-kit';
import { START } from './instrument';
import type { C22Sel } from './selection';
import { C22ContextView, GeneratorsView, PValuesView, PowerView, SpecimenView } from './Views';

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C22.json');
const selOf = (id: string): C22Sel => {
  const entry = manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === id)!;
  const data: CaseData = { manifest, variant: read<VariantArtifact>(entry.path), models: read<ModelsArtifact>(entry.models_ref as string) };
  return { data, alphas: COMMITTED, level: 0.05, portfolio: { ...START } };
};
const LADDERED = ['miscalibration', 'clustering', 'drift', 'discrimination-decay', 'leakage', 'broken-monotonicity', 'concentration'];

describe('U16-F10e C22', () => {
  it('c22 B2 and m14: the One report gives the rung the data were drawn at, and "under its null" for the null family', () => {
    for (const id of LADDERED) {
      const sel = selOf(id);
      const o = sel.data.variant.outputs as unknown as { specimen: { severity: number }; ladder: { values: number[]; label: { en: string } } };
      const value = o.ladder.values[o.specimen.severity];
      const en = textOf(render(<SpecimenView sel={sel} />, 'en'));
      expect(en, id).not.toMatch(/drawn at severity \d/);
      expect(en, id).toContain(`drawn at ${new Intl.NumberFormat('en-US', { maximumSignificantDigits: 4 }).format(value)} (${o.ladder.label.en})`);
    }
    const nul = textOf(render(<SpecimenView sel={selOf('null')} />, 'en'));
    expect(nul).not.toMatch(/severity 0/);
    expect(nul).toMatch(/under its null/);
  });

  it('c22 B3: a test with no p-value shows none in the p-value column', () => {
    for (const id of ['discrimination-decay', 'broken-monotonicity']) {
      const sel = selOf(id);
      const html = render(<SpecimenView sel={sel} />, 'en');
      const cells = html.match(/<td data-na="true" data-p="none">-<\/td>/g) ?? [];
      const nulls = sel.data.variant.tests.filter((t) => t.p_value === null).length;
      expect(nulls, id).toBeGreaterThan(0);
      expect(cells.length, id).toBe(nulls);
    }
  });

  it('c22 B4: the Spanish Context glosses the licences and the source descriptions, the English originals marked', () => {
    const html = render(<C22ContextView sel={selOf('null')} />, 'es');
    expect(html).toContain('Todos los derechos reservados');
    expect(html).toContain('tablas 5 a 8 (la simulación de las pruebas normal y de semáforos)');
    expect(html).toContain('original en inglés');
    const text = textOf(html.replace(/<span[^>]*lang="en"[\s\S]*?<\/span>/g, ' '));
    expect(text).not.toMatch(/All rights reserved|Tables 5 to 8|the rejection rates/);
  });

  it('c22 M2: the leakage designs table puts the scenario under the design, so its rate column fits', () => {
    const html = render(<PowerView sel={selOf('leakage')} />, 'en');
    const table = /<table[^>]*data-table="designs"[\s\S]*?<\/table>/.exec(html)![0];
    expect(table).not.toMatch(/<th[^>]*>Scenario<\/th>/);
    expect(table).toMatch(/class="ct-row-detail"/);
  });

  it('c22 M1: every small multiple keeps a floor for its plot under its key', () => {
    for (const [id, View] of [['other-families', PowerView], ['null', PValuesView]] as const) {
      const html = render(<View sel={selOf(id)} />, 'en');
      const panels = [...html.matchAll(/class="ct-small-multiple"[^>]*>/g)].map((m) => m[0]);
      expect(panels.length, id).toBeGreaterThan(0);
      expect(html, id).toMatch(/data-plot-floor="10rem"/);
    }
  });

  it('m2 and m3: no -0 and no floating-point noise in the generator configurations', () => {
    for (const id of ['miscalibration', 'null']) {
      const text = textOf(render(<GeneratorsView sel={selOf(id)} />, 'en'));
      expect(text, id).not.toMatch(/(^|\s)-0(\s|$)/);
      expect(text, id).not.toMatch(/E-1[2-9]/);
    }
  });
});
