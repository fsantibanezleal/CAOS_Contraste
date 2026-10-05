// What Contraste is, whom it serves, the three lenses of the request, the honest scope, how to read the App and the
// six pages. Transcribed from SDD sections 1 and 10 and research dossier 06 (section A, the model risk guidance).
import { Cite, DocPage, DocSection, Figure } from '@fasl-work/caos-app-shell';
import product from '../../../product.json';
import { OverviewFigure } from '../architecture/figures';
import { L, P, useT } from '../content/bi';

export function Introduction() {
  const t = useT();
  return (
    <DocPage title={{ en: 'Introduction', es: 'Introducción' }} lede={t(product.tagline.en, product.tagline.es)}>
      <DocSection title={{ en: 'What Contraste is', es: 'Qué es Contraste' }} refs={['sr117', 'sr262', 'ss123', 'ecb2019']}>
        <P
          en={<>A bank's financial, risk and analytical models must be technically robust, compliant with the regulation that applies to them, and used appropriately in decisions. The people who build them and the people who validate them independently need the same things: the model families done properly, the full battery of validation tests with their exact formulas and references, the model's regulatory and accounting impact, and a record of what was found. Contraste is that workbench, for authored cases built on public data and on generators whose truth is known.</>}
          es={<>Los modelos financieros, de riesgo y analíticos de un banco deben ser técnicamente robustos, cumplir la regulación que les aplica y usarse de forma adecuada en las decisiones. Quienes los construyen y quienes los validan de forma independiente necesitan lo mismo: las familias de modelos bien hechas, la batería completa de pruebas de validación con sus fórmulas exactas y sus referencias, el impacto regulatorio y contable del modelo, y un registro de lo encontrado. Contraste es ese banco de trabajo, para casos construidos sobre datos públicos y sobre generadores cuya verdad se conoce.</>}
        />
        <P
          en={<>Model risk management grew from the US supervisory guidance of 2011 <Cite id="sr117" />, which defined a model, model risk and effective challenge, and asked validation for conceptual soundness, ongoing monitoring and outcomes analysis. Its successor of April 2026 <Cite id="sr262" /> narrows the definition and states that it is not binding; the PRA's principles <Cite id="ss123" /> and the ECB's internal-model supervision keep the same structure, and the ECB fixes the tests an IRB validation reports, with no pass or fail threshold <Cite id="ecb2019" />. Contraste follows that structure case by case.</>}
          es={<>La gestión del riesgo de modelos nació de la guía supervisora de Estados Unidos de 2011 <Cite id="sr117" />, que definió un modelo, el riesgo de modelo y el desafío efectivo, y pidió a la validación solidez conceptual, monitoreo continuo y análisis de resultados. Su sucesora de abril de 2026 <Cite id="sr262" /> estrecha la definición y declara que no es vinculante; los principios de la PRA <Cite id="ss123" /> y la supervisión de modelos internos del BCE mantienen la misma estructura, y el BCE fija las pruebas que reporta una validación IRB, sin umbral de aprobación <Cite id="ecb2019" />. Contraste sigue esa estructura caso por caso.</>}
        />
        <Figure caption={t('Contraste end to end: public sources and generators, the offline pipeline with the engine riskvalidation, the committed artifacts, and the web that replays them and recomputes what is light enough.', 'Contraste de extremo a extremo: fuentes públicas y generadores, el pipeline fuera de línea con el motor riskvalidation, los artefactos comprometidos, y la web que los reproduce y recalcula lo que es lo bastante liviano.')}>
          <OverviewFigure />
        </Figure>
      </DocSection>
      <DocSection title={{ en: 'The three lenses', es: 'Los tres lentes' }} noRefsReason={{ en: 'States the product\'s scope.', es: 'Declara el alcance del producto.' }}>
        <L
          items={[
            { en: 'Technical robustness: every rung of a model ladder fitted for real, on a leakage-safe split, with the tests that a validator runs, and the size and power of those tests measured on generators whose truth is known.', es: 'Robustez técnica: cada peldaño de una escalera de modelos ajustado de verdad, en una partición sin fugas, con las pruebas que corre un validador, y el tamaño y la potencia de esas pruebas medidos en generadores cuya verdad se conoce.' },
            { en: 'Regulatory compliance: each test and each calculator tied to its paragraph and its date of application (Basel, IFRS 9, the CMF and the Banco de España), and every threshold labelled as the policy it is.', es: 'Cumplimiento regulatorio: cada prueba y cada calculadora atada a su párrafo y a su fecha de aplicación (Basilea, IFRS 9, la CMF y el Banco de España), y cada umbral rotulado como la política que es.' },
            { en: 'Appropriate use in decisions: what the model changes in approvals, losses, capital, provisions or liquidity, and the findings a model risk function would record, with their severity and evidence.', es: 'Uso adecuado en las decisiones: lo que el modelo cambia en aprobaciones, pérdidas, capital, provisiones o liquidez, y los hallazgos que registraría una función de riesgo de modelos, con su severidad y su evidencia.' },
          ]}
        />
      </DocSection>
      <DocSection title={{ en: 'What Contraste is not', es: 'Qué no es Contraste' }} noRefsReason={{ en: 'States the product\'s limits.', es: 'Declara los límites del producto.' }}>
        <L
          items={[
            { en: 'It certifies nothing: a passed test is evidence, not compliance with SR 26-2, SS1/23, the ECB, the EBA, the CMF, the Banco de España, IFRS 9 or the EU AI Act.', es: 'No certifica nada: una prueba aprobada es evidencia, no cumplimiento de SR 26-2, SS1/23, el BCE, la EBA, la CMF, el Banco de España, IFRS 9 ni la Ley de IA de la UE.' },
            { en: 'It represents no real bank: every synthetic institution is labelled synthetic, and public aggregates are used as aggregates.', es: 'No representa a ningún banco real: toda institución sintética se rotula como sintética, y los agregados públicos se usan como agregados.' },
            { en: 'It scores nobody and decides nothing about a real person; it gives no investment advice and no market forecast.', es: 'No puntúa a nadie ni decide nada sobre una persona real; no da consejos de inversión ni pronósticos de mercado.' },
            { en: 'It mirrors no proprietary data: rating agency tables, private loan data and competition datasets are linked, never copied.', es: 'No replica datos propietarios: las tablas de agencias, los datos privados de préstamos y los datos de competencias se enlazan, nunca se copian.' },
            { en: 'It does not claim that machine learning beats a logistic scorecard unless the held-out comparison of the case shows it, with its interval.', es: 'No afirma que el aprendizaje automático supere a una scorecard logística salvo que la comparación reservada del caso lo muestre, con su intervalo.' },
          ]}
        />
      </DocSection>
      <DocSection title={{ en: 'How to read the App', es: 'Cómo leer la App' }} noRefsReason={{ en: 'Describes this interface.', es: 'Describe esta interfaz.' }}>
        <P
          en="The App is one workbench. The rail on the left holds what you choose and what you read: the case, its variant, and the live inputs in three sections (the decision: the challenger, the approval rate and the loss given default; the policy: the thresholds that turn p-values into lights; the applicant: one holdout applicant scored live). The instrument on the right holds six groups, in this order: Model (the ladder and the inside of each rung), Validation (the battery), Impact (what the model changes in the decision), Findings (what the validation found), Variants (the regimes of the case side by side) and Context (the case, its data and licences, its limits)."
          es="La App es un banco de trabajo. El panel de la izquierda contiene lo que se elige y lo que se lee: el caso, su variante, y las entradas en vivo en tres secciones (la decisión: el retador, la tasa de aprobación y la pérdida dado el incumplimiento; la política: los umbrales que convierten valores p en luces; el solicitante: uno de la muestra reservada puntuado en vivo). El instrumento de la derecha contiene seis grupos, en este orden: Modelo (la escalera y el interior de cada peldaño), Validación (la batería), Impacto (lo que el modelo cambia en la decisión), Hallazgos (lo que encontró la validación), Variantes (los regímenes del caso lado a lado) y Contexto (el caso, sus datos y licencias, sus límites)."
        />
        <P
          en="Every view carries two badges: its lane (live, recomputed in your browser; replay, read from a committed artifact) and its data (real, synthetic or published). A view still showing an earlier selection says so while it recomputes. A case can be linked directly with ?case= followed by its identifier."
          es="Cada vista lleva dos insignias: su carril (en vivo, recalculado en el navegador; reproducción, leído de un artefacto comprometido) y sus datos (reales, sintéticos o publicados). Una vista que todavía muestra una selección anterior lo indica mientras recalcula. Un caso se puede enlazar directamente con ?case= seguido de su identificador."
        />
      </DocSection>
      <DocSection title={{ en: 'The six pages', es: 'Las seis páginas' }} noRefsReason={{ en: 'Describes this site.', es: 'Describe este sitio.' }}>
        <L
          items={[
            { en: 'App: the workbench, the landing page.', es: 'App: el banco de trabajo, la página de inicio.' },
            { en: 'Introduction: what Contraste is and how to read it (this page).', es: 'Introducción: qué es Contraste y cómo leerlo (esta página).' },
            { en: 'Methodology: the model families and the validation tests, with their equations, assumptions and sources.', es: 'Metodología: las familias de modelos y las pruebas de validación, con sus ecuaciones, supuestos y fuentes.' },
            { en: 'Implementation: the pipeline, the contracts, the sources and their licences, the lanes, the engine and the gates.', es: 'Implementación: el pipeline, los contratos, las fuentes y sus licencias, los carriles, el motor y las compuertas.' },
            { en: 'Experiments: the coverage of the 22 cases and, case by case, every variant read from its artifacts.', es: 'Experimentos: la cobertura de los 22 casos y, caso por caso, cada variante leída desde sus artefactos.' },
            { en: 'Benchmark: the held-out comparisons, challenger against champion, with their tests.', es: 'Benchmark: las comparaciones reservadas, retador contra campeón, con sus pruebas.' },
          ]}
        />
      </DocSection>
    </DocPage>
  );
}
