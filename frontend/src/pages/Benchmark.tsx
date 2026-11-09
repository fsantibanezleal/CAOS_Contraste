// The held-out comparisons: every rung against the champion on each case's holdout, with the interval of its AUC and
// the paired DeLong test, its calibration, and the decision it would make. Every number is read from the committed
// artifacts at load time; none is typed in. The claim each table supports is only what its test shows.
import { Callout, Cite, DocPage, DocSection, PlotCard, TabGroups, Verdict, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo, type ReactNode } from 'react';
import { loadAllManifests, loadAllVariants, useArtifact } from '../api/artifacts';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { COMMITTED, relight } from '../lib/policy';
import { P, T, useT } from '../content/bi';
import { sourceText } from '../content/sources';
import { CHAMPION, extra, test, value } from '../workbench/model';
import { familyOf } from './experiments/families';
import { C04Benchmark } from './C04Sections';
import { C05BenchmarkSection } from './C05Sections';
import { C22BenchmarkSection } from './C22Sections';
import { Table, U6BenchmarkSection, U6_BENCHMARK_CASES, num } from './U6Sections';
import { W2BenchmarkSection, W2_BENCHMARK_CASES } from './Wave2Sections';
import { B3BenchmarkSection, B3_BENCHMARK_CASES } from './Batch3Sections';

export function Comparison({ v, title }: { v: VariantArtifact; title: string }) {
  const lang = useShellLang();
  const t = useT();
  const rows = v.model
    .filter((m) => m.id !== 'P0-constant')
    .map((m) => {
      const auc = test(v, 'disc.auc', m.id);
      const dl = test(v, 'disc.delong', m.id);
      return {
        m,
        auc: value(auc),
        lo: extra(auc, 'ci95_low'),
        hi: extra(auc, 'ci95_high'),
        dl,
        brier: value(test(v, 'pd.brier', m.id)),
        jef: test(v, 'pd.jeffreys', m.id),
      };
    });
  const champ = rows.find((r) => r.m.id === CHAMPION);
  const better = rows.filter((r) => r.dl && relight(r.dl, COMMITTED) !== 'green' && (extra(r.dl, 'difference') ?? 0) > 0);
  return (
    <PlotCard title={{ en: title, es: title }} lane="replay" provenance={v.provenance.truth_status === 'real-outcomes' ? 'real' : 'synthetic'}>
      <Verdict
        compact
        title={{ en: 'What the paired test supports', es: 'Lo que respalda la prueba pareada' }}
        tone={better.length ? 'accent' : 'neutral'}
        verdict={
          better.length
            ? {
                en: `${better.map((r) => r.m.short_title.en).join(', ')} rank significantly better than the scorecard (DeLong, policy 5%) on ${formatNumber(v.outputs.n, 'en')} held-out records; the gain in AUC is ${better.map((r) => formatNumber(extra(r.dl, 'difference'), 'en', { decimals: 3 })).join(', ')}.`,
                es: `${better.map((r) => r.m.short_title.es).join(', ')} ordenan significativamente mejor que la tarjeta de puntuación (DeLong, política 5 %) en ${formatNumber(v.outputs.n, 'es')} registros reservados; la ganancia en AUC es ${better.map((r) => formatNumber(extra(r.dl, 'difference'), 'es', { decimals: 3 })).join(', ')}.`,
              }
            : { en: 'No rung ranks significantly better than the scorecard here.', es: 'Ningún peldaño ordena significativamente mejor que la tarjeta de puntuación aquí.' }
        }
      />
      <table className="caos-table">
        <thead>
          <tr>
            <th className="caos-col-text">{t('Rung', 'Peldaño')}</th>
            <th>AUC</th>
            <th>{t('95% interval', 'Intervalo 95 %')}</th>
            <th>{t('Difference to P1', 'Diferencia con P1')}</th>
            <th>{t('DeLong p', 'p de DeLong')}</th>
            <th>Brier</th>
            <th>{t('Jeffreys p (portfolio)', 'p de Jeffreys (cartera)')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.m.id}>
              <td className="caos-col-text">
                {pick(r.m.short_title, lang)}
              </td>
              <td>{formatNumber(r.auc, lang, { decimals: 4 })}</td>
              <td>{r.lo !== null && r.hi !== null ? `${formatNumber(r.lo, lang, { decimals: 4 })} - ${formatNumber(r.hi, lang, { decimals: 4 })}` : ''}</td>
              <td>{r.m.id === CHAMPION ? '' : num(r.auc !== null && champ?.auc != null ? r.auc - champ.auc : null, lang, 4)}</td>
              <td>{r.dl ? formatNumber(r.dl.p_value, lang, { digits: 3 }) : ''}</td>
              <td>{formatNumber(r.brier, lang, { decimals: 4 })}</td>
              <td>{formatNumber(r.jef?.p_value ?? null, lang, { digits: 3 })}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </PlotCard>
  );
}

function CaseBenchmark({ manifest }: { manifest: CaseManifest }) {
  const all = useArtifact<VariantArtifact[]>((s) => loadAllVariants(manifest, s), [manifest.case_id]);
  const t = useT();
  const picks = useMemo(() => {
    if (all.state !== 'ready') return null;
    // the variants whose rows are the data as observed: the holdout, the small sample, the twin
    return all.data.filter((v) => v.provenance.truth_status === 'real-outcomes');
  }, [all]);
  if (!picks) return <p className="caos-pending" data-state="loading">{t('Loading the comparisons', 'Cargando las comparaciones')}</p>;
  const titles = Object.fromEntries(manifest.artifacts.map((a) => [a.variant_id, a.title]));
  return (
    <div data-state="ready">
      {picks.map((v) => (
        <Comparison key={v.variant_id} v={v} title={`${manifest.case_id}, ${t(titles[v.variant_id]?.en ?? v.variant_id, titles[v.variant_id]?.es ?? v.variant_id)}`} />
      ))}
    </div>
  );
}

/** The legend of the truth status of an artifact, for the provenance table. */
const TRUTH: Record<string, { en: string; es: string }> = {
  'real-outcomes': { en: 'real outcomes', es: 'resultados reales' },
  'synthetic-known-truth': { en: 'real rows perturbed by a known amount (known truth)', es: 'filas reales perturbadas en una cantidad conocida (verdad conocida)' },
  'synthetic-calibrated': { en: 'synthetic, calibrated to public aggregates', es: 'sintéticos, calibrados a agregados públicos' },
  'published-answer': { en: 'a published answer', es: 'una respuesta publicada' },
};

const CLASS_TEXT: Record<string, { en: string; es: string }> = {
  'mirror-allowed': { en: 'mirror-allowed', es: 'espejo permitido' },
  'derived-only': { en: 'derived-only', es: 'solo derivados' },
  'link-only': { en: 'link-only', es: 'solo enlace' },
  unusable: { en: 'unusable', es: 'inutilizable' },
};

/** Per case and source: the dataset, its licence class, and what its artifacts say about their truth. */
function Provenance({ manifests }: { manifests: CaseManifest[] }) {
  const lang = useShellLang();
  const t = useT();
  const rows = manifests.flatMap((m) => {
    const truths = [...new Set(m.artifacts.filter((a) => a.role === 'variant').map((a) => a.truth_status))];
    return m.sources.map((id) => ({ key: `${m.case_id}/${id}`, m, id, truths }));
  });
  return (
    <table className="caos-table ct-wrap-head" data-state="ready" data-table="provenance">
      <thead>
        <tr>
          <th>{t('Case', 'Caso')}</th>
          <th className="caos-col-text">{t('Dataset', 'Conjunto de datos')}</th>
          <th className="caos-col-text">{t('Redistribution class', 'Clase de redistribución')}</th>
          <th className="caos-col-text">{t('Truth of the variants', 'Verdad de las variantes')}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ key, m, id, truths }) => {
          const d = m.source_details?.[id];
          return (
            <tr key={key}>
              <td>{m.case_id}</td>
              <td className="caos-col-text">{d ? sourceText(id, d.name, lang) : id}</td>
              <td className="caos-col-text">{d ? pick(CLASS_TEXT[d.class] ?? { en: d.class, es: d.class }, lang) : '-'}</td>
              <td className="caos-col-text">{truths.map((x) => pick(TRUTH[x] ?? { en: x, es: x }, lang)).join('; ')}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/** The AUC of the scorecard and of the best rung across the variants of a case that perturbs its data: a degradation curve. */
function Robustness({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const all = useArtifact<VariantArtifact[]>((s) => loadAllVariants(manifest, s), [manifest.case_id]);
  if (all.state !== 'ready') return <p className="caos-pending" data-state="loading">{t('Loading the variants', 'Cargando las variantes')}</p>;
  const variants = all.data.filter((v) => v.model.some((m) => m.id === CHAMPION));
  const rows = variants.map((v) => {
    const best = v.model
      .filter((m) => m.id !== 'P0-constant')
      .map((m) => ({ id: m.id, auc: value(test(v, 'disc.auc', m.id)) ?? 0 }))
      .sort((a, b) => b.auc - a.auc)[0];
    return { v, best, bestRung: pick(v.model.find((m) => m.id === best.id)?.short_title ?? { en: best.id, es: best.id }, lang), auc: value(test(v, 'disc.auc', CHAMPION)) };
  });
  if (rows.length < 2) return null;
  const titles = Object.fromEntries(manifest.artifacts.map((a) => [a.variant_id, a.short_title]));
  const numbered = rows.map((r, i) => `${i + 1} ${pick(titles[r.v.variant_id] ?? r.v.variant_id, lang)}`).join(', ');
  return (
    <>
    <PlotCard
      title={{ en: `${manifest.case_id}: AUC across the perturbed variants`, es: `${manifest.case_id}: AUC a lo largo de las variantes perturbadas` }}
      lane="replay"
      provenance="real"
      note={{ en: `The AUC of the scorecard and of the best rung on each variant, numbered: ${numbered}. A variant that perturbs the data shows how much each ranking degrades.`, es: `El AUC de la tarjeta de puntuación y del mejor peldaño en cada variante, numeradas: ${numbered}. Una variante que perturba los datos muestra cuánto se degrada cada ordenamiento.` }}
    >
      <UPlotChart
        height={260}
        x={{ values: rows.map((_, i) => i + 1), label: { en: 'Variant (the number in the note)', es: 'Variante (el número de la nota)' }, format: { decimals: 0 } }}
        y={{ label: { en: 'AUC', es: 'AUC' }, format: { decimals: 3 } }}
        series={[
          { label: { en: 'Scorecard (P1)', es: 'Tarjeta de puntuación (P1)' }, values: rows.map((r) => r.auc), color: '--color-accent', mode: 'points' },
          { label: { en: 'Best rung', es: 'Mejor peldaño' }, values: rows.map((r) => r.best.auc), color: '--color-magenta', mode: 'points' },
        ]}
      />
    </PlotCard>
    <RobustnessTable
      rows={rows.map((r, i) => ({ n: i + 1, title: pick(titles[r.v.variant_id] ?? r.v.variant_id, lang), scorecard: r.auc, best: r.best.auc, bestRung: r.bestRung }))}
    />
    </>
  );
}

/** The numbers the robustness chart draws, one row per variant (the chart has no table of its own): the number of the note, the variant, the AUC of the scorecard and of the best rung. */
export function RobustnessTable({ rows }: { rows: Array<{ n: number; title: string; scorecard: number | null; best: number; bestRung?: string }> }) {
  const lang = useShellLang();
  const t = useT();
  return (
    <table className="caos-table ct-wrap-head" data-state="ready" data-table="robustness">
      <caption className="ct-note">{t('The AUC the chart draws, by variant', 'El AUC que dibuja el gráfico, por variante')}</caption>
      <thead>
        <tr>
          <th>{t('No.', 'N.º')}</th>
          <th className="caos-col-text">{t('Variant', 'Variante')}</th>
          {/* the two AUC headers keep a width: at 390 they wrapped one word per line over their three-digit values (R5 c30 m8) */}
          <th style={{ minWidth: '8rem' }}>{t('AUC of the scorecard (P1)', 'AUC de la tarjeta de puntuación (P1)')}</th>
          <th className="caos-col-text">{t('Best rung', 'Mejor peldaño')}</th>
          <th style={{ minWidth: '8rem' }}>{t('AUC of the best rung', 'AUC del mejor peldaño')}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.n}>
            <td>{r.n}</td>
            <td className="caos-col-text">{r.title}</td>
            <td>{formatNumber(r.scorecard, lang, { decimals: 3 })}</td>
            <td className="caos-col-text">{r.bestRung ?? ''}</td>
            <td>{formatNumber(r.best, lang, { decimals: 3 })}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export const HAS_OWN_BENCHMARK = new Set(['C04', 'C05', 'C22']);
const IRRBB_REASON: { en: string; es: string } = {
  en: 'An IRRBB measure is a regulatory calculation under prescribed shocks, so there is no champion to rank against challengers; the case is compared in the App with and without the behavioural assumptions.',
  es: 'Una medida de IRRBB es un cálculo regulatorio bajo choques prescritos, así que no hay un campeón que ordenar frente a retadores; el caso se compara en la App con y sin los supuestos conductuales.',
};
/** Cases with no champion-against-challenger comparison, each with the reason the page states: no section here, their data still appears under Provenance. */
export const NO_BENCHMARK: Record<string, { en: string; es: string }> = {
  C06: {
    en: 'The provisions cases compare regimes (CMF B-1, IFRS 9, BdE Annex 9), not a champion with challengers; the regime comparison is in the App.',
    es: 'Los casos de provisiones comparan regímenes (CMF B-1, IFRS 9, Anejo 9 del BdE), no un campeón con retadores; la comparación de regímenes está en la App.',
  },
  C07: {
    en: 'The provisions cases compare regimes (CMF B-1, IFRS 9, BdE Annex 9), not a champion with challengers; the regime comparison is in the App.',
    es: 'Los casos de provisiones comparan regímenes (CMF B-1, IFRS 9, Anejo 9 del BdE), no un campeón con retadores; la comparación de regímenes está en la App.',
  },
  C14: IRRBB_REASON,
  C15: IRRBB_REASON,
  C16: {
    en: 'The liquidity case sets prescribed run-off scenarios (the LCR, the LiST Adverse and Extreme scenarios, a fast run) against one realised deposit run, not a champion with challengers; the scenarios and the March 2023 scoring are compared in the App.',
    es: 'El caso de liquidez contrasta escenarios de salida de depósitos prescritos (el LCR, los escenarios Adverso y Extremo de LiST, una corrida rápida) con una corrida real, no un campeón con retadores; los escenarios y la evaluación de marzo de 2023 se comparan en la App.',
  },
  C21: {
    en: 'Disparity measurement scores no model against another: it measures the gap in approval rates between groups of one lender and whether it replicates in the next year, so there is no champion to rank against challengers; the contrasts are read in the App.',
    es: 'La medición de disparidad no evalúa un modelo frente a otro: mide la brecha de tasas de aprobación entre grupos de un prestamista y si se replica en el año siguiente, así que no hay un campeón que ordenar frente a retadores; los contrastes se leen en la App.',
  },
};

/**
 * The Benchmark page as groups of tabs (GATE-15B, ADR-0071 and ADR-0017.2): the page was one document of every case's
 * comparison and the traversal of the gate stopped at its budget on it, and one tab per question family still did on the
 * scoring and the capital families. Now each case comparison is a tab of its own, in the group of the case's question
 * family (`experiments/families.ts`, the one the Experiments page uses), and each section of the page sits in exactly one
 * tab: the reading, the cases with no comparison and the limits in the first tab of the first group, the robustness charts
 * and the provenance of the data in its next two. At most six groups and six tabs in a group (ADR-0071); a tab or a group
 * with no section is not drawn.
 */
export type BenchGroupId = 'reading' | 'pd' | 'losses' | 'capital' | 'market' | 'validation';
export interface BenchTab {
  id: string;
  label: BiText;
  /** The sections of the tab in order: `how`, `case:<id>`, `excluded`, `limits`, `robustness`, `provenance`. */
  sections: string[];
}
export interface BenchGroup {
  id: BenchGroupId;
  label: BiText;
  tabs: BenchTab[];
}
const BENCH_GROUP_LABEL: Record<BenchGroupId, BiText> = {
  reading: { en: 'How are the comparisons read, and what stands behind them?', es: '¿Cómo se leen las comparaciones y qué hay detrás?' },
  pd: { en: 'Credit scoring and PD', es: 'Calificación crediticia y PD' },
  losses: { en: 'Credit losses', es: 'Pérdidas de crédito' },
  capital: { en: 'Capital, aggregation and stress', es: 'Capital, agregación y estrés' },
  market: { en: 'Market and balance-sheet risk', es: 'Riesgo de mercado y de balance' },
  validation: { en: 'ML, AI and the validator', es: 'ML, IA y el validador' },
};
/** The group of the comparisons of a question family. */
export const FAMILY_GROUP: Record<string, BenchGroupId> = {
  pd: 'pd',
  'credit-losses': 'losses',
  capital: 'capital',
  'market-balance': 'market',
  'ml-ai-risk': 'validation',
  validator: 'validation',
};
/** The group of a case's comparison: its family's; a family not listed lands in the capital group. */
export function benchGroupOf(caseId: string): BenchGroupId {
  return FAMILY_GROUP[familyOf(caseId).id] ?? 'capital';
}
const READING_TABS: BenchTab[] = [
  { id: 'reading', label: { en: 'Reading and limits', es: 'Lectura y límites' }, sections: [] },
  { id: 'robustness', label: { en: 'Robustness', es: 'Robustez' }, sections: ['robustness'] },
  { id: 'provenance', label: { en: 'Provenance', es: 'Procedencia' }, sections: ['provenance'] },
];
/** The groups of the page for the cases shown, whether cases are excluded and whether a robustness chart exists, in the order of the page. */
export function benchmarkPlan(shown: string[], excluded: boolean, comparable: boolean): BenchGroup[] {
  const reading = READING_TABS.map((t) => ({ ...t, sections: [...t.sections] }));
  reading[0].sections = excluded ? ['how', 'excluded', 'limits'] : ['how', 'limits'];
  const groups: BenchGroup[] = [{ id: 'reading', label: BENCH_GROUP_LABEL.reading, tabs: reading.filter((t) => t.id !== 'robustness' || comparable) }];
  for (const id of ['pd', 'losses', 'capital', 'market', 'validation'] as BenchGroupId[]) {
    const tabs = shown.filter((c) => benchGroupOf(c) === id).map((c) => ({ id: `case-${c.toLowerCase()}`, label: { en: c, es: c }, sections: [`case:${c}`] }));
    if (tabs.length) groups.push({ id, label: BENCH_GROUP_LABEL[id], tabs });
  }
  return groups;
}

export function Benchmark() {
  const t = useT();
  const lang = useShellLang();
  const all = useArtifact((s) => loadAllManifests(s), []);
  const ready = all.state === 'ready';
  const manifests = ready ? all.data.manifests : [];
  const shown = manifests.filter((m) => !(m.case_id in NO_BENCHMARK));
  const excluded = manifests.filter((m) => m.case_id in NO_BENCHMARK);
  const comparable = shown.filter((m) => !HAS_OWN_BENCHMARK.has(m.case_id) && !U6_BENCHMARK_CASES.has(m.case_id) && !W2_BENCHMARK_CASES.has(m.case_id) && !B3_BENCHMARK_CASES.has(m.case_id));
  const plan = benchmarkPlan(shown.map((m) => m.case_id), excluded.length > 0, comparable.length > 0);
  const section = (key: string): ReactNode => {
    if (key === 'how')
      return (
        <DocSection key={key} title={{ en: 'How to read the comparisons', es: 'Cómo leer las comparaciones' }} refs={['delong1988', 'lessmann2015']}>
          <P
            en={<>A challenger beats the champion only when the paired DeLong test on the same obligors says so <Cite id="delong1988" />, and only by the difference it measures: the literature reports gains of a few AUC points for tree ensembles on retail data <Cite id="lessmann2015" />, and this page shows whether each case agrees, with the interval of every AUC and the calibration of every rung.</>}
            es={<>Un retador supera al campeón solo cuando la prueba pareada de DeLong sobre los mismos deudores lo dice <Cite id="delong1988" />, y solo por la diferencia que mide: la literatura reporta ganancias de unos pocos puntos de AUC para los ensambles de árboles en datos minoristas <Cite id="lessmann2015" />, y esta página muestra si cada caso lo confirma, con el intervalo de cada AUC y la calibración de cada peldaño.</>}
          />
        </DocSection>
      );
    if (key.startsWith('case:')) {
      const m = shown.find((x) => x.case_id === key.slice(5));
      if (!m) return null;
      return (
        <DocSection
          key={key}
          area={HAS_OWN_BENCHMARK.has(m.case_id) ? 'results' : 'comparison'}
          title={{ en: `${m.case_id}: ${m.title.en}`, es: `${m.case_id}: ${m.title.es}` }}
          noRefsReason={{ en: 'Read from the committed artifacts.', es: 'Leído desde los artefactos versionados.' }}
        >
          {m.case_id === 'C04' ? <C04Benchmark manifest={m} /> : m.case_id === 'C05' ? <C05BenchmarkSection manifest={m} /> : m.case_id === 'C22' ? <C22BenchmarkSection manifest={m} /> : U6_BENCHMARK_CASES.has(m.case_id) ? <U6BenchmarkSection manifest={m} /> : W2_BENCHMARK_CASES.has(m.case_id) ? <W2BenchmarkSection manifest={m} /> : B3_BENCHMARK_CASES.has(m.case_id) ? <B3BenchmarkSection manifest={m} /> : <CaseBenchmark manifest={m} />}
        </DocSection>
      );
    }
    if (key === 'excluded')
      return (
        <DocSection key={key} area="comparison" title={{ en: 'Cases with no champion-against-challenger comparison', es: 'Casos sin comparación de campeón contra retadores' }} noRefsReason={{ en: 'States why a case is not compared here.', es: 'Declara por qué un caso no se compara aquí.' }}>
          <Table head={[t('Case', 'Caso'), t('Why it is not compared here', 'Por qué no se compara aquí')]} rows={excluded.map((m) => [`${m.case_id}: ${pick(m.title, lang)}`, pick(NO_BENCHMARK[m.case_id], lang)])} wide={2} />
        </DocSection>
      );
    if (key === 'robustness')
      return (
        <DocSection key={key} area="robustness" title={{ en: 'Robustness to perturbed data', es: 'Robustez ante datos perturbados' }} noRefsReason={{ en: 'Read from the committed artifacts.', es: 'Leído desde los artefactos versionados.' }}>
          {comparable.map((m) => (
            <Robustness key={m.case_id} manifest={m} />
          ))}
        </DocSection>
      );
    if (key === 'provenance')
      return (
        <DocSection key={key} area="provenance" title={{ en: 'Provenance of the data', es: 'Procedencia de los datos' }} noRefsReason={{ en: 'Read from the manifests and the source registry.', es: 'Leído de los manifiestos y del registro de fuentes.' }}>
          <Provenance manifests={manifests} />
        </DocSection>
      );
    return (
      <DocSection key={key} area="caveat" title={{ en: 'The limits of the comparison', es: 'Los límites de la comparación' }} noRefsReason={{ en: 'States the limits of this page.', es: 'Declara los límites de esta página.' }}>
        <Callout variant="honest" title={<T en="What these comparisons do not show" es="Lo que estas comparaciones no muestran" />}>
          <T
            en="Each comparison holds for its dataset and its split: a gain on one portfolio is not a gain on another, no out-of-time validation is possible on a single snapshot, and a significant difference in AUC is not a difference that matters for a decision until its capital or loss effect is read. Nothing here certifies a model."
            es="Cada comparación vale para su conjunto de datos y su partición: una ganancia en una cartera no es una ganancia en otra, no es posible una validación fuera del tiempo sobre una sola foto, y una diferencia significativa de AUC no es una diferencia que importe para una decisión hasta que se lee su efecto en capital o en pérdida. Nada de esto certifica un modelo."
          />
        </Callout>
      </DocSection>
    );
  };
  return (
    <DocPage
      wide
      title={{ en: 'Benchmark', es: 'Benchmark' }}
      lede={t(
        'Every rung against the champion on held-out data: discrimination with its interval and the paired test, calibration, the degradation under perturbed data, the provenance of every dataset, the comparison of a learned model with a classical one, and only the claims those tests support.',
        'Cada peldaño contra el campeón en datos reservados: discriminación con su intervalo y la prueba pareada, calibración, la degradación con datos perturbados, la procedencia de cada conjunto de datos, la comparación de un modelo aprendido con uno clásico, y solo las afirmaciones que esas pruebas respaldan.',
      )}
      floorWaivers={[
        {
          floor: 'live',
          reason: {
            en: 'The Benchmark replays committed artifacts. The live inference on held-out data is the App workbench, in its Impact group, where the reader moves the controls.',
            es: 'El Benchmark reproduce artefactos versionados. La inferencia en vivo sobre datos reservados es el banco de trabajo de la App, en su grupo Impacto, donde el lector mueve los controles.',
          },
        },
      ]}
    >
      <TabGroups
        ariaLabel={t('Parts of the benchmark', 'Partes del benchmark')}
        groups={plan.map((g) => ({
          id: g.id,
          label: pick(g.label, lang),
          tabs: g.tabs.map((tab) => ({
            id: tab.id,
            label: pick(tab.label, lang),
            content: (
              <>
                {tab.sections.map((key) => section(key))}
                {!ready && tab.id === 'reading' && (
                  <p className="caos-pending" data-state="loading">
                    {t('Loading the case manifests', 'Cargando los manifiestos de los casos')}
                  </p>
                )}
              </>
            ),
          })),
        }))}
      />
    </DocPage>
  );
}
