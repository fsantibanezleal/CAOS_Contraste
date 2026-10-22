// The Introduction opens on the executive view (ADR-0017 section 2.1; CAOS_MANAGE conventions/problem-context-first.md):
// the shell's ExecutiveView rendering content/executive.json, the industry problem of defending internal risk models
// before supervisors (the pain, the context, the current situation, the trends, the proposal), general and never tied to a
// client, every figure linked to its source in the file. It then turns technical: the previous page, its subsections as
// sub-tabs (problem, principles, math with its glossary, pipeline, honesty, how to read the App, the six pages).
import { Callout, Cite, DocPage, DocSection, Equation, ExecutiveView, Figure, Glossary, SubTabs, Tabs } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { OverviewFigure } from '../architecture/figures';
import { L, P, T, useT } from '../content/bi';
import executive from '../../../content/executive.json';

/** One list item written in both languages. */
const Li = ({ en, es }: { en: ReactNode; es: ReactNode }) => (
  <li>
    <T en={en} es={es} />
  </li>
);

/** The technical view's subsections, each a sub-tab (a page with subsections is never one long scroll). */
function Technical() {
  const t = useT();
  const tabs = [
    {
      id: 'problem',
      label: t('What Contraste is', 'Qué es Contraste'),
      content: (
      <DocSection area="problem" title={{ en: 'What Contraste is', es: 'Qué es Contraste' }} refs={['sr117', 'sr262', 'ss123', 'ecb2019']}>
        <P
          en={<>A bank's financial, risk and analytical models must be technically robust, compliant with the regulation that applies to them, and used appropriately in decisions. The people who build them and the people who validate them independently need the same things: the model families done properly, the full battery of validation tests with their exact formulas and references, the model's regulatory and accounting impact, and a record of what was found. Contraste is that workbench, for authored cases built on public data and on generators whose truth is known.</>}
          es={<>Los modelos financieros, de riesgo y analíticos de un banco deben ser técnicamente robustos, cumplir la regulación que les aplica y usarse de forma adecuada en las decisiones. Quienes los construyen y quienes los validan de forma independiente necesitan lo mismo: las familias de modelos bien hechas, la batería completa de pruebas de validación con sus fórmulas exactas y sus referencias, el impacto regulatorio y contable del modelo, y un registro de lo encontrado. Contraste es ese banco de trabajo, para casos construidos sobre datos públicos y sobre generadores cuya verdad se conoce.</>}
        />
        <P
          en={<>Model risk management grew from the US supervisory guidance of 2011 <Cite id="sr117" />, which defined a model, model risk and effective challenge, and asked validation for conceptual soundness, ongoing monitoring and outcomes analysis. Its successor of April 2026 <Cite id="sr262" /> narrows the definition and states that it is not binding; the PRA's principles <Cite id="ss123" /> and the ECB's internal-model supervision keep the same structure, and the ECB fixes the tests an IRB validation reports, with no pass or fail threshold <Cite id="ecb2019" />. Contraste follows that structure case by case.</>}
          es={<>La gestión del riesgo de modelos nació de la guía supervisora de Estados Unidos de 2011 <Cite id="sr117" />, que definió un modelo, el riesgo de modelo y el desafío efectivo, y pidió a la validación solidez conceptual, monitoreo continuo y análisis de resultados. Su sucesora de abril de 2026 <Cite id="sr262" /> estrecha la definición y declara que no es vinculante; los principios de la PRA <Cite id="ss123" /> y la supervisión de modelos internos del BCE mantienen la misma estructura, y el BCE fija las pruebas que reporta una validación IRB, sin umbral de aprobación <Cite id="ecb2019" />. Contraste sigue esa estructura caso por caso.</>}
        />
        <Figure caption={t('Contraste end to end: public sources and generators, the offline pipeline with the engine riskvalidation, the committed artifacts, and the web that replays them and recomputes what is light enough.', 'Contraste de extremo a extremo: fuentes públicas y generadores, el pipeline fuera de línea con el motor riskvalidation, los artefactos versionados, y la web que los reproduce y recalcula lo que es lo bastante liviano.')}>
          <OverviewFigure />
        </Figure>
      </DocSection>
      ),
    },
    {
      id: 'principles',
      label: t('The principles', 'Los principios'),
      content: (
      <DocSection area="principles" title={{ en: 'The principles', es: 'Los principios' }} refs={['ecb2019']}>
        <P
          en={<>Three principles decide what a case is allowed to claim. First, every fit and every test runs on a leakage-safe partition: a locked stratified holdout of 30%, a calibration slice of 20% of the rest that is disjoint from it, and a training slice where every binning, weight of evidence, rule, hyperparameter and fit is learned, with repeated stratified five-fold cross-validation inside it for each choice a rung makes. Nothing the holdout holds is ever used to choose or to fit.</>}
          es={<>Tres principios deciden lo que un caso puede afirmar. Primero, cada ajuste y cada prueba corre sobre una partición sin fugas: una muestra reservada estratificada y bloqueada de 30%, una tajada de calibración de 20% del resto, disjunta de ella, y una tajada de entrenamiento donde se aprende cada tramado, peso de evidencia, regla, hiperparámetro y ajuste, con validación cruzada estratificada repetida de cinco pliegues dentro de ella para cada elección de un peldaño. Nada de lo que contiene la muestra reservada se usa jamás para elegir ni para ajustar.</>}
        />
        <P
          en={<>Second, where the behaviour of a test matters, the truth is known: generators with a planted correlation, bias or shift let the size and the power of each test be measured instead of assumed. Third, a threshold is a policy, not a regulation, because the ECB fixes the statistics and p-values an IRB validation reports and no pass or fail level <Cite id="ecb2019" />; so every light on a result is labelled as the policy it is and can be moved by the reader, and each case declares, before it is baked, the range a reader should see for its named results, and the bake fails when a result falls outside it.</>}
          es={<>Segundo, donde importa el comportamiento de una prueba, la verdad se conoce: generadores con una correlación, un sesgo o un desplazamiento plantados permiten medir el tamaño y la potencia de cada prueba en vez de suponerlos. Tercero, un umbral es una política, no una regulación, porque el BCE fija los estadísticos y los valores p que reporta una validación IRB y ningún nivel de aprobación <Cite id="ecb2019" />; así que cada luz de un resultado se rotula como la política que es y el lector puede moverla, y cada caso declara, antes de generarse, el rango que debe ver el lector en sus resultados nombrados, y la generación falla cuando un resultado cae fuera de él.</>}
        />
        <L
          items={[
            { en: 'Technical robustness: every rung of a model ladder fitted for real, on a leakage-safe split, with the tests that a validator runs, and the size and power of those tests measured on generators whose truth is known.', es: 'Robustez técnica: cada peldaño de una escalera de modelos ajustado de verdad, en una partición sin fugas, con las pruebas que corre un validador, y el tamaño y la potencia de esas pruebas medidos en generadores cuya verdad se conoce.' },
            { en: 'Regulatory compliance: each test and each calculator tied to its paragraph and its date of application (Basel, IFRS 9, the CMF and the Banco de España), and every threshold labelled as the policy it is.', es: 'Cumplimiento regulatorio: cada prueba y cada calculadora atada a su párrafo y a su fecha de aplicación (Basilea, IFRS 9, la CMF y el Banco de España), y cada umbral rotulado como la política que es.' },
            { en: 'Appropriate use in decisions: what the model changes in approvals, losses, capital, provisions or liquidity, and the findings a model risk function would record, with their severity and evidence.', es: 'Uso adecuado en las decisiones: lo que el modelo cambia en aprobaciones, pérdidas, capital, provisiones o liquidez, y los hallazgos que registraría una función de riesgo de modelos, con su severidad y su evidencia.' },
          ]}
        />
      </DocSection>
      ),
    },
    {
      id: 'math',
      label: t('The mathematics', 'Las matemáticas'),
      content: (
      <DocSection area="math" title={{ en: 'The mathematics', es: 'Las matemáticas' }} refs={['wp14', 'bcbs2005irb', 'vasicek2002']}>
        <P
          en={<>Four quantities carry the product: how often a test rejects, how sure that rate is, how well a score ranks, and what a PD costs in capital.</>}
          es={<>Cuatro cantidades sostienen el producto: con qué frecuencia rechaza una prueba, qué tan segura es esa tasa, qué tan bien ordena un puntaje y cuánto capital cuesta una PD.</>}
        />
        <Equation
          tex={String.raw`\hat\alpha = \frac{1}{R}\sum_{r=1}^{R}\mathbf{1}\{p_r < \alpha\}`}
          caption={<T en={<>The measured rejection rate of a test: R repetitions of a generator, p_r the p-value of the test in repetition r, α the level. On a correct model it is the size and should sit near α; with a planted defect it is the power (Basel Committee Working Paper 14).</>} es={<>La tasa de rechazo medida de una prueba: R repeticiones de un generador, p_r el valor p de la prueba en la repetición r, α el nivel. En un modelo correcto es el tamaño y debe quedar cerca de α; con un defecto plantado es la potencia (documento de trabajo 14 del Comité de Basilea).</>} />}
        />
        <Equation
          tex={String.raw`\frac{\hat\alpha + \dfrac{z^2}{2R} \pm z\sqrt{\dfrac{\hat\alpha(1-\hat\alpha)}{R} + \dfrac{z^2}{4R^2}}}{1 + \dfrac{z^2}{R}}`}
          caption={<T en={<>The Wilson interval of that rate: α̂ the measured rate, R the number of repetitions, z the standard normal quantile of the confidence level (1.96 for 95%). It stays inside 0 and 1 and is honest for rates near the edges.</>} es={<>El intervalo de Wilson de esa tasa: α̂ la tasa medida, R el número de repeticiones, z el cuantil normal estándar del nivel de confianza (1,96 para 95%). Queda dentro de 0 y 1 y es honesto para tasas cercanas a los bordes.</>} />}
        />
        <Equation
          tex={String.raw`\mathrm{AUC} = \Pr(S_B > S_G) + \tfrac{1}{2}\Pr(S_B = S_G), \qquad \mathrm{Gini} = 2\,\mathrm{AUC} - 1`}
          caption={<T en={<>The ranking power of a score: S_B the risk score of an obligor drawn at random among those who defaulted, S_G of one drawn among those who did not, AUC the area under the ROC curve, Gini its rescaling to the range from -1 to 1.</>} es={<>El poder de ordenamiento de un puntaje: S_B el puntaje de riesgo de un deudor tomado al azar entre los que incumplieron, S_G el de uno tomado entre los que no, AUC el área bajo la curva ROC, Gini su reescalamiento al rango de -1 a 1.</>} />}
        />
        <Equation
          tex={String.raw`K = \mathrm{LGD}\left[\Phi\!\left(\frac{\Phi^{-1}(\mathrm{PD}) + \sqrt{\rho}\,\Phi^{-1}(0.999)}{\sqrt{1-\rho}}\right) - \mathrm{PD}\right], \qquad \mathrm{RW} = 12.5\,K`}
          caption={<T en={<>The internal-ratings-based capital requirement of a retail exposure (no maturity adjustment): PD the probability of default, LGD the loss given default, ρ the asset correlation, Φ the standard normal distribution function, 0.999 the confidence level, K the capital per unit of exposure and RW the risk weight (Basel Committee, 2005).</>} es={<>El requerimiento de capital por el método de calificaciones internas de una exposición minorista (sin ajuste por vencimiento): PD la probabilidad de incumplimiento, LGD la pérdida dado el incumplimiento, ρ la correlación de activos, Φ la función de distribución normal estándar, 0,999 el nivel de confianza, K el capital por unidad de exposición y RW el ponderador de riesgo (Comité de Basilea, 2005).</>} />}
        />
        <Glossary
          entries={[
            { term: 'PD', definition: { en: 'Probability of default over the horizon of the model, usually one year.', es: 'Probabilidad de incumplimiento en el horizonte del modelo, por lo general un año.' } },
            { term: 'LGD', definition: { en: 'Loss given default: the share of the exposure lost when the obligor defaults.', es: 'Pérdida dado el incumplimiento: la fracción de la exposición que se pierde cuando el deudor incumple.' } },
            { term: 'EAD', definition: { en: 'Exposure at default: what is owed at the moment of default.', es: 'Exposición al incumplimiento: lo adeudado en el momento del incumplimiento.' } },
            { term: 'ρ', definition: { en: 'Asset correlation of the obligors in the one-factor model.', es: 'Correlación de activos de los deudores en el modelo de un factor.' } },
            { term: 'Φ', definition: { en: 'The standard normal distribution function; Φ^-1 is its inverse.', es: 'La función de distribución normal estándar; Φ^-1 es su inversa.' } },
            { term: 'α', definition: { en: 'The level of a test: the rate of false rejection it is meant to hold.', es: 'El nivel de una prueba: la tasa de rechazo falso que debe mantener.' } },
            { term: 'α̂', definition: { en: 'The measured rejection rate: the size on a correct model, the power under a defect.', es: 'La tasa de rechazo medida: el tamaño en un modelo correcto, la potencia bajo un defecto.' } },
            { term: 'R', definition: { en: 'The number of repetitions of a generator in a simulation.', es: 'El número de repeticiones de un generador en una simulación.' } },
            { term: 'p', definition: { en: 'The p-value: the probability, under the null, of a statistic at least as extreme as the one observed.', es: 'El valor p: la probabilidad, bajo la nula, de un estadístico al menos tan extremo como el observado.' } },
            { term: 'z', definition: { en: 'The standard normal quantile of the confidence level of an interval.', es: 'El cuantil normal estándar del nivel de confianza de un intervalo.' } },
            { term: 'AUC', definition: { en: 'Area under the ROC curve: the probability that a defaulter scores riskier than a non-defaulter.', es: 'Área bajo la curva ROC: la probabilidad de que un deudor que incumple puntúe como más riesgoso que uno que no.' } },
            { term: 'Gini', definition: { en: 'The rescaling 2 AUC - 1 of the AUC.', es: 'El reescalamiento 2 AUC - 1 del AUC.' } },
            { term: 'K', definition: { en: 'The capital requirement per unit of exposure.', es: 'El requerimiento de capital por unidad de exposición.' } },
            { term: 'RW', definition: { en: 'The risk weight: 12.5 times K, as a share of the exposure.', es: 'El ponderador de riesgo: 12,5 veces K, como fracción de la exposición.' } },
          ]}
        />
      </DocSection>
      ),
    },
    {
      id: 'pipeline',
      label: t('The pipeline', 'El pipeline'),
      content: (
      <DocSection area="pipeline" title={{ en: 'The pipeline', es: 'El pipeline' }} noRefsReason={{ en: 'Describes this repository.', es: 'Describe este repositorio.' }}>
        <ol>
          <Li en="Ingest: a fetched public source is read through the input contract, which checks every field's kind, unit and range, and the licence class of the source decides what may be committed." es="Ingesta: una fuente pública descargada se lee a través del contrato de entrada, que revisa el tipo, la unidad y el rango de cada campo, y la clase de licencia de la fuente decide qué puede versionarse." />
          <Li en="Split and fit: a leakage-safe partition, then every rung of the model ladder fitted for real on the training slice." es="Partición y ajuste: una partición sin fugas, y luego cada peldaño de la escalera de modelos ajustado de verdad sobre la tajada de entrenamiento." />
          <Li en="Test: the validation battery of the engine riskvalidation runs on the holdout, with its size and power measured on generators with known truth." es="Pruebas: la batería de validación del motor riskvalidation corre sobre la muestra reservada, con su tamaño y su potencia medidos en generadores de verdad conocida." />
          <Li en="Commit: compact artifacts, one manifest per case and a readiness document that says what is real, partial, stale, provided or missing, each with its provenance." es="Versionado: artefactos compactos, un manifiesto por caso y un documento de disponibilidad que dice qué es real, parcial, desactualizado, provisto o faltante, cada uno con su procedencia." />
          <Li en="Show: the web replays the committed artifacts and recomputes live what is light and exact, such as a scorecard, a policy light or the capital at any approval rate; a case not built yet says so." es="Muestra: la web reproduce los artefactos versionados y recalcula en vivo lo que es liviano y exacto, como una scorecard, una luz de política o el capital a cualquier tasa de aprobación; un caso aún no construido lo dice." />
        </ol>
      </DocSection>
      ),
    },
    {
      id: 'honesty',
      label: t('What is exact, and what is not', 'Qué es exacto y qué no'),
      content: (
      <DocSection area="honesty" title={{ en: 'What is exact, and what is not', es: 'Qué es exacto y qué no' }} noRefsReason={{ en: 'States the product\'s limits.', es: 'Declara los límites del producto.' }}>
        <P
          en="What is exact: the formulas and constants of each test as the engine runs them, the reproduction of published tables with the gap recorded, and every number a view draws, which comes from a committed artifact or from a recomputation that a test compares with the pipeline. What is illustrative: the generators, whose truth is known because it is assumed, the synthetic institutions, which are labelled as such, and the cases still planned, which show no number at all."
          es="Lo que es exacto: las fórmulas y constantes de cada prueba tal como las corre el motor, la reproducción de tablas publicadas con la brecha registrada, y cada número que dibuja una vista, que viene de un artefacto versionado o de un recálculo que una prueba compara con el pipeline. Lo que es ilustrativo: los generadores, cuya verdad se conoce porque se supone, las instituciones sintéticas, que se rotulan como tales, y los casos aún planificados, que no muestran ningún número."
        />
        <Callout variant="honest" title={<T en="What Contraste is not" es="Qué no es Contraste" />}>
          <L
            items={[
              { en: 'It certifies nothing: a passed test is evidence, not compliance with SR 26-2, SS1/23, the ECB, the EBA, the CMF, the Banco de España, IFRS 9 or the EU AI Act.', es: 'No certifica nada: una prueba aprobada es evidencia, no cumplimiento de SR 26-2, SS1/23, el BCE, la EBA, la CMF, el Banco de España, IFRS 9 ni la ley de IA de la UE.' },
              { en: 'It represents no real bank: every synthetic institution is labelled synthetic, and public aggregates are used as aggregates.', es: 'No representa a ningún banco real: toda institución sintética se rotula como sintética, y los agregados públicos se usan como agregados.' },
              { en: 'It scores nobody and decides nothing about a real person; it gives no investment advice and no market forecast.', es: 'No puntúa a nadie ni decide nada sobre una persona real; no da consejos de inversión ni pronósticos de mercado.' },
              { en: 'It mirrors no proprietary data: rating agency tables, private loan data and competition datasets are linked, never copied.', es: 'No replica datos propietarios: las tablas de agencias, los datos privados de préstamos y los datos de competencias se enlazan, nunca se copian.' },
              { en: 'It does not claim that machine learning beats a logistic scorecard unless the held-out comparison of the case shows it, with its interval.', es: 'No afirma que el aprendizaje automático supere a una scorecard logística salvo que la comparación reservada del caso lo muestre, con su intervalo.' },
            ]}
          />
        </Callout>
      </DocSection>
      ),
    },
    {
      id: 'read',
      label: t('Reading the App and the site', 'Leer la App y el sitio'),
      content: (
        <>
      <DocSection title={{ en: 'How to read the App', es: 'Cómo leer la App' }} noRefsReason={{ en: 'Describes this interface.', es: 'Describe esta interfaz.' }}>
        <P
          en="The App is one workbench. The rail on the left holds what you choose and what you read: the case, its variant, and the case's live inputs in sections, each with a read-out that moves with its controls. The instrument beside it has one row of groups, which the selected case names; the groups of C01 are Model, Validation, Impact, Findings, Variants and Context."
          es="La App es un banco de trabajo. El panel de la izquierda contiene lo que se elige y lo que se lee: el caso, su variante, y las entradas en vivo del caso en secciones, cada una con una lectura que se mueve con sus controles. El instrumento a su lado tiene una fila de grupos, que nombra el caso elegido; los grupos de C01 son Modelo, Validación, Impacto, Hallazgos, Variantes y Contexto."
        />
        <P
          en="Every view carries two badges: its lane (live, recomputed in your browser; replay, read from a committed artifact) and its data (real, synthetic or published). A view still showing an earlier selection says so while it recomputes. A case that is planned and not built yet is listed with a planned mark, can be selected, and says in every group that it is not available yet, with the reason."
          es="Cada vista lleva dos insignias: su carril (en vivo, recalculado en el navegador; reproducción, leído de un artefacto versionado) y sus datos (reales, sintéticos o publicados). Una vista que todavía muestra una selección anterior lo indica mientras recalcula. Un caso planificado y aún no construido aparece en la lista con una marca de planificado, se puede seleccionar y dice en cada grupo que aún no está disponible, con la razón."
        />
      </DocSection>
      <DocSection title={{ en: 'The six pages', es: 'Las seis páginas' }} noRefsReason={{ en: 'Describes this site.', es: 'Describe este sitio.' }}>
        <L
          items={[
            { en: 'Introduction: the landing page, with the executive view of the problem first and then the technical view (this page).', es: 'Introducción: la página de inicio, con la vista ejecutiva del problema primero y luego la vista técnica (esta página).' },
            { en: 'App: the workbench, opened from the navigation or from the link at the end of the executive view.', es: 'App: el banco de trabajo, que se abre desde la navegación o desde el enlace al final de la vista ejecutiva.' },
            { en: 'Methodology: the model families and the validation tests, with their equations, assumptions and sources.', es: 'Metodología: las familias de modelos y las pruebas de validación, con sus ecuaciones, supuestos y fuentes.' },
            { en: 'Implementation: the pipeline, the contracts, the sources and their licences, the lanes, the engine and the gates.', es: 'Implementación: el pipeline, los contratos, las fuentes y sus licencias, los carriles, el motor y las compuertas.' },
            { en: 'Experiments: the coverage of the 22 cases and, case by case, every variant read from its artifacts.', es: 'Experimentos: la cobertura de los 22 casos y, caso por caso, cada variante leída desde sus artefactos.' },
            { en: 'Benchmark: the held-out comparisons, challenger against champion, with their tests.', es: 'Benchmark: las comparaciones reservadas, retador contra campeón, con sus pruebas.' },
          ]}
        />
      </DocSection>
        </>
      ),
    },
  ];
  return <SubTabs ariaLabel={t('Parts of the technical view', 'Partes de la vista técnica')} tabs={tabs} />;
}

export function Introduction() {
  const t = useT();
  return (
    <DocPage
      title={{ en: 'Introduction', es: 'Introducción' }}
      lede={t(
        'The industry problem of defending internal risk models before supervisors, framed for decision makers: the pain, its context, the current situation, the trends and a proposal. The technical view then shows how the work explores it.',
        'El problema de la industria de defender ante los supervisores los modelos internos de riesgo, planteado para quienes deciden: el problema, su contexto, la situación actual, las tendencias y una propuesta. La vista técnica muestra luego cómo lo explora el trabajo.',
      )}
    >
      <Tabs
        ariaLabel={t('Views of the introduction', 'Vistas de la introducción')}
        initial="executive"
        tabs={[
          { id: 'executive', label: t('Executive view', 'Vista ejecutiva'), content: <ExecutiveView data={executive} base={import.meta.env.BASE_URL} /> },
          { id: 'technical', label: t('Technical view', 'Vista técnica'), content: <Technical /> },
        ]}
      />
    </DocPage>
  );
}
