// U15-W: the governance views on the reviewed fixtures (docs/contracts/fixtures/governance), in both languages. What each
// tab shows, its labels, the missing-document state, the opinion block and the six-tab limit. The fixtures stand in for
// the documents the governance bake writes; every number the views print is read from them.
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CITATIONS } from '../../content/citations';
import { ArtifactUnavailable } from '../../api/artifacts';
import {
  GOVERNANCE_APPETITE,
  GOVERNANCE_FINDINGS,
  GOVERNANCE_INVENTORY,
  GOVERNANCE_REPORT,
  conform,
} from '../../lib/contract.types';
import { groupCases, topRow } from '../../pages/Experiments';
import { entryText } from '../names';
import { DESIGN_GROUP_LABEL, governanceTabs } from '../../pages/experiments/governanceTabs';
import { collectSections } from '../../pages/methodologyRegistry';
import * as governanceSection from '../../pages/methodology/governance';
import { setLang } from '../c03/u6-testkit';
import { MapDrawing } from './DependencyMap';
import { InventoryTab } from './InventoryView';
import { FindingsWithOpinion, OpinionBlock, OpinionBlockView, OpinionCard, ReportOpinion } from './OpinionBlock';
import { AppetiteTable, FindingsTab, RegisterTable, SeverityStatusBars } from './RegisterView';
import { ReportDocument, ReportReader } from './ReportView';
import { MatrixDrawing } from './TierMatrix';
import { readerWords } from './readerText';
import {
  ECB_F_OF,
  GOVERNANCE_FILES,
  RULE_OUTPUT_LABEL,
  adoptedCell,
  ageingBins,
  loadGovernance,
  matrixCells,
  reportFile,
  resetGovernance,
  severityByStatus,
  sortRows,
  tierOf,
  type GovAppetite,
  type GovFindings,
  type GovInventory,
  type GovReport,
} from './model';

const dir = new URL('../../../../docs/contracts/fixtures/governance/', import.meta.url);
const read = <T,>(f: string): T => JSON.parse(readFileSync(new URL(f, dir), 'utf8')) as T;
const inv = read<GovInventory>('inventory-fixture.json');
const findings = read<GovFindings>('findings-fixture.json');
const appetite = read<GovAppetite>('appetite-fixture.json');
const c07 = read<GovReport>('report-C07-banco-andino-fixture.json');
const c18 = read<GovReport>('report-C18-banco-andino-fixture.json');
const html = (el: ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
const text = (markup: string) => markup.replace(/<[^>]*>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
const BAD = /NaN|undefined|Infinity|\[object/;
const LANGS = ['en', 'es'] as const;
const count = (s: string, re: RegExp) => (s.match(re) ?? []).length;

afterEach(() => {
  setLang('en');
  resetGovernance();
  vi.unstubAllGlobals();
});

describe('the descriptors read the reviewed fixtures', () => {
  it('conform, both ways', () => {
    expect(conform(inv, { object: GOVERNANCE_INVENTORY })).toEqual([]);
    expect(conform(findings, { object: GOVERNANCE_FINDINGS })).toEqual([]);
    expect(conform(appetite, { object: GOVERNANCE_APPETITE })).toEqual([]);
    expect(conform(c07, { object: GOVERNANCE_REPORT })).toEqual([]);
    expect(conform(c18, { object: GOVERNANCE_REPORT })).toEqual([]);
  });
  it('refuse a drifted document', () => {
    expect(conform({ ...inv, planted: 1 }, { object: GOVERNANCE_INVENTORY }).join()).toMatch(/planted/);
  });
});

describe('Inventory and tiers', () => {
  it('draws the map from the inventory: one node per entry, every edge with its kind, the engine once, no related link as an edge', () => {
    const m = html(<MapDrawing inv={inv} width={640} height={240} />);
    expect(count(m, /data-node="[A-Z]\d\d\//g)).toBe(inv.entries.length);
    expect(count(m, /data-edge="document"/g)).toBe(inv.edges.filter((e) => e.kind === 'document').length);
    expect(count(m, /data-edge="code"/g)).toBe(inv.edges.filter((e) => e.kind === 'code').length);
    expect(count(m, /data-edge="engine"/g)).toBe(inv.entries.length);
    expect(count(m, /data-node="engine"/g)).toBe(1);
    expect(inv.related.length).toBeGreaterThan(0);
    expect(count(m, /<path[^>]*data-from=/g)).toBe(inv.edges.length);
    for (const e of inv.entries) expect(m).toContain(`data-node="${e.key}" data-tier="${e.tier_block.tier}"`);
  });
  it('rings a node by the worst open severity of its entry', () => {
    const m = html(<MapDrawing inv={inv} width={640} height={240} />);
    expect(m).toMatch(/data-node="C18\/banco-andino"[^>]*data-worst="S1"/);
    // the fixtures carry the case findings only (the generic red-row findings are the governance bake's): the German twin's worst
    // open finding is S3
    expect(m).toMatch(/data-node="C01\/german"[^>]*data-worst="S3"/);
  });
  it('draws the 4 by 4 matrix with counts that sum to the entries, each cell with the tier of the stated rule', () => {
    const m = html(<MatrixDrawing inv={inv} width={420} picked={null} />);
    expect(count(m, /data-cell="\d-\d"/g)).toBe(16);
    const sum = [...m.matchAll(/data-count="(\d+)"/g)].reduce((a, x) => a + Number(x[1]), 0);
    expect(sum).toBe(inv.entries.length);
    for (const e of inv.entries) {
      const cell = adoptedCell(e)!;
      expect(e.tier_block.tier, e.key).toBe(tierOf(cell.m, cell.c));
      expect(matrixCells(inv.entries).keys[cell.m][cell.c]).toContain(e.key);
    }
    expect(m).toMatch(/data-cell="3-2" data-count="1" data-tier="2"/);
  });
  it('shows the rubric sensitivity: the counts of the four readings, the adopted one marked', () => {
    for (const lang of LANGS) {
      setLang(lang);
      const h = html(<InventoryTab inv={inv} />);
      expect(count(h, /data-reading="[A-D]"/g)).toBe(4);
      expect(h).toMatch(/data-reading="B" data-adopted="true"/);
      for (const row of inv.tier_counts) expect(h).toContain(`data-reading="${row.reading}"`);
      expect(text(h)).toContain(lang === 'es' ? 'adoptada' : 'adopted');
    }
  });
  it('lists the entries, the left-out cases with their reason and the findings of the inventory with their ECB F', () => {
    const t = text(html(<InventoryTab inv={inv} />));
    // each entry by its name, never its key (the R2b page review)
    for (const e of inv.entries) expect(t).toContain(entryText(e.key).en);
    for (const x of inv.excluded) expect(t).toContain(x.reason.en);
    for (const f of inv.governance_findings) {
      expect(t).toContain(f.severity);
      expect(t).toContain(`ECB ${f.ecb_f}`);
    }
    expect(t).toMatch(/not a dependency/i);
  });
  it('says every convention is a convention, in both languages, and approves nothing', () => {
    for (const lang of LANGS) {
      setLang(lang);
      const h = html(<InventoryTab inv={inv} />);
      expect(h).toContain('data-convention-note');
      expect(text(h)).toMatch(lang === 'en' ? /never a regulatory value/ : /nunca un valor regulatorio/);
      expect(text(h)).not.toMatch(/\b(certified|certifies a model|compliant|regulatory requirement)\b/i);
    }
  });
});

describe('Findings and appetite', () => {
  it('shows every register row with its severity beside the ECB F equivalent and the status beside the product status', () => {
    const h = html(<RegisterTable rows={findings.rows} />);
    expect(count(h, /data-finding="/g)).toBe(findings.rows.length);
    expect(count(h, /ECB F[1-4]/g)).toBe(findings.rows.length);
    for (const [s, f] of Object.entries(ECB_F_OF)) expect(findings.rows.filter((r) => r.severity === s).every((r) => r.ecb_f === f)).toBe(true);
    expect(count(h, /product status:/g)).toBe(findings.rows.length);
  });
  it('gives an anchor or its absence with the reason', () => {
    const h = html(<RegisterTable rows={findings.rows} />);
    expect(count(h, /data-anchor="unavailable"/g)).toBe(findings.rows.filter((r) => r.anchor === null).length);
    // in reader words (R3 c23 B3, the ruling of 2026-10-27: an engine key in reader text is a raw id)
    expect(text(h)).toContain(readerWords(findings.rows.find((r) => r.anchor === null)!.anchor_reason!.en, 'en'));
  });
  it('sorts by a column and keeps the document order on ties', () => {
    const by = sortRows(findings.rows, 'severity', 'asc');
    expect(by[0].severity).toBe('S1');
    expect(by.at(-1)!.severity).toBe('S4');
    const due = sortRows(findings.rows, 'due', 'desc').map((r) => r.due);
    expect([...due].sort().reverse()).toEqual(due);
    expect(sortRows(findings.rows, 'entry', 'asc').map((r) => r.key)).toEqual(sortRows(findings.rows, 'entry', 'asc').map((r) => r.key));
  });
  it('flags the overdue rows of the document and none else', () => {
    const h = html(<RegisterTable rows={findings.rows} />);
    expect(count(h, /data-overdue="true"/g)).toBe(findings.counts.overdue);
  });
  it('stacks severity by status to the register total, and ages the findings not closed', () => {
    const total = severityByStatus(findings.rows).reduce((a, d) => a + d.total, 0);
    expect(total).toBe(findings.counts.total);
    for (const d of severityByStatus(findings.rows)) expect(d.total).toBe(findings.counts.by_severity[d.severity]);
    const bars = html(<SeverityStatusBars rows={findings.rows} />);
    expect(count(bars, /data-severity-bar="/g)).toBe(4);
    const live = findings.rows.filter((r) => r.status !== 'validated_closed').length;
    expect(ageingBins(findings.rows).reduce((a, b) => a + b.count, 0)).toBe(live);
  });
  it('shows the seven B.6 metrics with light, value, distinct count, register-row count and convention label', () => {
    for (const lang of LANGS) {
      setLang(lang);
      const h = html(<AppetiteTable appetite={appetite} />);
      expect(count(h, /data-metric="/g)).toBe(7);
      const open = appetite.metrics.find((m) => m.id === 'open-high-severity')!;
      expect(open.register_rows).toBe(9); // the fixtures' case findings (the generic red-row findings stay out of the contract fixture)
      expect(h).toMatch(/data-metric="open-high-severity" data-light="red"/);
      expect(text(h)).toContain(lang === 'es' ? 'convención' : 'convention');
      expect(text(h)).toContain(lang === 'es' ? 'Filas del registro' : 'Register rows');
    }
  });
});

describe('Reports', () => {
  it('shows the twelve sections of one entry, filled or absent with the reason', () => {
    const h = html(<ReportDocument report={c18} />);
    expect(count(h, /data-section="\d+"/g)).toBe(12);
    expect(count(h, /data-status="absent"/g)).toBe(c18.sections.filter((s) => s.status === 'absent').length);
    expect(c18.sections.filter((s) => s.status === 'absent').length).toBeGreaterThan(0);
    const absent = c18.sections.find((s) => s.status === 'absent')!;
    // a reason after "Not available:" starts with a capital (U16-R2 b12 m6)
    const cap = (x: string) => x.charAt(0).toUpperCase() + x.slice(1);
    expect(text(h)).toContain(cap(absent.absent_reason!.en));
    expect(text(h)).toContain(cap(c18.sections[0].missing[0]?.reason.en ?? ''));
  });
  it('shows section 11 with the opinion level, the rule and the labelled recommendation', () => {
    for (const lang of LANGS) {
      setLang(lang);
      for (const r of [c07, c18]) {
        const h = html(<ReportDocument report={r} />);
        expect(h).toContain('data-opinion');
        expect(h).toContain('data-rule-label');
        const op = (r.sections[10] as { opinion: { label: { en: string; es: string } } }).opinion;
        expect(text(h)).toContain(op.label[lang]);
        expect(op.label.en).toBe(RULE_OUTPUT_LABEL.en);
        // the rule by what it is and in reader words, never by its decision id (R3 c23 B5, the ruling of 2026-10-27)
        expect(text(h)).not.toContain('W15-7');
        expect(text(h)).toContain(readerWords((r.sections[10] as { opinion: { rule: { text: { en: string; es: string } } } }).opinion.rule.text[lang], lang));
      }
    }
  });
  it('offers every inventory entry in the select', () => {
    const h = html(<ReportReader inv={inv} />);
    expect(count(h, /<option /g)).toBe(inv.entries.length);
  });
  it('maps an entry to the file the bake writes', () => {
    expect(reportFile('C07/banco-andino')).toBe('governance/reports/C07-banco-andino.json');
  });
});

describe('the opinion block of a Findings group', () => {
  it('shows the level, the rule and the label of the opinion', () => {
    const s = c07.sections[10] as Extract<GovReport['sections'][number], { number: 11 }>;
    for (const lang of LANGS) {
      setLang(lang);
      const h = html(<OpinionCard opinion={s.opinion} />);
      expect(h).toContain(`data-level="${s.opinion.level}"`);
      expect(text(h)).toContain(s.opinion.label[lang]);
      expect(h).not.toMatch(BAD);
    }
    expect(html(<ReportOpinion report={c18} />)).toContain('data-opinion');
  });
  it('says not available yet, with its reason, for a case the inventory leaves out or does not hold', () => {
    const left = html(<OpinionBlockView caseId="C02" inv={inv} />);
    expect(left).toContain('data-state="unavailable"');
    expect(text(left)).toContain('Not available yet');
    expect(text(left)).toContain(inv.excluded.find((x) => x.case_id === 'C02')!.reason.en);
    setLang('es');
    expect(text(html(<OpinionBlockView caseId="C99" inv={inv} />))).toContain('Aún no disponible');
  });
  it('asks for the report of each entry of the case while it loads', () => {
    expect(html(<OpinionBlockView caseId="C07" inv={inv} />)).toContain('data-opinion-entry="C07/banco-andino"');
  });
});

describe('the Findings group with its opinion', () => {
  it('keeps the group content and adds the opinion in a disclosure, in both languages', () => {
    for (const lang of LANGS) {
      setLang(lang);
      const h = html(<FindingsWithOpinion caseId="C07"><p data-group-content>the findings</p></FindingsWithOpinion>);
      expect(h).toContain('data-group-content');
      expect(h).toContain('data-opinion-disclosure');
      // nothing is read until the disclosure is opened
      expect(h).not.toContain('data-governance-opinion');
      expect(text(h)).toContain(lang === 'es' ? 'Opinión global sobre la evidencia' : 'Overall opinion on the evidence');
    }
  });
});

describe('the opinion block of a case', () => {
  it('reads the inventory when it is drawn, in the declared loading state', () => {
    const h = html(<OpinionBlock caseId="C07" />);
    expect(h).toContain('data-governance-opinion="C07"');
    expect(h).toContain('data-state="loading"');
  });
});

describe('a missing governance document', () => {
  it('is the declared not-available state with the reason that the bake has not written the file', async () => {
    vi.stubGlobal('fetch', async () => new Response('', { status: 404 }));
    const err = await loadGovernance(GOVERNANCE_FILES.inventory).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ArtifactUnavailable);
    expect((err as ArtifactUnavailable).reason.en).toBe('The governance bake has not written governance/inventory.json.');
    expect((err as ArtifactUnavailable).reason.es).toContain('governance/inventory.json');
  });
  it('is the same when the host answers its HTML page', async () => {
    vi.stubGlobal('fetch', async () => new Response('<html>', { status: 200, headers: { 'content-type': 'text/html' } }));
    expect(await loadGovernance(GOVERNANCE_FILES.findings).catch((e: unknown) => e)).toBeInstanceOf(ArtifactUnavailable);
  });
});

describe('both languages, no leak, no approval', () => {
  const pages = (): Array<[string, ReactElement]> => [
    ['inventory', <InventoryTab inv={inv} />],
    ['findings', <FindingsTab findings={findings} appetite={appetite} />],
    ['report c07', <ReportDocument report={c07} />],
    ['report c18', <ReportDocument report={c18} />],
  ];
  it('prints no NaN, undefined or [object in either language', () => {
    for (const lang of LANGS) {
      setLang(lang);
      for (const [name, el] of pages()) expect(html(el), `${name} ${lang}`).not.toMatch(BAD);
    }
  });
  it('leaves no English label on the Spanish page', () => {
    setLang('es');
    for (const [name, el] of pages()) {
      const t = text(html(el));
      for (const w of ['Show all', 'Findings of the inventory itself', 'Register rows', 'product status', 'Not available:', 'Open findings', 'Severity by status', 'The model risk appetite', 'Opinion level', 'Recommendation:'])
        expect(t, `${name}: ${w}`).not.toContain(w);
    }
  });
  it('never approves or certifies and never calls a convention regulatory', () => {
    for (const lang of LANGS) {
      setLang(lang);
      for (const [name, el] of pages()) {
        // the fixed negations ("never a regulatory value", "nunca un valor regulatorio") are the labels themselves
        const t = text(html(el)).replace(/never a regulatory value|nunca un valor regulatorio/gi, '');
        expect(t, name).not.toMatch(/\b(certified|compliant|regulatory (threshold|value|requirement))\b|\bcumple la regulaci/i);
        expect(t, name).not.toMatch(/\bapproved by\b|\bapproves the model\b/i);
      }
    }
  });
});

describe('the design group holds six tabs at most', () => {
  const caseTabs = ['c01', 'c02', 'c03', 'c07', 'c18', 'c22'].map((id) => ({ id, label: id.toUpperCase(), content: null }));
  const base = [
    { id: 'coverage', label: 'Coverage', content: null },
    { id: 'protocol-metrics', label: 'Protocol and metrics', content: null },
  ];
  it('adds three governance tabs: Inventory and tiers, Findings and appetite, Reports', () => {
    for (const lang of LANGS) {
      const tabs = governanceTabs(lang);
      expect(tabs.map((t) => t.id)).toEqual(['inventory', 'findings', 'reports']);
      expect(tabs.map((t) => t.label)).toEqual(lang === 'en' ? ['Inventory and tiers', 'Findings and appetite', 'Reports'] : ['Inventario y niveles', 'Hallazgos y apetito', 'Informes']);
    }
  });
  it('keeps the design group at six tabs and the top row at six groups, in both languages', () => {
    for (const lang of LANGS) {
      const top = topRow([...base, ...governanceTabs(lang)], caseTabs, lang);
      expect(top[0].tabs.map((t) => t.id)).toEqual(['coverage', 'protocol-metrics', 'inventory', 'findings', 'reports', 'c22']);
      for (const g of top) expect(g.tabs.length, g.id).toBeLessThanOrEqual(6);
      expect(top.length).toBeLessThanOrEqual(6);
      expect(groupCases(caseTabs.filter((c) => c.id !== 'c22')).length + 1).toBeLessThanOrEqual(6);
    }
  });
  it('relabels the group as designed and governed, with its accents', () => {
    expect(DESIGN_GROUP_LABEL.en).toBe('How are the experiments designed and governed?');
    expect(DESIGN_GROUP_LABEL.es).toBe('¿Cómo se diseñan y gobiernan los experimentos?');
  });
  it('renders every tab body in its declared loading state', () => {
    for (const lang of LANGS) {
      setLang(lang);
      for (const t of governanceTabs(lang)) {
        const h = html(<>{t.content}</>);
        expect(h).toContain('data-state="loading"');
        expect(h).not.toMatch(BAD);
      }
    }
  });
});

describe('the Methodology section', () => {
  it('registers as a method section of an existing group', () => {
    const [s] = collectSections({ './methodology/governance.tsx': governanceSection }, ['models', 'tests', 'loss', 'capital', 'market', 'balance']);
    expect(s.id).toBe('governance');
    expect(s.group).toBe('models');                       // beside Model risk; the group holds six tabs (ADR-0071)
    expect(s.title).toBeTruthy();
  });
  it('states the tier rule, the opinion rule and the labels in both languages, and cites the sources', () => {
    for (const lang of LANGS) {
      setLang(lang);
      const h = html(<CitationsProvider items={CITATIONS}><governanceSection.methodologySection.Body /></CitationsProvider>);
      expect(h).not.toMatch(BAD);
      expect(h).toContain('katex');
      expect(h).toContain('data-area="method"');
      const t = text(h);
      expect(t).toContain(RULE_OUTPUT_LABEL[lang]);
      expect(t).toMatch(/SR 26-2/);
      expect(t).toMatch(/E-23/);
      expect(t).toMatch(/SS1\/23/);
      expect(t).toMatch(/18-month|18 meses/);
      expect(t).not.toMatch(/\b(certified|compliant)\b/i);
    }
  });
});
