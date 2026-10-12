// The Introduction opens for the person who answers to the supervisor for a bank's models (ADR-0017 section 2.1, the
// executive view of 2026-10-12) and then turns technical. Two views: `executive`, first and open on load, in business
// language, with every claim of value a number with its unit and its source (transcribed from the executive brief of
// the design document, each figure read at its primary source on 2026-10-12), and `technical`, the previous page under
// its five areas: problem, principles, math with its glossary, pipeline and honesty.
import { Callout, Cite, DocPage, DocSection, Equation, Figure, Glossary, Question, Stat, Tabs } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { OverviewFigure } from '../architecture/figures';
import { L, P, Ref, T, useT } from '../content/bi';
import { NoTranslateRefs } from './NoTranslateRefs';

/** One list item written in both languages. */
const Li = ({ en, es }: { en: ReactNode; es: ReactNode }) => (
  <li>
    <T en={en} es={es} />
  </li>
);

/** A statement with its number: the value written as each language writes it, its unit and its source. */
const S = ({ en, es, unit, source }: { en: string; es?: string; unit: { en: string; es: string }; source: { en: string; es: string } }) => (
  <Stat value={{ en, es: es ?? en }} unit={unit} source={source} />
);

const SRC = {
  trim: { en: 'ECB, TRIM project report', es: 'BCE, informe del proyecto TRIM' },
  ar: { en: 'ECB, Annual Report on supervisory activities 2025', es: 'BCE, Informe anual de actividades de supervisión 2025' },
  eba: { en: 'EBA, press release of 2026-03-23', es: 'EBA, comunicado del 2026-03-23' },
  crr: { en: 'CRR3, Article 465(1)', es: 'CRR3, artículo 465(1)' },
  cmf: { en: 'CMF, Basel III calendar', es: 'CMF, calendario de Basilea III' },
  c22: { en: 'Contraste, case C22', es: 'Contraste, caso C22' },
  c05: { en: 'Contraste, case C05', es: 'Contraste, caso C05' },
  c04: { en: 'Contraste, case C04', es: 'Contraste, caso C04' },
  c01: { en: 'Contraste, case C01', es: 'Contraste, caso C01' },
};

function Executive() {
  return (
    <>
      <DocSection
        area="initiative"
        title={{ en: 'The initiative', es: 'La iniciativa' }}
        refs={['ecbtrim', 'ecbar2025', 'crr3floor', 'praps126', 'osfie23', 'aiact', 'ebapr2026', 'cmfcal', 'cmfmi2026']}
      >
        <P
          en={<>The person accountable for a bank's models answers to the supervisor for them: in most banks the chief risk officer, with the head of model validation. Their initiative is to keep the bank's internal credit and provisioning models defensible to the supervisor through the regime changes of 2027, and to know what each modelling choice costs in capital before the supervisor does. The reason to act now is measured, and it has four parts.</>}
          es={<>La persona que responde ante el supervisor por los modelos de un banco es, en la mayoría de los bancos, el gerente de riesgos, junto con el responsable de validación de modelos. Su iniciativa es mantener defendibles ante el supervisor los modelos internos de crédito y de provisiones del banco a través de los cambios de régimen de 2027, y saber qué cuesta en capital cada decisión de modelación antes de que lo sepa el supervisor. La razón para actuar ahora es medible y tiene cuatro partes.</>}
        />
        <ul>
          <Li
            en={<>The last time the euro-area supervisor reviewed internal models at scale it ran 200 on-site investigations at 65 banks and raised <S en="5,800" unit={{ en: 'findings, about 30% of them of high severity', es: 'hallazgos, cerca de un 30% de ellos de severidad alta' }} source={SRC.trim} /> <Cite id="ecbtrim" />. The models reviewed ended with about <S en="12" unit={{ en: '% more risk-weighted assets (about EUR 275 billion), with a median effect of 51 basis points on the CET1 ratio', es: '% más de activos ponderados por riesgo (unos 275 mil millones de euros), con un efecto mediano de 51 puntos base en la razón CET1' }} source={SRC.trim} />.</>}
            es={<>La última vez que el supervisor de la zona euro revisó modelos internos a gran escala realizó 200 investigaciones in situ en 65 bancos y levantó <S en="5800" unit={{ en: 'findings', es: 'hallazgos, cerca de un 30% de ellos de severidad alta' }} source={SRC.trim} /> <Cite id="ecbtrim" />. Los modelos revisados terminaron con cerca de <S en="12" unit={{ en: '%', es: '% más de activos ponderados por riesgo (unos 275 mil millones de euros), con un efecto mediano de 51 puntos base en la razón CET1' }} source={SRC.trim} />.</>}
          />
          <Li
            en={<>It has not eased: in 2025 the ECB launched <S en="77" unit={{ en: 'internal model investigations, with 16 findings each on average and almost half of them of high severity', es: 'investigaciones de modelos internos, con 16 hallazgos en promedio cada una y casi la mitad de severidad alta' }} source={SRC.ar} /> <Cite id="ecbar2025" />.</>}
            es={<>No ha cedido: en 2025 el BCE inició <S en="77" unit={{ en: 'investigations', es: 'investigaciones de modelos internos, con 16 hallazgos en promedio cada una y casi la mitad de severidad alta' }} source={SRC.ar} /> <Cite id="ecbar2025" />.</>}
          />
          <Li
            en={<>The finding that sits closest to this product: banks "often did not ensure that all appropriate validation analyses and adequate quantitative thresholds were in place, in particular for the back-testing, discriminatory power and stability tests" <Cite id="ecbtrim" />.</>}
            es={<>El hallazgo más cercano a este producto: los bancos "con frecuencia no se aseguraron de contar con todos los análisis de validación apropiados ni con umbrales cuantitativos adecuados, en particular para las pruebas de backtesting, poder discriminatorio y estabilidad" (traducción propia) <Cite id="ecbtrim" />.</>}
          />
          <Li
            en={<>2027 changes four regimes at once: the EU output floor reaches <S en="60" unit={{ en: '% in 2027 (72.5% from 2030)', es: '% en 2027 (72,5% desde 2030)' }} source={SRC.crr} /> <Cite id="crr3floor" />; the UK's Basel 3.1 rules take effect on 2027-01-01 <Cite id="praps126" />; Canada's model risk guideline E-23 on 2027-05-01 <Cite id="osfie23" />; and credit scoring becomes a high-risk AI system in the EU on 2027-12-02 <Cite id="aiact" />. The EBA projects an average <S en="4.7" es="4,7" unit={{ en: '% increase in Tier 1 minimum required capital once the floor is fully in, with the banks bound by it rising from 2 to 33', es: '% de aumento del capital mínimo exigido de Nivel 1 una vez que el piso rija por completo, y los bancos sujetos a él suben de 2 a 33' }} source={SRC.eba} /> <Cite id="ebapr2026" />.</>}
            es={<>2027 cambia cuatro regímenes a la vez: el piso de output de la UE llega a <S en="60" unit={{ en: '%', es: '% en 2027 (72,5% desde 2030)' }} source={SRC.crr} /> <Cite id="crr3floor" />; las reglas de Basilea <Ref>3.1</Ref> del Reino Unido entran en vigor el 2027-01-01 <Cite id="praps126" />; la directriz E-23 de riesgo de modelos de Canadá el 2027-05-01 <Cite id="osfie23" />; y el scoring de crédito pasa a ser un sistema de IA de alto riesgo en la UE el 2027-12-02 <Cite id="aiact" />. La EBA proyecta un <S en="4.7" es="4,7" unit={{ en: '%', es: '% de aumento promedio del capital mínimo exigido de Nivel 1 una vez que el piso rija por completo, y los bancos sujetos a él suben de 2 a 33' }} source={SRC.eba} /> <Cite id="ebapr2026" />.</>}
          />
          <Li
            en={<>In Chile the Pillar 2 charge reaches <S en="100" unit={{ en: '% on 2027-12-01', es: '% el 2027-12-01' }} source={SRC.cmf} /> <Cite id="cmfcal" />, and the CMF consulted in August 2026 on opening internal models for provisions and credit risk-weighted assets, which no bank uses today <Cite id="cmfmi2026" />.</>}
            es={<>En Chile el cargo de Pilar 2 llega al <S en="100" unit={{ en: '%', es: '% el 2027-12-01' }} source={SRC.cmf} /> <Cite id="cmfcal" />, y la CMF consultó en agosto de 2026 abrir los modelos internos para provisiones y activos ponderados por riesgo de crédito, que hoy ningún banco usa <Cite id="cmfmi2026" />.</>}
          />
        </ul>
      </DocSection>

      <DocSection area="outcomes" title={{ en: 'The outcomes', es: 'Los resultados' }} refs={['contrasteC22', 'contrasteC05', 'contrasteC04', 'contrasteC01']}>
        <P
          en={<>The vision: a validation function that can say, with numbers, how far each of its tests can be trusted and what each modelling choice costs, before it signs an opinion. Each capability below is tied to the business outcome it gives and to a proof point recomputed from public inputs or from generators whose truth is known.</>}
          es={<>La visión: una función de validación que puede decir, con números, hasta dónde se puede confiar en cada una de sus pruebas y cuánto cuesta cada decisión de modelación, antes de firmar una opinión. Cada capacidad de la tabla se ata al resultado de negocio que entrega y a una prueba cuantificada, recalculada desde insumos públicos o desde generadores cuya verdad se conoce.</>}
        />
        <table className="caos-table ct-wrap-head">
          <thead>
            <tr>
              <th className="caos-col-text"><T en="Capability" es="Capacidad" /></th>
              <th className="caos-col-text"><T en="Business outcome" es="Resultado de negocio" /></th>
              <th className="caos-col-text"><T en="Proof point" es="Prueba" /></th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="caos-col-text"><T en="It recomputes published supervisory and academic results cell by cell" es="Recalcula celda por celda resultados supervisores y académicos publicados" /></td>
              <td className="caos-col-text"><T en="A number that stands when a supervisor or an auditor re-runs it" es="Un número que se sostiene cuando un supervisor o un auditor lo vuelve a correr" /></td>
              <td className="caos-col-text"><S en="143 of 144" es="143 de 144" unit={{ en: 'cells of the Basel Committee Working Paper 14, Tables 7 and 8, reproduced', es: 'celdas de las tablas 7 y 8 del documento de trabajo 14 del Comité de Basilea, reproducidas' }} source={SRC.c22} /> <Cite id="contrasteC22" /></td>
            </tr>
            <tr>
              <td className="caos-col-text"><T en="It measures how often each validation test is wrong" es="Mide con qué frecuencia se equivoca cada prueba de validación" /></td>
              <td className="caos-col-text"><T en="No sound model rejected, and no weak one passed, because of the test" es="Ningún modelo sano rechazado y ninguno débil aprobado por culpa de la prueba" /></td>
              <td className="caos-col-text">
                <S en="10.98" es="10,98" unit={{ en: '% of correct PDs rejected by a standard calibration test (Hosmer-Lemeshow) at a 5% level', es: '% de PD correctas rechazadas por una prueba de calibración estándar (Hosmer-Lemeshow) a un nivel de 5%' }} source={SRC.c22} />{' '}
                <T en="; the supervisor's discrimination test raises a false alarm 17.0% of the time in the case's setting. Both were found by measurement and corrected in the product." es="; la prueba de discriminación del supervisor da una falsa alarma el 17,0% de las veces en el escenario del caso. Ambas se encontraron midiendo y se corrigieron en el producto." />{' '}
                <Cite id="contrasteC22" />
              </td>
            </tr>
            <tr>
              <td className="caos-col-text"><T en="It prices a modelling choice in capital" es="Pone precio en capital a una decisión de modelación" /></td>
              <td className="caos-col-text"><T en="The board sees the capital effect of a calibration or a data definition before it is committed" es="El directorio ve el efecto en capital de una calibración o de una definición de datos antes de comprometerla" /></td>
              <td className="caos-col-text">
                <S en="64.8" es="64,8" unit={{ en: '% more capital asked by carrying last year\'s PD curve unchanged instead of recalibrating it', es: '% más de capital exigido por llevar sin cambios la curva de PD del año anterior en vez de recalibrarla' }} source={SRC.c05} />{' '}
                <T en="; one default definition against another moves the speculative-grade PD from 26.64% to 8.61% and the portfolio's risk weight from 58.0% to 47.5%." es="; una definición de incumplimiento frente a otra mueve la PD del grado especulativo de 26,64% a 8,61% y el ponderador de riesgo de la cartera de 58,0% a 47,5%." />{' '}
                <Cite id="contrasteC05" /> <Cite id="contrasteC04" />
              </td>
            </tr>
            <tr>
              <td className="caos-col-text"><T en="It holds a challenger model to the same tests as the champion" es="Somete al modelo retador a las mismas pruebas que al campeón" /></td>
              <td className="caos-col-text"><T en="Complexity is adopted only where it earns its keep" es="La complejidad se adopta solo donde se justifica" /></td>
              <td className="caos-col-text">
                <S en="0.018" es="0,018" unit={{ en: 'AUC gained over the scorecard by a monotone gradient-boosted model on 9000 held-out records, saving 4.2% of capital', es: 'de AUC ganado sobre la scorecard por un modelo de gradient boosting monótono en 9000 registros reservados, con un ahorro de 4,2% del capital' }} source={SRC.c01} />{' '}
                <T en="; on 300 records it beats nothing." es="; con 300 registros no supera a nada." /> <Cite id="contrasteC01" />
              </td>
            </tr>
          </tbody>
        </table>
      </DocSection>

      <DocSection area="positioning" title={{ en: 'The positioning', es: 'El posicionamiento' }} noRefsReason={{ en: 'States what the product offers; the proof points are cited under the outcomes.', es: 'Declara lo que ofrece el producto; las pruebas se citan en los resultados.' }}>
        <ul>
          <Li
            en={<><strong>Reproducible</strong>: the supervisor will re-run the number, so every result is recomputed from published inputs with its gap recorded, and the opinion never rests on a figure nobody can rebuild.</>}
            es={<><strong>Reproducible</strong>: el supervisor volverá a correr el número, así que cada resultado se recalcula desde insumos publicados con su brecha registrada, y la opinión nunca descansa en una cifra que nadie puede reconstruir.</>}
          />
          <Li
            en={<><strong>Measured</strong>: a test is evidence only as far as its error rates are known, so each test comes with its measured false alarm rate and its power, which is the threshold work the supervisor found missing.</>}
            es={<><strong>Medido</strong>: una prueba es evidencia solo hasta donde se conocen sus tasas de error, así que cada prueba trae su tasa de falsa alarma y su potencia medidas, que es el trabajo de umbrales que el supervisor echó de menos.</>}
          />
          <Li
            en={<><strong>Priced</strong>: a modelling choice is a capital decision, so each calibration, definition and model swap is shown with what it changes in risk-weighted assets, and the choice is made knowingly.</>}
            es={<><strong>Valorizado</strong>: una decisión de modelación es una decisión de capital, así que cada calibración, definición y cambio de modelo se muestra con lo que cambia en los activos ponderados por riesgo, y la decisión se toma con conocimiento.</>}
          />
          <Li
            en={<><strong>Open</strong>: an opinion must be checkable by a third party, so the code, the data sources with their licences, the seeds and the expected ranges are public, and the limits are stated on every case.</>}
            es={<><strong>Abierto</strong>: una opinión debe poder verificarla un tercero, así que el código, las fuentes de datos con sus licencias, las semillas y los rangos esperados son públicos, y los límites se declaran en cada caso.</>}
          />
        </ul>
      </DocSection>

      <DocSection area="credibility" title={{ en: 'The credibility', es: 'La credibilidad' }} refs={['wp14', 'contrasteC22']}>
        <Question
          question={<T en="Does it reproduce what a supervisor would run?" es="¿Reproduce lo que correría un supervisor?" />}
          answer={<P en={<>For the tests it covers, yes, against published answers: 143 of 144 cells of Working Paper 14 <Cite id="wp14" />, 50 of 54 of a published stability study, and the published calibration and migration tables, each gap recorded. It covers credit scoring, rating calibration, rating migrations and the tests themselves today; provisions, market, liquidity and operational risk are planned and shown as not built yet.</>} es={<>Para las pruebas que cubre, sí, contra respuestas publicadas: 143 de 144 celdas del documento de trabajo 14 <Cite id="wp14" />, 50 de 54 de un estudio publicado de estabilidad, y las tablas publicadas de calibración y de migración, cada brecha registrada. Hoy cubre scoring de crédito, calibración de calificaciones, migraciones de calificación y las pruebas mismas; provisiones, mercado, liquidez y riesgo operacional están planificados y se muestran como aún no construidos.</>} />}
        />
        <Question
          question={<T en="Can I trust its tests?" es="¿Puedo confiar en sus pruebas?" />}
          answer={<P en={<>You can see how far: 19 of 21 tests hold their stated size, and the two that do not are named, with how much they over-reject <Cite id="contrasteC22" />. Where a widely used test misleads, the product says so and shows the measurement.</>} es={<>Se puede ver hasta dónde: 19 de 21 pruebas mantienen su tamaño declarado, y las dos que no lo hacen están nombradas, con cuánto rechazan de más <Cite id="contrasteC22" />. Donde una prueba muy usada induce a error, el producto lo dice y muestra la medición.</>} />}
        />
        <Question
          question={<T en="What does it change in my capital or provisions?" es="¿Qué cambia en mi capital o en mis provisiones?" />}
          answer={<P en="It shows what a choice changes on public and generated portfolios, as in the outcomes above. It does not compute your capital: it runs on no bank's portfolio." es="Muestra lo que cambia una decisión sobre carteras públicas y generadas, como en los resultados de arriba. No calcula su capital: no corre sobre la cartera de ningún banco." />}
        />
        <Question
          question={<T en="How does it fit my model inventory and governance?" es="¿Cómo calza con mi inventario de modelos y mi gobierno?" />}
          answer={<P en="It is a workbench, not an inventory or a workflow system. It records its own models and findings; it does not ingest a bank's inventory." es="Es un banco de trabajo, no un inventario ni un sistema de flujos. Registra sus propios modelos y hallazgos; no incorpora el inventario de un banco." />}
        />
        <Question
          question={<T en="What about machine-learning challengers and the AI rules?" es="¿Qué pasa con los modelos retadores de aprendizaje automático y las reglas de IA?" />}
          answer={<P en="It tests a monotone boosted model and an explainable additive model beside the scorecard, with paired tests, calibration and capital. It does not certify compliance with the AI Act or any regulation." es="Prueba un modelo con boosting monótono y un modelo aditivo explicable junto a la scorecard, con pruebas pareadas, calibración y capital. No certifica el cumplimiento de la ley de IA ni de ninguna otra regulación." />}
        />
        <Callout variant="honest" title={<T en="Limits" es="Límites" />}>
          <T
            en="Every case runs on public data or on generated data with known truth; no result is a regulatory threshold; a passed test is evidence, not compliance; the product certifies no model, represents no real bank and has no affiliation with any institution or supervisor named here."
            es="Cada caso corre sobre datos públicos o sobre datos generados con verdad conocida; ningún resultado es un umbral regulatorio; una prueba aprobada es evidencia, no cumplimiento; el producto no certifica ningún modelo, no representa a ningún banco real y no tiene afiliación con ninguna institución ni supervisor nombrado aquí."
          />
        </Callout>
      </DocSection>
    </>
  );
}

function Technical() {
  const t = useT();
  return (
    <>
      <DocSection area="problem" title={{ en: 'What Contraste is', es: 'Qué es Contraste' }} refs={['sr117', 'sr262', 'ss123', 'ecb2019']}>
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

      <DocSection area="pipeline" title={{ en: 'The pipeline', es: 'El pipeline' }} noRefsReason={{ en: 'Describes this repository.', es: 'Describe este repositorio.' }}>
        <ol>
          <Li en="Ingest: a fetched public source is read through the input contract, which checks every field's kind, unit and range, and the licence class of the source decides what may be committed." es="Ingesta: una fuente pública descargada se lee a través del contrato de entrada, que revisa el tipo, la unidad y el rango de cada campo, y la clase de licencia de la fuente decide qué puede comprometerse." />
          <Li en="Split and fit: a leakage-safe partition, then every rung of the model ladder fitted for real on the training slice." es="Partición y ajuste: una partición sin fugas, y luego cada peldaño de la escalera de modelos ajustado de verdad sobre la tajada de entrenamiento." />
          <Li en="Test: the validation battery of the engine riskvalidation runs on the holdout, with its size and power measured on generators with known truth." es="Pruebas: la batería de validación del motor riskvalidation corre sobre la muestra reservada, con su tamaño y su potencia medidos en generadores de verdad conocida." />
          <Li en="Commit: compact artifacts, one manifest per case and a readiness document that says what is real, partial, stale, provided or missing, each with its provenance." es="Compromiso: artefactos compactos, un manifiesto por caso y un documento de disponibilidad que dice qué es real, parcial, desactualizado, provisto o faltante, cada uno con su procedencia." />
          <Li en="Show: the web replays the committed artifacts and recomputes live what is light and exact, such as a scorecard, a policy light or the capital at any approval rate; a case not built yet says so." es="Muestra: la web reproduce los artefactos comprometidos y recalcula en vivo lo que es liviano y exacto, como una scorecard, una luz de política o el capital a cualquier tasa de aprobación; un caso aún no construido lo dice." />
        </ol>
      </DocSection>

      <DocSection area="honesty" title={{ en: 'What is exact, and what is not', es: 'Qué es exacto y qué no' }} noRefsReason={{ en: 'States the product\'s limits.', es: 'Declara los límites del producto.' }}>
        <P
          en="What is exact: the formulas and constants of each test as the engine runs them, the reproduction of published tables with the gap recorded, and every number a view draws, which comes from a committed artifact or from a recomputation that a test compares with the pipeline. What is illustrative: the generators, whose truth is known because it is assumed, the synthetic institutions, which are labelled as such, and the cases still planned, which show no number at all."
          es="Lo que es exacto: las fórmulas y constantes de cada prueba tal como las corre el motor, la reproducción de tablas publicadas con la brecha registrada, y cada número que dibuja una vista, que viene de un artefacto comprometido o de un recálculo que una prueba compara con el pipeline. Lo que es ilustrativo: los generadores, cuya verdad se conoce porque se supone, las instituciones sintéticas, que se rotulan como tales, y los casos aún planificados, que no muestran ningún número."
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

      <DocSection title={{ en: 'How to read the App', es: 'Cómo leer la App' }} noRefsReason={{ en: 'Describes this interface.', es: 'Describe esta interfaz.' }}>
        <P
          en="The App is one workbench. The rail on the left holds what you choose and what you read: the case, its variant, and the case's live inputs in sections, each with a read-out that moves with its controls. The instrument beside it has one row of groups: Model, Validation, Impact, Findings, Variants and Context."
          es="La App es un banco de trabajo. El panel de la izquierda contiene lo que se elige y lo que se lee: el caso, su variante, y las entradas en vivo del caso en secciones, cada una con una lectura que se mueve con sus controles. El instrumento a su lado tiene una fila de grupos: Modelo, Validación, Impacto, Hallazgos, Variantes y Contexto."
        />
        <P
          en="Every view carries two badges: its lane (live, recomputed in your browser; replay, read from a committed artifact) and its data (real, synthetic or published). A view still showing an earlier selection says so while it recomputes. A case that is planned and not built yet is listed with a planned mark, can be selected, and says in every group that it is not available yet, with the reason."
          es="Cada vista lleva dos insignias: su carril (en vivo, recalculado en el navegador; reproducción, leído de un artefacto comprometido) y sus datos (reales, sintéticos o publicados). Una vista que todavía muestra una selección anterior lo indica mientras recalcula. Un caso planificado y aún no construido aparece en la lista con una marca de planificado, se puede seleccionar y dice en cada grupo que aún no está disponible, con la razón."
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
    </>
  );
}

export function Introduction() {
  const t = useT();
  return (
    <DocPage
      title={{ en: 'Introduction', es: 'Introducción' }}
      lede={t(
        'Build financial risk models, then validate them the way a model risk function and a supervisor would: this page opens with what is at stake for the person who answers for a bank\'s models, and then turns to the problem, the principles, the mathematics, the pipeline and the limits of the work.',
        'Construir modelos de riesgo financiero y validarlos como lo harían una función de riesgo de modelos y un supervisor: esta página abre con lo que está en juego para quien responde por los modelos de un banco, y luego pasa al problema, los principios, las matemáticas, el pipeline y los límites del trabajo.',
      )}
    >
      <NoTranslateRefs />
      <Tabs
        ariaLabel={t('Views of the introduction', 'Vistas de la introducción')}
        initial="executive"
        tabs={[
          { id: 'executive', label: t('Executive view', 'Vista ejecutiva'), content: <Executive /> },
          { id: 'technical', label: t('Technical view', 'Vista técnica'), content: <Technical /> },
        ]}
      />
    </DocPage>
  );
}
