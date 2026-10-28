// U16-F13e (fix round 6, the fifth capture review R5, batch c26), on the six committed documents in both languages: the Real drift
// note calls the Fed's portfolios hypothetical, as the case page does (M1); the English unit of a list of multiples is plural (m1);
// the conformal chart and its table share one decimal (m2); the reasons-kept bars and the fairness-battery bars carry the light of
// their row (m3, m4); and every tests table of C20 names the segment of every row (R5 ruling 2).
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { C20ContextView } from './C20Common';
import { batteryBars } from './FairnessViews';
import { reasonBars } from './RobustnessViews';
import { CONFORMAL_FORMAT, RealDriftView } from './ShiftViews';
import { U14TestsTable } from './U14Common';
import { paramUnit } from './localise';
import { defaultSel, type C20Sel } from './selection';

const models = committedDoc<ModelsArtifact>('C20', 'models-c20-ladder');
const title = { en: 'ML model validation', es: 'Validación de modelos de ML' };
const doc = (name: string) => committedDoc<VariantArtifact>('C20', name);
const selOf = (name: string): C20Sel => defaultSel(fixtureData('C20', doc(name), models, title)) as C20Sel;
const DOCS = ['fed-shift', 'leakage-planted', 'perturbation-grid', 'seed-sweep', 'sgcd-held-out', 'sgcd-seen'] as const;
const LANGS = ['en', 'es'] as const;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const out = (name: string): any => doc(name).outputs;
const TONE = { green: 'good', amber: 'warn', red: 'bad' } as const;

describe('U16-F13e C20', () => {
  afterEach(() => setLang('en'));

  it('c26 M1: the Real drift note calls the Fed portfolios hypothetical, never real populations', () => {
    for (const lang of LANGS) {
      const text = textOf(render(<RealDriftView sel={selOf('fed-shift')} />, lang));
      expect(text, lang).not.toMatch(/real populations|poblaciones reales/);
      expect(text, lang).toContain(lang === 'en' ? "The Federal Reserve's three hypothetical portfolios" : 'Las tres carteras hipotéticas de la Reserva Federal');
    }
  });

  it('c26 m1: the English unit of a list of multiples, or of a 2, is plural', () => {
    expect(paramUnit("multiple of each feature's standard deviation", 'en')).toBe("multiples of each feature's standard deviation");
    expect(paramUnit('multiple of the average test error', 'en')).toBe('multiples of the average test error');
    expect(paramUnit("multiple of each feature's standard deviation", 'es')).toBe('múltiplos de la desviación estándar de cada variable');
    expect(paramUnit('AUC points', 'en')).toBe('AUC points');
    const en = textOf(render(<C20ContextView sel={selOf('perturbation-grid')} />, 'en'));
    expect(en).not.toMatch(/\b1 multiple of each feature|\b2 multiple of the average/);
    expect(en).toContain("multiples of each feature's standard deviation");
  });

  it('c26 m2: the conformal chart writes its coverage with the decimal of its table', () => {
    expect(CONFORMAL_FORMAT).toEqual({ percent: true, decimals: 1 });
  });

  it('c26 m3: each reasons-kept bar carries the light of its rung\'s reason-code test', () => {
    const o = out('seed-sweep');
    const tests = doc('seed-sweep').tests;
    const bars = reasonBars(o.rows, tests, null);
    expect(bars.length).toBe(o.rows.length);
    for (const b of bars) {
      const row = tests.find((t) => t.test_id === 'ml.reason_code_stability' && (t.model_id ?? '').startsWith(b.id.replace(/-reasons$/, '')));
      expect(row, b.id).toBeDefined();
      expect(b.tone, b.id).toBe(TONE[row!.light as keyof typeof TONE]);
    }
    expect(bars.some((b) => b.tone === 'warn')).toBe(true);
  });

  it('c26 m4: each fairness-battery bar carries the light of its row', () => {
    for (const name of ['leakage-planted', 'perturbation-grid', 'seed-sweep']) {
      const rows = out(name).fairness_battery.rows.filter((r: { test_id: string }) => r.test_id === 'fair.equalized_odds');
      const bars = batteryBars(rows, null);
      expect(bars.length, name).toBe(rows.length);
      bars.forEach((b, i) => expect(b.tone, `${name} ${b.id}`).toBe(TONE[rows[i].light as keyof typeof TONE]));
    }
    const grid = batteryBars(out('perturbation-grid').fairness_battery.rows.filter((r: { test_id: string }) => r.test_id === 'fair.equalized_odds'), null);
    expect(grid.filter((b) => b.tone === 'bad').map((b) => b.id).sort()).toEqual(['age', 'marital_status']);
  });

  it('ruling 2: every row of every C20 tests table names its segment', () => {
    for (const name of DOCS) {
      const tests = doc(name).tests;
      for (const lang of LANGS) {
        const html = render(<U14TestsTable tests={tests} caseId="C20" />, lang);
        const rows = [...html.matchAll(/<tr data-test="[^"]+"[^>]*>([\s\S]*?)<\/tr>/g)];
        expect(rows.length, `${name} ${lang}`).toBe(tests.length);
        for (const m of rows) expect(m[1], `${name} ${lang}`).toMatch(/class="ct-row-detail" data-segment="[^"]+">[^<]+</);
      }
    }
  });
});
