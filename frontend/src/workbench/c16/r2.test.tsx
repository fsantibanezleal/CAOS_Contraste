// U16-F4 (the U16-R2 capture review, batch b08): the Spanish view of C16 carries no English prose and no raw slug, on the six
// committed documents. The finding titles and the reverse-stress refusal are the producer's (tests/c16/test_u16_f4_texts.py).
import { afterEach, describe, expect, it } from 'vitest';
import type { ReactElement } from 'react';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, englishLeaks, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { defaultSel, type C16Sel } from './selection';
import { C16ContextView, C16FindingsView, C16TestsView } from './C16Common';
import { CbcStackView, LadderView, RunSpeedsView, RunoffView } from './LadderViews';
import { CbcView, HtmView, LcrView, TimeBlockView } from './BufferViews';
import { HtmLossView, ReverseBasesView, ReverseCurveView, UninsuredShareView } from './SensitivityViews';

const NAMES = ['lcr-standard', 'list-adverse', 'list-extreme', 'fast-run', 'htm-losses', 'reverse-stress'] as const;
const models = committedDoc<ModelsArtifact>('C16', 'models-svb-liquidity');
const title = { en: 'Liquidity stress, LCR and the March 2023 run', es: 'Estrés de liquidez, LCR y la corrida de marzo de 2023' };
const selOf = (name: string): C16Sel => defaultSel(fixtureData('C16', committedDoc<VariantArtifact>('C16', name), models, title)) as C16Sel;

type V = [string, (p: { sel: C16Sel | null }) => ReactElement];
const SCENARIO: V[] = [
  ['Ladder', LadderView], ['CbcStack', CbcStackView], ['Runoff', RunoffView], ['RunSpeeds', RunSpeedsView], ['Cbc', CbcView], ['Htm', HtmView],
  ['Lcr', LcrView], ['TimeBlock', TimeBlockView], ['UninsuredShare', UninsuredShareView], ['HtmLoss', HtmLossView], ['Tests', C16TestsView],
  ['Findings', C16FindingsView], ['Context', C16ContextView],
];
const REVERSE: V[] = [['ReverseCurve', ReverseCurveView], ['ReverseBases', ReverseBasesView], ['Tests', C16TestsView], ['Findings', C16FindingsView], ['Context', C16ContextView]];
const VERBATIM = ['Silicon Valley Bank', 'Liquidity Stress Testing', 'LiST', 'Basel', 'FDIC', 'Contraste'];

/** A slug printed as text: three or more words joined by hyphens or an underscore id. */
const SLUG = /\b[a-z]+(?:[-_][a-z0-9]+)+\b/g;
/** Identifiers that the producer's own prose names (a phase, a function of the engine, a haircut term): code in a sentence, not a label. */
const CODE_IN_PROSE = ['lcr-30-day', 'lcr_nsfr', 'roll-off'];

describe('U16-F4 C16: the Spanish view', () => {
  afterEach(() => setLang('en'));

  it('V16-1: no view of the Spanish capture carries English prose or a raw slug, on the six committed documents', () => {
    setLang('es');
    const all: string[] = [];
    for (const name of NAMES) {
      for (const [view, View] of name === 'reverse-stress' ? REVERSE : SCENARIO) {
        const text = visibleText(html(<View sel={selOf(name)} />));
        for (const leak of englishLeaks(text, VERBATIM)) all.push(`${name} ${view} ${leak}`);
        // the evidence ids of the shared findings card are that card's
        if (view !== 'Findings') for (const id of (text.match(SLUG) ?? []).filter((x) => !CODE_IN_PROSE.includes(x))) all.push(`${name} ${view} slug ${id}`);
      }
    }
    expect([...new Set(all)]).toEqual([]);
  });

  it('V16-1: the name of the bank has a Spanish form', () => {
    setLang('es');
    const text = visibleText(html(<C16ContextView sel={selOf('list-adverse')} />));
    expect(text).not.toContain('failed 2023-03-10');
    expect(text).toContain('quebró el 2023-03-10');
  });
});
