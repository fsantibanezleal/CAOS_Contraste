// U16-F2 (the R2 fix round, C05), on the committed documents: the Spanish context prints Spanish words for the truth status and the
// descriptive part of each licence and attribution, and the findings table keeps its Status column at 390 px.
import { afterEach, describe, expect, it } from 'vitest';
import { committedData, render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { C05ContextView, C05FindingsView } from './C05Common';
import { SOURCE_TEXT_ES, sourceText, truthStatusText, type C05Sel } from './selection';

const sel = (): C05Sel => ({ data: committedData('C05'), alphas: { amber: 0.05, red: 0.01 } } as unknown as C05Sel);

describe('U16-F2 C05', () => {
  afterEach(() => setLang('en'));

  it('V05-1: the Spanish context names the truth status in words and translates each licence and attribution, citations verbatim', () => {
    const s = sel();
    const es = textOf(render(<C05ContextView sel={s} />, 'es'));
    expect(es).not.toContain('published-answer');
    expect(es).toContain('respuesta publicada');
    for (const id of s.data.manifest.sources) {
      const d = s.data.manifest.source_details[id];
      expect(SOURCE_TEXT_ES[id], `${id}: a Spanish wording for the registry's licence and attribution`).toBeDefined();
      expect(sourceText(id, 'licence', d.licence, 'es')).not.toBe(d.licence);
      expect(es).toContain(sourceText(id, 'licence', d.licence, 'es'));
      expect(es).toContain(sourceText(id, 'attribution', d.attribution, 'es'));
      expect(es).not.toContain(d.licence);
    }
    expect(es).toContain('Tasche, D. (2013). The art of probability-of-default curve calibration.');   // the citation itself is verbatim
    const en = textOf(render(<C05ContextView sel={s} />, 'en'));
    expect(en).toContain('Truth status of this variant: published answer.');
    for (const id of s.data.manifest.sources) expect(en).toContain(s.data.manifest.source_details[id].licence);
  });

  it('V05-1: a wording the registry has changed is shown as declared, never as a stale translation', () => {
    expect(sourceText('tasche-2013', 'licence', 'a new licence wording', 'es')).toBe('a new licence wording');
    expect(sourceText('unknown-source', 'attribution', 'x', 'es')).toBe('x');
    expect(truthStatusText('something-new')).toEqual({ en: 'something-new', es: 'something-new' });
  });

  it('V05-2: the Status column of the findings stays in the table below 641 px (no ct-wide-only on it)', () => {
    const markup = render(<C05FindingsView sel={sel()} />, 'en');
    const head = /<th[^>]*>Status<\/th>/.exec(markup);
    expect(head, 'a Status header').not.toBeNull();
    expect(head![0]).not.toContain('ct-wide-only');
    expect(markup).not.toMatch(/<td class="ct-wide-only">(open|closed|accepted)/);
  });
});
