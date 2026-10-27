// U16-F12f (fix round 5): the C14 tests table localises the engine notes through the one rule list in `localise.ts`; the copy that
// C14Common kept is gone, and the Spanish C15 tests table still prints the estimation-window note in Spanish.
import { afterEach, describe, expect, it } from 'vitest';
import type { VariantArtifact } from '../../lib/contract.types';
import { IrrbbTestsTable } from './C14Common';
import { committedDoc, html, setLang, visibleText } from './testkit';

describe('U16-F12f C14 note rule', () => {
  afterEach(() => setLang('en'));

  it('the Spanish C15 tests table prints the estimation-window note in Spanish, the English one keeps the engine text', () => {
    const v = committedDoc<VariantArtifact>('C15', 'clp-steepener');
    const note = v.tests.find((t) => /^not evaluated: fewer than \d+ estimation windows$/.test(t.notes ?? ''));
    expect(note, 'the committed C15 document carries the note').toBeTruthy();
    const n = /(\d+)/.exec(note!.notes!)![1];
    setLang('es');
    const es = visibleText(html(<IrrbbTestsTable variant={v} />));
    expect(es).toContain(`no evaluada: menos de ${n} ventanas de estimación`);
    expect(es).not.toContain('estimation windows');
    setLang('en');
    expect(visibleText(html(<IrrbbTestsTable variant={v} />))).toContain(`not evaluated: fewer than ${n} estimation windows`);
  });
});
