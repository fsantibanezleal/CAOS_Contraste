// U16-F5: the shared views and the pages, fix round 2. One describe per row or minor of the U16-R2 triage that this unit
// owns; each fails on the defect the second capture review found, in both languages where the defect is a language one.
import { CitationsProvider, useLangStore } from '@fasl-work/caos-app-shell';
import { readFileSync, readdirSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { C04VariantsProvider } from '../content/cases/C04Results';
import { CITATIONS } from '../content/citations';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { C04Benchmark, C04Experiments } from '../pages/C04Sections';
import * as BenchmarkPage from '../pages/Benchmark';
import * as U6 from '../pages/U6Sections';
import { batch3ExperimentTables } from '../pages/Batch3Sections';
import { MatrixDrawing, SensitivityTable } from './governance/TierMatrix';
import { tierColor } from './governance/DependencyMap';
import { tierOf, type GovInventory, type GovReport } from './governance/model';
import { ReportDocument } from './governance/ReportView';
import { ContextView } from './ContextView';
import { ImpactView } from './ImpactView';
import { LadderView } from './ModelViews';
import { BatteryView, CalibrationView, DiscriminationView, StabilityView } from './ValidationViews';
import { COMMITTED } from '../lib/policy';
import { defaultChallenger } from './model';
import type { ModelsArtifact } from '../lib/contract.types';

const here = (rel: string) => new URL(rel, import.meta.url);
const text = (rel: string) => readFileSync(here(rel), 'utf8');
const css = text('../styles/contraste.css');
const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;

type Lang = 'en' | 'es';
function setLang(lang: Lang) {
  (useLangStore.getInitialState() as { lang: Lang }).lang = lang;
  useLangStore.setState({ lang });
}
afterEach(() => setLang('en'));
/** A server render as the app mounts it, in one language. */
const html = (el: ReactElement, lang: Lang = 'en', extra: ReactElement | null = null): string => {
  setLang(lang);
  return renderToStaticMarkup(
    <MemoryRouter>
      <CitationsProvider items={CITATIONS}>{extra ?? el}</CitationsProvider>
    </MemoryRouter>,
  );
};
const plain = (markup: string) => markup.replace(/<[^>]*>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/\s+/g, ' ');

/** The rules inside every `@media (<feature>: <px>px)` block of the product stylesheet, braces balanced. */
function media(feature: 'max-width' | 'min-width', px: number): string {
  const out: string[] = [];
  const re = new RegExp(`@media \\(${feature}: ${px}px\\)\\s*\\{`, 'g');
  for (let m = re.exec(css); m; m = re.exec(css)) {
    let depth = 1;
    let i = m.index + m[0].length;
    const start = i;
    while (i < css.length && depth) depth += css[i] === '{' ? 1 : css[i] === '}' ? -1 : 0, i++;
    out.push(css.slice(start, i - 1));
  }
  return out.join('\n');
}

describe('VS-1, V02-4, V06-5, V21-1: a table of a filling card keeps its rows at 390', () => {
  const narrow = media('max-width', 900);
  it('a scroll box (.ct-scroll, also inside a stack) flows below 900 px instead of keeping the clamp of the card', () => {
    expect(narrow).toMatch(/\.ct-scroll[^{]*\{[^}]*height:\s*auto/);
    expect(narrow).toMatch(/\.ct-stack\s*>\s*\.ct-scroll[^{]*\{[^}]*flex:\s*none/);
  });
  it('the panels of a C22 family flow as well, with their card body', () => {
    expect(narrow).toMatch(/\.ct-panels-fill\s*\{[^}]*height:\s*auto/);
    // the card body grows through the shell's flow contract (0.19.1, SHC-100): the panels carry data-caos-flow
    expect(text('./c22/Views.tsx')).toMatch(/className="ct-panels-fill" data-caos-flow=""/);
  });
  it('the card body that holds a scroll box grows with it (the shell flows it: every scroll box carries data-caos-flow)', () => {
    const shell = text('../../node_modules/@fasl-work/caos-app-shell/styles.css');
    expect(shell).toMatch(/\.caos-plot\.fill > \.caos-plot-body:has\(> \.caos-table, \[data-caos-flow\]\)\s*\{[^}]*height:\s*auto/);
    for (const f of ['./c05/SpViews.tsx', './c22/Views.tsx', './c16/C16Common.tsx']) expect(text(f)).not.toMatch(/className="ct-scroll"(?! data-caos-flow)/);
  });
});

describe('V21-4: each evidence chart keeps room for at least three y ticks, its title, legend and readout', () => {
  const src = text('./c21/FindingsEvidence.tsx');
  it('asks for at least 21 rem a chart (the plot kept 76 px of 15 rem at 1280 x 800)', () => {
    const m = /'--ct-chart-min': '(\d+(?:\.\d+)?)rem'/.exec(src);
    expect(m).not.toBeNull();
    expect(Number(m![1])).toBeGreaterThanOrEqual(21);
  });
  it('the card of the evidence is not shorter than its drawings below 900 px either', () => {
    expect(media('max-width', 900)).toMatch(/finding-evidence[^{]*\.ct-stack-chart[^{]*\{[^}]*height:/);
  });
});

describe('V21-5: a scroll box never ends in a line cut through its middle', () => {
  const wide = media('min-width', 901);
  // the bottom fade of V21-5 fell on a blank gap when a box ended on a row boundary (R4 ruling 8): the cue is now the measured band of
  // layout.ts over the box's last visible line (u16f12a.test.tsx), and a wide box keeps its gap under its last row
  for (const cls of ['.ct-stack-table', '.ct-stack-rest', '.ct-stack-fill', '.ct-scroll']) {
    it(`${cls} keeps a gap under its last row and draws the measured cue`, () => {
      const rule = new RegExp(`${cls.replace('.', '\\.')}[^{}]*\\{[^}]*\\}`, 'g');
      const rules = (wide.match(rule) ?? []).join('\n');
      expect(rules).toMatch(/padding-bottom:/);
      expect(css).toMatch(new RegExp(`:is\\([^)]*\\${cls}[^)]*\\)\\[data-more-y\\]::after`));
    });
  }
});

describe('PR-C04: the Experiments and Benchmark copy of C04 in Spanish carries the Spanish attribution', () => {
  const manifest = read<CaseManifest>('manifests/C04.json');
  const variants = manifest.artifacts.filter((a) => a.role === 'variant').map((a) => read<VariantArtifact>(a.path));
  const page = (el: ReactElement, lang: Lang) => html(el, lang, <C04VariantsProvider variants={variants}>{el}</C04VariantsProvider>);
  for (const [name, el] of [['Experiments', <C04Experiments manifest={manifest} />], ['Benchmark', <C04Benchmark manifest={manifest} />]] as const) {
    it(`${name}: no English attribution sentence in the Spanish view, the Spanish one in its place`, () => {
      const es = plain(page(el, 'es'));
      expect(es).not.toContain('Source: ESMA CEREP');
      expect(es).toContain('Fuente: ESMA CEREP; tablas transformadas por Contraste');
    });
    it(`${name}: the English view keeps the source registry's wording`, () => {
      expect(plain(page(el, 'en'))).toContain('Source: ESMA CEREP; tables transformed by Contraste');
    });
  }
});

describe('b11 m1: Spanish never renders git "commit" as "comprometer"', () => {
  const dirs = ['../pages/', '../pages/methodology/', '../architecture/'];
  const flat = dirs.flatMap((d) => readdirSync(here(d)).filter((f) => /\.(tsx|ts|svg)$/.test(f) && !/\.test\./.test(f)).map((f) => `${d}${f}`));
  // every view and content file too (the integrator, after the U16-F6 merge): a case view names the policy it ran under
  const walk = (d: string): string[] =>
    readdirSync(here(d), { withFileTypes: true }).flatMap((e) =>
      e.isDirectory() ? walk(`${d}${e.name}/`) : /\.(tsx|ts)$/.test(e.name) && !/\.test\./.test(e.name) ? [`${d}${e.name}`] : []);
  const files = [...flat, ...walk('./'), ...walk('../content/')];
  const COMMIT_SENSE = /artefactos? comprometid|muestras? comprometid|umbrales comprometid|documentos? comprometid|política comprometida|compromete el pipeline|pipeline compromete|pipeline comprometió|puede(?:n)? comprometerse|se compromete|Compromiso:|manifiesto de licencias comprometido|\(comprometido\)|(?:tabla de puntos|verdad exacta|evidencia|curva de corte|capital|EBM) comprometid/;
  it('reads the files of the pages and the figures', () => expect(files.length).toBeGreaterThan(20));
  for (const f of files) {
    it(`${f.replace('../', '')} uses versionar for what the pipeline commits`, () => {
      expect(COMMIT_SENSE.exec(text(f))?.[0] ?? null).toBeNull();
    });
  }
});

describe('b11 m2 and m3, b12 m3, b13 m3: a box that scrolls sideways at a phone shows a cue', () => {
  const narrow = media('max-width', 900);
  // the equation's cue is the shell's since 0.19.1 (SHC-100): the product restyles no shell class
  it('.equation fades its right edge on a phone in the shell', () => {
    expect(text('../../node_modules/@fasl-work/caos-app-shell/styles.css')).toMatch(/\.equation\s*\{\s*padding-right:\s*1\.5rem;\s*mask-image:\s*linear-gradient\(to right/);
  });
  for (const sel of ['.prose table', '.ct-fig-scroll']) {
    it(`${sel} fades its right edge and keeps a gap after its last column`, () => {
      const rules = (narrow.match(new RegExp(`${sel.replace('.', '\.').replace('.', '\.')}[^{}]*\{[^}]*\}`, 'g')) ?? []).join('\n');
      expect(rules).toMatch(/mask-image:\s*linear-gradient\(to right/);
      expect(rules).toMatch(/padding-right:/);
    });
  }
});

describe('b11 m4 and m5: no negative zero, one p-value format on the pages', () => {
  it('num rounds a tiny negative to an unsigned zero, in both languages', async () => {
    const { num, pct } = await import('../pages/U6Sections');
    for (const lang of ['en', 'es'] as const) {
      expect(num(-2.95e-5, lang, 4)).toBe(lang === 'en' ? '0.0000' : '0,0000');
      expect(num(-0.0004, lang, 3)).toBe(lang === 'en' ? '0.000' : '0,000');
      expect(num(-0.0016, lang, 3)).toMatch(/^-0[.,]002$/);
      expect(pct(-0.000245, lang, 1)).not.toContain('-');
      expect(pct(-0.0261, lang, 1)).toContain('-');
    }
  });
  it('pval keeps three significant digits where num with three decimals printed 0.000', async () => {
    const { pval, num } = await import('../pages/U6Sections');
    expect(num(1.0e-91, 'en', 3)).toBe('0.000');
    expect(pval(1.0e-91, 'en')).not.toBe('0.000');
    expect(pval(0.314, 'en')).toBe('0.314');
    expect(pval(0.314, 'es')).toBe('0,314');
  });
  it('the C02 and C11 page rows read their p-values through pval', () => {
    expect(text('../pages/Batch3Sections.tsx')).toMatch(/pval\(r\.calibration\.hosmer_lemeshow\.p_value/);
    expect(text('../pages/Batch3Sections.tsx')).toMatch(/pval\(pair\.delong_p_value/);
    expect(text('../pages/Wave2Sections.tsx')).toMatch(/pval\(dm\.p_value/);
  });
  it('the Benchmark difference to P1 goes through num', () => {
    expect(text('../pages/Benchmark.tsx')).toMatch(/num\(r\.auc !== null && champ\?\.auc != null \? r\.auc - champ\.auc : null, lang, 4\)/);
  });
});

describe('b11 m6 and m10: one label per rung, the best rung named', () => {
  const c01 = read<CaseManifest>('manifests/C01.json');
  const holdout = read<VariantArtifact>(c01.artifacts.find((a) => a.role === 'variant' && a.variant_id === 'holdout')!.path);
  const c08 = read<CaseManifest>('manifests/C08.json');
  const c08v = read<VariantArtifact>(c08.artifacts.find((a) => a.role === 'variant')!.path);
  const Comparison = BenchmarkPage.Comparison;
  for (const lang of ['en', 'es'] as const) {
    it(`the Benchmark verdict names the rungs the way its table does, never by id (${lang})`, () => {
      const text = plain(html(<Comparison v={holdout} title="C01" />, lang));
      for (const m of holdout.model) expect(text, m.id).not.toContain(m.id);
      const labels = holdout.model.filter((m) => m.id !== 'P0-constant').map((m) => m.short_title[lang]);
      expect(new Set(labels).size).toBe(labels.length);
      for (const l of labels) expect(text).toContain(l);
    });
  }
  it('a rung reads its short title, not "beta Beta regression"', () => {
    const rungName = U6.rungName;
    expect(rungName(c08v as VariantArtifact<unknown>, 'L3-beta', 'en')).toBe('L3 Beta');
    expect(rungName(c08v as VariantArtifact<unknown>, 'L3-beta', 'es')).toBe(c08v.model.find((m) => m.id === 'L3-beta')!.short_title.es);
  });
  it('a rung the document declares absent is named, not shown by its id', () => {
    expect(U6.rungName(c08v as VariantArtifact<unknown>, 'P5-tabpfn', 'es')).toBe('P5 TabPFN');
  });
  it('the robustness table names the best rung of each variant', () => {
    const T = (BenchmarkPage as unknown as { RobustnessTable: (p: { rows: Array<{ n: number; title: string; scorecard: number | null; best: number; bestRung: string }> }) => ReactElement }).RobustnessTable;
    const markup = html(<T rows={[{ n: 1, title: 'Drift', scorecard: 0.7123, best: 0.7456, bestRung: 'P4 LightGBM' }]} />);
    expect(plain(markup)).toContain('P4 LightGBM');
  });
});

describe('b12 m1: the forbidden arc of the protocol figure does not strike through its label', () => {
  it('the label sits below the lowest point of the curve (y 175)', () => {
    const m = /className="dg-axis-label" x=\{W \/ 2\} y=\{(\d+)\} textAnchor="middle">\{t\('forbidden/.exec(text('../pages/DocFigures.tsx'));
    expect(m).not.toBeNull();
    expect(Number(m![1])).toBeGreaterThanOrEqual(192);
  });
});

describe('b12 m4: the tier matrix uses the tier colours of the dependency map', () => {
  const inv = read<GovInventory>('governance/inventory.json');
  const markup = html(<MatrixDrawing inv={inv} width={480} picked={null} />);
  it('every non-empty cell is filled with the colour of its tier', () => {
    const cells = [...markup.matchAll(/data-count="(\d+)" data-tier="(\d)"[^>]*>\s*<rect[^>]*fill="([^"]+)"/g)];
    expect(cells.length).toBe(16);
    let seen = 0;
    for (const [, n, tier, fill] of cells) {
      if (Number(n) === 0) continue;
      seen += 1;
      expect(fill).toBe(tierColor(Number(tier)));
    }
    expect(seen).toBeGreaterThan(0);
    expect(tierOf(4, 4)).toBeGreaterThan(0);
  });
});

describe('b12 m5: the caption of the sensitivity table is above the scroll box, not inside the table', () => {
  const inv = read<GovInventory>('governance/inventory.json');
  it('has a paragraph above the table and no <caption>', () => {
    const markup = html(<SensitivityTable inv={inv} />);
    expect(markup).not.toContain('<caption');
    expect(markup.indexOf('<p')).toBeGreaterThanOrEqual(0);
    expect(markup.indexOf('<p')).toBeLessThan(markup.indexOf('<table'));
  });
});

describe('b12 m6 and m7: the report wording and the narrow outcomes table', () => {
  const report = read<GovReport>('governance/reports/C01-german.json');
  it('a reason after "Not available:" starts with a capital, in both languages', () => {
    for (const lang of ['en', 'es'] as const) {
      const t = plain(html(<ReportDocument report={report} />, lang));
      expect(t).not.toMatch(/(Not available|No disponible): [a-záéíóú]/);
    }
  });
  it('the test counts read word: number, with the plural a count of rows takes (no evaluadas: 31)', () => {
    const t = plain(html(<ReportDocument report={report} />, 'es'));
    expect(t).toMatch(/no evaluadas: \d+/);
    expect(t.split('Filas de prueba:')[1].slice(0, 120)).not.toMatch(/no evaluada \d+/);
    expect(plain(html(<ReportDocument report={report} />, 'en'))).toMatch(/not evaluated: \d+/);
  });
  it('the test cell carries the model and the segment for a phone (the column is wide-only)', () => {
    const markup = html(<ReportDocument report={report} />);
    // the test in words, then its model and segment in words for a phone (U16-R2b: no raw id where a name exists)
    expect(markup).toMatch(/<td class="caos-col-text">Jeffreys<span class="ct-narrow-only">P\d[^<]*, portfolio<\/span>/);
    expect(markup).not.toMatch(/>pd\.jeffreys</);
  });
  it('a scroll box of the report fades its end like every other', () => {
    expect(text('./governance/ReportView.tsx')).not.toMatch(/maxHeight: (360|420), overflow: 'auto'/);
    expect(text('./governance/ReportView.tsx')).toMatch(/ct-fade-scroll/);
  });
  it('the register and the methodology page say "fecha de registro", not "fecha de levantamiento"', () => {
    expect(text('./governance/RegisterView.tsx')).not.toContain('fecha de levantamiento');
    expect(text('../pages/methodology/governance.tsx')).not.toContain('fecha de levantamiento');
    expect(text('./governance/RegisterView.tsx')).toContain('fecha de registro');
  });
});

describe('b12 m11, m12, m13, m9, m14: the Experiments page', () => {
  it('only C01 reads the scorecard paragraph; C04, C05 and C22 read the generic one', () => {
    const src = text('../pages/Experiments.tsx');
    expect(src).not.toMatch(/kind !== 'c04'/);
    expect(src).toMatch(/kind === 'scorecard'/);
  });
  it('the C01 table heads its records column as the holdout records and names the best rung by its short title', () => {
    const src = text('../pages/Experiments.tsx');
    expect(src).toContain("t('Holdout records', 'Registros reservados')");
    expect(src).not.toMatch(/\{r\.best\.id\} \(/);
  });
  const c02 = read<CaseManifest>('manifests/C02.json');
  const c02v = c02.artifacts.filter((a) => a.role === 'variant').map((a) => read<VariantArtifact>(a.path));
  it('C02 transfer: the 1-year row shows an off-diagonal cell and a singular year', () => {
    const [t] = batch3ExperimentTables(c02 as never, c02v as never, 'en');
    const row = t.rows.find((r) => String(r[0]).includes('1 year') || String(r[1]) === '1 year')!;
    const last = String(row[row.length - 1]);
    expect(last).not.toContain('fitted on 1 years');
    expect(last).not.toMatch(/fitted on (\d+) years?, scored on /);
    expect(last).toMatch(/fitted on 1 year,/);
  });
  it('the C09 bias is written in percentage points', () => {
    const c09 = read<CaseManifest>('manifests/C09.json');
    const vs = c09.artifacts.filter((a) => a.role === 'variant').map((a) => read<VariantArtifact<unknown>>(a.path));
    const rows = U6.experimentRows(c09, vs, 'en');
    expect(rows.map((r) => String(r[3])).every((c) => / pp$/.test(c))).toBe(true);
  });
  it('a table amount prints one decimal when scaled so the amounts of a table read alike', () => {
    // a million is "mn" in English, never "m", which reads as milli (R3 c13 m8, the shared compactMoney; U16-F10a)
    expect(U6.money(867_000_000, 'USD', 'en')).toBe('867.0 mn USD');
    expect(U6.money(457_300_000, 'USD', 'en')).toBe('457.3 mn USD');
    expect(U6.money(99_712_000_000, 'USD', 'en')).toBe('99.7 bn USD');
    expect(U6.money(99_600_000_000, 'USD', 'es')).toBe('99,6 mil M USD');
  });
  it('the C10 note of the Experiments page says "superaciones"', () => {
    expect(text('../pages/Wave2Sections.tsx')).not.toContain('las excedencias cuentan');
  });
});

describe('b13 m1, m2, m4: the methodology captions and figures', () => {
  it('no caption writes the entity &ell; (HTML has none, so it printed literally)', () => {
    expect(text('../pages/methodology/aggregation-stress.tsx')).not.toContain('&ell;');
  });
  it('the legend of the share figure names the colours the bars are drawn in, not "grey"', () => {
    const src = text('../pages/methodology/portfolio-capital.tsx');
    expect(src).not.toContain('grey: share of the exposure');
    expect(src).not.toContain('gris: parte de la exposición');
  });
  it('the tier figure takes its colours from the one tier scale of the dependency map, with no hard-coded hex', () => {
    const src = text('../pages/methodology/governance.tsx');
    expect(src).not.toContain('#2d1b69');
    expect(src).toContain('tierColor');
  });
});

// D16-22: the Spanish name is the regulator's own, "Anejo 9" of Circular 4/2017 (b04 m3, b12 m10)
describe('b12 m10: the BdE annex is "Anejo 9" in Spanish on every page, as Banco de España names it', () => {
  for (const f of ['../pages/Benchmark.tsx', '../pages/methodology/provisions.tsx', '../pages/U6Sections.tsx', '../content/coverage/U5.ts', '../content/coverage/base.ts']) {
    it(`${f.replace('../', '')} has no "Anexo 9"`, () => expect(text(f)).not.toContain('Anexo 9'));
  }
});

describe('b01 m6, b04 m6, b10 m13: the disclosure line of the governance opinion is not clipped', () => {
  const src = text('./governance/OpinionBlock.tsx');
  it('has a line height that keeps the descenders, and its box fades like the others', () => {
    expect(src).not.toMatch(/lineHeight: 1,/);
    expect(src).toMatch(/lineHeight: 1\.[3-9]/);
    expect(src).toContain('ct-fade-scroll');
  });
});

describe('b01 m1, m3, m4, m5, m16: the C01 views of the Model and Validation groups', () => {
  const c01 = read<CaseManifest>('manifests/C01.json');
  const entry = c01.artifacts.find((a) => a.role === 'variant' && a.variant_id === 'holdout')!;
  const variant = read<VariantArtifact>(entry.path);
  const models = read<ModelsArtifact>(entry.models_ref as string);
  const sel = { data: { manifest: c01, variant, models }, challenger: defaultChallenger(variant), alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 } as never;
  const view = (el: ReactElement, lang: Lang) => plain(html(el, lang));
  it('m1: the Impact decision says why the live figure differs from the applicant-by-applicant one', () => {
    // the wording U16-F6 settled for the same minor (merged at 093b85e)
    expect(view(<ImpactView sel={sel} />, 'en')).toContain('The live figures interpolate the cut-off curve');
    expect(view(<ImpactView sel={sel} />, 'es')).toContain('Las cifras en vivo interpolan la curva de corte');
  });
  it('m3: the DeLong cell of the battery names the direction of the difference, not only a red light', () => {
    expect(view(<BatteryView sel={sel} />, 'en')).toMatch(/AUC (higher|lower)/);
    expect(view(<BatteryView sel={sel} />, 'es')).toMatch(/AUC (mayor|menor)/);
  });
  it('m4: the interval and the ECE the ladder note names are shown at every width', () => {
    const markup = html(<LadderView sel={sel} />, 'en');
    expect((markup.match(/ct-narrow-only/g) ?? []).length).toBeGreaterThanOrEqual(2 * 7);
  });
  it('m4: the calibration note says the posterior interval is shown where there is room', () => {
    // R3 c01 m16 (U16-F10a): the note says what the reader can do, a wider window, not a pixel width
    expect(view(<CalibrationView sel={sel} />, 'en')).toMatch(/which a wide window adds/i);
  });
  it('m5: the PSI note says that ties merge deciles', () => {
    expect(view(<StabilityView sel={sel} />, 'en')).toMatch(/tie[sd][^.]*merge/i);
    expect(view(<StabilityView sel={sel} />, 'es')).toMatch(/empat\w*[^.]*(fusionan|unen)/i);
  });
  it('m8: the attribution column of the Spanish Context says its text is the own wording of the source', () => {
    expect(view(<ContextView sel={sel} />, 'es')).toContain('texto exigido por la fuente, en su idioma');
  });
  it('m8, the licence: the Spanish gloss is read as Spanish and the licence name, with its version, is marked translate="no" (gate G11)', () => {
    const raw = html(<ContextView sel={sel} />, 'es');
    expect(raw).toMatch(/Este conjunto de datos tiene licencia <span translate="no">Creative Commons Atribución 4\.0 Internacional \(CC BY 4\.0\)<\/span>\./);
    expect(raw).not.toMatch(/translate="no">Este conjunto de datos/);
  });
  it('m16: the AUC and its interval are written to the same four decimals', () => {
    expect(view(<DiscriminationView sel={sel} />, 'en')).toMatch(/0\.\d{4} \(0\.\d{4} - 0\.\d{4}\)/);
  });
});
