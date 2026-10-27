// U16-F10e (fix round 4, the third capture review R3, batch c19), on the committed documents in both languages: the loss-only
// headline table closes row by row (the start of each year, the year's loss and the end), the Spanish views write the P2G and Tier 1
// proxies in Spanish, the lower stack drawing keeps room for its axis title, the NGFS path is drawn in the unit of the level it plots,
// a reverse-stress start that did not converge is drawn with its distance and says so, and the minors of the batch.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { cell } from './C18Common';
import { C18ContextView, C18VariantsTable } from './C18Common';
import { FanView, StackView } from './CapitalViews';
import { MarginalsView, EulerView } from './AggregationViews';
import { PathsView, SeverityView, BackcastView, plottedUnit } from './StressViews';
import { ReverseSolutionView, startBars } from './ReverseViews';
import { defaultSel, outputsOf, type C18Sel } from './selection';
import { variantName } from '../names';

const SCENARIOS = ['baseline', 'eba-2025-adverse', 'fed-2026-severely-adverse', 'ngfs-delayed-transition'] as const;
const models = committedDoc<ModelsArtifact>('C18', 'models-banco-andino');
const title = { en: 'ICAAP and IAPE capital aggregation under macro scenarios', es: 'Agregación de capital ICAAP e IAPE bajo escenarios macro' };
const selOf = (name: string): C18Sel => defaultSel(fixtureData('C18', committedDoc<VariantArtifact>('C18', name), models, title)) as C18Sel;
const tableOf = (_html: string, id: string) => /<table[^>]*data-table="ID"[\s\S]*?<\/table>/.source.replace('ID', id);

describe('U16-F10e C18', () => {
  afterEach(() => setLang('en'));

  it('c19 B1: the loss-only table gives each year its start, its loss and its end, and the row closes', () => {
    for (const name of SCENARIOS) {
      const sel = selOf(name);
      const o = outputsOf(sel)!;
      for (const lang of ['en', 'es'] as const) {
        const html = render(<FanView sel={sel} />, lang);
        const table = new RegExp(tableOf(html, 'c18-headline')).exec(html)![0];
        const text = textOf(table);
        expect(text, `${name} ${lang}`).not.toMatch(/CET1 at the jump-off|CET1 en el punto de partida \(/);
        expect(text, `${name} ${lang}`).toMatch(lang === 'en' ? /CET1 at the start of the year/ : /CET1 al inicio del año/);
        for (const r of o.headline_cet1.rows) {
          const loss = o.losses.scenario_losses.find((x) => x.year === r.year)!.total;
          // the row closes: start less the year's loss is the end of the year
          expect(Math.abs(r.cet1_start_clp_m - loss - r.cet1_clp_m), `${name} ${r.year}`).toBeLessThan(1);
          const row = new RegExp(`<tr[^>]*data-year="${r.year}"[\\s\\S]*?</tr>`).exec(table)![0];
          for (const v of [r.cet1_start_clp_m, loss, r.cumulative_loss_clp_m, r.cet1_clp_m]) expect(textOf(row), `${name} ${lang} ${r.year}`).toContain(cell(v, lang));
        }
      }
    }
  });

  it('c19 B3: the Spanish views write the proxies in Spanish (no "proxy", no "Tier 1")', () => {
    const fed = selOf('fed-2026-severely-adverse');
    const texts = [textOf(render(<StackView sel={fed} />, 'es')), textOf(render(<C18ContextView sel={fed} />, 'es'))];
    const variants = SCENARIOS.map((n) => ({ id: n, title: variantName('C18', n) ?? { en: n, es: n }, v: committedDoc<VariantArtifact>('C18', n) }));
    texts.push(textOf(render(<C18VariantsTable variants={variants as never} aggregation={null} reverse={null} onPick={() => {}} current="baseline" />, 'es')));
    for (const t of texts) {
      // the producer's basis sentence is re-baked by the integrator: the view's own labels are checked here
      const own = t.replace(/El APR es el proxy[^.]*\.[^.]*\./g, ' ');
      expect(own).not.toMatch(/Proxy de|El proxy de P2G|Proxy de Tier 1/);
    }
    expect(texts[0]).toContain('La aproximación de P2G');
    expect(texts[1]).toContain('Aproximación del capital de nivel 1');
  });

  it('c19 M1: the lower stack drawing has a floor that holds its ticks, its axis title and the read-out hint', () => {
    const html = render(<StackView sel={selOf('fed-2026-severely-adverse')} />, 'en');
    expect(html).toMatch(/data-box="legal-stack"[^>]*style="[^"]*min-height:9rem/);
  });

  it('c19 M2: a path drawn as a level carries the unit of the level, not of the published deviation', () => {
    const ngfs = outputsOf(selOf('ngfs-delayed-transition'))!.scenario.paths;
    const unemployment = ngfs.find((p) => p.maps_to_regressor === 'unemployment_rate')!;
    expect(unemployment.unit).toBe('Abs. difference');
    expect(plottedUnit(unemployment)).toEqual({ en: 'percent', es: 'por ciento' });
    const fed = outputsOf(selOf('fed-2026-severely-adverse'))!.scenario.paths[0];
    expect(plottedUnit(fed).en).toBe(fed.unit);
    const text = textOf(render(<PathsView sel={selOf('ngfs-delayed-transition')} />, 'en'));
    expect(text).toContain('Published unit');
  });

  it('c19 M4: a start that did not converge is drawn at its committed distance and says so', () => {
    const sel = selOf('reverse-stress');
    const r = (sel.data.variant.outputs as unknown as { starts: Array<{ start_id: string; converged: boolean; distance: number }> }).starts;
    const bars = startBars(r, sel.start);
    r.forEach((s, i) => {
      expect(bars[i].value, s.start_id).toBe(s.distance);
      if (!s.converged) expect(bars[i].label.en, s.start_id).toMatch(/did not converge/);
    });
    expect(r.some((s) => !s.converged)).toBe(true);
  });

  it('m1: the severity table names the peak deviation of the path and of the crisis', () => {
    const text = textOf(render(<SeverityView sel={selOf('fed-2026-severely-adverse')} />, 'en'));
    expect(text).toContain('Peak deviation of the path');
    expect(text).toContain('Peak deviation of the crisis');
    expect(textOf(render(<SeverityView sel={selOf('fed-2026-severely-adverse')} />, 'es'))).toContain('Desviación máxima de la trayectoria');
  });

  it('m4: a tail probability under 0.1 percent keeps its exponent', () => {
    for (const lang of ['en', 'es'] as const) {
      const text = textOf(render(<ReverseSolutionView sel={selOf('reverse-stress')} />, lang));
      expect(text, lang).not.toMatch(/0[.,]00 %/);
      expect(text, lang).toMatch(/2[.,]4E-15/);
    }
  });

  it('m5: the Variants table names the aggregation and reverse variants as the rail does', () => {
    const agg = committedDoc<VariantArtifact>('C18', 't-copula-baseline');
    const rev = committedDoc<VariantArtifact>('C18', 'reverse-stress');
    const text = textOf(render(<C18VariantsTable variants={[]} aggregation={agg as never} reverse={rev as never} onPick={() => {}} current="baseline" />, 'es'));
    expect(text).toContain(variantName('C18', 't-copula-baseline')!.es);
    expect(text).toContain(variantName('C18', 'reverse-stress')!.es);
  });

  it('m11 and m12: no negative zero percent, the VaR error column carries its unit', () => {
    for (const name of SCENARIOS) {
      for (const lang of ['en', 'es'] as const) expect(textOf(render(<BackcastView sel={selOf(name)} />, lang)), name).not.toMatch(/-0[.,]000 %/);
    }
    expect(textOf(render(<MarginalsView sel={selOf('t-copula-baseline')} />, 'en'))).toMatch(/VaR error \(CLP millions\)/);
  });

  it('m10: the Euler caption says "Information, not capital" once', () => {
    const text = textOf(render(<EulerView sel={selOf('t-copula-baseline')} />, 'en'));
    expect(text.split('Information, not capital').length - 1).toBeLessThanOrEqual(1);
  });

  it('m8: an acronym keeps its case inside a sentence', () => {
    const text = textOf(render(<PathsView sel={{ ...selOf('eba-2025-adverse'), path: 0 }} />, 'en'));
    expect(text).not.toMatch(/real gdp growth/);
  });
});

describe('U16-F10e C18 context', () => {
  afterEach(() => setLang('en'));
  it('m6: the adaptation label ends with one full stop', () => {
    for (const lang of ['en', 'es'] as const) expect(textOf(render(<C18ContextView sel={selOf('fed-2026-severely-adverse')} />, lang)), lang).not.toMatch(/UU\.\.|\.\. /);
  });
});

describe('U16-F10e C18 fan', () => {
  afterEach(() => setLang('en'));
  it('m13: in the baseline the PPNR key says its line is the Base line', () => {
    // the shell's chart prints its key in the server markup only as data; the legend label is read from the chart's props through the summary
    const html = render(<FanView sel={selOf('baseline')} />, 'en');
    expect(html).toContain('identical to Base in this variant');
    expect(render(<FanView sel={selOf('fed-2026-severely-adverse')} />, 'en')).not.toContain('identical to Base in this variant');
  });
});
