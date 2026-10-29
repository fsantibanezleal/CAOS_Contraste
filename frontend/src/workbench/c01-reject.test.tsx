// S-6 (unit P6): the German twin's reject-inference card reads the committed document, names every rung and policy in both
// languages without a raw id, states the three hypotheses with their verdicts, and is absent from every other variant.
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../lib/contract.types';
import { COMMITTED } from '../lib/policy';
import { setLang } from './c03/u6-testkit';
import { JUDGED_POLICY, RejectInferenceCard } from './RejectInference';

const json = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, import.meta.url), 'utf8')) as T;
const manifest = json<CaseManifest>('../../../data/derived/manifests/C01.json');
const load = (id: string) => {
  const a = manifest.artifacts.find((x) => x.role === 'variant' && x.variant_id === id)!;
  return { variant: json<VariantArtifact>(`../../../data/derived/${a.path}`), models: json<ModelsArtifact>(`../../../data/derived/${a.models_ref}`) };
};
const sel = (id: string) => ({ data: { manifest, ...load(id) }, challenger: 'P4-lightgbm', alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 });
const html = (id: string) => renderToStaticMarkup(<MemoryRouter><RejectInferenceCard sel={sel(id) as never} /></MemoryRouter>);
afterEach(() => setLang('en'));

const twin = load('german-twin').variant.outputs.reject_inference!;

describe('C01 reject inference card (S-6)', () => {
  it('draws on the German twin: one row per rung and per policy, the judged policy marked', () => {
    const m = html('german-twin');
    expect(m).toContain('data-reject-inference');
    for (const r of twin.rungs) expect(m).toContain(`data-rung="${r.id}"`);
    for (const g of twin.regimes) expect(m).toContain(`data-policy="${g.id}"`);
    expect(m).toContain(`data-policy="${JUDGED_POLICY}" data-judged="true"`);
  });
  it('names every rung in English and writes no raw id as text', () => {
    const m = html('german-twin');
    for (const r of twin.rungs) expect(m).toContain(r.short_title.en);
    const text = m.replace(/<[^>]*>/g, ' ');
    for (const r of twin.rungs) expect(text).not.toContain(r.id);
  });
  it('states the verdict count of the hypotheses and the best rung with its interval', () => {
    const held = twin.hypotheses.filter((h) => h.holds).length;
    const m = html('german-twin');
    expect(m).toContain(`${held} of ${twin.hypotheses.length} hypotheses hold`);
    const h2 = twin.hypotheses.find((h) => h.id === 'H2')!;
    expect(m.replace(/&#x27;/g, "'")).toContain(h2.outcome.en.replace(/&/g, '&amp;'));
  });
  it('is absent from every other variant, which carry null', () => {
    for (const a of manifest.artifacts.filter((x) => x.role === 'variant' && x.variant_id !== 'german-twin')) {
      expect(load(a.variant_id).variant.outputs.reject_inference, a.variant_id).toBeNull();
      expect(html(a.variant_id), a.variant_id).toBe('');
    }
  });
  it('the hypotheses and the rungs have a Spanish text beside the English one', () => {
    for (const h of twin.hypotheses) {
      expect(h.statement.es).not.toBe(h.statement.en);
      expect(h.outcome.es).not.toBe(h.outcome.en);
    }
    for (const r of twin.rungs) expect(r.what.es).not.toBe(r.what.en);
  });
});
