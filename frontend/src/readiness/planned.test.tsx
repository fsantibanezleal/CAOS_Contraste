// A planned case (an index entry whose manifest the readiness lists as missing) is declared absent in every group:
// one data-state="unavailable" line with a reason in both languages, never a chart, a number or a test result, never
// data-state="loading" (the gate waits on loading), and the Context group shows the index entry.
import { useLangStore } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseIndex } from '../lib/contract.types';
import { absentInstrument, plannedReason } from './Planned';

type Entry = CaseIndex['cases'][number];
const entry: Entry = {
  case_id: 'C06',
  title: { en: 'Mortgage lifetime PD, IFRS 9 staging and ECL', es: 'PD de vida de hipotecas, etapas IFRS 9 y ECL' },
  category: { en: 'Provisions', es: 'Provisiones' },
  category_id: 'provisions',
  kind: 'real',
  manifest_path: 'manifests/C06.json',
};
const why = { en: '18 of 22 cases are planned and not built yet: C06.', es: '18 de 22 casos están planificados y aún no construidos: C06.' };

// the server render reads the store's initial state (zustand), so the test sets the language there
const init = useLangStore.getInitialState() as { lang: 'en' | 'es' };
afterEach(() => {
  init.lang = 'en';
});
function html(el: ReactElement, lang: 'en' | 'es') {
  init.lang = lang;
  return renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
}

describe('the absent instrument of a planned case', () => {
  const inst = absentInstrument(plannedReason(entry.title, why), entry);
  const views = [...inst.groups.map((g) => [g.id, g.content] as const), ['variants', inst.compare.content] as const, ['context', inst.context.content] as const];
  it('has the four groups, the variants and the context', () => {
    expect(inst.groups.map((g) => g.id)).toEqual(['model', 'validation', 'impact', 'findings']);
  });
  it.each(['en', 'es'] as const)('every group draws one unavailable line with a reason, and nothing else, in %s', (lang) => {
    for (const [id, content] of views) {
      const out = html(content, lang);
      expect(out.match(/data-state="unavailable"/g), id).toHaveLength(1);
      expect(out, id).not.toContain('data-state="loading"');
      expect(out, id).not.toMatch(/<canvas|<svg|<table|data-state="ready"/);
      const text = out.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
      expect(text.length, id).toBeGreaterThan(40);
    }
  });
  it('the reason names the case, says planned and not built, and keeps the readiness reason, each language apart', () => {
    const en = html(inst.groups[0].content, 'en');
    const es = html(inst.groups[0].content, 'es');
    expect(en).toContain('Mortgage lifetime PD');
    expect(en).toMatch(/planned/);
    expect(en).toContain(why.en);
    expect(es).toContain('PD de vida de hipotecas');
    expect(es).toMatch(/planificado/);
    expect(es).toContain(why.es);
    expect(es).not.toContain('planned and not built');
  });
  it('the context group shows the title, the category and the data kind of the index entry', () => {
    const en = html(inst.context.content, 'en');
    expect(en).toContain('Mortgage lifetime PD');
    expect(en).toContain('Provisions');
    expect(en).toContain('real');
    expect(html(inst.context.content, 'es')).toContain('Provisiones');
  });
  it('declares no live control and no rail section that draws', () => {
    expect(inst.controls).toEqual({});
  });
});
