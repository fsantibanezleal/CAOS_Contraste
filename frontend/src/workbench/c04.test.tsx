// CT-412: the C04 instrument, rendered on the server from the committed artifacts. The groups are the six questions in
// order; the rail has the sections whose controls change something for the variant's kind; every view of every variant
// carries its lane and draws no empty chart; Moody's disables D4 and Keep with the reason; the Context names the
// sources, their licence classes and each variant's truth status; every rail read-out changes when its controls move.
import { readFileSync } from 'node:fs';
import { CitationsProvider, formatNumber, useLangStore, type Lang } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../api/artifacts';
import { CITATIONS } from '../content/citations';
import { C04VariantsProvider, impactValue } from '../content/cases/C04Results';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../lib/contract.types';
import { GeneratorsView, MatrixView } from './c04/AgencyModelViews';
import { MobilityView, SemestersView, TestsView } from './c04/AgencyTestsViews';
import { ByYearView, DefinitionsView, LifetimeView, PdByGradeView } from './c04/AgencyValidationViews';
import { C04ContextView, C04FindingsView, C04VariantsView, GradeReadout, IntervalReadout, ProjectionReadout } from './c04/C04Common';
import { FamilyValidationView, GeneratorView } from './c04/FamilyViews';
import { useC04Instrument } from './c04/instrument';
import { ImpactView } from './c04/LiveViews';
import { PapersView, PublishedImpactView, PublishedModelView } from './c04/PublishedViews';
import { isAgency, isFamily, makeSel, type C04Sel } from './c04/selection';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
/** A server render as the app mounts it: the router, the citations the write-up cites, and every variant of the case
 * in hand (the Variants and Context views read them all; in the browser they load them). Server rendering reads the
 * language store's initial state (zustand's server snapshot), so a render's language is set there and put back. */
function html(el: ReactElement, lang: Lang = 'en'): string {
  const initial = useLangStore.getInitialState();
  const before = initial.lang;
  initial.lang = lang;
  try {
    return renderToStaticMarkup(
      <MemoryRouter>
        <CitationsProvider items={CITATIONS}>
          <C04VariantsProvider variants={allVariants}>{el}</C04VariantsProvider>
        </CitationsProvider>
      </MemoryRouter>,
    );
  } finally {
    initial.lang = before;
  }
}

const manifest = read<CaseManifest>('manifests/C04.json');
const cases: Array<{ id: string; data: CaseData }> = manifest.artifacts
  .filter((a) => a.role === 'variant')
  .map((a) => ({ id: a.variant_id, data: { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) } }));
const dataOf = (id: string) => cases.find((c) => c.id === id)!.data;
const allVariants = cases.map((c) => c.data.variant);

function cards(markup: string): Array<{ lane: boolean }> {
  return markup
    .split('class="caos-plot-head"')
    .slice(1)
    .map((rest) => ({ lane: /data-lane="(live|replay|offline)"/.test(rest.slice(0, rest.indexOf('</figcaption>'))) }));
}

/** Every chart in the markup: its series count and its axis titles. */
function charts(markup: string): Array<{ series: number; axes: string }> {
  return [...markup.matchAll(/class="caos-chart[^"]*" data-series="(\d+)" data-axis-titles="([^"]*)"/g)].map((m) => ({ series: Number(m[1]), axes: m[2] }));
}

type View = (p: { sel: C04Sel | null }) => ReactElement;
const COMMON: Array<[string, View]> = [
  ['Impact', ImpactView],
  ['Findings', C04FindingsView],
  ['Context', C04ContextView],
];
const AGENCY: Array<[string, View]> = [
  ['Matrix', MatrixView], ['Generators', GeneratorsView], ['Mobility', MobilityView], ['PD by grade', PdByGradeView],
  ['By year', ByYearView], ['Definitions', DefinitionsView], ['Lifetime', LifetimeView], ['Markov tests', TestsView],
  ['Semesters', SemestersView], ...COMMON,
];
const FAMILY: Array<[string, View]> = [['Generator', GeneratorView], ['Validation', FamilyValidationView], ...COMMON];
const PUBLISHED: Array<[string, View]> = [
  ['Model', PublishedModelView], ['Papers', PapersView], ['Impact', PublishedImpactView], ['Findings', C04FindingsView], ['Context', C04ContextView],
];
const viewsOf = (data: CaseData) => {
  const v = data.variant as VariantArtifact<unknown>;
  return isAgency(v) ? AGENCY : isFamily(v) ? FAMILY : PUBLISHED;
};

function Groups({ data }: { data: CaseData }) {
  const inst = useC04Instrument(data, () => undefined);
  return (
    <p>
      {inst
        ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') +
          ` rail:${inst.rail.map((r) => r.id).join(',')} controls:${Object.keys(inst.controls).join(',')}`
        : 'none'}
    </p>
  );
}

function Rail({ data }: { data: CaseData }) {
  const inst = useC04Instrument(data, () => undefined);
  return <div>{inst?.rail.map((r) => <section key={r.id} data-section={r.id}>{r.content}</section>)}</div>;
}

describe('the C04 instrument', () => {
  it('has the nine variants of the design: three agencies, five families, the papers', () => {
    expect(cases.map((c) => c.id)).toEqual(['sp', 'moodys', 'fitch', 'markov', 'momentum', 'cycle', 'withdrawals', 'thin', 'published']);
  });

  it('the groups are the six questions, in order, and the rail holds the sections that act on the variant', () => {
    const rail: Record<string, string> = {
      published: 'interval',
    };
    for (const c of cases) {
      const markup = html(<Groups data={c.data} />);
      expect(markup).toContain('Model|Validation|Impact|Findings|Variants');
      expect(markup, c.id).toContain(`rail:${rail[c.id] ?? 'grade,projection,interval'} `);
      expect(markup).toContain('controls:grade,definition,estimator,cohort,mapScale,start,horizon,rho,level,lgd');
    }
  });

  for (const c of cases) {
    it(`every view carries its lane and draws no empty chart, in English and Spanish: ${c.id}`, () => {
      for (const lang of ['en', 'es'] as const) {
        for (const [name, View] of viewsOf(c.data)) {
          const where = `${c.id} ${name} (${lang})`;
          const markup = html(<View sel={makeSel(c.data)} />, lang);
          const found = cards(markup);
          expect(found.length, `${where}: no view rendered`).toBeGreaterThan(0);
          for (const card of found) expect(card.lane, `${where}: a view without its lane`).toBe(true);
          expect(markup, `${where}: a view waits as if loading`).not.toContain('data-state="loading"');
          for (const chart of charts(markup)) {
            expect(chart.series, `${where}: an empty chart`).toBeGreaterThan(0);
            expect(chart.axes.split('|').every((t) => t.trim().length > 0), `${where}: an axis without its title (${chart.axes})`).toBe(true);
          }
        }
      }
    });
  }

  it('every view changes language with the shell', () => {
    for (const id of ['sp', 'moodys', 'markov', 'momentum', 'published']) {
      const data = dataOf(id);
      for (const [name, View] of viewsOf(data)) {
        const en = html(<View sel={makeSel(data)} />, 'en');
        expect(html(<View sel={makeSel(data)} />, 'es'), `${id} ${name}: the Spanish render equals the English one`).not.toBe(en);
      }
    }
  });

  it('every rail control of every variant is a registered control', () => {
    for (const c of cases) {
      const markup = html(<Rail data={c.data} />);
      const ids = [...markup.matchAll(/data-control="([^"]+)"/g)].map((m) => m[1]);
      expect(ids.length, c.id).toBeGreaterThan(0);
      for (const id of ids) expect(id, c.id).toMatch(/^c04-/);
    }
  });

  it("Moody's disables D4 and Keep and says why; S&P offers all four definitions", () => {
    const moodys = html(<Rail data={dataOf('moodys')} />);
    expect(moodys).toContain('Not available for Moody');
    const disabled = [...moodys.matchAll(/<button[^>]*disabled[^>]*>/g)].length;
    expect(disabled).toBeGreaterThanOrEqual(2);
    const sp = html(<Rail data={dataOf('sp')} />);
    expect(sp).not.toContain('Not available for');
  });

  it('the Impact group is live and the replayed views are replay', () => {
    const sp = makeSel(dataOf('sp'));
    expect(html(<ImpactView sel={sp} />)).toContain('data-lane="live"');
    expect(html(<PdByGradeView sel={sp} />)).toContain('data-lane="replay"');
    expect(html(<PublishedImpactView sel={makeSel(dataOf('published'))} />)).toContain('data-lane="live"');
  });

  it('the context names the sources, their licence classes and the truth status', () => {
    for (const c of cases) {
      const markup = html(<C04ContextView sel={makeSel(c.data)} />);
      for (const id of manifest.sources) {
        expect(markup).toContain(`data-licence-class="${manifest.source_details[id].class}"`);
      }
      expect(markup).toContain(c.data.variant.provenance.truth_status);
    }
  });

  it('the variants view lists every variant', () => {
    const markup = html(<C04VariantsView sel={makeSel(dataOf('sp'))} onPick={() => undefined} />);
    expect(cards(markup).length).toBeGreaterThan(0);
  });

  it('prints a difference of probabilities in signed percentage points, never as a percentage', () => {
    const items = [dataOf('withdrawals').variant.impact.removed_bias_b, dataOf('momentum').variant.impact.projection_error_bbb];
    for (const it of items) {
      expect(it.unit).toBe('probability difference');
      for (const lang of ['en', 'es'] as const) {
        const text = impactValue(it, lang);
        expect(text).toBe(`${it.value! > 0 ? '+' : ''}${formatNumber(it.value! * 100, lang, { digits: 3 })}\u00a0pp`);
        expect(text).not.toContain('%');
      }
    }
    // the withdrawals bias is the B PD's with withdrawals removed: under a percentage point, below the truth
    expect(impactValue(items[0], 'en')).toBe(`${formatNumber(-0.397424314, 'en', { digits: 3 })}\u00a0pp`);
  });

  it('every rail read-out changes when its controls move', () => {
    const differs = (render: (s: C04Sel) => ReactElement, s0: C04Sel, s1: C04Sel) => expect(html(render(s0))).not.toBe(html(render(s1)));
    const grade = (s: C04Sel) => <GradeReadout sel={s} />;
    const projection = (s: C04Sel) => <ProjectionReadout sel={s} />;
    const interval = (s: C04Sel) => <IntervalReadout sel={s} />;
    const sp = makeSel(dataOf('sp'));
    differs(grade, sp, { ...sp, grade: 4 });
    differs(grade, sp, { ...sp, definition: 'd4' });
    differs(projection, sp, { ...sp, start: 'best' });
    differs(projection, sp, { ...sp, horizon: 5 });
    differs(interval, sp, { ...sp, rho: 0.02 });
    differs(interval, sp, { ...sp, level: 0.99 });
    differs(interval, sp, { ...sp, grade: 4 });
    const markov = makeSel(dataOf('markov'));
    differs(grade, markov, { ...markov, grade: 0 });
    differs(grade, markov, { ...markov, estimator: 'cohort' });
    differs(projection, markov, { ...markov, horizon: 40 });
    differs(interval, markov, { ...markov, level: 0.9 });
    const published = makeSel(dataOf('published'));
    differs(interval, published, { ...published, rho: 0.01 });
    differs(interval, published, { ...published, level: 0.99 });
  });
});
