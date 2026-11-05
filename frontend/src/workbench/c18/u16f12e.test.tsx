// U16-F12e (fix round 5, the fourth capture review R4, batches c22 and c23), on the committed documents in both languages: the
// Annex 3 bars carry no raw cell status, the Spanish test references carry no English annotation, the internal-target formula
// writes its layers as symbols with subscripts beside the layer table that names them, no reader text names a code function, the
// reverse-stress row of the Variants table prints the headline capital its document carries, the upper stack drawing keeps a
// floor for its axis title, the back-cast marks the peaks its test judges, and the small, local minors of the two batches.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { C18ContextView, C18TestsView, C18VariantsTable, cell } from './C18Common';
import { Annex3View, FanView, StackView, annex3Bars } from './CapitalViews';
import { BandView, SensitivityView, sensitivitySeries } from './AggregationViews';
import { BackcastView, backcastMarks, lossesOverlap, severityBars } from './StressViews';
import { MarginalsView } from './AggregationViews';
import { phraseEs } from './localise';
import { defaultSel, methodShort, outputsOf, type C18Sel } from './selection';

const SCENARIOS = ['baseline', 'eba-2025-adverse', 'fed-2026-severely-adverse', 'ngfs-delayed-transition'] as const;
const ALL = [...SCENARIOS, 't-copula-baseline', 'reverse-stress'] as const;
const models = committedDoc<ModelsArtifact>('C18', 'models-banco-andino');
const title = { en: 'ICAAP and IAPE capital aggregation under macro scenarios', es: 'Agregación de capital ICAAP e IAPE bajo escenarios macro' };
const selOf = (name: string): C18Sel => defaultSel(fixtureData('C18', committedDoc<VariantArtifact>('C18', name), models, title)) as C18Sel;
const LANGS = ['en', 'es'] as const;

describe('U16-F12e C18', () => {
  afterEach(() => setLang('en'));

  it('c22 B1: the Annex 3 bars carry no raw cell status ("value") as their note', () => {
    for (const name of SCENARIOS) {
      // the bars are drawn in the browser: their data is the function the view draws
      const { data } = annex3Bars(outputsOf(selOf(name))!.annex3);
      expect(data.length, name).toBeGreaterThan(0);
      for (const b of data) expect((b as { hint?: unknown }).hint, `${name} ${b.id}`).toBeUndefined();
    }
  });

  it('c22 B2: the Spanish test references carry no English annotation "(full allocation)"', () => {
    for (const name of SCENARIOS) {
      const es = textOf(render(<C18TestsView sel={selOf(name)} />, 'es'));
      expect(es, name).not.toContain('(full allocation)');
      if (/Capital allocation to business units/.test(es)) expect(es, name).toContain('(asignación completa)');
    }
  });

  it('c22 B3: the internal-target formula and the P2G statement write the layers as symbols with subscripts, never as data keys', () => {
    for (const name of SCENARIOS) {
      for (const lang of LANGS) {
        const html = render(<StackView sel={selOf(name)} />, lang);
        expect(textOf(html), `${name} ${lang}`).not.toMatch(/\bc_(?:DSIB|P2|CCoB|CCyB|d)\b/);
        expect(html, `${name} ${lang}`).toContain('c<sub>DSIB</sub>');
        expect(html, `${name} ${lang}`).toContain('c<sub>d</sub>');
        expect(textOf(html), `${name} ${lang}`).not.toContain('>=');
        // the layer table is the legend: each layer row names its symbol
        const table = /<table[^>]*data-table="c18-stack"[\s\S]*?<\/table>/.exec(html)![0];
        for (const s of ['DSIB', 'P2', 'CCoB', 'CCyB', 'd']) expect(table, `${name} ${lang} ${s}`).toContain(`c<sub>${s}</sub>`);
      }
    }
  });

  it('c22 B4 and c23 B2: no Context names a code function; the rule reads "linear interpolation", the Spanish with a decimal comma', () => {
    for (const name of ALL) {
      const en = textOf(render(<C18ContextView sel={selOf(name)} />, 'en'));
      const es = textOf(render(<C18ContextView sel={selOf(name)} />, 'es'));
      expect(en + es, name).not.toContain('np.interp');
      if (/Hazen/.test(en)) {
        expect(en, name).toContain('linear interpolation on the Hazen positions');
        expect(es, name).toContain('interpolación lineal sobre las posiciones de Hazen');
        expect(es, name).toContain('0,5');
        expect(es, name).not.toMatch(/\(i - 0\.5\)/);
      }
    }
  });

  it('c22 M2: the reverse-stress row of the Variants table prints the headline capital its document carries', () => {
    const rev = committedDoc<VariantArtifact>('C18', 'reverse-stress');
    const value = (rev.impact as unknown as { capital_simple_sum: { value: number } }).capital_simple_sum.value;
    for (const lang of LANGS) {
      const html = render(<C18VariantsTable variants={[]} aggregation={null} reverse={rev as never} onPick={() => {}} current="baseline" />, lang);
      const row = textOf(/<tr[^>]*data-variant="reverse-stress"[\s\S]*?<\/tr>/.exec(html)![0]);
      expect(row, lang).toContain(cell(value, lang));
      expect(row, lang).not.toMatch(/does not compute it|no lo calcula/);
    }
  });

  it('c23 M1: the upper stack drawing has a floor for its bars, its axis title and the read-out hint', () => {
    const html = render(<StackView sel={selOf('ngfs-delayed-transition')} />, 'en');
    const box = /<div data-box="oi-stack" data-plot-floor="([\d.]+rem)" style="([^"]*)"/.exec(html);
    expect(box).not.toBeNull();
    // layout.ts reads the floor from a plain rem length (a calc() counts as none), so the attribute and the min-height agree
    expect(box![2]).toContain(`min-height:${box![1]}`);
  });

  it('c23 M3: the back-cast chart marks the predicted and realised peaks its red test judges, with their values', () => {
    for (const name of SCENARIOS) {
      const o = outputsOf(selOf(name))!;
      for (const bc of o.backcast.per_loan_type) {
        const marks = backcastMarks(bc);
        expect(marks.length, `${name} ${bc.fed_loan_type}`).toBeGreaterThanOrEqual(1);
        const labels = marks.map((m) => (m.label as { en: string }).en).join(' | ');
        expect(labels).toContain('Predicted peak');
        expect(labels).toContain('Realised peak');
        const at = (q: string) => bc.quarters.findIndex((x) => x.quarter_end === q) + 1;
        expect(marks.map((m) => m.x)).toContain(at(bc.metrics.peak_predicted_quarter));
        expect(marks.map((m) => m.x)).toContain(at(bc.metrics.peak_realised_quarter));
      }
    }
  });

  it('c23 m7: the back-cast note writes its fitted window in quarters, never in ISO dates', () => {
    for (const lang of LANGS) {
      const html = render(<BackcastView sel={selOf('fed-2026-severely-adverse')} />, lang);
      const note = textOf(/<p class="caos-plot-note">[\s\S]*?<\/p>/.exec(html)![0]);
      expect(note, lang).not.toMatch(/\d{4}-\d{2}-\d{2}/);
    }
  });

  it('c22 m6: a severity bar carries no note that repeats its label', () => {
    const o = outputsOf(selOf('fed-2026-severely-adverse'))!;
    for (const b of severityBars(o)) if (b.hint) expect(b.hint).not.toEqual(b.label);
  });

  it('c22 m8, c23 m8: the band card says "only the simple sum is the capital" and "Information, not capital" once each; the headline ends as a sentence', () => {
    for (const lang of LANGS) {
      const text = textOf(render(<BandView sel={selOf('t-copula-baseline')} />, lang));
      expect(text.split(lang === 'en' ? /only the simple sum is the capital of this case/i : /solo la suma simple es el capital de este caso/i).length - 1, lang).toBe(1);
      expect(text.split(lang === 'en' ? 'Information, not capital' : 'Información, no capital').length - 1, lang).toBeLessThanOrEqual(1);
      expect(text, lang).toMatch(lang === 'en' ? /in the SREP\./ : /en el SREP\./);
    }
  });

  it('c22 m3: the t copula is written with its symbol and the reweighting parameter as theta', () => {
    expect(methodShort({ method: 't-copula', nu: 4 })).toEqual({ en: 't copula, ν 4', es: 'Cópula t, ν 4' });
    for (const lang of LANGS) expect(textOf(render(<BandView sel={selOf('t-copula-baseline')} />, lang)), lang).not.toMatch(/\btheta\b|\bnu \d/);
  });

  it('c22 m11, c23 m9: the references write Rüschendorf with its umlaut, in both languages', () => {
    const ref = '(VaR is not subadditive; worst-case VaR bounds by the rearrangement algorithm of Embrechts, Puccetti and Ruschendorf 2013,';
    expect(phraseEs(ref, 'en')).toContain('Rüschendorf');
    expect(phraseEs(ref, 'es')).toContain('Puccetti y Rüschendorf');
    for (const lang of LANGS) expect(textOf(render(<C18TestsView sel={selOf('t-copula-baseline')} />, lang)), lang).not.toContain('Ruschendorf');
  });

  it('c23 m2: the copula sensitivity draws its three degrees of freedom as points, never a line between them', () => {
    const series = sensitivitySeries([{ gaussian_capital_clp_m: 1, t_capital_clp_m: 2 }], 1);
    expect(series.map((s) => s.mode)).toEqual(['points', 'points']);
    expect(render(<SensitivityView sel={selOf('t-copula-baseline')} />, 'en')).toContain('data-table="c18-copula-sensitivity"');
  });

  it('c23 m3: the reverse-stress Context says why the aggregation facts are not available', () => {
    for (const lang of LANGS) {
      const text = textOf(render(<C18ContextView sel={selOf('reverse-stress')} />, lang));
      expect(text, lang).toMatch(lang === 'en' ? /not available: the reverse stress runs no aggregation/ : /no disponible: la tensión inversa no corre una agregación/);
    }
  });

  it('c23 m10: the captions write the consolidation and the ratio unit in words', () => {
    expect(textOf(render(<Annex3View sel={selOf('baseline')} />, 'en'))).toContain('local (solo) consolidation');
    const en = textOf(render(<C18ContextView sel={selOf('baseline')} />, 'en'));
    expect(en).toContain('ratios as decimals');
    expect(en).not.toMatch(/CLP millions; decimal\b/);
  });

  it('c23 m12, m13: the adaptation row and the P2G status do not repeat their label', () => {
    for (const lang of LANGS) {
      const ctx = textOf(render(<C18ContextView sel={selOf('fed-2026-severely-adverse')} />, lang));
      expect(ctx, lang).not.toMatch(lang === 'en' ? /US-calibrated adaptation\. US-calibrated adaptation/ : /Adaptación calibrada en EE\. UU\.\s*Adaptación calibrada en EE\. UU\./);
      const stack = textOf(render(<StackView sel={selOf('fed-2026-severely-adverse')} />, lang));
      expect(stack, lang).not.toMatch(lang === 'en' ? /Contraste approximation\. A Contraste approximation/ : /Aproximación de Contraste\. Una aproximación de Contraste/);
    }
  });

  it('c22 m5: the Variants note names the reverse variant as the rail does', () => {
    const rev = committedDoc<VariantArtifact>('C18', 'reverse-stress');
    const es = textOf(render(<C18VariantsTable variants={[]} aggregation={null} reverse={rev as never} onPick={() => {}} current="baseline" />, 'es'));
    expect(es).not.toContain('En el estrés inverso');
  });

  it('c22 m9, c23 m6: the losses note says which lines lie on each other, from the committed rows', () => {
    for (const name of SCENARIOS) {
      const rows = outputsOf(selOf(name))!.losses.scenario_losses;
      const note = lossesOverlap(rows);
      const zero = (['market', 'irrbb', 'operational'] as const).filter((k) => rows.every((r) => r[k] === 0));
      if (zero.length > 1) expect(note?.en, name).toMatch(/are zero in every year/);
      if (note) expect(note.es, name).not.toMatch(/\b(?:the|and|line)\b/);
    }
    expect(lossesOverlap([{ credit: 1, market: 1, irrbb: 1, operational: 1, total: 4 }])).toBeNull();
  });

  it('c23 m5: every money column of the marginals table carries its unit', () => {
    for (const lang of LANGS) {
      const html = render(<MarginalsView sel={selOf('t-copula-baseline')} />, lang);
      const head = textOf(/<table[^>]*data-table="c18-marginals"[\s\S]*?<\/thead>/.exec(html)![0]);
      expect(head.split(lang === 'en' ? 'CLP millions' : 'millones de CLP').length - 1, lang).toBe(5);
    }
  });

  it('c22 m12: the mitigation reason after "not available:" starts in lower case', () => {
    for (const lang of LANGS) {
      const text = textOf(render(<FanView sel={selOf('fed-2026-severely-adverse')} />, lang));
      expect(text, lang).not.toMatch(/not available: No |no disponible: No /);
    }
  });
});
