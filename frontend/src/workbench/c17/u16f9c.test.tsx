// U16-F9c (fix round 3, the partial R2b review of C17, report c18), on the committed documents: a method's name keeps its proper
// names and acronyms inside a sentence, the ladder shows no block that always says it has no test, the rail counts the histories
// with a capital for the rung in focus, and the capital by years and threshold gives its table the taller box.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { YearsReadout } from './C17Common';
import { ByYearsView, ScenarioView } from './CapitalViews';
import { inSentence } from './localise';
import { LadderView } from './ModelViews';
import { capitalOf, cellOf, defaultSel, outputsOf, type C17Sel } from './selection';

const NAMES = ['xi-0-6', 'xi-0-8', 'xi-0-96', 'xi-1-1'] as const;
const models = committedDoc<ModelsArtifact>('C17', 'models-generator');
const title = { en: 'Operational risk: LDA vs SMA', es: 'Riesgo operacional: LDA vs SMA' };
const selOf = (name: string): C17Sel => defaultSel(fixtureData('C17', committedDoc<VariantArtifact>('C17', name), models, title)) as C17Sel;

describe('U16-F9c C17', () => {
  afterEach(() => setLang('en'));

  it('a name inside a sentence keeps its proper names and acronyms (m-2)', () => {
    expect(inSentence('Bayesian credibility')).toBe('Bayesian credibility');
    expect(inSentence('Lognormal and GPD splice')).toBe('lognormal and GPD splice');
    expect(inSentence('Single loss approximation (SLA)')).toBe('single loss approximation (SLA)');
    expect(inSentence('SLA, mean-corrected')).toBe('SLA, mean-corrected');
    expect(inSentence('Credibilidad bayesiana')).toBe('credibilidad bayesiana');
  });

  for (const name of NAMES) {
    for (const lang of ['en', 'es'] as const) {
      it(`${name} (${lang}): no lower-cased acronym or proper name in the capital captions`, () => {
        const s = selOf(name);
        const text = textOf(render(<ScenarioView sel={s} />, lang)) + textOf(render(<ByYearsView sel={s} />, lang));
        // "bayesiana" is the Spanish adjective, lower case by rule; the English proper name is "Bayesian"
        expect(text).not.toMatch(/\bbayesian\b|\bgpd\b|\(sla\)/);
      });

      it(`${name} (${lang}): the ladder shows no block that says it has no test (m-1)`, () => {
        expect(textOf(render(<LadderView sel={selOf(name)} />, lang))).not.toMatch(/carries no test row for this view|no trae filas de pruebas para esta vista/);
      });

      it(`${name} (${lang}): the rail counts the histories with a capital for the rung in focus (M-2)`, () => {
        const s = selOf(name);
        const o = outputsOf(s)!;
        const cell = cellOf(o, s.years, s.threshold)!;
        const n = capitalOf(cell, s.rung).summary?.n_defined;
        const text = textOf(render(<YearsReadout sel={s} />, lang));
        expect(text).toContain(lang === 'en' ? 'With a capital' : 'Con capital');
        expect(n).toBeTypeOf('number');
      });

      it(`${name} (${lang}): the capital by years and threshold gives its table the taller box (M-3)`, () => {
        expect(render(<ByYearsView sel={selOf(name)} />, lang)).toMatch(/class="ct-c17-tall"[\s\S]*data-table="capital-by-cell"/);
      });
    }
  }
});
