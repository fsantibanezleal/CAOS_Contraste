// U16-F10e (fix round 4, the third capture review R3, batch c21), on the six committed year pairs in both languages: the excluded
// categories and the licence sentences in Spanish, no "odds" in the Spanish views, no configuration key in the situation-testing note,
// the identifiers formula in words, every test row with its segment, the situation-testing light traced to its number and its cut,
// and the minors of the batch.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { C21ContextView } from './C21Common';
import { ControlledView, RateSpreadView, ReplicationView, SituationView, groupAxis } from './EstimateViews';
import { FourFifthsView, RatesView, TestsView } from './RateViews';
import { defaultSel, outputsOf, type C21Sel } from './selection';

const PAIRS = ['pair-2018-19', 'pair-2019-20', 'pair-2020-21', 'pair-2021-22', 'pair-2022-23', 'pair-2023-24'] as const;
const models = committedDoc<ModelsArtifact>('C21', 'models-hmda-de-2018-2023');
const title = { en: 'Fair lending', es: 'Préstamos justos' };
const selOf = (name: string): C21Sel => defaultSel(fixtureData('C21', committedDoc<VariantArtifact>('C21', name), models, title)) as C21Sel;
const tests = (html: string) => [...html.matchAll(/<tr[^>]*data-test="[^"]+"[\s\S]*?<\/tr>/g)].map((m) => textOf(m[0]));

describe('U16-F10e C21', () => {
  afterEach(() => setLang('en'));

  it('c21 B1: the Spanish Rates view names the excluded categories in Spanish', () => {
    for (const name of PAIRS) {
      const text = textOf(render(<RatesView sel={selOf(name)} />, 'es'));
      expect(text, name).not.toMatch(/\b(Joint|Free Form Text Only|Race Not Available)\b/);
    }
    expect(textOf(render(<RatesView sel={selOf('pair-2018-19')} />, 'es'))).toContain('Conjunto');
  });

  it('c21 B3: the Spanish licence card renders both sentences in Spanish with the English original marked', () => {
    const html = render(<C21ContextView sel={selOf('pair-2018-19')} />, 'es');
    expect(html).toContain('«Como obra del Gobierno de Estados Unidos');
    expect(html).toContain('«Los datos públicos se modifican para proteger la privacidad');
    expect((html.match(/original en inglés/g) ?? []).length).toBeGreaterThanOrEqual(2);
  });

  it('c21 B5: no Spanish view of these files says "odds" or "log-odds"', () => {
    for (const name of PAIRS) {
      const sel = selOf(name);
      for (const View of [RatesView, TestsView, ControlledView, RateSpreadView, ReplicationView]) {
        // the engine's test notes and the producer's titles are re-baked by the integrator; the view's own words are read here
        const html = render(<View sel={sel} />, 'es').replace(/<tr[^>]*data-test="[\s\S]*?<\/tr>/g, ' ');
        expect(textOf(html), name).not.toMatch(/\bodds\b|log-odds/);
      }
    }
    expect(textOf(render(<ControlledView sel={selOf('pair-2018-19')} />, 'es'))).toMatch(/razón de probabilidades/);
  });

  it('c21 B6: the situation-testing note names its cut, never the key extras.thresholds', () => {
    for (const lang of ['en', 'es'] as const) {
      const text = textOf(render(<SituationView sel={selOf('pair-2018-19')} />, lang));
      expect(text, lang).not.toMatch(/extras\.thresholds/);
      // the re-baked note states the cut in words itself (the amber share of significant complainants), and the row gives its value
      expect(text, lang).toMatch(lang === 'en' ? /amber share of significant complainants/ : /denunciantes significativos/);
      expect(text, lang).toMatch(lang === 'en' ? /amber from 0\.20 \(convention\)/ : /ámbar desde 0,20/);
    }
  });

  it('c21 B7: the identifiers formula is in words, no raw key', () => {
    for (const lang of ['en', 'es'] as const) {
      const text = textOf(render(<C21ContextView sel={selOf('pair-2018-19')} />, lang));
      expect(text, lang).not.toMatch(/<activity_year>|<row>/);
      expect(text, lang).toContain(lang === 'en' ? '<activity year>-<row number>' : '<año de actividad>-<fila>');
    }
  });

  it('c21 M1: every test row shows the attribute and the contrast it tests', () => {
    for (const lang of ['en', 'es'] as const) {
      const rows = tests(render(<TestsView sel={selOf('pair-2018-19')} />, lang));
      expect(rows.length).toBeGreaterThan(4);
      // no two rows read the same
      expect(new Set(rows).size, lang).toBe(rows.length);
    }
    const html = render(<TestsView sel={selOf('pair-2018-19')} />, 'en');
    expect(html).toMatch(/data-segment="derived_race\|American Indian or Alaska Native vs White"/);
  });

  it('c21 M2: below 640 px the group axis numbers its ticks, keyed to the table rows', () => {
    const contrasts = outputsOf(selOf('pair-2018-19'))!.attributes[0].contrasts;
    const wide = groupAxis(contrasts, false);
    const narrow = groupAxis(contrasts, true);
    expect(wide.ticks[0].label).not.toEqual({ en: '1', es: '1' });
    expect(narrow.ticks.map((t) => t.label)).toEqual(contrasts.map((_, i) => ({ en: String(i + 1), es: String(i + 1) })));
    expect(textOf(render(<ControlledView sel={selOf('pair-2018-19')} />, 'en'))).toMatch(/\b1\. /);
  });

  it('c21 M3: the situation-testing view shows the share that decides the light and its cut, and says what the other share is of', () => {
    for (const name of PAIRS) {
      const sel = selOf(name);
      const t = sel.data.variant.tests.find((x) => x.test_id === 'fair.situation_testing')!;
      const en = textOf(render(<SituationView sel={sel} />, 'en'));
      const pct = new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(t.metric!).replace('%', '');
      expect(en, name).toContain(`${pct} %`.replace(' %', '')) ;
      expect(en, name).toMatch(/of the complainants/);
      expect(en, name).toMatch(/of the cases tested/);
      expect(en, name).toMatch(/amber from 0\.20/);
    }
  });

  it('m1: a test that ran shows its metric when its statistic is null', () => {
    const rows = tests(render(<RatesView sel={selOf('pair-2018-19')} />, 'en'));
    const parity = rows.find((r) => r.trim().startsWith('Demographic parity'))!;
    expect(parity).not.toMatch(/not available/);
  });

  it('m5: one Spanish word for the complainants, "por pares", and the distance in a sentence', () => {
    const text = textOf(render(<SituationView sel={selOf('pair-2018-19')} />, 'es'));
    expect(text).not.toMatch(/Demandantes|demandante/);
    expect(text).toMatch(/normalización por rango; parámetros por convención/);
    expect(textOf(render(<RatesView sel={selOf('pair-2018-19')} />, 'es'))).not.toMatch(/pruebas de a pares/);
  });

  it('m2: the four-fifths card is a tall card like Rates', () => {
    expect(render(<FourFifthsView sel={selOf('pair-2018-19')} />, 'en')).toContain('class="ct-c21-tall"');
  });
});
