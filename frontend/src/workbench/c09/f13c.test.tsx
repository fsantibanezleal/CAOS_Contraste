// U16-F13c (R5 batch c12, C09, and R5 ruling 2): every row of the CCF and EAD tests tables names its segment, and a row its document
// gives none (every C09 row) names the whole portfolio; with the minor of the batch fixed in the view: the facility-class table of the
// Floor card keeps its columns in view at 1280 (n1: the Paragraph column, which the supervisory card beside it lists, is the class cell's
// hint). Reads the committed documents, in both languages.
import { afterEach, describe, expect, it } from 'vitest';
import { html, setLang } from '../c03/u6-testkit';
import { committedData } from '../c08/spanish-testkit';
import { WHOLE_PORTFOLIO } from '../c08/words';
import { EstimatorTestsView } from './CcfViews';
import { BacktestTestsView, FloorsView } from './EadViews';
import { defaultSel, type C09Sel } from './selection';

const TITLE = { en: 'EAD and CCF for revolving lines', es: 'EAD y CCF de líneas rotativas' };
const LEVELS = [0, 1, 2, 3, 4, 5];
const DESIGNS = ['fixed-horizon', 'cohort', 'variable-horizon'];
const selOf = (n: number) => defaultSel(committedData('C09', `level-${n}.json`, 'models-generator.json', TITLE)) as C09Sel;
const rowsOf = (markup: string) => [...markup.matchAll(/<tr [^>]*data-test="([^"]+)"[^>]*>([\s\S]*?)<\/tr>/g)].map((m) => m[2]);
const tableOf = (markup: string, name: string) => /<table[^>]*data-table="[^"]*"[^>]*>[\s\S]*?<\/table>/g.exec(markup.slice(markup.indexOf(`data-table="${name}"`) - 200))?.[0] ?? '';

describe('U16-F13c, C09 (R5 c12)', () => {
  afterEach(() => setLang('en'));

  it('ruling 2: every CCF and EAD tests row names its segment, the whole portfolio where the document gives none', () => {
    for (const n of LEVELS) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const words = WHOLE_PORTFOLIO[lang];
        const views = [
          ...DESIGNS.map((design) => html(<EstimatorTestsView sel={{ ...selOf(n), design }} />)),
          html(<BacktestTestsView sel={selOf(n)} />),
        ];
        let seen = 0;
        for (const markup of views) {
          for (const r of rowsOf(markup)) {
            seen += 1;
            expect(r, `level ${n} ${lang}`).toContain('ct-row-detail');
            expect(r.replace(/<[^>]*>/g, ' '), `level ${n} ${lang}`).toContain(words);
          }
        }
        expect(seen, `level ${n}`).toBeGreaterThan(0);
      }
    }
  });

  it('n1: the facility-class table of the Floor card has no Paragraph column; the paragraph is the class cell\'s hint', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = html(<FloorsView sel={selOf(3)} />);
      const floor = tableOf(markup, 'ead-floor');
      expect(floor).toContain('data-class=');
      expect(floor).not.toContain(lang === 'en' ? '>Paragraph<' : '>Párrafo<');
      expect(floor).toMatch(/<td class="ct-text" title="[^"]*CRE20/);
      // the supervisory card beside it keeps its paragraphs
      expect(tableOf(markup, 'supervisory-ccfs')).toContain(lang === 'en' ? '>Paragraph<' : '>Párrafo<');
    }
  });
});
