// U16-F10d (fix round 4, the third capture review R3, batch c17, C16): the Spanish name of the run-off back-test is Spanish (B1, the
// C16 copy; names/tests.ts is the names module's), no Spanish string of the C16 views carries an English word of the 2026-10-27
// ruling, the reverse note states the cap rule as the document does (n5), and the light-theme scored bars are called amber (n1).
import { readFileSync, readdirSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { C16TestsView } from './C16Common';
import { ReverseCurveView } from './SensitivityViews';
import { defaultSel, type C16Sel } from './selection';

const models = committedDoc<ModelsArtifact>('C16', 'models-svb-liquidity');
const title = { en: 'Liquidity stress, LCR and the March 2023 run', es: 'Estrés de liquidez, LCR y la corrida de marzo de 2023' };
const selOf = (name: string): C16Sel => defaultSel(fixtureData('C16', committedDoc<VariantArtifact>('C16', name), models, title)) as C16Sel;

describe('U16-F10d C16', () => {
  afterEach(() => setLang('en'));

  it('B1: the Spanish tests table names the run-off test without "backtest"', () => {
    setLang('es');
    const text = visibleText(html(<C16TestsView sel={selOf('list-adverse')} />));
    expect(text).toContain('La prueba retrospectiva de la salida de depósitos contra la corrida realizada');
    expect(text).not.toMatch(/\bbacktest/i);
  });

  it('n5: the reverse note states the cap as the document does: at most 1, a rate already at 1 stays', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const text = visibleText(html(<ReverseCurveView sel={selOf('reverse-stress')} />));
      expect(text).not.toMatch(/stays below 1\.|quede bajo 1\./);
      expect(text).toContain(lang === 'en' ? 'each rate stays at most 1; a rate already at 1 stays' : 'cada tasa quede como máximo en 1');
    }
  });

  it('the Spanish strings of the C16 views carry no English word of the 2026-10-27 ruling, and no bar is called orange', () => {
    const dir = new URL('./', import.meta.url);
    const found: string[] = [];
    for (const f of readdirSync(dir).filter((n) => /\.tsx?$/.test(n) && !n.includes('.test.'))) {
      const src = readFileSync(new URL(f, dir), 'utf8');
      for (const m of src.matchAll(/\bes: (['`])((?:\\.|(?!\1).)*)\1/g)) {
        const words = m[2].match(/\b(backtest\w*|back-test\w*|proxy|hazard|roll-off|shock\w*|offline|golden|naranjas?)\b/gi);
        if (words) found.push(`${f}: ${words.join(', ')}`);
      }
      expect(src, f).not.toMatch(/Orange bars/);
    }
    expect(found).toEqual([]);
  });
});
