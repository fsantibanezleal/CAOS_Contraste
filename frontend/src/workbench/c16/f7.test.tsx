// U16-F7 (the U16-R2 capture review, batch b08, C16): the minors of the liquidity views, read on the committed documents.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, englishLeaks, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { defaultSel, scenarioPhrase, type C16Sel } from './selection';
import { C16ContextView, C16TestsView, cell } from './C16Common';
import { TimeBlockView, htmLossOfBalanceSheet } from './BufferViews';
import { HtmLossView } from './SensitivityViews';

const models = committedDoc<ModelsArtifact>('C16', 'models-svb-liquidity');
const title = { en: 'Liquidity stress, LCR and the March 2023 run', es: 'Estrés de liquidez, LCR y la corrida de marzo de 2023' };
const selOf = (name: string): C16Sel => defaultSel(fixtureData('C16', committedDoc<VariantArtifact>('C16', name), models, title)) as C16Sel;
const VERBATIM = ['Silicon Valley Bank', 'Liquidity Stress Testing', 'LiST', 'Basel', 'FDIC', 'Contraste'];

describe('U16-F7 C16 (b08 minors)', () => {
  afterEach(() => setLang('en'));

  it('m2: the document date of a variant with no HTM block takes its loss from its own held-to-maturity line (fair value less amortised cost)', () => {
    const doc = committedDoc<VariantArtifact>('C16', 'lcr-standard') as any;
    expect(doc.outputs.htm).toBeNull();
    const loss = htmLossOfBalanceSheet(doc.outputs.balance_sheet.items);
    expect(loss).toBe(-15159000);
    const text = visibleText(html(<TimeBlockView sel={selOf('lcr-standard')} />));
    expect(text).toContain('-15,159,000');
    expect(htmLossOfBalanceSheet([])).toBeNull();
  });

  it('m3: a loss that rounds to zero prints 0, never "-0", and the note describes the chart that is drawn', () => {
    expect(cell(-0, 'en')).toBe('0');
    expect(cell(-0.3, 'es')).toBe('0');
    expect(cell(-15159000.4, 'en')).toBe('-15,159,000');
    const text = visibleText(html(<HtmLossView sel={selOf('htm-losses')} />));
    expect(text).not.toMatch(/-0(?![.,\d])/);
    expect(text).not.toMatch(/The axis of the CBC/);
    expect(text).toMatch(/The chart draws the survival period of each multiple/);
  });

  it('m6: at 390 the segment of a test stays under its name (the Against column is wide-only)', () => {
    const markup = html(<C16TestsView sel={selOf('lcr-standard')} />);
    const doc = committedDoc<VariantArtifact>('C16', 'lcr-standard');
    const withSegment = doc.tests.filter((t) => t.segment !== null).length;
    expect(withSegment).toBeGreaterThan(0);
    // every row from R5 ruling 2 on (U16-F13d): a row of no segment says "whole balance sheet, no comparator"
    expect((markup.match(/class="ct-narrow-only" data-segment=/g) ?? []).length).toBe(doc.tests.length);
  });

  it('m8: one name for the call report, and the scenario phrase names the phase', () => {
    expect(scenarioPhrase('idiosyncratic', 'protracted', 'es')).toBe('idiosincrático, fase prolongada');
    expect(scenarioPhrase('idiosyncratic', 'acute', 'es')).toBe('idiosincrático, fase aguda');
    expect(scenarioPhrase('combined', 'acute', 'en')).toBe('combined, acute');
    setLang('es');
    for (const name of ['lcr-standard', 'list-adverse']) {
      const ctx = visibleText(html(<C16ContextView sel={selOf(name)} />));
      expect(ctx).not.toMatch(/condición/);
      expect(ctx).not.toMatch(/idiosincrático, (aguda|prolongada)/);
    }
    expect(visibleText(html(<TimeBlockView sel={selOf('lcr-standard')} />))).not.toMatch(/reportes de condición/);
  });

  it('notes: a test with an empty note shows its reference in the Spanish view too, without English prose', () => {
    setLang('es');
    for (const name of ['lcr-standard', 'list-adverse', 'htm-losses']) {
      const text = visibleText(html(<C16TestsView sel={selOf(name)} />));
      expect(englishLeaks(text, VERBATIM), name).toEqual([]);
    }
  });
});
