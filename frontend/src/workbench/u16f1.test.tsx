// U16-F1: the shared views, the pages and the governance views, one test per row of the U16-R2 triage that this unit owns
// (VS-1 to VS-11, PR-C01 and V01-1 to V01-5, the shared parts of V21-1/3/4). Each is written to fail on the defect the
// second capture review found, in both languages where the defect is a language one.
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../lib/contract.types';
import { setLang } from './c03/u6-testkit';
import { ChartOverTable } from './c06/format';
import { FindingsCard } from './c06/C06Common';
import { ChartAbove } from './c16/C16Common';
import { LabelledOverTable } from './c20/U14Common';
import { FindingsView } from './FindingsView';
import * as ModelViews from './ModelViews';
import { COMMITTED } from '../lib/policy';
import { defaultChallenger } from './model';
import { SeverityStatusBars, AppetiteSection } from './governance/RegisterView';
import { ReportDocument } from './governance/ReportView';
import { BatteryView } from './ValidationViews';
import { Table } from '../pages/U6Sections';
import * as Benchmark from '../pages/Benchmark';
import * as Figures from '../architecture/figures';

// the module this unit adds: loaded by name so that a missing file fails its tests, not the whole file
const C01Text = await import(/* @vite-ignore */ './c01Text').catch(() => ({}));
const here = (rel: string) => new URL(rel, import.meta.url);
const text = (rel: string) => readFileSync(here(rel), 'utf8');
const json = <T,>(rel: string): T => JSON.parse(text(rel)) as T;
const html = (el: ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
const plain = (markup: string) => markup.replace(/<[^>]*>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/\s+/g, ' ');
const LANGS = ['en', 'es'] as const;
afterEach(() => setLang('en'));

const css = text('../styles/contraste.css');
/** The rules inside every `@media (max-width: <px>px)` block of the product stylesheet, braces balanced. */
function media(px: number): string {
  const out: string[] = [];
  const re = new RegExp(`@media \\(max-width: ${px}px\\)\\s*\\{`, 'g');
  for (let m = re.exec(css); m; m = re.exec(css)) {
    let depth = 1;
    let i = m.index + m[0].length;
    const start = i;
    while (i < css.length && depth) depth += css[i] === '{' ? 1 : css[i] === '}' ? -1 : 0, i++;
    out.push(css.slice(start, i - 1));
  }
  return out.join('\n');
}

describe('VS-1: below 900 px a table box never collapses (the stack flows naturally)', () => {
  const boxes = [
    ['ChartOverTable', <ChartOverTable chart={<i>chart</i>}><table data-t /></ChartOverTable>],
    ['LabelledOverTable', <LabelledOverTable chart={<i>chart</i>}><table data-t /></LabelledOverTable>],
    ['ChartAbove', <ChartAbove chart={<i>chart</i>}><table data-t /></ChartAbove>],
  ] as const;
  for (const [name, el] of boxes) {
    it(`${name} gives its boxes classes the narrow stylesheet can release, not inline caps`, () => {
      const markup = html(el);
      expect(markup).not.toMatch(/max-height/);
      expect(markup).toMatch(/class="ct-stack-(table|rest)"/);
      expect(markup).toMatch(/class="ct-stack-(chart|fixed)"/);
      // the card body flows on a phone through the shell's contract (0.19.1, SHC-100), never a product rule on .caos-plot-body
      expect(markup).toMatch(/class="ct-stack" data-caos-flow=""/);
    });
  }
  it('FindingsEvidenceCard keeps no inline cap on its table box', () => {
    expect(text('./c21/FindingsEvidence.tsx')).not.toMatch(/maxHeight/);
  });
  it('the 900 px stylesheet releases the stack: natural height, no cap, the card body grows with it', () => {
    const narrow = media(900);
    expect(narrow).toMatch(/\.ct-stack\s*\{[^}]*height:\s*auto/);
    expect(narrow).toMatch(/\.ct-stack-table[^{]*\{[^}]*max-height:\s*none/);
    // it flows down, and a table wider than its card scrolls sideways in its own box: the shell's card body hides what overflows
    // it, so `overflow: visible` cut the right columns at 390 (U16-R2b, c03 M2, c11 B1, c12 B3, c15 B1)
    expect(narrow).toMatch(/\.ct-stack-table[^{]*\{[^}]*overflow-x:\s*auto;\s*overflow-y:\s*visible/);
    expect(narrow).not.toMatch(/\.ct-stack-table[^{]*\{[^}]*overflow:\s*visible/);
    expect(narrow).toMatch(/:has\(> table\.caos-table\)[^{]*\{[^}]*overflow-x:\s*auto/);
    // a column is hidden on a phone only when its value is repeated under the row text
    expect(media(640)).toMatch(/td\.ct-wide-only\.ct-repeated/);
    expect(media(640)).not.toMatch(/^\s*\.ct-wide-only\s*\{\s*display:\s*none/m);
    // the product restyles no shell class: the card body's flow is the shell's (data-caos-flow, 0.19.1)
    expect(css).not.toMatch(/\.caos-plot-body:has|\.caos-plot\.fill\s*>\s*\.caos-plot-body/);
    expect(css).not.toMatch(/(^|[\s,]})?\.equation\s*[,{]/m);
  });
});

describe('VS-2 and V01-4: the status of a finding is reachable at 390', () => {
  const c06 = json<VariantArtifact>('../../../data/derived/C06/rd-2020-06.json');
  for (const lang of LANGS) {
    it(`C06 FindingsCard prints the status under the finding in ${lang}`, () => {
      setLang(lang);
      const markup = html(<FindingsCard variant={c06} />);
      expect(markup).toMatch(/class="ct-narrow-only"/);
      expect(markup).toContain(lang === 'es' ? 'abierto' : 'open');
    });
  }
  it('the stylesheet shows the narrow-only status below 641 px and hides it above', () => {
    expect(css).toMatch(/\.ct-narrow-only\s*\{\s*display:\s*none/);
    expect(media(640)).toMatch(/\.ct-narrow-only\s*\{\s*display:\s*block/);
  });
});

describe('VS-3: a stacked bar prints no count a thin segment cannot hold', () => {
  const findings = json<{ rows: Parameters<typeof SeverityStatusBars>[0]['rows']; counts: { by_severity: Record<string, number> } }>('../../../data/derived/governance/findings.json');
  for (const lang of LANGS) {
    it(`no segment of the S4 bar holds text, and the counts are stated beside it in ${lang}`, () => {
      setLang(lang);
      const markup = html(<SeverityStatusBars rows={findings.rows} />);
      for (const seg of markup.match(/<span[^>]*data-segment="[^"]*"[^>]*>[^<]*<\/span>/g) ?? []) expect(seg.replace(/<[^>]*>/g, '').trim()).toBe('');
      const s4 = findings.rows.filter((r) => r.severity === 'S4');
      const open = s4.filter((r) => r.status === 'open').length;
      const bar = markup.slice(markup.indexOf('data-severity-bar="S4"'));
      expect(plain(bar.slice(0, bar.indexOf('data-severity-bar="', 10) > 0 ? bar.indexOf('data-severity-bar="', 10) : bar.length))).toContain(`${lang === 'es' ? 'abierto' : 'open'} ${open}`);
    });
  }
});

describe('VS-4: a report table cell is translated, not printed as a raw token', () => {
  const report = json<Parameters<typeof ReportDocument>[0]['report']>('../../../data/derived/governance/reports/C01-taiwan.json');
  it('the Spanish report has no raw light, role or status token as a cell', () => {
    setLang('es');
    const markup = html(<ReportDocument report={report} />);
    for (const token of ['not_evaluated', 'risk_accepted', 'validated_closed', 'challenger', 'benchmark', 'champion']) expect(markup, token).not.toMatch(new RegExp(`>${token}<`));
    expect(plain(markup)).toMatch(/ámbar|rojo|verde/);
  });
  it('the English report names a status in words, not as an identifier', () => {
    setLang('en');
    const markup = html(<ReportDocument report={report} />);
    for (const token of ['not_evaluated', 'risk_accepted', 'validated_closed']) expect(markup, token).not.toMatch(new RegExp(`>${token}<`));
  });
});

describe('VS-5: the appetite names the rows it counts', () => {
  const appetite = json<Parameters<typeof AppetiteSection>[0]['appetite']>('../../../data/derived/governance/appetite.json');
  const findings = json<{ counts: { total: number } }>('../../../data/derived/governance/findings.json');
  for (const lang of LANGS) {
    it(`states ${findings.counts.total} register rows and the inventory's own in ${lang}`, () => {
      setLang(lang);
      const Section = AppetiteSection as unknown as (p: { appetite: unknown; registerRows: number }) => ReactElement;
      const p = plain(html(<Section appetite={appetite} registerRows={findings.counts.total} />));
      const extra = appetite.population.findings - findings.counts.total;
      expect(extra).toBeGreaterThan(0);
      expect(p).toContain(String(findings.counts.total));
      expect(p).toContain(String(appetite.population.findings));
      expect(p).toMatch(lang === 'es' ? /del propio inventario/ : /of the inventory itself/);
    });
  }
});

describe('VS-6: the Truth column of C05 is in words', () => {
  it('the source no longer prints the enum', () => {
    expect(text('../pages/C05Sections.tsx')).not.toMatch(/<td>\{v\.provenance\.truth_status\}<\/td>/);
    expect(text('../pages/C05Sections.tsx')).toMatch(/TRUTH_TEXT/);
  });
});

describe('VS-7: a long text cell wraps instead of widening the table', () => {
  it('the generic table wraps a cell of more than a few words, whatever its column', () => {
    const markup = html(<Table head={['A', 'B', 'C']} rows={[['row', '1', 'not available (the document holds no paired test for this rung, so none is shown)']]} />);
    expect(markup).toMatch(/<td class="caos-col-text">not available \(the document/);
  });
});

describe('VS-8: the lanes say what D16-9 decided', () => {
  it('neither the sentence nor the diagram announces Pyodide as the next step', () => {
    const svg = text('../architecture/02-lanes.svg');
    expect(svg).not.toMatch(/Next: the engine in the browser|once on PyPI/);
    expect(text('../pages/Implementation.tsx')).not.toMatch(/The next step is riskvalidation in the browser/);
    expect(svg).toMatch(/parity tests/);
    expect(svg).toMatch(/Pyodide/);
  });
});

describe('VS-9: a wide diagram is read at native size in a scroll box on a phone', () => {
  it('Inline wraps the figure in a region that scrolls, with a hint', () => {
    const markup = html(<Figures.OverviewFigure />);
    expect(markup).toMatch(/class="ct-fig-scroll"/);
    expect(markup).toMatch(/tabindex="0"/);
    expect(media(900)).toMatch(/\.ct-fig-scroll[^{]*svg\s*\{[^}]*min-width:\s*\d+px/);
  });
});

describe('VS-10: the Benchmark robustness chart has a table of its variants', () => {
  it('RobustnessTable lists every variant with both AUCs', () => {
    const T = (Benchmark as unknown as { RobustnessTable?: (p: { rows: Array<{ n: number; title: string; scorecard: number | null; best: number }> }) => ReactElement }).RobustnessTable;
    expect(T).toBeTypeOf('function');
    const Cmp = T!;
    const markup = html(<Cmp rows={[{ n: 1, title: 'Drift', scorecard: 0.7123, best: 0.7456 }, { n: 2, title: 'Noise', scorecard: null, best: 0.7 }]} />);
    expect(markup).toMatch(/data-table="robustness"/);
    expect(plain(markup)).toContain('0.712');
    expect((markup.match(/<tr/g) ?? []).length).toBe(3);
  });
});

describe('VS-11: the methodology prose counts the register as the register does', () => {
  const findings = json<{ counts: { total: number; by_case: unknown[] } }>('../../../data/derived/governance/findings.json');
  it('states the total rows and the cases of findings.json, in both languages', () => {
    const src = text('../pages/methodology/governance.tsx');
    expect(src).not.toMatch(/447/);
    expect(src).toContain(`${findings.counts.total} finding rows in ${findings.counts.by_case.length} cases`);
    expect(src).toContain(`${findings.counts.total} filas de hallazgos en ${findings.counts.by_case.length} casos`);
  });
});

describe('V01-1, V01-2, V01-5: the EBM panels', () => {
  const models = json<ModelsArtifact>('../../../data/derived/C01/models-taiwan.json');
  const ebm = (models.model.find((m) => m.id === 'P3-ebm')?.details as { export: unknown }).export;
  const shapes = (ModelViews as unknown as { ebmShapes?: (ex: unknown, fit: unknown, lang: 'en' | 'es') => Array<{ name: string; x: number[]; y: number[]; xLabel: { en: string; es: string } }> }).ebmShapes;
  it('plots a category at its own code, not at its position', () => {
    expect(shapes).toBeTypeOf('function');
    const education = shapes!(ebm, models.fit, 'en').find((s) => s.name === 'EDUCATION');
    expect(education).toBeDefined();
    const cats = (ebm as { features: Array<{ name: string; levels: Array<{ categories?: Record<string, number> }> }>; terms: Array<{ name: string; scores: number[] }> });
    const levels = cats.features.find((f) => f.name === 'EDUCATION')!.levels[0].categories!;
    const scores = cats.terms.find((t) => t.name === 'EDUCATION')!.scores;
    education!.x.forEach((x, i) => expect(education!.y[i]).toBe(scores[levels[String(x)]]));
  });
  it('names the unit of a money feature on its axis, in both languages', () => {
    const limit = shapes!(ebm, models.fit, 'en').find((s) => s.name === 'LIMIT_BAL');
    if (limit) {
      expect(limit.xLabel.en).toContain('NT dollars');
      expect(limit.xLabel.es).not.toContain('dollars');
    }
  });
  it('the Spanish share axis of the scorecard fits a short plot', () => {
    expect(text('./ModelViews.tsx')).not.toContain("es: 'Fracción del grupo'");
  });
});

describe('V01-3: six small multiples are one per row on a phone, each tall enough to read', () => {
  it('the 900 px stylesheet makes the grid one column of fixed-height rows and lets the card grow', () => {
    const narrow = media(900);
    expect(narrow).toMatch(/\.ct-grid6-fill\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
    expect(narrow).toMatch(/\.ct-grid6-fill[^{]*\{[^}]*grid-auto-rows:\s*\d+px/);
    // the card grows through the shell's flow contract (0.19.1, SHC-100): the grid carries data-caos-flow
    expect(text('./ModelViews.tsx') + text('./c03/ModelViews.tsx')).toMatch(/className="ct-grid6-fill" data-caos-flow=""/);
  });
});

describe('PR-C01: no English word in the Spanish C01 views', () => {
  it('names a currency in the language', () => {
    const c = C01Text as unknown as { currencyName: (u: string) => { en: string; es: string } };
    expect(c.currencyName('NT dollars').es).toMatch(/dólares/);
    expect(c.currencyName('NT dollars').es).not.toMatch(/dollars/);
    expect(c.currencyName('DM')).toEqual({ en: 'Deutsche Mark', es: 'marcos alemanes' });
    expect(c.currencyName('USD thousands').en).toBe('USD thousands');
  });
  it('writes a PLTR rule from its parts, with y and the locale decimal sign', () => {
    const c = C01Text as unknown as { ruleText: (r: string, lang: 'en' | 'es') => string };
    expect(c.ruleText('PAY_0 <= 1.5 and PAY_2 <= 1.5', 'es')).toBe('PAY_0 <= 1,5 y PAY_2 <= 1,5');
    expect(c.ruleText('PAY_0 <= 1.5 and PAY_2 <= 1.5', 'en')).toBe('PAY_0 <= 1.5 and PAY_2 <= 1.5');
    expect(c.ruleText('LIMIT_BAL > 145000 and LIMIT_BAL <= 245000', 'es')).toBe('LIMIT_BAL > 145.000 y LIMIT_BAL <= 245.000');
  });
  it('names an engine in Spanish and leaves a library name as written', () => {
    const c = C01Text as unknown as { engineText: (e: string, lang: 'en' | 'es') => string };
    expect(c.engineText('own on optbinning', 'es')).toBe('propio sobre optbinning');
    expect(c.engineText('own', 'en')).toBe('own');
    expect(c.engineText('LightGBM', 'es')).toBe('LightGBM');
    expect(c.engineText('scikit-learn trees and LogisticRegression, own rule extraction', 'es')).not.toMatch(/(own|trees|and)/);
  });
  it('names a design limit in words', () => {
    const c = C01Text as unknown as { designLimit: (id: string) => { en: string; es: string } };
    expect(c.designLimit('single-snapshot').es).toMatch(/una sola foto|única foto/);
    expect(c.designLimit('some-new-limit')).toEqual({ en: 'some-new-limit', es: 'some-new-limit' });
  });
  it('the Spanish findings view prints the design limit in words', () => {
    const index = json<{ cases: Array<{ case_id: string; manifest_path: string }> }>('../../../data/derived/manifests/index.json');
    const entry = index.cases.find((c) => c.case_id === 'C01')!;
    const manifest = json<CaseManifest>(`../../../data/derived/${entry.manifest_path}`);
    const a = manifest.artifacts.find((x) => x.role === 'variant' && x.variant_id === 'holdout')!;
    const variant = json<VariantArtifact>(`../../../data/derived/${a.path}`);
    const models = json<ModelsArtifact>(`../../../data/derived/${a.models_ref}`);
    const sel = { data: { manifest, variant, models }, challenger: defaultChallenger(variant), alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 };
    setLang('es');
    const markup = plain(html(<FindingsView sel={sel as never} />));
    expect(markup).not.toContain('single-snapshot');
  });
});

describe('V21-3 and V21-4: the evidence charts keep room for their axes', () => {
  it('each evidence chart has at least 16 rem and no inline cap on the table', () => {
    const src = text('./c21/FindingsEvidence.tsx');
    expect(src).not.toMatch(/minHeight: '12rem'/);
    expect(src).toMatch(/--ct-chart-min/);
  });
});

describe('minors of the shared files', () => {
  const index = json<{ cases: Array<{ case_id: string; manifest_path: string }> }>('../../../data/derived/manifests/index.json');
  const manifest = json<CaseManifest>(`../../../data/derived/${index.cases.find((c) => c.case_id === 'C01')!.manifest_path}`);
  const a = manifest.artifacts.find((x) => x.role === 'variant' && x.variant_id === 'holdout')!;
  const variant = json<VariantArtifact>(`../../../data/derived/${a.path}`);
  const models = json<ModelsArtifact>(`../../../data/derived/${a.models_ref}`);
  const sel = { data: { manifest, variant, models }, challenger: defaultChallenger(variant), alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 };
  it('b01 m2: the descriptive Kolmogorov-Smirnov row shows the distance, not the p-value', () => {
    const ks = variant.tests.find((t) => t.test_id === 'disc.ks' && t.model_id === 'P1-scorecard')!;
    const d = (ks.metric ?? ks.statistic) as number;
    const row = plain(html(<BatteryView sel={sel as never} />)).split('Kolmogorov-Smirnov (descriptive)')[1].slice(0, 40);
    expect(row).toContain(formatNumber(d, 'en', { decimals: 3 }));
  });
  it('b06 m4: the findings tables read from the top of the row', () => {
    expect(html(<FindingsView sel={sel as never} />)).toMatch(/class="caos-table ct-top"/);
  });
});

describe('b13 m5: the momentum coefficient the methodology quotes is the committed one', () => {
  it('rounds the fitted c of alpha 0.125 as momentum.json holds it', () => {
    const d = json<{ outputs: { ladder: { values: number[] }; rungs: Array<{ coefficient: { mean: number } }> } }>('../../../data/derived/C04/momentum.json').outputs;
    const c = d.rungs[d.ladder.values.indexOf(0.125)].coefficient.mean;
    const src = text('../pages/MethodologyTransitions.tsx');
    expect(src).toContain(`a fitted c of ${formatNumber(c, 'en', { decimals: 3 })}:`);
    expect(src).toContain(`un c ajustado de ${formatNumber(c, 'es', { decimals: 3 })}:`);
  });
});

describe('b11 m7: the Introduction does not give the groups of C01 as the groups of every case', () => {
  it('says that the selected case names the groups', () => {
    const src = text('../pages/Introduction.tsx');
    expect(src).toContain('which the selected case names; the groups of C01 are');
    expect(src).toContain('que nombra el caso elegido; los grupos de C01 son');
  });
});
