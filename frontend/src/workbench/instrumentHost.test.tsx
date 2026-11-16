// The instrument host (BL-102): the component that calls a case's `useInstrument` is keyed by the case id, so a case change
// mounts a new one and each mount calls exactly one hook; the pending and failed states are the shell's declared ones.
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { createInstrumentLoader, instrumentLoaders } from './registry';
import { failedInstrument, instrumentSlot, instrumentStatus, pendingInstrument } from './instrumentHost';
import type { CaseData } from '../api/artifacts';
import type { Instrument } from './registry';

const data = (id: string) => ({ manifest: { case_id: id } }) as unknown as CaseData;
const instrumentOf = (id: string): Instrument => ({ sel: id, rail: [], groups: [], compare: { label: { en: 'v', es: 'v' }, lane: 'replay', provenance: 'real' as never, content: <i /> }, context: { content: <i /> }, controls: {} });

describe('the instrument host', () => {
  it('is keyed by the case id: a case change mounts another host', () => {
    const a = instrumentSlot({ caseId: 'C04', hook: () => null, data: null, setVariantId: () => undefined, onInstrument: () => undefined });
    const b = instrumentSlot({ caseId: 'C05', hook: () => null, data: null, setVariantId: () => undefined, onInstrument: () => undefined });
    expect(a.key).toBe('C04');
    expect(b.key).toBe('C05');
    expect(a.type).toBe(b.type);
  });

  it('calls the hook of its case once per render and no other: after a switch from A to B no hook of A runs', () => {
    const hookA = vi.fn((d: CaseData | null) => (d ? instrumentOf('A') : null));
    const hookB = vi.fn((d: CaseData | null) => (d ? instrumentOf('B') : null));
    const mk = (caseId: string, hook: typeof hookA) => instrumentSlot({ caseId, hook, data: data(caseId), setVariantId: () => undefined, onInstrument: () => undefined });
    renderToStaticMarkup(mk('CA', hookA) as ReactElement);
    expect(hookA).toHaveBeenCalledTimes(1);
    expect(hookB).not.toHaveBeenCalled();
    hookA.mockClear();
    renderToStaticMarkup(mk('CB', hookB) as ReactElement);
    expect(hookB).toHaveBeenCalledTimes(1);
    expect(hookA).not.toHaveBeenCalled();
  });

  it('hands the hook the data of the selected case, never another', () => {
    const seen: Array<string | undefined> = [];
    const hook = (d: CaseData | null) => {
      seen.push(d?.manifest.case_id);
      return null;
    };
    renderToStaticMarkup(instrumentSlot({ caseId: 'C11', hook, data: data('C11'), setVariantId: () => undefined, onInstrument: () => undefined }));
    expect(seen).toEqual(['C11']);
  });
});

describe('the state of a case instrument', () => {
  const loaders = instrumentLoaders({ './c06/instrument.tsx': async () => ({ useInstrument: () => null }) });
  it('is none for a case without an instrument file, loading before the module is there, ready after, failed on a failed import', async () => {
    const l = createInstrumentLoader(loaders);
    expect(instrumentStatus(l, 'C01', null)).toEqual({ state: 'none' });
    expect(instrumentStatus(l, null, null)).toEqual({ state: 'none' });
    expect(instrumentStatus(l, 'C06', null)).toEqual({ state: 'loading' });
    await l.load('C06');
    expect(instrumentStatus(l, 'C06', null).state).toBe('ready');
    expect(instrumentStatus(l, 'C06', { caseId: 'C06', message: 'offline' }).state).toBe('ready');
    const l2 = createInstrumentLoader(loaders);
    expect(instrumentStatus(l2, 'C06', { caseId: 'C06', message: 'offline' })).toEqual({ state: 'failed', message: 'offline' });
    // a failure of another case does not mark this one
    expect(instrumentStatus(l2, 'C06', { caseId: 'C05', message: 'offline' })).toEqual({ state: 'loading' });
  });
});

describe('the pending and failed instruments', () => {
  const html = (el: ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
  it('the pending instrument draws the shell pending state in every group, the variants and the context', () => {
    const p = pendingInstrument(null);
    const markup = [...p.groups.map((g) => g.content), p.compare.content, p.context.content].map(html).join('');
    expect(p.groups.map((g) => g.id)).toEqual(['model', 'validation', 'impact', 'findings']);
    expect((markup.match(/data-state="loading"/g) ?? []).length).toBe(6);
  });
  it('the failed instrument is the absent instrument with the reason, in both languages', () => {
    const f = failedInstrument('C11', 'Failed to fetch dynamically imported module', null);
    const markup = html(f.groups[0].content);
    expect(markup).toContain('data-state="unavailable"');
    expect(markup).toContain('Failed to fetch dynamically imported module');
    expect(f.groups).toHaveLength(4);
  });
});
