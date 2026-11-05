// U16-F12e (fix round 5, the fourth capture review R4, batches c26 and c27: the minors of C22 in these files), on the committed
// documents in both languages: the cited-rates chart has no padding rows, the detection matrix tells a false alarm from a power in
// text and says "a stronger colour" (true in both themes), the ladder label nests no parenthesis, a code identifier breaks only at
// its separators, and the Context names n with its subscript and states the ECB condition its numbers show.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { COMMITTED } from '../../lib/policy';
import { render, textOf } from '../c03/u16f2-kit';
import { START } from './instrument';
import type { C22Sel } from './selection';
import { GeneratorsView, HEAT_NOTE, PowerView, citedAxis, codeBreaks, heatText } from './Views';

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C22.json');
const selOf = (id: string): C22Sel => {
  const entry = manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === id)!;
  const data: CaseData = { manifest, variant: read<VariantArtifact>(entry.path), models: read<ModelsArtifact>(entry.models_ref as string) };
  return { data, alphas: COMMITTED, level: 0.05, portfolio: { ...START } };
};
const NESTED = /\([^()]*\([^()]*\)\)/;

describe('U16-F12e C22', () => {
  it('c27 n1: the cited-rates axis holds the cited rates only, its half steps as the range', () => {
    expect(citedAxis(28)).toEqual({ values: Array.from({ length: 28 }, (_, i) => i + 1), range: [0.5, 28.5] });
  });

  it('c26 n1, c27 n3: the matrix note says a stronger colour, and a false alarm or a size is marked in text, not by hue only', () => {
    expect(HEAT_NOTE.en).not.toMatch(/Darker/);
    expect(HEAT_NOTE.es).not.toMatch(/Más oscuro/);
    expect(HEAT_NOTE.en).toMatch(/A stronger colour: a higher rate/);
    expect(HEAT_NOTE.es).toMatch(/Color más intenso: una tasa mayor/);
    expect(heatText({ rate: 0.049, kind: 'size' }, 'en')).toBe('4.9 %†');
    expect(heatText({ rate: 1, kind: 'power' }, 'es')).toBe('100,0 %');
  });

  it('c27 m13: the ladder label of the generators and power notes nests no parenthesis', () => {
    for (const id of ['other-families', 'null', 'miscalibration']) {
      for (const lang of ['en', 'es'] as const) {
        // the notes (the row labels of the committed documents take the producer's fix at the re-bake: tests/test_c22_u16_f12e.py)
        for (const View of [GeneratorsView, PowerView]) {
          const note = /<p class="caos-plot-note">[\s\S]*?<\/p>/.exec(render(<View sel={selOf(id)} />, lang))?.[0] ?? '';
          expect(textOf(note), `${id} ${lang}`).not.toMatch(NESTED);
        }
      }
    }
  });

  it('c27 n5: a code identifier of the generators appendix breaks only after its separators', () => {
    expect(render(<>{codeBreaks('ccr.pfe_exceedance_backtest-null')}</>, 'en')).toBe('ccr.<wbr/>pfe_<wbr/>exceedance_<wbr/>backtest-<wbr/>null');
    expect(render(<GeneratorsView sel={selOf('other-families')} />, 'en')).toContain('<wbr/>');
  });

  it('c27 m6, n2: the Context writes n with its subscript and the ECB condition as its numbers show it', () => {
    const page = readFileSync(new URL('../../content/cases/C22.tsx', import.meta.url), 'utf8');
    expect(page).not.toMatch(/over n_sim repetitions|en n_sim repeticiones/);
    expect(page).not.toContain('When it was estimated on a sample less than half the size of the current one the test over-rejects');
    expect(page).toContain("When it was estimated, the test over-rejects: about one time in six at C01's slice sizes (a development sample under half the size of the current one), about one in nine at equal sizes.");
  });
});
