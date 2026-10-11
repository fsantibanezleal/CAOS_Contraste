// C04's sections of the cross-case pages: Experiments (every variant read from its artifact, and the agencies' PDs by
// grade under two definitions) and Benchmark (the default definitions, the generators, the five-year projections, the
// estimators, the tests and the intervals compared, and the papers recomputed). Every number is read from the committed
// artifacts at load time and every verdict is computed from them, never typed in.
import { PlotCard, Verdict, formatNumber, pick, useShellLang, type BiText, type Provenance } from '@fasl-work/caos-app-shell';
import { UPlotChart, type ChartSeries } from '@fasl-work/caos-app-shell/chart';
import { useT } from '../content/bi';
import {
  ATTRIBUTION_FALLBACK,
  GENERATOR_TEXT,
  LoadError,
  SEVERITY_TEXT,
  TRUTH_TEXT,
  agencyFacts,
  atPrintedDigits,
  familyDesign,
  impactValue,
  irwMethod,
  kindsOf,
  pText,
  paperAgreements,
  pctText,
  shortOf,
  testName,
  titleOf,
  useC04Variants,
  type Lang,
} from '../content/cases/C04Results';
import type { C04MarkovRung, C04Simulation, C04ThinRung, CaseManifest, VariantArtifact } from '../lib/contract.types';
import { provenanceOf } from '../workbench/model';
import { agencyLraChart, nonEmpty, rungText } from '../workbench/c04/C04Common';
import { SP_ENTITY } from '../workbench/c04/FamilyViews';
import {
  ESMA_DEFINITIONS,
  ESTIMATOR_COLOR,
  ESTIMATOR_LABEL,
  ESTIMATORS,
  GRADE_AXIS,
  GRADES,
  N_GRADES,
  isAgency,
  isFamily,
  isPublished,
  type AgencyVariant,
  type FamilyVariant,
  type PublishedVariant,
} from '../workbench/c04/selection';

const REPLAY = 'replay' as const;
const AT5 = 'p<0.05';
const AT1 = 'p<0.01';
/** the power a test is said to reach a defect with */
const POWER = 0.8;
/** the one-sided 99.9% normal quantile: a rate within the level plus this many Monte Carlo SEs keeps its size */
const SIZE_Z = 3.090232306167813;
const CCC = N_GRADES - 1;
const B = N_GRADES - 2;
const BB = N_GRADES - 3;
const CHART_HEIGHT = 300;

const finite = (x: number | null | undefined): x is number => x !== null && x !== undefined && Number.isFinite(x);
const ratioText = (lang: Lang, x: number | null | undefined) => formatNumber(x, lang, { digits: 3 });
const share = (lang: Lang, x: number | null | undefined) => formatNumber(x, lang, { percent: true, decimals: 1 });
/** An exact probability (by enumeration, no Monte Carlo error) at the findings' two decimals: 0.33%, not 0.3%. */
const exactShare = (lang: Lang, x: number | null | undefined) => formatNumber(x, lang, { percent: true, decimals: 2 });
const range = (lang: Lang, xs: number[], f: (l: Lang, x: number) => string) =>
  xs.length ? (Math.min(...xs) === Math.max(...xs) ? f(lang, xs[0]) : `${f(lang, Math.min(...xs))} ${lang === 'es' ? 'a' : 'to'} ${f(lang, Math.max(...xs))}`) : '-';

/** A test's size holds when its rate is at most the level plus 3.09 Monte Carlo SEs of a rate at the level. */
const sizeBound = (level: number, n: number) => level + SIZE_Z * Math.sqrt((level * (1 - level)) / n);

// ---------------------------------------------------------------------------------------------------------------------
// Experiments

/** The families draw their paths from a generator fitted to S&P's CEREP counts: a card of theirs names the entity and
 * carries ESMA's attribution (verbatim, the source's own wording), as the family views do. */
const FAMILY_SOURCE = {
  en: ` CEREP counts of ${SP_ENTITY.name}. ${ATTRIBUTION_FALLBACK}.`,
  es: ` Conteos de CEREP de ${SP_ENTITY.name}. ${ATTRIBUTION_FALLBACK}.`,
} as const;

function agencyData(v: AgencyVariant, lang: Lang): string {
  const a = agencyFacts(v);
  return lang === 'es'
    ? `${a.entity}: ${a.cohorts} cohortes anuales de ${a.first} a ${a.last} y ${a.semesters} semestres; ${formatNumber(a.ratings, 'es')} calificaciones en las cohortes anuales. ${a.attribution}.`
    : `${a.entity}: ${a.cohorts} annual cohorts from ${a.first} to ${a.last} and ${a.semesters} semesters; ${formatNumber(a.ratings, 'en')} ratings over the annual cohorts. ${a.attribution}.`;
}

function agencyShows(v: AgencyVariant, lang: Lang): string {
  const o = v.outputs;
  const a = agencyFacts(v);
  const d4 = o.lra.d4 ? pctText(lang, o.lra.d4.rate[CCC]) : null;
  const gap = o.definition_gap.d4_over_d2?.[CCC] ?? null;
  const head =
    lang === 'es'
      ? `${GRADES[CCC]}: D2 ${pctText('es', o.lra.d2.rate[CCC])}${d4 ? `, D4 ${d4} (D4/D2 agrupada ${ratioText('es', gap)})` : ', sin D4'}`
      : `${GRADES[CCC]}: D2 ${pctText('en', o.lra.d2.rate[CCC])}${d4 ? `, D4 ${d4} (pooled D4/D2 ${ratioText('en', gap)})` : ', no D4'}`;
  const homog =
    lang === 'es'
      ? `homogeneidad temporal chi-cuadrado ${formatNumber(a.homogeneity.statistic, 'es', { decimals: 0 })} con ${formatNumber(a.homogeneity.dof, 'es')} grados de libertad, ${pText('es', a.homogeneity.p_value)}; ${a.reference.red} de ${a.reference.total} cohortes se apartan de la matriz agrupada al ${formatNumber(a.reference.alpha, 'es', { percent: true, decimals: 0 })}`
      : `time homogeneity chi-square ${formatNumber(a.homogeneity.statistic, 'en', { decimals: 0 })} on ${formatNumber(a.homogeneity.dof, 'en')} degrees of freedom, ${pText('en', a.homogeneity.p_value)}; ${a.reference.red} of ${a.reference.total} cohorts depart from the pooled matrix at ${formatNumber(a.reference.alpha, 'en', { percent: true, decimals: 0 })}`;
  const ttc = a.ttc === null ? '' : lang === 'es' ? `; tasa TTC de incumplimiento ${pctText('es', a.ttc)}` : `; TTC default rate ${pctText('en', a.ttc)}`;
  return `${head}; ${homog}${ttc}.`;
}

function familyShows(f: FamilyVariant, lang: Lang): string {
  const items = Object.values(f.impact).map((it) => `${pick(it.label, lang)}: ${impactValue(it, lang)}`);
  const findings = f.findings.map((x) => `${x.id} (${pick(SEVERITY_TEXT[x.severity] ?? x.severity, lang)})`).join(', ');
  return `${items.join('; ')}. ${lang === 'es' ? 'Hallazgos' : 'Findings'}: ${findings || '-'}.`;
}

function publishedShows(p: PublishedVariant, lang: Lang): string {
  return paperAgreements(p)
    .map((x) => (lang === 'es' ? `${pick(x.name, 'es')}: ${x.agree} de ${x.total} a los dígitos impresos` : `${pick(x.name, 'en')}: ${x.agree} of ${x.total} at the printed digits`))
    .join('; ');
}

export function C04Experiments({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const all = useC04Variants(manifest);
  if (all.state === 'loading') return <p className="caos-pending" data-state="loading">{t('Loading the variants', 'Cargando las variantes')}</p>;
  if (all.state === 'error') return <LoadError error={all.error} />;
  const vs = all.data;
  const { agencies } = kindsOf(vs);
  const chart = agencyLraChart(agencies, (id) => shortOf(manifest, id), null);
  const attribution = agencies[0]?.outputs.attribution || ATTRIBUTION_FALLBACK;
  const describe = (v: VariantArtifact<unknown>): [string, string] => {
    if (isAgency(v)) return [agencyData(v, lang), agencyShows(v, lang)];
    if (isFamily(v)) return [familyDesign(v, lang), familyShows(v, lang)];
    if (isPublished(v)) {
      const papers = manifest.sources.filter((s) => manifest.source_details[s]?.class === 'derived-only').map((s) => manifest.source_details[s].name);
      return [papers.join('; '), publishedShows(v, lang)];
    }
    return ['', ''];
  };
  return (
    <div data-state="ready">
      <div className="ct-scroll">
        <table className="caos-table ct-wrap-head" data-table="c04-variants">
          <thead>
            <tr>
              <th className="caos-col-text">{t('Variant', 'Variante')}</th>
              <th>{t('Truth', 'Verdad')}</th>
              <th className="caos-col-text">{t('Data', 'Datos')}</th>
              <th className="caos-col-text">{t('What the variant shows', 'Lo que muestra la variante')}</th>
            </tr>
          </thead>
          <tbody>
            {vs.map((v) => {
              const [data, shows] = describe(v);
              return (
                <tr key={v.variant_id} data-variant={v.variant_id}>
                  <td className="caos-col-text">{pick(titleOf(manifest, v.variant_id), lang)}</td>
                  <td>{pick(TRUTH_TEXT[v.provenance.truth_status] ?? v.provenance.truth_status, lang)}</td>
                  <td className="caos-col-text">{data}</td>
                  <td className="caos-col-text">{shows}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {chart && (
        <PlotCard
          title={{ en: 'C04, the agencies\' long-run average PD by grade, D2 and D4', es: 'C04, la PD promedio de largo plazo por grado de las agencias, D2 y D4' }}
          lane={REPLAY}
          provenance={provenanceOf(agencies[0]?.provenance.truth_status)}
          note={{
            en: `The mean of the yearly one-year PDs (EBA/GL/2017/16 paragraph 84), percent a year on a log scale; colour the definition (D2 the default-rate page, D4 the transition page's default column), dash the agency's EU entity (${agencies.map((a) => a.outputs.agency.name).join('; ')}). A zero average has no point. Grey: each agency's TTC default rate under its pooled matrix. ${pick(ESMA_DEFINITIONS, 'en')} ${attribution}.`,
            es: `La media de las PD anuales (párrafo 84 de EBA/GL/2017/16), porcentaje al año en escala logarítmica; color la definición (D2 la página de tasas de incumplimiento, D4 la columna de incumplimiento de la página de transiciones), trazo la entidad UE de la agencia (${agencies.map((a) => a.outputs.agency.name).join('; ')}). Un promedio cero no tiene punto. Gris: la tasa TTC de incumplimiento de cada agencia con su matriz agrupada. ${pick(ESMA_DEFINITIONS, 'es')} ${attribution}.`,
          }}
        >
          <UPlotChart height={CHART_HEIGHT} x={chart.x} y={chart.y} series={chart.series} marks={chart.marks} />
        </PlotCard>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Benchmark

function DefinitionsCard({ agencies, manifest, provenance }: { agencies: AgencyVariant[]; manifest: CaseManifest; provenance: Provenance }) {
  const lang = useShellLang();
  const t = useT();
  const short = (id: string) => pick(shortOf(manifest, id), lang);
  const pct0 = (l: Lang, x: number | null | undefined) => formatNumber(x, l, { percent: true, decimals: 0 });
  const parts = (l: Lang) =>
    agencies
      .map((a) => {
        const gap = a.outputs.definition_gap.d4_over_d2;
        const s = pick(shortOf(manifest, a.variant_id), l);
        if (!gap) return l === 'es' ? `${s} no tiene D4 (su página de transiciones no tiene categoría de incumplimiento)` : `${s} has no D4 (its transition page has no default category)`;
        return l === 'es'
          ? `${s} ${pct0('es', gap[CCC])} de la PD de la página de incumplimientos (D2) en ${GRADES[CCC]} y ${pct0('es', gap[B])} en ${GRADES[B]}`
          : `${s} ${pct0('en', gap[CCC])} of the default page's PD (D2) at ${GRADES[CCC]} and ${pct0('en', gap[B])} at ${GRADES[B]}`;
      })
      .join('; ');
  const same = agencies.filter((a) => a.outputs.lra.d3.defaults.every((d, i) => d === a.outputs.lra.d2.defaults[i]));
  const sameNames = (l: Lang) => same.map((a) => pick(shortOf(manifest, a.variant_id), l)).join(', ');
  return (
    <PlotCard
      title={{ en: 'C04, the default definitions compared', es: 'C04, las definiciones de incumplimiento comparadas' }}
      lane={REPLAY}
      provenance={provenance}
      note={{
        en: `Long-run averages (EBA/GL/2017/16 paragraph 84) by agency and grade under D2, D3 and D4, and the pooled ratios. ${agencies.map((a) => a.outputs.agency.name).join('; ')}. ${agencies[0]?.outputs.attribution || ATTRIBUTION_FALLBACK}.`,
        es: `Promedios de largo plazo (párrafo 84 de EBA/GL/2017/16) por agencia y grado con D2, D3 y D4, y las razones agrupadas. ${agencies.map((a) => a.outputs.agency.name).join('; ')}. ${agencies[0]?.outputs.attribution || ATTRIBUTION_FALLBACK}.`,
      }}
    >
      <Verdict
        compact
        title={{ en: 'What the definitions do to a PD', es: 'Lo que las definiciones hacen a una PD' }}
        tone="accent"
        verdict={{
          en: `Pooled over the years both pages hold, the transition matrix's default column (D4) gives ${parts('en')}.${same.length ? ` D3 counts the same defaults as D2 in every grade for ${sameNames('en')}: the two differ by the cohort only.` : ''} ${pick(ESMA_DEFINITIONS, 'en')}`,
          es: `Agrupada en los años que ambas páginas cubren, la columna de incumplimiento de la matriz de transición (D4) da ${parts('es')}.${same.length ? ` D3 cuenta los mismos incumplimientos que D2 en cada grado para ${sameNames('es')}: las dos difieren solo por la cohorte.` : ''} ${pick(ESMA_DEFINITIONS, 'es')}`,
        }}
      />
      <div className="ct-scroll">
        <table className="caos-table" data-table="bench-definitions">
          <thead>
            <tr>
              <th className="caos-col-text">{t('Agency', 'Agencia')}</th>
              <th className="caos-col-text">{t('Grade', 'Grado')}</th>
              <th>D2</th>
              <th>D3</th>
              <th>D4</th>
              <th>D4 / D2</th>
              <th>D3 / D2</th>
            </tr>
          </thead>
          <tbody>
            {agencies.flatMap((a) =>
              GRADES.map((g, i) => {
                const o = a.outputs;
                return (
                  <tr key={`${a.variant_id}-${g}`} data-variant={a.variant_id} data-grade={g}>
                    <td className="caos-col-text">{short(a.variant_id)}</td>
                    <td className="caos-col-text">{g}</td>
                    <td>{pctText(lang, o.lra.d2.rate[i])}</td>
                    <td>{pctText(lang, o.lra.d3.rate[i])}</td>
                    <td>{o.lra.d4 ? pctText(lang, o.lra.d4.rate[i]) : t('none', 'no hay')}</td>
                    <td>{o.definition_gap.d4_over_d2 ? ratioText(lang, o.definition_gap.d4_over_d2[i]) : t('none', 'no hay')}</td>
                    <td>{o.definition_gap.d3_over_d2 ? ratioText(lang, o.definition_gap.d3_over_d2[i]) : t('none', 'no hay')}</td>
                  </tr>
                );
              }),
            )}
          </tbody>
        </table>
      </div>
    </PlotCard>
  );
}

function GeneratorsCard({ agencies, manifest, provenance }: { agencies: AgencyVariant[]; manifest: CaseManifest; provenance: Provenance }) {
  const lang = useShellLang();
  const t = useT();
  const close = agencies.flatMap((a) => (['em', 'diagonal', 'weighted'] as const).map((k) => a.outputs.generators[k]?.l1).filter(finite));
  const jlt = agencies.map((a) => a.outputs.generators.jlt?.l1).filter(finite);
  const ratios = agencies
    .map((a) => {
      const j = a.outputs.generators.jlt?.l1;
      const d = a.outputs.generators.diagonal?.l1;
      return finite(j) && finite(d) && d > 0 ? j / d : null;
    })
    .filter(finite);
  const excluded = agencies.filter((a) => a.outputs.embedding.exact_generator_excluded);
  const monotone = agencies.filter((a) => a.outputs.embedding.stochastically_monotone).length;
  // each condition of Theorem 3 with the agencies that meet it: (c) counts the moves reachable but never observed
  const byC = agencies.filter((a) => a.outputs.embedding.theorem3.c.length > 0);
  const byA = agencies.filter((a) => a.outputs.embedding.theorem3.a);
  const byB = agencies.filter((a) => a.outputs.embedding.theorem3.b);
  const names = (list: typeof agencies, l: Lang) => list.map((a) => pick(shortOf(manifest, a.variant_id), l)).join(', ');
  const moves = (l: Lang) => byC.map((a) => `${pick(shortOf(manifest, a.variant_id), l)} ${a.outputs.embedding.theorem3.c.length}`).join(', ');
  const conditions = (l: Lang) =>
    [
      byC.length ? (l === 'es' ? `por (c) para ${byC.length} (movimientos alcanzables pero nunca observados: ${moves(l)})` : `by (c) for ${byC.length} (moves reachable but never observed: ${moves(l)})`) : null,
      byA.length ? (l === 'es' ? `por (a), det P no positivo, para ${names(byA, l)}` : `by (a), det P not positive, for ${names(byA, l)}`) : null,
      byB.length ? (l === 'es' ? `por (b), det P sobre el producto de la diagonal, para ${names(byB, l)}` : `by (b), det P above the product of the diagonal, for ${names(byB, l)}`) : null,
    ]
      .filter(Boolean)
      .join('; ');
  const l1 = (l: Lang, x: number) => formatNumber(x, l, { digits: 3 });
  const times = (l: Lang, x: number) => formatNumber(x, l, { digits: 2 });
  return (
    <PlotCard
      title={{ en: 'C04, the generators of the pooled matrices', es: 'C04, los generadores de las matrices agrupadas' }}
      lane={REPLAY}
      provenance={provenance}
      note={{
        en: `The L1 distance of exp(Q) to each agency's pooled one-year matrix for the EM generator of the annual counts (Smith and dos Reis 2018), the diagonal and weighted adjustments and the JLT approximation (Israel, Rosenthal and Wei 2001); Theorem 3(c)'s moves are reachable through other grades but never observed. ${agencies.map((a) => a.outputs.agency.name).join('; ')}. ${agencies[0]?.outputs.attribution || ATTRIBUTION_FALLBACK}.`,
        es: `La distancia L1 de exp(Q) a la matriz anual agrupada de cada agencia para el generador EM de los conteos anuales (Smith y dos Reis 2018), los ajustes diagonal y ponderado y la aproximación JLT (Israel, Rosenthal y Wei 2001); los movimientos del Teorema 3(c) son alcanzables a través de otros grados pero nunca observados. ${agencies.map((a) => a.outputs.agency.name).join('; ')}. ${agencies[0]?.outputs.attribution || ATTRIBUTION_FALLBACK}.`,
      }}
    >
      <Verdict
        compact
        title={{ en: 'What the generators support', es: 'Lo que respaldan los generadores' }}
        tone="accent"
        verdict={{
          en: `EM and the diagonal and weighted adjustments reproduce the pooled matrices within ${range('en', close, l1)} in L1; JLT lies ${range('en', jlt, l1)} from them, ${range('en', ratios, times)} times the diagonal adjustment's distance. Theorem 3 excludes an exact generator for ${excluded.length} of ${agencies.length} agencies${excluded.length ? ` (${conditions('en')})` : ''}; ${monotone} of ${agencies.length} pooled matrices are stochastically monotone.`,
          es: `EM y los ajustes diagonal y ponderado reproducen las matrices agrupadas dentro de ${range('es', close, l1)} en L1; JLT queda a ${range('es', jlt, l1)} de ellas, ${range('es', ratios, times)} veces la distancia del ajuste diagonal. El teorema 3 excluye un generador exacto para ${excluded.length} de ${agencies.length} agencias${excluded.length ? ` (${conditions('es')})` : ''}; ${monotone} de ${agencies.length} matrices agrupadas son estocásticamente monótonas.`,
        }}
      />
      <div className="ct-scroll">
        <table className="caos-table ct-wrap-head" data-table="bench-generators">
          <thead>
            <tr>
              <th className="caos-col-text">{t('Agency', 'Agencia')}</th>
              <th>{t('EM, L1', 'EM, L1')}</th>
              <th>{t('Diagonal, L1', 'Diagonal, L1')}</th>
              <th>{t('Weighted, L1', 'Ponderado, L1')}</th>
              <th>{t('JLT, L1', 'JLT, L1')}</th>
              <th>{t('EM iterations', 'Iteraciones EM')}</th>
              <th>{t('Moves never observed', 'Movimientos nunca observados')}</th>
              <th>{t('Stochastically monotone', 'Estocásticamente monótona')}</th>
            </tr>
          </thead>
          <tbody>
            {agencies.map((a) => {
              const gens = a.outputs.generators;
              const e = a.outputs.embedding;
              return (
                <tr key={a.variant_id} data-variant={a.variant_id}>
                  <td className="caos-col-text">{pick(shortOf(manifest, a.variant_id), lang)}</td>
                  <td>{formatNumber(gens.em.l1, lang, { digits: 3 })}</td>
                  <td>{formatNumber(gens.diagonal?.l1 ?? null, lang, { digits: 3 })}</td>
                  <td>{formatNumber(gens.weighted?.l1 ?? null, lang, { digits: 3 })}</td>
                  <td>{formatNumber(gens.jlt?.l1 ?? null, lang, { digits: 3 })}</td>
                  <td>{`${formatNumber(gens.em.iterations, lang)}${gens.em.converged ? '' : t(', not converged', ', sin converger')}`}</td>
                  <td>{e.theorem3.c.length}</td>
                  <td>{e.stochastically_monotone ? t('yes', 'sí') : t('no', 'no')}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </PlotCard>
  );
}

function LifetimeCard({ agencies, manifest, provenance }: { agencies: AgencyVariant[]; manifest: CaseManifest; provenance: Provenance }) {
  const lang = useShellLang();
  const t = useT();
  const latest = agencies.flatMap((a) => {
    const w = a.outputs.lifetime[a.outputs.lifetime.length - 1];
    return w ? [{ a, w }] : [];
  });
  if (!latest.length) return null;
  const sentence = (l: Lang) =>
    latest
      .map(({ a, w }) => {
        const s = pick(shortOf(manifest, a.variant_id), l);
        const obs = w.observed.cumulative_d2?.[CCC] ?? null;
        const chain = w.projected.chain_state[CCC];
        const pow = w.projected.pooled_power[CCC];
        if (!finite(chain))
          return l === 'es'
            ? `${s}, ${w.label}: ${pctText('es', obs)} de las calificaciones ${GRADES[CCC]} incumplieron en los cinco años; sin proyección, su página de transiciones no tiene categoría de incumplimiento`
            : `${s}, ${w.label}: ${pctText('en', obs)} of the ${GRADES[CCC]} ratings defaulted within the five years; no projection, its transition page has no default category`;
        return l === 'es'
          ? `${s}, ${w.label}: ${pctText('es', obs)} de las calificaciones ${GRADES[CCC]} incumplieron en los cinco años en la página de incumplimientos; las matrices anuales de la ventana encadenadas dan ${pctText('es', chain)} y la matriz agrupada a la quinta ${pctText('es', pow)}`
          : `${s}, ${w.label}: ${pctText('en', obs)} of the ${GRADES[CCC]} ratings defaulted within the five years on the default page; the window's own annual matrices chained give ${pctText('en', chain)} and the pooled matrix to the fifth power ${pctText('en', pow)}`;
      })
      .join('; ');
  const grades = [BB, B, CCC];
  return (
    <PlotCard
      title={{ en: 'C04, five-year PDs: what the windows observed against the chained matrices', es: 'C04, PD a cinco años: lo que observaron las ventanas contra las matrices encadenadas' }}
      lane={REPLAY}
      provenance={provenance}
      note={{
        en: `The latest five-year window of each agency: the share of its starting cohort that defaulted within the window on the default-rate page (D2, cumulative), the share in a default category at the window's end (D4), and the projections of the same cohort by the window's annual matrices chained (withdrawals a state), the pooled matrix to the fifth power and exp(5Q) of the EM generator. ${agencies.map((a) => a.outputs.agency.name).join('; ')}. ${agencies[0]?.outputs.attribution || ATTRIBUTION_FALLBACK}.`,
        es: `La última ventana de cinco años de cada agencia: la fracción de su cohorte inicial que incumplió dentro de la ventana en la página de tasas de incumplimiento (D2, acumulada), la fracción en una categoría de incumplimiento al final de la ventana (D4), y las proyecciones de la misma cohorte por las matrices anuales de la ventana encadenadas (los retiros como estado), la matriz agrupada a la quinta y exp(5Q) del generador EM. ${agencies.map((a) => a.outputs.agency.name).join('; ')}. ${agencies[0]?.outputs.attribution || ATTRIBUTION_FALLBACK}.`,
      }}
    >
      <Verdict
        compact
        title={{ en: 'What a Markov projection misses', es: 'Lo que una proyección de Markov pierde' }}
        tone="warn"
        verdict={{
          en: `${sentence('en')}. The chained matrices carry the transition page's default column, which does not count a rating withdrawn after defaulting.`,
          es: `${sentence('es')}. Las matrices encadenadas llevan la columna de incumplimiento de la página de transiciones, que no cuenta una calificación retirada después de incumplir.`,
        }}
      />
      <div className="ct-scroll">
        <table className="caos-table ct-wrap-head" data-table="bench-lifetime">
          <thead>
            <tr>
              <th className="caos-col-text">{t('Agency', 'Agencia')}</th>
              <th className="caos-col-text">{t('Window', 'Ventana')}</th>
              <th className="caos-col-text">{t('Grade', 'Grado')}</th>
              <th>{t('Ratings at the start', 'Calificaciones al inicio')}</th>
              <th>{t('Defaulted within (D2)', 'Incumplieron dentro (D2)')}</th>
              <th>{t('In default at the end (D4)', 'En incumplimiento al final (D4)')}</th>
              <th>{t('Annual matrices chained', 'Matrices anuales encadenadas')}</th>
              <th>{t('Pooled matrix to the fifth', 'Matriz agrupada a la quinta')}</th>
              <th>{t('EM, exp(5Q)', 'EM, exp(5Q)')}</th>
            </tr>
          </thead>
          <tbody>
            {latest.flatMap(({ a, w }) =>
              grades.map((i) => (
                <tr key={`${a.variant_id}-${w.label}-${i}`} data-variant={a.variant_id} data-grade={GRADES[i]}>
                  <td className="caos-col-text">{pick(shortOf(manifest, a.variant_id), lang)}</td>
                  <td className="caos-col-text">{w.label}</td>
                  <td className="caos-col-text">{GRADES[i]}</td>
                  <td>{formatNumber(w.size[i], lang)}</td>
                  <td>{pctText(lang, w.observed.cumulative_d2?.[i] ?? null)}</td>
                  <td>{pctText(lang, w.observed.default_end[i])}</td>
                  <td>{pctText(lang, w.projected.chain_state[i])}</td>
                  <td>{pctText(lang, w.projected.pooled_power[i])}</td>
                  <td>{pctText(lang, w.projected.em[i])}</td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>
    </PlotCard>
  );
}

/** The Markov family's estimators: RMSE by grade on a log axis against the true PD, one line per estimator. */
export function estimatorsChart(markov: FamilyVariant): { x: number[]; series: ChartSeries[] } | null {
  const rung = (markov.outputs.rungs as C04MarkovRung[])[0];
  if (!rung) return null;
  const x = GRADES.map((_, i) => i + 1);
  const lines = nonEmpty(
    ESTIMATORS.map((e) => ({
      label: ESTIMATOR_LABEL[e],
      values: (rung.estimators[e]?.rmse ?? []).map((r) => (finite(r) && r > 0 ? r : null)),
      color: ESTIMATOR_COLOR[e],
      width: 2,
    })),
  );
  if (!lines.length) return null;
  return {
    x,
    series: [...lines, { label: { en: 'True one-year PD', es: 'PD anual verdadera' }, values: markov.outputs.generator.pd_1y.map((p) => (p > 0 ? p : null)), color: '--color-fg-subtle', width: 1.2, dash: [6, 4] }],
  };
}

function EstimatorsCard({ markov, manifest, provenance }: { markov: FamilyVariant; manifest: CaseManifest; provenance: Provenance }) {
  const lang = useShellLang();
  const t = useT();
  const rung = (markov.outputs.rungs as C04MarkovRung[])[0];
  const chart = estimatorsChart(markov);
  if (!rung || !chart) return null;
  const truth = markov.outputs.generator.pd_1y;
  const est = rung.estimators;
  const zero = est.cohort?.zero[0];
  const spread = (l: Lang) =>
    GRADES.map((g, i) => {
      const r = ESTIMATORS.map((e) => est[e]?.rmse[i]).filter((x): x is number => finite(x) && x > 0);
      return `${g} ${r.length ? formatNumber(Math.max(...r) / Math.min(...r), l, { digits: 2 }) : '-'}`;
    }).join(', ');
  return (
    <PlotCard
      title={{ en: 'C04, the estimators of the one-year PD against the truth', es: 'C04, los estimadores de la PD anual contra la verdad' }}
      lane={REPLAY}
      provenance={provenance}
      note={{
        en: `The ${pick(shortOf(manifest, markov.variant_id), 'en')} family (${pick(titleOf(manifest, markov.variant_id), 'en')}): ${familyDesign(markov, 'en')}; paths drawn from ${GENERATOR_TEXT.en}. RMSE of each estimator's one-year PD by grade, percent a year on a log scale, against the true PD (dashed).${FAMILY_SOURCE.en}`,
        es: `La familia ${pick(shortOf(manifest, markov.variant_id), 'es')} (${pick(titleOf(manifest, markov.variant_id), 'es')}): ${familyDesign(markov, 'es')}; trayectorias generadas desde ${GENERATOR_TEXT.es}. RMSE de la PD anual de cada estimador por grado, porcentaje al año en escala logarítmica, contra la PD verdadera (segmentada).${FAMILY_SOURCE.es}`,
      }}
    >
      <Verdict
        compact
        title={{ en: 'What the estimators support', es: 'Lo que respaldan los estimadores' }}
        tone="accent"
        verdict={{
          en: `At ${GRADES[0]} (true one-year PD ${pctText('en', truth[0])}) the cohort estimator is exactly zero in ${share('en', zero?.rate)} of ${formatNumber(zero?.n ?? null, 'en')} repetitions; its RMSE is ${pctText('en', est.cohort?.rmse[0])}, EM's ${pctText('en', est.em?.rmse[0])}, the duration estimator's ${pctText('en', est.duration?.rmse[0])} (it needs the transition times, which CEREP does not publish). The largest RMSE over the smallest, grade by grade: ${spread('en')}.`,
          es: `En ${GRADES[0]} (PD anual verdadera ${pctText('es', truth[0])}) el estimador de cohortes es exactamente cero en ${share('es', zero?.rate)} de ${formatNumber(zero?.n ?? null, 'es')} repeticiones; su RMSE es ${pctText('es', est.cohort?.rmse[0])}, el de EM ${pctText('es', est.em?.rmse[0])}, el del estimador de duración ${pctText('es', est.duration?.rmse[0])} (necesita los tiempos de transición, que CEREP no publica). El mayor RMSE sobre el menor, grado a grado: ${spread('es')}.`,
        }}
      />
      <UPlotChart
        height={CHART_HEIGHT}
        x={{ values: chart.x, label: GRADE_AXIS, format: { decimals: 0 } }}
        y={{ label: { en: 'RMSE of the one-year PD (log scale)', es: 'RMSE de la PD anual (escala log.)' }, log: true, format: { percent: true, digits: 2 } }}
        series={chart.series}
      />
      <div className="ct-scroll">
        <table className="caos-table" data-table="bench-estimators">
          <thead>
            <tr>
              <th className="caos-col-text">{t('Estimator', 'Estimador')}</th>
              {GRADES.map((g) => (
                <th key={g}>{`RMSE ${g}`}</th>
              ))}
              <th>{t(`Zero, ${GRADES[0]}`, `Cero, ${GRADES[0]}`)}</th>
            </tr>
          </thead>
          <tbody>
            {ESTIMATORS.map((e) => (
              <tr key={e} data-estimator={e}>
                <td className="caos-col-text">{pick(ESTIMATOR_LABEL[e], lang)}</td>
                {GRADES.map((g, i) => (
                  <td key={g}>{pctText(lang, est[e]?.rmse[i] ?? null)}</td>
                ))}
                <td>{share(lang, est[e]?.zero[0]?.rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PlotCard>
  );
}

function rateCell(s: C04Simulation, key: string, lang: Lang): string {
  const r = s.rates[key];
  return r ? `${share(lang, r.rate)} (${share(lang, r.se)})` : '-';
}

function TestsCard({ families, manifest, provenance }: { families: FamilyVariant[]; manifest: CaseManifest; provenance: Provenance }) {
  const lang = useShellLang();
  const t = useT();
  const withSims = families.filter((f) => f.outputs.simulations.length > 0);
  if (!withSims.length) return null;
  const markov = withSims.find((f) => f.outputs.ladder === null);
  const sizes = markov?.outputs.simulations ?? [];
  const holds = (s: C04Simulation) => {
    const r5 = s.rates[AT5];
    const r1 = s.rates[AT1];
    return !!r5 && !!r1 && r5.rate <= sizeBound(0.05, s.n_rep) && r1.rate <= sizeBound(0.01, s.n_rep);
  };
  const failing = sizes.filter((s) => !holds(s));
  const label = (f: FamilyVariant, s: C04Simulation, l: Lang) => `${pick(testName(s.test_id), l)} (${rungText(f, s, l)})`;
  const power = (f: FamilyVariant, l: Lang) => {
    const ladder = f.outputs.ladder;
    if (!ladder) return '';
    const ids = [...new Set(f.outputs.simulations.map((s) => s.test_id))];
    return ids
      .map((id) => {
        const rows = f.outputs.simulations.filter((s) => s.test_id === id && s.rung !== null).sort((a, b) => (a.rung ?? 0) - (b.rung ?? 0));
        const reach = rows.find((s) => s.rung !== ladder.values[0] && (s.rates[AT5]?.rate ?? 0) >= POWER);
        const top = rows[rows.length - 1];
        const name = pick(testName(id), l);
        if (reach) return l === 'es' ? `${name} desde ${formatNumber(reach.rung, 'es', { digits: 4 })}` : `${name} from ${formatNumber(reach.rung, 'en', { digits: 4 })}`;
        return l === 'es'
          ? `${name} no dentro de la escala (${share('es', top?.rates[AT5]?.rate)} en ${formatNumber(top?.rung ?? null, 'es', { digits: 4 })})`
          : `${name} not within the ladder (${share('en', top?.rates[AT5]?.rate)} at ${formatNumber(top?.rung ?? null, 'en', { digits: 4 })})`;
      })
      .join(', ');
  };
  const defects = withSims.filter((f) => f.outputs.ladder !== null);
  const verdict = (l: Lang) => {
    const size = markov
      ? l === 'es'
        ? `En la cadena de Markov (${formatNumber(sizes[0]?.n_rep ?? null, 'es')} repeticiones o más), ${sizes.length - failing.length} de ${sizes.length} formas de prueba mantienen su tamaño al 5% y al 1% (la tasa a lo más el nivel más 3,09 EE de Monte Carlo)${failing.length ? `; no: ${failing.map((s) => `${label(markov, s, 'es')} ${share('es', s.rates[AT5]?.rate)} al 5%`).join('; ')}` : ''}.`
        : `On the Markov chain (${formatNumber(sizes[0]?.n_rep ?? null, 'en')} repetitions or more), ${sizes.length - failing.length} of ${sizes.length} test forms hold their size at 5% and 1% (the rate at most the level plus 3.09 Monte Carlo SEs)${failing.length ? `; not: ${failing.map((s) => `${label(markov, s, 'en')} ${share('en', s.rates[AT5]?.rate)} at 5%`).join('; ')}` : ''}.`
      : '';
    const pw = defects
      .map((f) => `${pick(shortOf(manifest, f.variant_id), l)}, ${l === 'es' ? `${Math.round(POWER * 100)}% de potencia al 5%` : `${Math.round(POWER * 100)}% power at 5%`}: ${power(f, l)}`)
      .join('. ');
    return `${size} ${pw}.`;
  };
  return (
    <PlotCard
      title={{ en: 'C04, the transition tests: size and power on known truth', es: 'C04, las pruebas de transición: tamaño y potencia con verdad conocida' }}
      lane={REPLAY}
      provenance={provenance}
      note={{
        en: `Each rate is the share of repetitions in which the test rejects, with its Monte Carlo SE; the setting is the family's ladder (the Markov family has none: its rates are sizes). Paths drawn from ${GENERATOR_TEXT.en}.${FAMILY_SOURCE.en}`,
        es: `Cada tasa es la fracción de repeticiones en que la prueba rechaza, con su EE de Monte Carlo; el ajuste es la escala de la familia (la familia de Markov no tiene: sus tasas son tamaños). Trayectorias generadas desde ${GENERATOR_TEXT.es}.${FAMILY_SOURCE.es}`,
      }}
    >
      <Verdict compact title={{ en: 'What the simulations support', es: 'Lo que respaldan las simulaciones' }} tone={failing.length ? 'warn' : 'accent'} verdict={{ en: verdict('en'), es: verdict('es') }} />
      <div className="ct-scroll">
        <table className="caos-table ct-wrap-head" data-table="bench-tests">
          <thead>
            <tr>
              <th className="caos-col-text">{t('Family', 'Familia')}</th>
              <th className="caos-col-text">{t('Test', 'Prueba')}</th>
              <th className="caos-col-text">{t('Setting', 'Ajuste')}</th>
              <th>{t('Rate at 5% (SE)', 'Tasa al 5% (EE)')}</th>
              <th>{t('Rate at 1% (SE)', 'Tasa al 1% (EE)')}</th>
              <th>{t('Wilson 95%, 5%', 'Wilson 95%, 5%')}</th>
              <th>{t('Repetitions', 'Repeticiones')}</th>
            </tr>
          </thead>
          <tbody>
            {withSims.flatMap((f) =>
              f.outputs.simulations.map((s) => (
                <tr key={`${f.variant_id}-${s.key}`} data-variant={f.variant_id} data-sim={s.key} data-holds={f === markov ? (holds(s) ? 'yes' : 'no') : undefined}>
                  <td className="caos-col-text">{pick(shortOf(manifest, f.variant_id), lang)}</td>
                  <td className="caos-col-text">{pick(testName(s.test_id), lang)}</td>
                  <td className="caos-col-text">{rungText(f, s, lang)}</td>
                  <td>{rateCell(s, AT5, lang)}</td>
                  <td>{rateCell(s, AT1, lang)}</td>
                  <td>{s.rates[AT5] ? `${share(lang, s.rates[AT5].wilson_low)} ${lang === 'es' ? 'a' : 'to'} ${share(lang, s.rates[AT5].wilson_high)}` : '-'}</td>
                  <td>{formatNumber(s.n_rep, lang)}</td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>
    </PlotCard>
  );
}

const METHOD_LABEL: Record<'wald' | 'agresti_coull' | 'jeffreys' | 'bootstrap', BiText> = {
  wald: 'Wald',
  agresti_coull: 'Agresti-Coull',
  jeffreys: 'Jeffreys',
  bootstrap: { en: 'Bootstrap (duration PD)', es: 'Bootstrap (PD de duración)' },
};
const METHOD_COLOR = { wald: '--color-bad', agresti_coull: '--color-warn', jeffreys: '--color-accent', bootstrap: '--color-magenta' } as const;

/** The Markov family's Monte Carlo coverage of each interval by grade, against the nominal level. */
export function coverageChart(markov: FamilyVariant): { x: number[]; series: ChartSeries[]; level: number } | null {
  const rung = (markov.outputs.rungs as C04MarkovRung[])[0];
  if (!rung) return null;
  const x = GRADES.map((_, i) => i + 1);
  const lines = nonEmpty(
    (['wald', 'agresti_coull', 'jeffreys', 'bootstrap'] as const).map((k) => ({
      label: METHOD_LABEL[k],
      values: (rung.coverage[k] ?? []).map((r) => (finite(r?.rate) ? r.rate : null)),
      color: METHOD_COLOR[k],
      width: 2,
      mode: 'line' as const,
    })),
  );
  if (!lines.length) return null;
  return {
    x,
    level: rung.level,
    series: [...lines, { label: { en: `Nominal ${Math.round(rung.level * 100)}%`, es: `Nominal ${Math.round(rung.level * 100)}%` }, values: x.map(() => rung.level), color: '--color-fg-subtle', width: 1.2, dash: [6, 4] }],
  };
}

function CoverageCard({ markov, thin, provenance }: { markov: FamilyVariant | null; thin: FamilyVariant | null; provenance: Provenance }) {
  const lang = useShellLang();
  const t = useT();
  const rung = markov ? (markov.outputs.rungs as C04MarkovRung[])[0] : undefined;
  const chart = markov ? coverageChart(markov) : null;
  const thinRungs = thin ? (thin.outputs.rungs as C04ThinRung[]) : [];
  if (!chart && !thinRungs.length) return null;
  const rates = (k: 'wald' | 'agresti_coull' | 'jeffreys' | 'bootstrap') => (rung?.coverage[k] ?? []).map((r) => r.rate).filter(finite);
  const first = thinRungs[0];
  const last = thinRungs[thinRungs.length - 1];
  const mc = (l: Lang) =>
    rung
      ? l === 'es'
        ? `Monte Carlo (familia de Markov, ${formatNumber(markov?.outputs.design.reps ?? null, 'es')} repeticiones, nivel ${share('es', rung.level)}): Wald cubre la PD anual verdadera en ${share('es', rung.coverage.wald[0]?.rate)} de las repeticiones en ${GRADES[0]} y ${share('es', rung.coverage.wald[CCC]?.rate)} en ${GRADES[CCC]}; Agresti-Coull ${range('es', rates('agresti_coull'), share)} entre los grados; Jeffreys ${range('es', rates('jeffreys'), share)}; el bootstrap de la PD de duración ${range('es', rates('bootstrap'), share)} (${formatNumber(rung.bootstrap.repetitions, 'es')} repeticiones).`
        : `Monte Carlo (Markov family, ${formatNumber(markov?.outputs.design.reps ?? null, 'en')} repetitions, level ${share('en', rung.level)}): Wald covers the true one-year PD in ${share('en', rung.coverage.wald[0]?.rate)} of the repetitions at ${GRADES[0]} and ${share('en', rung.coverage.wald[CCC]?.rate)} at ${GRADES[CCC]}; Agresti-Coull ${range('en', rates('agresti_coull'), share)} across the grades; Jeffreys ${range('en', rates('jeffreys'), share)}; the bootstrap of the duration PD ${range('en', rates('bootstrap'), share)} (${formatNumber(rung.bootstrap.repetitions, 'en')} repetitions).`
      : '';
  const exact = (l: Lang) =>
    first && last
      ? l === 'es'
        ? ` Exacta (familia delgada): con ${formatNumber(first.value, 'es')} deudores por grado, Wald cubre ${GRADES[0]} con probabilidad ${exactShare('es', first.coverage.wald[0])} y Jeffreys ${exactShare('es', first.coverage.jeffreys[0])}; con ${formatNumber(last.value, 'es')}, ${exactShare('es', last.coverage.wald[0])} y ${exactShare('es', last.coverage.jeffreys[0])}.`
        : ` Exact (thin family): with ${formatNumber(first.value, 'en')} obligors a grade, Wald covers ${GRADES[0]} with probability ${exactShare('en', first.coverage.wald[0])} and Jeffreys ${exactShare('en', first.coverage.jeffreys[0])}; with ${formatNumber(last.value, 'en')}, ${exactShare('en', last.coverage.wald[0])} and ${exactShare('en', last.coverage.jeffreys[0])}.`
      : '';
  return (
    <PlotCard
      title={{ en: 'C04, the intervals for a PD by grade: coverage on known truth', es: 'C04, los intervalos para una PD por grado: cobertura con verdad conocida' }}
      lane={REPLAY}
      provenance={provenance}
      note={{
        en: `The share of repetitions in which each 95% interval covers the true one-year PD, by grade (Markov family, the chart), and the exact coverage by enumeration for cohorts of each size (thin family, the table). Paths drawn from ${GENERATOR_TEXT.en}.${FAMILY_SOURCE.en}`,
        es: `La fracción de repeticiones en que cada intervalo al 95% cubre la PD anual verdadera, por grado (familia de Markov, el gráfico), y la cobertura exacta por enumeración para cohortes de cada tamaño (familia delgada, la tabla). Trayectorias generadas desde ${GENERATOR_TEXT.es}.${FAMILY_SOURCE.es}`,
      }}
    >
      <Verdict compact title={{ en: 'What the coverage supports', es: 'Lo que respalda la cobertura' }} tone="accent" verdict={{ en: `${mc('en')}${exact('en')}`, es: `${mc('es')}${exact('es')}` }} />
      {chart && (
        <UPlotChart
          height={CHART_HEIGHT}
          x={{ values: chart.x, label: GRADE_AXIS, format: { decimals: 0 } }}
          y={{ label: { en: 'Coverage of the true PD', es: 'Cobertura de la PD verdadera' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
          series={chart.series}
        />
      )}
      {thinRungs.length > 0 && (
        <div className="ct-scroll">
          <table className="caos-table" data-table="bench-coverage-thin">
            <thead>
              <tr>
                <th>{t('Obligors a grade', 'Deudores por grado')}</th>
                <th className="caos-col-text">{t('Interval', 'Intervalo')}</th>
                {GRADES.map((g) => (
                  <th key={g}>{g}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {thinRungs.flatMap((r) =>
                (['wald', 'agresti_coull', 'jeffreys'] as const).map((k) => (
                  <tr key={`${r.value}-${k}`} data-obligors={r.value} data-interval={k}>
                    <td>{formatNumber(r.value, lang)}</td>
                    <td className="caos-col-text">{pick(METHOD_LABEL[k], lang)}</td>
                    {GRADES.map((g, i) => (
                      <td key={g}>{share(lang, r.coverage[k][i])}</td>
                    ))}
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      )}
    </PlotCard>
  );
}

function PapersCard({ published }: { published: PublishedVariant }) {
  const lang = useShellLang();
  const t = useT();
  const o = published.outputs;
  const agreements = paperAgreements(published);
  const yes = (b: boolean) => (b ? t('agrees', 'concuerda') : t('differs', 'difiere'));
  const STATES = [...GRADES, 'D'];
  // Israel et al. print six decimals (0.116900): the printed and the recomputed values at the same six decimals
  const f6 = (x: number) => formatNumber(x, lang, { decimals: 6 });
  return (
    <PlotCard
      title={{ en: 'C04, the published answers recomputed', es: 'C04, las respuestas publicadas recalculadas' }}
      lane={REPLAY}
      provenance={provenanceOf(published.provenance.truth_status)}
      note={{
        en: "Each paper's printed values beside their recomputation from the paper's own inputs; the papers' agency matrices are read from the data root and never enter an artifact.",
        es: 'Los valores impresos de cada artículo junto a su recálculo desde los insumos del propio artículo; las matrices de agencias de los artículos se leen desde la raíz de datos y nunca entran a un artefacto.',
      }}
    >
      <Verdict
        compact
        title={{ en: 'What the recomputation supports', es: 'Lo que respalda el recálculo' }}
        tone={agreements.every((p) => p.agree === p.total) ? 'good' : 'accent'}
        verdict={{
          en: agreements.map((p) => `${pick(p.name, 'en')}: ${p.agree} of ${p.total} at the printed digits (${pick(p.detail, 'en')})`).join('. '),
          es: agreements.map((p) => `${pick(p.name, 'es')}: ${p.agree} de ${p.total} a los dígitos impresos (${pick(p.detail, 'es')})`).join('. '),
        }}
      />
      <div className="ct-scroll">
        <table className="caos-table" data-table="bench-irw">
          <thead>
            <tr>
              <th className="caos-col-text">{t('Matrix', 'Matriz')}</th>
              <th className="caos-col-text">{t('Generator', 'Generador')}</th>
              <th>{t('Printed L1', 'L1 impresa')}</th>
              <th>{t('Recomputed', 'Recalculada')}</th>
              <th>{t('At six decimals', 'A seis decimales')}</th>
            </tr>
          </thead>
          <tbody>
            {o.irw.rows.map((r) => (
              <tr key={`${r.matrix}-${r.method}`} data-agrees={r.agrees ? 'yes' : 'no'}>
                <td className="caos-col-text">{r.matrix}</td>
                <td className="caos-col-text">{pick(irwMethod(r.method), lang)}</td>
                <td>{f6(r.printed)}</td>
                <td>{f6(r.recomputed)}</td>
                <td>{yes(r.agrees)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="ct-scroll">
        <table className="caos-table" data-table="bench-sr190">
          <thead>
            <tr>
              <th>{t('Correlation', 'Correlación')}</th>
              <th className="caos-col-text">{t('Interval', 'Intervalo')}</th>
              <th>{t('Printed lower, upper, length', 'Impreso inferior, superior, largo')}</th>
              <th>{t('Recomputed', 'Recalculado')}</th>
              <th>{t('Printed digits', 'Dígitos impresos')}</th>
            </tr>
          </thead>
          <tbody>
            {o.sr190.rows.map((r) => (
              <tr key={`${r.rho}-${r.interval}`} data-agrees={r.agrees ? 'yes' : 'no'}>
                <td>{share(lang, r.rho)}</td>
                <td className="caos-col-text">{r.interval === 'agresti_coull' ? 'Agresti-Coull' : r.interval === 'wald' ? 'Wald' : r.interval}</td>
                <td>{r.printed.map((x) => f6(x)).join('; ')}</td>
                <td>{r.recomputed.map((x) => f6(x)).join('; ')}</td>
                <td>{yes(r.agrees)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="ct-scroll">
        <table className="caos-table" data-table="bench-engelmann">
          <thead>
            <tr>
              <th className="caos-col-text">{t('Value', 'Valor')}</th>
              <th>{t('Printed', 'Impreso')}</th>
              <th>{t('Recomputed', 'Recalculado')}</th>
              <th className="caos-col-text">{t('Check', 'Verificación')}</th>
            </tr>
          </thead>
          <tbody>
            {o.engelmann.w_ttc.printed.map((x, i) => (
              <tr key={`w-${i}`}>
                <td className="caos-col-text">{`W_ttc ${STATES[i] ?? i + 1}`}</td>
                <td>{formatNumber(x, lang, { decimals: o.engelmann.w_ttc.decimals[i] })}</td>
                <td>{f6(o.engelmann.w_ttc.recomputed[i])}</td>
                <td className="caos-col-text">{yes(atPrintedDigits(x, o.engelmann.w_ttc.recomputed[i], o.engelmann.w_ttc.decimals[i]))}</td>
              </tr>
            ))}
            <tr>
              <td className="caos-col-text">{t('TTC PD', 'PD TTC')}</td>
              <td>{pctText(lang, o.engelmann.ttc_pd.printed, 4)}</td>
              <td>{pctText(lang, o.engelmann.ttc_pd.recomputed, 6)}</td>
              <td className="caos-col-text">{yes(atPrintedDigits(o.engelmann.ttc_pd.printed, o.engelmann.ttc_pd.recomputed, o.engelmann.ttc_pd.decimals))}</td>
            </tr>
            {o.engelmann.portfolios.flatMap((q) => [
              <tr key={`${q.name}-pd0`}>
                <td className="caos-col-text">{`${q.name}, ${t('PD of the first year', 'PD del primer año')}`}</td>
                <td>{pctText(lang, q.pd0.printed, 4)}</td>
                <td>{pctText(lang, q.pd0.recomputed, 6)}</td>
                <td className="caos-col-text">
                  {q.pd0.check === 'printed digits'
                    ? yes(atPrintedDigits(q.pd0.printed, q.pd0.recomputed, q.pd0.decimals))
                    : t(
                        `within the rounding of its printed entries${q.pd0.note ? ` (${q.pd0.note.en})` : ''}`,
                        `dentro del redondeo de sus entradas impresas${q.pd0.note ? ` (${q.pd0.note.es})` : ''}`,
                      )}
                </td>
              </tr>,
              ...(q.extreme
                ? [
                    <tr key={`${q.name}-extreme`}>
                      <td className="caos-col-text">{`${q.name}, ${q.extreme.kind === 'min' ? t('lowest projected PD', 'menor PD proyectada') : t('highest projected PD', 'mayor PD proyectada')}`}</td>
                      <td>{pctText(lang, q.extreme.printed, 4)}</td>
                      <td>{pctText(lang, q.extreme.recomputed, 6)}</td>
                      <td className="caos-col-text">{yes(atPrintedDigits(q.extreme.printed, q.extreme.recomputed, q.extreme.decimals))}</td>
                    </tr>,
                  ]
                : []),
            ])}
          </tbody>
        </table>
      </div>
    </PlotCard>
  );
}

export function C04Benchmark({ manifest }: { manifest: CaseManifest }) {
  const t = useT();
  const all = useC04Variants(manifest);
  if (all.state === 'loading') return <p className="caos-pending" data-state="loading">{t('Loading the comparisons', 'Cargando las comparaciones')}</p>;
  if (all.state === 'error') return <LoadError error={all.error} />;
  const { agencies, families, published } = kindsOf(all.data);
  const real = provenanceOf(agencies[0]?.provenance.truth_status ?? 'real-outcomes');
  const synthetic = provenanceOf(families[0]?.provenance.truth_status ?? 'synthetic-known-truth');
  const markov = families.find((f) => f.outputs.family === 'markov') ?? null;
  const thin = families.find((f) => f.outputs.family === 'thin') ?? null;
  return (
    <div data-state="ready">
      {agencies.length > 0 && (
        <>
          <DefinitionsCard agencies={agencies} manifest={manifest} provenance={real} />
          <GeneratorsCard agencies={agencies} manifest={manifest} provenance={real} />
          <LifetimeCard agencies={agencies} manifest={manifest} provenance={real} />
        </>
      )}
      {markov && <EstimatorsCard markov={markov} manifest={manifest} provenance={synthetic} />}
      <TestsCard families={families} manifest={manifest} provenance={synthetic} />
      <CoverageCard markov={markov} thin={thin} provenance={synthetic} />
      {published && <PapersCard published={published} />}
    </div>
  );
}
