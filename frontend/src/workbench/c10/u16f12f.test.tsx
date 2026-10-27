// U16-F12f (fix round 5), C10: the cards that open with the illustrative-portfolio notice put the notice and the drawing over its
// tables in one column (`c10-flow.css`), so the stack takes the height left under the notice and the card body cuts nothing
// (U16-R4 c13 M1). Reads the committed documents, in both languages.
import { afterEach, describe, expect, it } from 'vitest';
import { html, setLang } from '../c03/u6-testkit';
import { committedData } from '../c08/spanish-testkit';
import { ContributionsView, GranularityView, LossView, RungsView } from './CapitalViews';
import { PortfolioView } from './ModelViews';
import { defaultSel, type C10Sel } from './selection';

const TITLE = { en: 'Portfolio credit capital', es: 'Capital de crédito de cartera' };
const sel = defaultSel(committedData('C10', 'other-consumer.json', 'models-c10.json', TITLE)) as C10Sel;

describe('U16-F12f C10 notice flow', () => {
  afterEach(() => setLang('en'));
  const views = { Rungs: RungsView, Granularity: GranularityView, Contributions: ContributionsView, Loss: LossView, Portfolio: PortfolioView };
  for (const lang of ['en', 'es'] as const) {
    for (const [name, View] of Object.entries(views)) {
      it(`${name} (${lang}): the notice and the stack share one column that gives the stack the height left`, () => {
        setLang(lang);
        const markup = html(<View sel={sel} />);
        const flow = markup.indexOf('class="ct-c10-flow"');
        expect(flow, 'the flow column').toBeGreaterThan(-1);
        const notice = markup.indexOf('data-portfolio="illustrative"', flow);
        const stack = markup.indexOf('class="ct-stack"', flow);
        expect(notice).toBeGreaterThan(flow);
        expect(stack).toBeGreaterThan(notice);
        // the column is a flow box the shell's body measures (SHC-100), like every stack
        expect(markup.slice(flow - 5, flow + 60)).toContain('data-caos-flow=""');
      });
    }
  }
});
