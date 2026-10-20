// The coverage of the 22 cases and, case by case, every variant read from its committed artifacts. No number on this
// page is typed in: whether a case is built comes from the index, every metric from the variant artifacts (T13).
import { DocPage, DocSection, Equation, Figure, PlotCard, TabGroups, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo, type ReactNode } from 'react';
import { loadAllManifests, loadAllVariants, useArtifact } from '../api/artifacts';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { COMMITTED, LIGHT_TEXT, relight } from '../lib/policy';
import { CASES, CATEGORY_TITLES } from '../content/coverage';
import { P, T, useT } from '../content/bi';
import { ProtocolFigure } from './DocFigures';
import { CHAMPION, test, value } from '../workbench/model';
import { C04Experiments } from './C04Sections';
import { C05ExperimentsSection } from './C05Sections';
import { C22ExperimentsSection } from './C22Sections';
import { NoTranslateRefs } from './NoTranslateRefs';
import { U6ExperimentsSection, U6_CASES } from './U6Sections';
import { W2ExperimentsSection, W2_CASES } from './Wave2Sections';
import { B3ExperimentsSection, B3_CASES, ImpactSection } from './Batch3Sections';

/** The C01 scorecard table: it reads the fields of the C01 documents (`outputs.n`, `outputs.defaults`, the scorecard test rows), so it is for C01 only. */
function CaseVariants({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const all = useArtifact<VariantArtifact[]>((s) => loadAllVariants(manifest, s), [manifest.case_id]);
  const rows = useMemo(() => {
    if (all.state !== 'ready') return null;
    return all.data.map((v) => {
      const ids = v.model.map((m) => m.id);
      const best = ids
        .filter((id) => id !== 'P0-constant')
        .map((id) => ({ id, auc: value(test(v, 'disc.auc', id)) ?? 0 }))
        .sort((a, b) => b.auc - a.auc)[0];
      const jef = test(v, 'pd.jeffreys', CHAMPION);
      const psi = test(v, 'stability.psi', CHAMPION);
      return { v, best, jef, psi, auc: value(test(v, 'disc.auc', CHAMPION)) };
    });
  }, [all]);
  if (!rows) return <p className="caos-pending" data-state="loading">{t('Loading the variants', 'Cargando las variantes')}</p>;
  const entries = manifest.artifacts.filter((a) => a.role === 'variant');
  const x = rows.map((_, i) => i + 1);
  return (
    <>
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th>#</th>
            <th className="caos-col-text">{t('Variant', 'Variante')}</th>
            <th>{t('Records', 'Registros')}</th>
            <th>{t('Default rate', 'Tasa de incumplimiento')}</th>
            <th>{t('AUC, scorecard', 'AUC, scorecard')}</th>
            <th>{t('Best rung by AUC', 'Mejor peldaño por AUC')}</th>
            <th>{t('Jeffreys, scorecard', 'Jeffreys, scorecard')}</th>
            <th>{t('PSI, scorecard', 'PSI, scorecard')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.v.variant_id}>
              <td>{i + 1}</td>
              <td className="caos-col-text">{pick(entries[i].title, lang)}</td>
              <td>{formatNumber(r.v.outputs.n, lang)}</td>
              <td>{formatNumber(r.v.outputs.defaults / r.v.outputs.n, lang, { percent: true, decimals: 1 })}</td>
              <td>{formatNumber(r.auc, lang, { decimals: 4 })}</td>
              <td>
                {r.best.id} ({formatNumber(r.best.auc, lang, { decimals: 4 })})
              </td>
              <td>{r.jef ? `p ${formatNumber(r.jef.p_value, lang, { digits: 3 })}, ${pick(LIGHT_TEXT[relight(r.jef, COMMITTED)], lang)}` : '-'}</td>
              <td>{r.psi ? `${formatNumber(value(r.psi), lang, { decimals: 4 })}, ${pick(LIGHT_TEXT[relight(r.psi, COMMITTED)], lang)}` : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <PlotCard title={{ en: 'Discrimination of the scorecard and of the best rung, variant by variant', es: 'Discriminación de la scorecard y del mejor peldaño, variante por variante' }} lane="replay" provenance="real">
        <UPlotChart
          height={260}
          x={{ values: x, label: { en: 'Variant (the number in the table)', es: 'Variante (el número de la tabla)' }, format: { decimals: 0 } }}
          y={{ label: { en: 'AUC', es: 'AUC' }, format: { decimals: 3 } }}
          series={[
            { label: { en: 'Scorecard (P1)', es: 'Scorecard (P1)' }, values: rows.map((r) => r.auc), color: '--color-accent', mode: 'points' },
            { label: { en: 'Best rung', es: 'Mejor peldaño' }, values: rows.map((r) => r.best.auc), color: '--color-magenta', mode: 'points' },
          ]}
        />
      </PlotCard>
    </>
  );
}

/** What a case declares and what its bake wrote, read from its manifest: the second paragraph of its question. */
function CaseFacts({ m }: { m: CaseManifest }) {
  const lang = useShellLang();
  const variants = m.artifacts.filter((a) => a.role === 'variant');
  const titles = variants.map((a) => pick(a.short_title, lang)).join(', ');
  const expected = Object.keys(m.expect ?? {}).length;
  const engine = Object.entries(m.engine ?? {})
    .map(([k, v]) => `${k} ${v}`)
    .join(', ');
  return (
    <P
      en={`The case was baked with seed ${m.seed} by ${engine || 'the pipeline'} and holds ${variants.length} variants (${titles}). ${m.sources.length ? `It reads ${m.sources.join(', ')}, and the` : 'It reads no outside file (its data are generated), and the'} ${expected} expected ranges it declared before the bake all held when it ran. Every number below is read from those committed artifacts when the page opens, and none is typed into this page.`}
      es={`El caso se generó con la semilla ${m.seed} por ${engine || 'el pipeline'} y contiene ${variants.length} variantes (${titles}). ${m.sources.length ? `Lee ${m.sources.join(', ')}, y los` : 'No lee ningún archivo externo (sus datos se generan), y los'} ${expected} rangos esperados que declaró antes de la generación se cumplieron todos cuando corrió. Cada número de abajo se lee de esos artefactos comprometidos cuando se abre la página, y ninguno está escrito en esta página.`}
    />
  );
}

/** Which section reads a case on this page: its own, or the generic table of its impact items; the C01 scorecard table is for C01 only. */
export type SectionKind = 'scorecard' | 'c04' | 'c05' | 'c22' | 'u6' | 'wave2' | 'batch3' | 'generic';
export function sectionKindOf(caseId: string): SectionKind {
  if (caseId === 'C04') return 'c04';
  if (caseId === 'C05') return 'c05';
  if (caseId === 'C22') return 'c22';
  if (U6_CASES.has(caseId)) return 'u6';
  if (W2_CASES.has(caseId)) return 'wave2';
  if (B3_CASES.has(caseId)) return 'batch3';
  return caseId === 'C01' ? 'scorecard' : 'generic';
}

function CaseTopic({ m }: { m: CaseManifest }) {
  const kind = sectionKindOf(m.case_id);
  return (
    <DocSection
      area="question"
      title={{ en: `${m.case_id}: ${m.title.en}`, es: `${m.case_id}: ${m.title.es}` }}
      noRefsReason={{ en: 'Read from the committed artifacts; the methods are cited in Methodology.', es: 'Leído de los artefactos comprometidos; los métodos se citan en Metodología.' }}
    >
      <P en={m.question.en} es={m.question.es} />
      <CaseFacts m={m} />
      {kind !== 'scorecard' && kind !== 'c04' && kind !== 'c05' && kind !== 'c22' ? (
        <P
          en="Each variant of this case is the same question asked of different data, and the table below reads one headline row per variant from its artifact, in the measures this case declares; a number the artifact leaves out is said to be not available, with its reason, in the App."
          es="Cada variante de este caso es la misma pregunta hecha a datos distintos, y la tabla de abajo lee una fila de resultados por variante desde su artefacto, en las medidas que declara este caso; un número que el artefacto omite se dice no disponible, con su razón, en la App."
        />
      ) : (
      <P
        en="Each variant of a case is the same question asked of different data, and the tables and charts below are read from its artifacts: the number of records, the default rate, the discrimination of the champion and of the best challenger, and the policy light of its calibration and stability tests under the committed thresholds. A variant that perturbs the data has a known effect, and a sound test must detect it or must not, as the case declares."
        es="Cada variante de un caso es la misma pregunta hecha a datos distintos, y las tablas y gráficos de abajo se leen de sus artefactos: el número de registros, la tasa de incumplimiento, la discriminación del campeón y del mejor retador, y la luz de política de sus pruebas de calibración y estabilidad bajo los umbrales comprometidos. Una variante que perturba los datos tiene un efecto conocido, y una prueba sana debe detectarlo o no, según declara el caso."
      />
      )}
      {kind === 'c04' ? <C04Experiments manifest={m} /> : kind === 'c05' ? <C05ExperimentsSection manifest={m} /> : kind === 'c22' ? <C22ExperimentsSection manifest={m} /> : kind === 'u6' ? <U6ExperimentsSection manifest={m} /> : kind === 'wave2' ? <W2ExperimentsSection manifest={m} /> : kind === 'batch3' ? <B3ExperimentsSection manifest={m} /> : kind === 'scorecard' ? <CaseVariants manifest={m} /> : <ImpactSection manifest={m} />}
    </DocSection>
  );
}

function Coverage({ built }: { built: Set<string> | null }) {
  const lang = useShellLang();
  const t = useT();
  return (
    <DocSection area="datasets" title={{ en: 'Coverage and datasets', es: 'Cobertura y conjuntos de datos' }} noRefsReason={{ en: 'The plan of this product.', es: 'El plan de este producto.' }}>
      <P
        en="Twenty-two cases in eleven categories, each with its data and licence class, the status of its truth, and the unit of the plan that builds it. A case is marked built only when its manifest exists; every other one is the plan, stated as such, and the site shows it as not available yet in every group, with the reason, never as an empty chart."
        es="Veintidós casos en once categorías, cada uno con sus datos y su clase de licencia, el estado de su verdad y la unidad del plan que lo construye. Un caso se marca construido solo cuando existe su manifiesto; cada uno de los demás es el plan, declarado como tal, y el sitio lo muestra como aún no disponible en cada grupo, con la razón, nunca como un gráfico vacío."
      />
      <table className="caos-table" data-state={built ? 'ready' : 'loading'}>
        <thead>
          <tr>
            <th>{t('Case', 'Caso')}</th>
            <th>{t('Category', 'Categoría')}</th>
            <th className="caos-col-text">{t('Question', 'Pregunta')}</th>
            <th className="caos-col-text">{t('Data', 'Datos')}</th>
            <th>{t('Truth', 'Verdad')}</th>
            <th>{t('Status', 'Estado')}</th>
          </tr>
        </thead>
        <tbody>
          {CASES.map((c) => (
            <tr key={c.id} data-built={built?.has(c.id) ? 'true' : 'false'}>
              <td>{c.id}</td>
              <td>{pick(CATEGORY_TITLES[c.category], lang)}</td>
              <td className="caos-col-text">{pick(c.title, lang)}</td>
              <td className="caos-col-text">{pick(c.data, lang)}</td>
              <td>{pick(c.truth, lang)}</td>
              <td>{built?.has(c.id) ? t('built', 'construido') : `${t('planned', 'planificado')} (${c.unit})`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </DocSection>
  );
}

function Protocol() {
  const t = useT();
  return (
    <DocSection area="protocol" title={{ en: 'The held-out protocol', es: 'El protocolo con muestra reservada' }} noRefsReason={{ en: 'Describes this product\'s own protocol.', es: 'Describe el protocolo propio de este producto.' }}>
      <P
        en="Every experiment follows one protocol. A stratified holdout of 30% is locked before anything is fitted; of the rest, 20% is kept as a calibration slice; the training slice is where every binning, weight of evidence, rule, hyperparameter and fit is learned, with repeated stratified five-fold cross-validation inside it for every choice a rung makes. The tests then run on the holdout, once, and their results are what the pages show."
        es="Todo experimento sigue un protocolo. Una muestra reservada estratificada de 30% se bloquea antes de ajustar nada; del resto, 20% se guarda como tajada de calibración; la tajada de entrenamiento es donde se aprende cada tramado, peso de evidencia, regla, hiperparámetro y ajuste, con validación cruzada estratificada repetida de cinco pliegues dentro de ella para cada elección de un peldaño. Las pruebas corren luego sobre la muestra reservada, una vez, y sus resultados son lo que muestran las páginas."
      />
      <Figure caption={t('The leakage-safe protocol: what each part of the data may be used for, and the forbidden path that uses the locked holdout to choose or to fit.', 'El protocolo sin fugas: para qué puede usarse cada parte de los datos, y el camino prohibido que usa la muestra reservada bloqueada para elegir o ajustar.')}>
        <ProtocolFigure />
      </Figure>
    </DocSection>
  );
}

function Metrics() {
  return (
    <DocSection area="metrics" title={{ en: 'The metrics', es: 'Las métricas' }} refs={['ecb2019', 'yurdakul2020']}>
      <P
        en="The tables and charts of the case topics read three families of metrics from the artifacts: the discrimination of a score, the stability of its distribution, and the level of its PDs. Each is defined here by the exact equation the engine runs, and each result is shown with the policy light that the reader's thresholds give it."
        es="Las tablas y gráficos de los temas de cada caso leen de los artefactos tres familias de métricas: la discriminación de un puntaje, la estabilidad de su distribución y el nivel de sus PD. Cada una se define aquí con la ecuación exacta que corre el motor, y cada resultado se muestra con la luz de política que le dan los umbrales del lector."
      />
      <Equation
        tex="\mathrm{AUC} = \frac{1}{|A|\,|B|}\sum_{a\in A}\sum_{b\in B} u_{a,b}"
        caption={<T en={<>The area under the ROC curve: A the defaulters, B the non-defaulters, u_ab = 1 when a is ranked riskier than b, 1/2 on a tie and 0 otherwise (ECB 2019).</>} es={<>El área bajo la curva ROC: A los incumplidores, B los no incumplidores, u_ab = 1 cuando a queda como más riesgoso que b, 1/2 en un empate y 0 en otro caso (BCE 2019).</>} />}
      />
      <Equation
        tex="\mathrm{PSI} = \sum_{i=1}^{B}(a_i - e_i)\ln\frac{a_i}{e_i}"
        caption={<T en={<>The population stability index of a score: B the number of bins, a_i the share of the current population in bin i and e_i the share expected from development (Yurdakul and Naranjo 2020).</>} es={<>El índice de estabilidad poblacional de un puntaje: B el número de tramos, a_i la fracción de la población actual en el tramo i y e_i la fracción esperada desde el desarrollo (Yurdakul y Naranjo 2020).</>} />}
      />
      <Equation
        tex="p = F_{\mathrm{Beta}\left(D+\frac12,\; N-D+\frac12\right)}(\mathrm{PD})"
        caption={<T en={<>The Jeffreys p-value of the level of a PD: D the defaults among N obligors, F the distribution function of the Beta posterior with the Jeffreys prior, evaluated at the PD applied (ECB 2019).</>} es={<>El valor p de Jeffreys del nivel de una PD: D los incumplimientos entre N deudores, F la función de distribución del posterior Beta con el prior de Jeffreys, evaluada en la PD aplicada (BCE 2019).</>} />}
      />
    </DocSection>
  );
}

/** The question families the case tabs are grouped by (ADR-0071 rule 5: at most six peer tabs, then group by the question), keyed by the category of the coverage registry; a category without a family keeps its own title. */
const FAMILY: Record<string, { id: string; label: BiText }> = {
  'credit-scoring': { id: 'pd', label: { en: 'Credit scoring and PD', es: 'Scoring de crédito y PD' } },
  'ratings-calibration': { id: 'pd', label: { en: 'Credit scoring and PD', es: 'Scoring de crédito y PD' } },
  provisions: { id: 'credit-losses', label: { en: 'Credit losses: provisions, severity and exposure', es: 'Pérdidas de crédito: provisiones, severidad y exposición' } },
  'lgd-ead': { id: 'credit-losses', label: { en: 'Credit losses: provisions, severity and exposure', es: 'Pérdidas de crédito: provisiones, severidad y exposición' } },
  validator: { id: 'validator', label: { en: 'Validating the validator', es: 'Validar al validador' } },
  'portfolio-capital': { id: 'capital', label: { en: 'Capital, aggregation and stress', es: 'Capital, agregación y estrés' } },
  operational: { id: 'capital', label: { en: 'Capital, aggregation and stress', es: 'Capital, agregación y estrés' } },
  'capital-stress': { id: 'capital', label: { en: 'Capital, aggregation and stress', es: 'Capital, agregación y estrés' } },
  'ml-ai-risk': { id: 'ml-ai-risk', label: { en: 'ML and AI risk', es: 'Riesgo de ML e IA' } },
  'market-ccr': { id: 'market-balance', label: { en: 'Market and balance-sheet risk', es: 'Riesgo de mercado y de balance' } },
  'balance-sheet': { id: 'market-balance', label: { en: 'Market and balance-sheet risk', es: 'Riesgo de mercado y de balance' } },
};

/** The case tabs grouped by the question family of their category; the order of the families is the order of the first case. */
export function groupCases(tabs: Array<{ id: string; label: string; content: ReactNode }>): Array<{ id: string; label: BiText; tabs: Array<{ id: string; label: string; content: ReactNode }> }> {
  const groups: Array<{ id: string; label: BiText; tabs: Array<{ id: string; label: string; content: ReactNode }> }> = [];
  for (const tab of tabs) {
    const category = CASES.find((c) => c.id.toLowerCase() === tab.id)?.category ?? 'other';
    const fam = FAMILY[category] ?? { id: category, label: CATEGORY_TITLES[category] ?? { en: 'Other cases', es: 'Otros casos' } };
    const g = groups.find((x) => x.id === fam.id);
    if (g) g.tabs.push(tab);
    else groups.push({ id: fam.id, label: fam.label, tabs: [tab] });
  }
  return groups;
}

export function Experiments() {
  const lang = useShellLang();
  const t = useT();
  const all = useArtifact((s) => loadAllManifests(s), []);
  const built = all.state === 'ready' ? new Set(all.data.manifests.map((m) => m.case_id)) : null;
  const caseTabs =
    all.state === 'ready'
      ? all.data.manifests.map((m) => ({ id: m.case_id.toLowerCase(), label: m.case_id, content: <CaseTopic m={m} /> }))
      : [
          {
            id: 'cases',
            label: t('Cases', 'Casos'),
            content:
              all.state === 'error' ? (
                <p className="caos-pending" data-state="unavailable">
                  {t(`The cases are not available yet: their manifests could not be read (${all.error}).`, `Los casos aún no están disponibles: no se pudieron leer sus manifiestos (${all.error}).`)}
                </p>
              ) : (
                <p className="caos-pending" data-state="loading">
                  {t('Loading the case manifests', 'Cargando los manifiestos de los casos')}
                </p>
              ),
          },
        ];
  return (
    <DocPage
      wide
      title={{ en: 'Experiments', es: 'Experimentos' }}
      lede={t(
        'The coverage of the 22 cases, the held-out protocol every experiment follows, the metrics it reads, and every built case variant by variant, all read from the committed artifacts: no number on this page is typed in, and a case that is planned says so.',
        'La cobertura de los 22 casos, el protocolo con muestra reservada que sigue todo experimento, las métricas que lee, y cada caso construido variante por variante, todo leído de los artefactos comprometidos: ningún número de esta página está escrito a mano, y un caso planificado lo dice.',
      )}
    >
      <NoTranslateRefs />
      <TabGroups
        ariaLabel={lang === 'es' ? 'Partes de los experimentos' : 'Parts of the experiments'}
        groups={[
          {
            id: 'design',
            label: t('How are the experiments designed?', '¿Cómo se diseñan los experimentos?'),
            tabs: [
              { id: 'coverage', label: t('Coverage', 'Cobertura'), content: <Coverage built={built} /> },
              { id: 'protocol', label: t('Protocol', 'Protocolo'), content: <Protocol /> },
              { id: 'metrics', label: t('Metrics', 'Métricas'), content: <Metrics /> },
            ],
          },
          ...(all.state === 'ready'
            ? groupCases(caseTabs).map((g) => ({ id: g.id, label: pick(g.label, lang), tabs: g.tabs }))
            : [{ id: 'cases', label: t('What did each built case find?', '¿Qué encontró cada caso construido?'), tabs: caseTabs }]),
        ]}
      />
    </DocPage>
  );
}
