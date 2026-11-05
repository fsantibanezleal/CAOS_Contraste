// U16-F13e (fix round 6, the fifth capture review R5, batches c24 and c25), on the committed documents in both languages: every row of
// the tests table names its segment, and a row of no segment its scope in words (R5 ruling 2: "whole balance sheet" / "todo el
// balance"; c24 M1, c25 M1), the tests card is titled for what the variant runs, the Spanish names the reverse stress one way, the
// severity chart says "deviation" as its table does, the reverse note sits under the Variants box (not cut inside it), the P2G block
// says "utilizables", the Context writes c<sub>P2</sub> and c<sub>d</sub> as the stack does, the dates of the severity caption and the
// satellites window are quarters, the shock window is not said twice, and the reverse Context says what its headline is.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { C18ContextView, C18TestsView, C18VariantsTable, NOT_REVERSE } from './C18Common';
import { StackView } from './CapitalViews';
import { PathsView, SEVERITY_TITLE, SeverityView } from './StressViews';
import { defaultSel, type C18Sel } from './selection';

const SCENARIOS = ['baseline', 'eba-2025-adverse', 'fed-2026-severely-adverse', 'ngfs-delayed-transition'] as const;
const ALL = [...SCENARIOS, 't-copula-baseline', 'reverse-stress'] as const;
const models = committedDoc<ModelsArtifact>('C18', 'models-banco-andino');
const title = { en: 'ICAAP and IAPE capital aggregation under macro scenarios', es: 'Agregación de capital ICAAP e IAPE bajo escenarios macro' };
const doc = (name: string) => committedDoc<VariantArtifact>('C18', name);
const selOf = (name: string): C18Sel => defaultSel(fixtureData('C18', doc(name), models, title)) as C18Sel;
const LANGS = ['en', 'es'] as const;
const SCOPE = { en: 'whole balance sheet', es: 'todo el balance' } as const;

describe('U16-F13e C18', () => {
  afterEach(() => setLang('en'));

  it('c24 M1, c25 M1 (ruling 2): every row of every tests table names its segment, a row of no segment its scope in words', () => {
    let scoped = 0;
    for (const name of ALL) {
      const tests = doc(name).tests;
      for (const lang of LANGS) {
        const html = render(<C18TestsView sel={selOf(name)} />, lang);
        const rows = [...html.matchAll(/<tr data-test="[^"]+"[^>]*>([\s\S]*?)<\/tr>/g)];
        expect(rows.length, `${name} ${lang}`).toBe(tests.length);
        rows.forEach((m, i) => {
          const cell = /<td class="ct-text"[^>]*>([\s\S]*?)<\/td>/.exec(m[1])![1];
          const scope = /data-scope="([^"]+)"/.exec(m[1]);
          expect(scope, `${name} ${lang} row ${i}`).not.toBeNull();
          if (!tests[i].segment) {
            expect(textOf(cell), `${name} ${lang} row ${i}`).toContain(`(${SCOPE[lang]})`);
            scoped += 1;
          }
        });
      }
    }
    expect(scoped).toBe(2 * 46);
  });

  it('c25 n3: the tests card is titled for what the variant runs', () => {
    expect(textOf(render(<C18TestsView sel={selOf('reverse-stress')} />, 'en'))).toContain('The test of the reverse stress');
    expect(textOf(render(<C18TestsView sel={selOf('reverse-stress')} />, 'es'))).toContain('La prueba de la tensión inversa');
    expect(textOf(render(<C18TestsView sel={selOf('t-copula-baseline')} />, 'en'))).toContain('The tests of the aggregation');
    expect(textOf(render(<C18TestsView sel={selOf('t-copula-baseline')} />, 'en'))).not.toContain('and the stress');
    expect(textOf(render(<C18TestsView sel={selOf('baseline')} />, 'en'))).toContain('The tests of the aggregation and the stress');
  });

  it('c24 n1: the Spanish names the reverse stress "tensión inversa", never "estrés inverso"', () => {
    expect((NOT_REVERSE as { es: string }).es).toContain('tensión inversa');
    const variants = SCENARIOS.map((id) => ({ id, title: { en: id, es: id }, v: doc(id) as never }));
    const html = render(<C18VariantsTable variants={variants} aggregation={doc('t-copula-baseline') as never} reverse={doc('reverse-stress') as never} onPick={() => undefined} current="baseline" />, 'es');
    expect(textOf(html)).not.toContain('estrés inverso');
    expect(textOf(html)).toContain('de tensión inversa tienen sus propias medidas');
  });

  it('c24 n4: the reverse note sits under the Variants box, not as a cut line inside it', () => {
    const variants = SCENARIOS.map((id) => ({ id, title: { en: id, es: id }, v: doc(id) as never }));
    const html = render(<C18VariantsTable variants={variants} aggregation={null} reverse={doc('reverse-stress') as never} onPick={() => undefined} current="baseline" />, 'en');
    const box = /<div class="ct-stack-table">([\s\S]*?)<\/table><\/div>/.exec(html);
    expect(box).not.toBeNull();
    expect(box![1]).not.toContain('failure point');
    expect(html).toMatch(/<\/table><\/div><\/div><p class="ct-note"[^>]*>For the reverse stress the CET1 column is the failure point/);
  });

  it('c24 n3: the severity chart says "deviation" as its table does', () => {
    expect(SEVERITY_TITLE).toEqual({ en: 'Path peak deviation over the crisis peak deviation', es: 'Desviación máxima de la trayectoria sobre la de la crisis' });
    for (const lang of LANGS) {
      const text = textOf(render(<SeverityView sel={selOf('fed-2026-severely-adverse')} />, lang));
      expect(text, lang).toContain(lang === 'en' ? 'Peak deviation of the path' : 'Desviación máxima de la trayectoria');
    }
  });

  it('c25 n2: the severity caption writes the crisis in quarters and ends with a full stop', () => {
    for (const lang of LANGS) {
      const html = render(<SeverityView sel={selOf('ngfs-delayed-transition')} />, lang);
      const text = textOf(html);
      expect(text, lang).not.toMatch(/2008-03-31|2009-12-31/);
      expect(text, lang).toContain(lang === 'en' ? '2008 Q1 to 2009 Q4' : '2008 T1 a 2009 T4');
      expect(text, lang).toMatch(/\(05 l\.422\)\./);
    }
  });

  it('c25 n2: the satellites window of the Context is written in quarters', () => {
    for (const lang of LANGS) {
      const text = textOf(render(<C18ContextView sel={selOf('baseline')} />, lang));
      expect(text, lang).not.toMatch(/1985-03-31|2019-12-31/);
      expect(text, lang).toContain(lang === 'en' ? '1985 Q1 to 2019 Q4' : '1985 T1 a 2019 T4');
    }
  });

  it('c24 n5: the P2G block says "utilizables" in its label as in its statement', () => {
    const text = textOf(render(<StackView sel={selOf('baseline')} />, 'es'));
    expect(text).not.toContain('Colchones usables');
    expect(text).toContain('Colchones utilizables y mitigación');
  });

  it('c24 n6, c25 n5: the Context writes c<sub>P2</sub> and c<sub>d</sub> as the stack does', () => {
    for (const lang of LANGS) {
      const html = render(<C18ContextView sel={selOf('baseline')} />, lang);
      expect(html, lang).not.toMatch(/\(c_P2\)|\(c_d\)/);
      expect(html, lang).toContain('c<sub>P2</sub>');
      expect(html, lang).toContain('c<sub>d</sub>');
    }
  });

  it('c25 n1: the shock window is said once', () => {
    for (const lang of LANGS) {
      const text = textOf(render(<PathsView sel={selOf('ngfs-delayed-transition')} />, lang));
      expect(text, lang).not.toMatch(lang === 'en' ? /2031 to 2033: The policy shock acts in 2031 to 2033/ : /2031 a 2033: El choque de política actúa de 2031 a 2033/);
      expect(text, lang).toContain(lang === 'en' ? 'The policy shock acts in 2031 to 2033' : 'El choque de política actúa de 2031 a 2033');
    }
  });

  it('c25 n6: the reverse Context says its headline is the simple sum of the marginals', () => {
    const en = textOf(render(<C18ContextView sel={selOf('reverse-stress')} />, 'en'));
    expect(en).toContain('not available: the reverse stress runs no aggregation band; its headline capital is the simple sum of the four marginals');
    const es = textOf(render(<C18ContextView sel={selOf('reverse-stress')} />, 'es'));
    expect(es).toContain('no disponible: la tensión inversa no corre una agregación por bandas; su capital principal es la suma simple de las cuatro marginales');
  });
});
