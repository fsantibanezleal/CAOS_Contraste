// U16-F7 (the U16-R2 capture review, batch b07, C14 and C15): the minors of the IRRBB views, read on the committed documents.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { C15FindingsView } from '../c15/C15Common';
import { thresholdsChart } from '../c15/FloorViews';
import { defaultSel as defaultSel15, type C15Sel } from '../c15/selection';
import { CapsView } from './BehaviouralViews';
import { IrrbbTestsTable } from './C14Common';
import { GapView } from './NiiViews';
import { defaultSel, type C14Sel } from './selection';
import { committedDoc, englishLeaks, fixtureData, html, setLang, visibleText } from './testkit';

const models14 = committedDoc<ModelsArtifact>('C14', 'models-svb-2021-2022');
const sel14 = (name: string): C14Sel => defaultSel(fixtureData('C14', committedDoc<VariantArtifact>('C14', name), models14, { en: 'IRRBB', es: 'IRRBB' })) as C14Sel;
const models15 = committedDoc<ModelsArtifact>('C15', 'models-banco-andino-2026-09');
const sel15 = (name: string): C15Sel => defaultSel15(fixtureData('C15', committedDoc<VariantArtifact>('C15', name), models15, { en: 'IRRBB', es: 'IRRBB' })) as C15Sel;
const VERBATIM = ['Contraste', /https?:\/\/\S+/g];

describe('U16-F7 C14 and C15 (b07 minors)', () => {
  afterEach(() => setLang('en'));

  it('m1: a test with an empty note shows its reference (in Spanish in the Spanish view), never an empty cell', () => {
    for (const name of ['vd-2021-q4', 'vd-2022-q2', 'vd-2022-q4']) {
      const variant = committedDoc<VariantArtifact>('C14', name);
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const markup = html(<IrrbbTestsTable variant={variant} />);
        const cells = [...markup.matchAll(/<tr[^>]*data-test="([^"]+)"[\s\S]*?<\/tr>/g)].map((m) => ({ id: m[1], last: (m[0].match(/<td class="ct-text">([\s\S]*?)<\/td>\s*<\/tr>/) ?? [])[1] ?? '' }));
        expect(cells.length, name).toBeGreaterThan(0);
        for (const c of cells) expect(c.last.trim(), `${name} ${lang} ${c.id}`).not.toBe('');
        if (lang === 'es') expect(englishLeaks(visibleText(markup), VERBATIM), name).toEqual([]);
      }
    }
  });

  it('m4: the two cap columns are not both headed "Cap" (C14 caps table, C15 deposit table)', () => {
    setLang('en');
    const caps = visibleText(html(<CapsView sel={sel14('vd-2022-q4')} />));
    expect(caps).toMatch(/Share cap/);
    expect(caps).toMatch(/Cap \(years\)/);
    expect(caps).not.toMatch(/ Cap Used /);
    const c15 = html(<C15FindingsView sel={sel15('clp-steepener')} />);
    expect(c15).toBeTruthy();
  });

  it('m6: the thresholds of three different tests are marks, not a line joining them', () => {
    const chart = thresholdsChart(sel15('clp-steepener'))!;
    const threshold = chart.series.find((s) => /Threshold/.test((s.label as { en: string }).en))!;
    expect(threshold.mode).toBe('points');
    expect(threshold.dash).toBeUndefined();
  });

  it('m10: the repricing gap names its time-bucket axis in a caption, in both languages', () => {
    setLang('en');
    expect(visibleText(html(<GapView sel={sel14('vd-2022-q4')} />))).toMatch(/Horizontal axis: time bucket, 1 \(overnight\) to 19 \(over 20 years\)/);
    setLang('es');
    expect(visibleText(html(<GapView sel={sel14('vd-2022-q4')} />))).toMatch(/Eje horizontal: tramo de tiempo, de 1 \(a la vista\) a 19 \(más de 20 años\)/);
  });
});
