// CT-412, the views every C04 variant shares and the cross-case sections, rendered on the server from the committed
// artifacts in English and in Spanish: every card carries its lane and provenance, none declares a loading state once
// its data is in hand, every chart has a series with a value to draw, and the numbers printed are the artifact's.
import { CitationsProvider, formatNumber, pick, useLangStore } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import { C04Results, C04VariantsProvider, paperAgreements, yearRanges } from '../../content/cases/C04Results';
import { CITATIONS } from '../../content/citations';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { C04Benchmark, C04Experiments, coverageChart, estimatorsChart } from '../../pages/C04Sections';
import { provenanceOf } from '../model';
import {
  C04ContextView,
  C04FindingsView,
  C04VariantsView,
  GradeReadout,
  IntervalReadout,
  ProjectionReadout,
  agencyLraChart,
  citedOf,
  findingsDrawing,
  findingsEvidence,
  largestGap,
  pValueChart,
  pickRow,
  rateChart,
} from './C04Common';
import { GRADES, isAgency, isFamily, isPublished, makeSel, P_FLOOR, type C04Sel } from './selection';

type Lang = 'en' | 'es';
const LANGS: Lang[] = ['en', 'es'];

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;

const manifest = read<CaseManifest>('manifests/C04.json');
const entries = manifest.artifacts.filter((a) => a.role === 'variant');
const variants = entries.map((a) => read<VariantArtifact>(a.path));
const cases: Array<{ id: string; data: CaseData }> = entries.map((a, i) => ({
  id: a.variant_id,
  data: { manifest, variant: variants[i], models: read<ModelsArtifact>(a.models_ref as string) },
}));
const dataOf = (id: string) => {
  const c = cases.find((x) => x.id === id);
  if (!c) throw new Error(`no variant ${id}`);
  return c.data;
};
const variantOf = (id: string) => dataOf(id).variant as VariantArtifact<unknown>;

/** The shell reads the language from its store; a server render reads the store's initial state, so the test sets
 * both and puts English back after each test. */
function setLang(lang: Lang) {
  (useLangStore.getInitialState() as { lang: Lang }).lang = lang;
  useLangStore.setState({ lang });
}
afterEach(() => setLang('en'));

/** A server render as the app mounts it (the router, the citations the write-up cites) with every variant of the case
 * in hand, unless `preload` is false (the views then wait for the variants as they do in the browser). */
function html(el: ReactElement, lang: Lang = 'en', preload = true): string {
  setLang(lang);
  return renderToStaticMarkup(
    <MemoryRouter>
      <CitationsProvider items={CITATIONS}>{preload ? <C04VariantsProvider variants={variants}>{el}</C04VariantsProvider> : el}</CitationsProvider>
    </MemoryRouter>,
  );
}

/** React's escaping of text and attribute values, to find a printed string in the markup. */
const esc = (s: string) => s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#x27;');

function cards(markup: string): Array<{ title: string; lane: string; provenance: string }> {
  return [...markup.matchAll(/<figure class="caos-plot[^"]*" data-plot="([^"]*)" data-lane="([^"]*)" data-provenance="([^"]*)"/g)].map((m) => ({ title: m[1], lane: m[2], provenance: m[3] }));
}
const seriesCounts = (markup: string) => [...markup.matchAll(/data-series="(\d+)"/g)].map((m) => Number(m[1]));

/** What every view of this module promises: cards with a lane and a provenance, nothing still loading, no empty chart
 * host, no em-dash or arrow. */
function expectSound(markup: string, where: string) {
  const found = cards(markup);
  expect(found.length, `${where}: no card rendered`).toBeGreaterThan(0);
  for (const c of found) {
    expect(['replay', 'live'], `${where}: card "${c.title}" without its lane`).toContain(c.lane);
    expect(['real', 'synthetic', 'published'], `${where}: card "${c.title}" without its provenance`).toContain(c.provenance);
  }
  expect(markup, `${where}: a view still declares loading`).not.toContain('data-state="loading"');
  for (const n of seriesCounts(markup)) expect(n, `${where}: a chart without series`).toBeGreaterThan(0);
  expect(markup, `${where}: an em-dash or an arrow`).not.toMatch(/[\u2014\u2190-\u21ff]/);
}

const finiteSeries = (series: Array<{ values: Array<number | null> }>) => series.every((s) => s.values.some((v) => v !== null && Number.isFinite(v)));

const pct3 = (lang: Lang, v: number | null | undefined) => formatNumber(v, lang, { percent: true, digits: 3 });

describe('C04 Findings', () => {
  it('every finding cites evidence the artifact holds', () => {
    for (const c of cases) {
      const v = variantOf(c.id);
      for (const f of v.findings) for (const ref of f.evidence) expect(citedOf(v, ref).kind, `${c.id} ${f.id}: ${ref}`).not.toBe('missing');
    }
  });

  for (const c of cases) {
    for (const lang of LANGS) {
      it(`renders for ${c.id} in ${lang}, sorted by severity, with the artifact's titles and p-values`, () => {
        const v = variantOf(c.id);
        const markup = html(<C04FindingsView sel={makeSel(c.data)} />, lang);
        expectSound(markup, `findings ${c.id} ${lang}`);
        for (const card of cards(markup)) {
          expect(card.lane).toBe('replay');
          expect(card.provenance).toBe(provenanceOf(v.provenance.truth_status));
        }
        const order = [...markup.matchAll(/data-severity="(S\d)"/g)].map((m) => m[1]);
        expect(order).toEqual([...order].sort());
        expect(order.length).toBe(v.findings.length);
        for (const f of v.findings) expect(markup).toContain(esc(f.title[lang]));
        for (const f of v.findings) {
          for (const ref of f.evidence) {
            const cited = citedOf(v, ref);
            if (cited.kind === 'test' && cited.row.p_value !== null && cited.row.p_value > 0) {
              expect(markup).toContain(esc(`p ${formatNumber(cited.row.p_value, lang, { digits: 2 })}`));
            }
          }
        }
        if (isAgency(v)) {
          expect(markup).toContain(esc(v.outputs.agency.name));
          expect(markup).toContain(esc(v.outputs.attribution));
        }
        expect(markup).toContain(lang === 'es' ? 'Lo que encontró la validación' : 'What the validation found');
      });
    }
  }

  it('draws the cited p-values for an agency, the cited rates or design blocks where they are drawable, and only the table otherwise', () => {
    for (const c of cases) {
      const v = variantOf(c.id);
      const ev = findingsEvidence(v);
      const p = pValueChart(ev.points);
      const r = rateChart(ev.points);
      const markup = html(<C04FindingsView sel={makeSel(c.data)} />);
      if (isAgency(v)) {
        expect(p, c.id).not.toBeNull();
        expect(finiteSeries(p!.series), `${c.id}: a p-value series of gaps`).toBe(true);
        // an agency's time homogeneity underflows to p = 0, and its reference tests reach 1.9e-124: every p-value under
        // the one floor (1e-16, C01's too) is drawn at it in a series of its own, counted and said
        expect(p!.zeros, c.id).toBeGreaterThan(0);
        expect(p!.floor).toBe(P_FLOOR);
        const under = ev.points.filter((x) => x.cited.kind === 'test' && x.cited.row.p_value !== null && x.cited.row.p_value < P_FLOOR).length;
        expect(p!.below, c.id).toBe(under);
        for (const s of p!.series) for (const y of s.values) if (y !== null) expect(y, c.id).toBeGreaterThanOrEqual(P_FLOOR);
        expect(markup).toContain('The cited tests against the policy');
        expect(markup).toContain('data-views="2"');
      } else if (r) {
        expect(isFamily(v), c.id).toBe(true);
        expect(finiteSeries(r.series), `${c.id}: a rate series of gaps`).toBe(true);
        expect(markup).toContain('The cited rates against the nominal levels');
      } else if (findingsDrawing(v, ev, 0)) {
        // the design blocks a family or the papers cite, drawn beside the table
        const d = findingsDrawing(v, ev, 0)!;
        expect(finiteSeries(d.chart.series), `${c.id}: a design series of gaps`).toBe(true);
        expect(markup).toContain(esc(pick(d.title, 'en')));
        // a short table stacks over its drawing, a long one sits beside it
        expect(markup).toMatch(/data-views="1" data-layout="stacked"|data-views="2" data-layout="beside"/);
        expect(markup).toContain('data-series=');
        expect(markup, c.id).not.toContain('there is no p-value or rate to draw here');
      } else {
        expect(p, c.id).toBeNull();
        expect(markup, c.id).not.toContain('data-series=');
        expect(markup, c.id).toContain('there is no p-value or rate to draw here');
        expect(markup).toContain('data-views="1"');
      }
    }
    // the families whose findings cite measured rates
    expect(['markov', 'momentum', 'cycle'].every((id) => rateChart(findingsEvidence(variantOf(id)).points) !== null)).toBe(true);
    // the variants whose findings cite design blocks that can be drawn
    expect(['withdrawals', 'thin', 'published'].every((id) => findingsDrawing(variantOf(id), findingsEvidence(variantOf(id)), 0) !== null)).toBe(true);
  });

  it("prints a cited rate with its SE and Wilson interval, as the artifact holds them", () => {
    const v = variantOf('momentum');
    if (!isFamily(v)) throw new Error('momentum is a family');
    const s = v.outputs.simulations.find((x) => x.key === 'rating.momentum@alpha0.125')!;
    const markup = html(<C04FindingsView sel={makeSel(dataOf('momentum'))} />);
    expect(markup).toContain(`${pct3('en', s.rates['p<0.05'].rate)} at 5% (SE ${pct3('en', s.rates['p<0.05'].se)})`);
    expect(markup).toContain('(the empirical strength)');
  });
});

describe('C04 Variants', () => {
  for (const c of cases) {
    for (const lang of LANGS) {
      it(`renders for ${c.id} in ${lang}: every variant a row, the agencies' numbers the artifact's`, () => {
        const sel = makeSel(c.data);
        const markup = html(<C04VariantsView sel={sel} onPick={() => undefined} />, lang);
        expectSound(markup, `variants ${c.id} ${lang}`);
        for (const card of cards(markup)) expect(card.lane).toBe('replay');
        for (const e of entries) expect(markup, `${c.id}: row ${e.variant_id}`).toContain(`data-variant="${e.variant_id}"`);
        expect(markup).toContain(`<tr data-variant="${c.id}" class="ct-current"`);
        const provs = cards(markup).map((x) => x.provenance);
        expect(provs).toEqual(expect.arrayContaining(['real', 'synthetic', 'published']));
        for (const v of variants.map((x) => x as VariantArtifact<unknown>).filter(isAgency)) {
          expect(markup).toContain(`<td data-cell="d2">${esc(pct3(lang, v.outputs.lra.d2.rate[sel.grade]))}</td>`);
          if (v.outputs.lra.d4) expect(markup).toContain(`<td data-cell="d4">${esc(pct3(lang, v.outputs.lra.d4.rate[sel.grade]))}</td>`);
          expect(markup).toContain(esc(v.outputs.agency.name));
        }
        expect(markup).toContain(esc('Source: ESMA CEREP; tables transformed by Contraste'));
      });
    }
  }

  it("names the empty default columns, Moody's missing category, and marks the rail's grade on the chart", () => {
    const markup = html(<C04VariantsView sel={makeSel(dataOf('sp'), { grade: 3 })} onPick={() => undefined} />);
    expect(markup).toContain(esc("Fitch's default column is empty in the years 2006 to 2014, while its default page counts 189 rated defaulters in those years."));
    expect(markup).toContain('no default category');
    const agencies = variants.map((x) => x as VariantArtifact<unknown>).filter(isAgency);
    const chart = agencyLraChart(agencies, (id) => id, 3);
    expect(chart).not.toBeNull();
    expect(finiteSeries(chart!.series)).toBe(true);
    expect(chart!.marks).toEqual([{ x: 4, label: { en: 'BBB', es: 'BBB' } }]);
    // a zero average has no place on the log axis: S&P's AAA under D2 is a gap, not a zero
    const spD2 = chart!.series.find((s) => typeof s.label !== 'string' && s.label.en.startsWith('sp, D2'));
    expect(spD2?.values[0]).toBeNull();
    // the TTC default rates drawn are the artifacts'
    for (const a of agencies) {
      const t = a.impact.ttc_default_rate?.value;
      if (t) expect(chart!.series.some((s) => s.values.every((v) => v === t))).toBe(true);
    }
    expect(yearRanges(['2003', '2006', '2007', '2008'], 'es')).toBe('2003, 2006 a 2008');
  });

  it('a row click loads its variant and the open variant is marked', () => {
    const picked: string[] = [];
    const row = pickRow('fitch', 'sp', (id) => picked.push(id));
    row.onClick();
    expect(picked).toEqual(['fitch']);
    expect(row.className).toBeUndefined();
    expect(pickRow('sp', 'sp', () => undefined).className).toBe('ct-current');
  });

  it('declares loading while the variants load, and only then', () => {
    const sel = makeSel(dataOf('sp'));
    expect(html(<C04VariantsView sel={sel} onPick={() => undefined} />, 'en', false)).toContain('data-state="loading"');
    expect(html(<C04VariantsView sel={sel} onPick={() => undefined} />)).not.toContain('data-state="loading"');
  });
});

describe('C04 Context', () => {
  for (const c of cases) {
    for (const lang of LANGS) {
      it(`renders for ${c.id} in ${lang}: sources, licence classes, truth statuses, ESMA's statement, write-up and results`, () => {
        const markup = html(<C04ContextView sel={makeSel(c.data)} />, lang);
        expectSound(markup, `context ${c.id} ${lang}`);
        for (const id of manifest.sources) {
          expect(markup).toContain(`data-licence-class="${manifest.source_details[id].class}"`);
          expect(markup).toContain(esc(manifest.source_details[id].attribution));
        }
        expect(markup).toContain('data-licence-class="generator"');
        for (const e of entries) expect(markup).toContain(`data-truth="${e.truth_status}"`);
        expect(markup).toContain(c.data.variant.provenance.truth_status);
        expect(markup).toContain('data-statement="esma"');
        expect(markup).toContain(lang === 'es' ? 'no se ha establecido una definición determinista' : 'no deterministic definition of a default event has been set up');
        expect(markup).toContain('data-results="C04"');
        expect(markup).toContain(lang === 'es' ? 'La pregunta' : 'The question');
      });
    }
  }
});

describe('C04 Results', () => {
  for (const lang of LANGS) {
    it(`prints every variant's findings and the agencies' long-run averages as the artifacts hold them, in ${lang}`, () => {
      const markup = html(<C04Results manifest={manifest} />, lang);
      expect(markup).toContain('data-state="ready"');
      expect(markup).not.toContain('data-state="loading"');
      expect(markup).not.toMatch(/[\u2014\u2190-\u21ff]/);
      for (const v of variants) {
        expect(markup).toContain(`data-variant="${v.variant_id}"`);
        for (const f of v.findings) expect(markup).toContain(esc(f.title[lang]));
      }
      for (const v of variants.map((x) => x as VariantArtifact<unknown>).filter(isAgency)) {
        for (const d of ['d2', 'd3', 'd4'] as const) {
          const lra = v.outputs.lra[d];
          if (!lra) continue;
          for (const r of lra.rate) expect(markup).toContain(`<td>${esc(pct3(lang, r))}</td>`);
        }
        expect(markup).toContain(esc(v.outputs.agency.name));
      }
      const p = variants.map((x) => x as VariantArtifact<unknown>).find(isPublished)!;
      for (const a of paperAgreements(p)) expect(markup).toContain(lang === 'es' ? `${a.agree} de ${a.total}` : `${a.agree} of ${a.total}`);
    });
  }

  it("counts the papers' agreements from the outputs", () => {
    const p = variants.map((x) => x as VariantArtifact<unknown>).find(isPublished)!;
    const a = Object.fromEntries(paperAgreements(p).map((x) => [x.id, x]));
    expect([a.irw.agree, a.irw.total]).toEqual([p.outputs.irw.rows.filter((r) => r.agrees).length, p.outputs.irw.rows.length]);
    expect([a.sr190.agree, a.sr190.total]).toEqual([p.outputs.sr190.rows.filter((r) => r.agrees).length, p.outputs.sr190.rows.length]);
    // W hat is judged by the rounding of its printed entries, not at its printed digits
    expect(a.engelmann.total).toBe(p.outputs.engelmann.w_ttc.printed.length + 1 + 3 + 2);
  });
});

describe('C04 rail read-outs', () => {
  const at = (el: ReactElement, lang: Lang = 'en') => html(el, lang);
  const readout = (markup: string) => {
    const m = markup.match(/<div class="caos-readout[^"]*" data-readout="" data-lane="([^"]*)" data-provenance="([^"]*)"/);
    return m ? { lane: m[1], provenance: m[2] } : null;
  };

  it('every read-out renders on every variant, in both languages, with its lane and provenance', () => {
    for (const c of cases) {
      for (const lang of LANGS) {
        for (const R of [GradeReadout, ProjectionReadout, IntervalReadout]) {
          const markup = at(<R sel={makeSel(c.data)} />, lang);
          const r = readout(markup);
          expect(r, `${c.id} ${R.name} ${lang}`).not.toBeNull();
          expect(['live', 'replay']).toContain(r!.lane);
          expect(r!.provenance).toBe(provenanceOf(c.data.variant.provenance.truth_status));
          expect(markup).not.toMatch(/[\u2014\u2190-\u21ff]/);
        }
      }
    }
  });

  it("the grade read-out gives the artifact's long-run average and Jeffreys interval, and moves with the grade, the definition and the estimator", () => {
    const sp = dataOf('sp');
    const v = variantOf('sp');
    if (!isAgency(v)) throw new Error('sp is an agency');
    const s0 = makeSel(sp);
    const m0 = at(<GradeReadout sel={s0} />);
    expect(m0).toContain(pct3('en', v.outputs.lra.d2.rate[6]));
    // the interval is the artifact's, on the pooled counts: the read-out shows the pooled rate it is centred on
    expect(m0).toContain(pct3('en', v.outputs.lra.d2.pooled_rate[6]));
    expect(m0).toContain(`${pct3('en', v.outputs.lra.d2.jeffreys.lower[6])} to ${pct3('en', v.outputs.lra.d2.jeffreys.upper[6])}`);
    expect(readout(m0)?.lane).toBe('replay');
    expect(at(<GradeReadout sel={{ ...s0, grade: 4 }} />)).not.toBe(m0);
    const d4 = at(<GradeReadout sel={{ ...s0, definition: 'd4' }} />);
    expect(d4).not.toBe(m0);
    expect(d4).toContain(pct3('en', v.outputs.lra.d4!.rate[6]));
    const keep = at(<GradeReadout sel={{ ...s0, definition: 'keep' }} />);
    expect(keep).not.toBe(d4);
    expect(readout(keep)?.lane).toBe('live');
    const markov = makeSel(dataOf('markov'));
    const em = at(<GradeReadout sel={markov} />);
    expect(em).not.toBe(at(<GradeReadout sel={{ ...markov, estimator: 'cohort' }} />));
    expect(em).not.toBe(at(<GradeReadout sel={{ ...markov, grade: 0 }} />));
    // Moody's has no D4: the read-out says not available, it does not invent a number
    const moodys = at(<GradeReadout sel={makeSel(dataOf('moodys'), { definition: 'd4' })} />);
    expect(moodys).toContain('not available');
  });

  it("the projection read-out's TTC rate is the case's, and the read-out moves with the start and the horizon", () => {
    const v = variantOf('sp');
    const s0 = makeSel(dataOf('sp'));
    const m0 = at(<ProjectionReadout sel={s0} />);
    expect(readout(m0)?.lane).toBe('live');
    expect(m0).toContain(pct3('en', v.impact.ttc_default_rate.value));
    expect(at(<ProjectionReadout sel={{ ...s0, start: 'best' }} />)).not.toBe(m0);
    expect(at(<ProjectionReadout sel={{ ...s0, horizon: 35 }} />)).not.toBe(m0);
    const fam = makeSel(dataOf('cycle'));
    expect(at(<ProjectionReadout sel={fam} />)).not.toBe(at(<ProjectionReadout sel={{ ...fam, start: 'speculative' }} />));
    expect(largestGap([0.01, 0.004, 0.008], 0.006)).toEqual({ gap: 0.01 - 0.006, year: 1 });
  });

  it('the interval read-out gives N and moves with the correlation, the level and the grade', () => {
    const v = variantOf('sp');
    if (!isAgency(v)) throw new Error('sp is an agency');
    const s0: C04Sel = makeSel(dataOf('sp'));
    const m0 = at(<IntervalReadout sel={s0} />);
    expect(readout(m0)?.lane).toBe('live');
    // at no correlation N-dagger is N, the pooled ratings of the grade under D2
    expect(m0).toContain(`>${formatNumber(v.outputs.lra.d2.n[6], 'en', { digits: 4 })}<`);
    expect(at(<IntervalReadout sel={{ ...s0, rho: 0.02 }} />)).not.toBe(m0);
    expect(at(<IntervalReadout sel={{ ...s0, level: 0.99 }} />)).not.toBe(m0);
    expect(at(<IntervalReadout sel={{ ...s0, grade: 2 }} />)).not.toBe(m0);
    expect(at(<IntervalReadout sel={{ ...s0, definition: 'd4' }} />)).not.toBe(m0);
    const pub = at(<IntervalReadout sel={makeSel(dataOf('published'))} />);
    expect(pub).toContain('15 defaults among 531 obligors');
  });

  it('every grade has a reading under every definition an agency gives', () => {
    for (const id of ['sp', 'fitch', 'moodys']) {
      const v = variantOf(id);
      if (!isAgency(v)) throw new Error(`${id} is an agency`);
      for (const d of ['d2', 'd3', 'd4', 'keep'] as const) {
        if (v.outputs.pd[d] === null) continue;
        for (let g = 0; g < GRADES.length; g++) {
          const m = at(<GradeReadout sel={makeSel(dataOf(id), { definition: d, grade: g })} />);
          expect(m, `${id} ${d} ${GRADES[g]}`).toContain(`${GRADES[g]}, `);
          expect(m, `${id} ${d} ${GRADES[g]}`).not.toContain('NaN');
        }
      }
    }
  });
});

describe('C04 cross-case sections', () => {
  for (const lang of LANGS) {
    it(`Experiments: every variant a row with its truth, the agencies' chart drawn, in ${lang}`, () => {
      const markup = html(<C04Experiments manifest={manifest} />, lang);
      expectSound(markup, `experiments ${lang}`);
      expect(markup).toContain('data-state="ready"');
      for (const e of entries) expect(markup).toContain(`<tr data-variant="${e.variant_id}">`);
      for (const v of variants.map((x) => x as VariantArtifact<unknown>).filter(isAgency)) {
        expect(markup).toContain(esc(pct3(lang, v.outputs.lra.d2.rate[6])));
      }
      expect(seriesCounts(markup).length).toBe(1);
    });

    it(`Benchmark: the comparisons with their verdicts, every number the artifacts', in ${lang}`, () => {
      const markup = html(<C04Benchmark manifest={manifest} />, lang);
      expectSound(markup, `benchmark ${lang}`);
      expect(markup).toContain('data-state="ready"');
      for (const t of ['bench-definitions', 'bench-generators', 'bench-lifetime', 'bench-estimators', 'bench-tests', 'bench-coverage-thin', 'bench-irw', 'bench-sr190', 'bench-engelmann']) {
        expect(markup, t).toContain(`data-table="${t}"`);
      }
      expect((markup.match(/data-verdict=/g) ?? []).length).toBe(7);
      const p = variants.map((x) => x as VariantArtifact<unknown>).find(isPublished)!;
      for (const r of p.outputs.irw.rows) expect(markup).toContain(`<td>${formatNumber(r.printed, lang, { digits: 6 })}</td>`);
      const markov = variants.map((x) => x as VariantArtifact<unknown>).filter(isFamily).find((f) => f.outputs.family === 'markov')!;
      const est = estimatorsChart(markov);
      const cov = coverageChart(markov);
      expect(est && finiteSeries(est.series)).toBe(true);
      expect(cov && finiteSeries(cov.series)).toBe(true);
      expect(seriesCounts(markup)).toEqual([est!.series.length, cov!.series.length]);
    });
  }

  it('the sections declare loading while the variants load', () => {
    expect(html(<C04Experiments manifest={manifest} />, 'en', false)).toContain('data-state="loading"');
    expect(html(<C04Benchmark manifest={manifest} />, 'en', false)).toContain('data-state="loading"');
  });
});

