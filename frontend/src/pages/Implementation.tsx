// How Contraste is built, in six groups of topics (ADR-0017 as amended: at least eight topics, at most six groups):
// the pipeline, the contracts, the data and its licences, the engines and the lanes, the gates, and the deploy.
// Transcribed from SDD sections 2, 3, 7 and 8 and from the feature designs in docs/design/features/.
import { DocPage, DocSection, Figure, Tabs, useShellLang } from '@fasl-work/caos-app-shell';
import { ContractsFigure, FlowFigure, OverviewFigure } from '../architecture/figures';
import { L, P, useT } from '../content/bi';

const THIS_REPO = { en: 'Describes this repository.', es: 'Describe este repositorio.' };

function Pipeline() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'The stages', es: 'Las etapas' }} noRefsReason={THIS_REPO}>
        <P
          en="The offline pipeline (data-pipeline/, invoked by path, never installed) runs each case through named stages: ingest (a fetched source through contract 1), split (the leakage-safe partition), the fit of every rung, evaluate (the battery and the outputs the views draw) and export (contract 2). It is the only lane that writes artifacts, it runs on a workstation, and never in CI or in the browser. Every generator is seeded, so a second bake of the same release writes the same bytes."
          es="El pipeline fuera de línea (data-pipeline/, invocado por ruta, nunca instalado) pasa cada caso por etapas con nombre: ingesta (una fuente descargada a través del contrato 1), partición (la partición sin fugas), el ajuste de cada peldaño, evaluación (la batería y las salidas que dibujan las vistas) y exportación (contrato 2). Es el único carril que escribe artefactos, corre en una estación de trabajo, y nunca en CI ni en el navegador. Todo generador tiene semilla, así un segundo precálculo de la misma versión escribe los mismos bytes."
        />
        <Figure caption={t('Sources, the offline pipeline, the committed artifacts and the web.', 'Fuentes, el pipeline fuera de línea, los artefactos comprometidos y la web.')}>
          <OverviewFigure />
        </Figure>
      </DocSection>
      <DocSection title={{ en: 'The split and the expectations', es: 'La partición y las expectativas' }} noRefsReason={THIS_REPO}>
        <L
          items={[
            { en: 'A locked stratified holdout of 30%; a calibration slice of 20% of the rest, disjoint from it; the training slice, where every binning, WoE, rule, hyperparameter and fit is learned.', es: 'Una muestra reservada estratificada del 30%; un tramo de calibración del 20% del resto, disjunto de ella; el tramo de entrenamiento, donde se aprende todo tramado, WoE, regla, hiperparámetro y ajuste.' },
            { en: 'Repeated stratified five-fold cross-validation inside the training slice for every choice a rung makes (penalty strength, number of trees).', es: 'Validación cruzada estratificada repetida de cinco pliegues dentro del tramo de entrenamiento para toda elección de un peldaño (fuerza de penalización, número de árboles).' },
            { en: 'Each case declares, before it is baked, the range a reader should see for its named results (a default rate, an AUC, a PSI, a p-value under a known shift); the bake fails when a result falls outside.', es: 'Cada caso declara, antes de precalcularse, el rango que el lector debería ver para sus resultados con nombre (una tasa de incumplimiento, una AUC, un PSI, un valor p bajo un cambio conocido); el precálculo falla si un resultado cae fuera.' },
          ]}
        />
      </DocSection>
    </>
  );
}

function Contracts() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'Contract 1: what may enter', es: 'Contrato 1: lo que puede entrar' }} noRefsReason={THIS_REPO}>
        <P
          en="Eight families, one per kind of source data: scored samples, loan panels, rating histories, market series, yield curves, balance sheets, operational loss events and macro paths. Each field has its kind, unit and range; rules run across fields (an origination after its report is rejected) and across records (days past due rising more than 31 per month is flagged). Values are parsed strictly by their declared kind and never coerced. A record is accepted, rejected with the field, value, expected range and policy, flagged and counted, or excluded and counted. The declarations are exported for the web and mirrored in TypeScript."
          es="Ocho familias, una por tipo de dato fuente: muestras puntuadas, paneles de préstamos, historias de calificación, series de mercado, curvas de tasas, balances, eventos de pérdida operacional y trayectorias macro. Cada campo tiene su tipo, unidad y rango; hay reglas entre campos (una originación posterior a su reporte se rechaza) y entre registros (días de mora que suben más de 31 por mes se marcan). Los valores se leen estrictamente según su tipo declarado y nunca se fuerzan. Un registro se acepta, se rechaza con el campo, el valor, el rango esperado y la política, se marca y se cuenta, o se excluye y se cuenta. Las declaraciones se exportan para la web y se reflejan en TypeScript."
        />
      </DocSection>
      <DocSection title={{ en: 'Contract 2: what the pipeline commits', es: 'Contrato 2: lo que compromete el pipeline' }} noRefsReason={THIS_REPO}>
        <P
          en="An index of the cases; one manifest per case (its question, sources and their licences, the contract-1 report of its inputs, its expected ranges, and one entry per artifact); one models artifact per fit (the record of every rung: engine, version, licence, parameters with units, calibration map, and internals such as the points table, the EBM shape functions and the GBM partial dependence); and one artifact per variant (the outputs the views draw, the TestResult rows of the battery, the impact, the findings and the provenance). The web declares the same contract and a test reads every committed artifact against it in both directions."
          es="Un índice de los casos; un manifiesto por caso (su pregunta, sus fuentes y sus licencias, el reporte del contrato 1 de sus entradas, sus rangos esperados y una entrada por artefacto); un artefacto de modelos por ajuste (el registro de cada peldaño: motor, versión, licencia, parámetros con unidades, mapa de calibración, e interiores como la tabla de puntos, las funciones de forma del EBM y la dependencia parcial del GBM); y un artefacto por variante (las salidas que dibujan las vistas, las filas TestResult de la batería, el impacto, los hallazgos y la procedencia). La web declara el mismo contrato y una prueba lee cada artefacto comprometido contra él en ambos sentidos."
        />
        <Figure caption={t('Every source with its licence class, the licence manifest and the two contracts.', 'Cada fuente con su clase de licencia, el manifiesto de licencias y los dos contratos.')}>
          <ContractsFigure />
        </Figure>
      </DocSection>
    </>
  );
}

function DataAndLicences() {
  return (
    <>
      <DocSection title={{ en: 'The source registry', es: 'El registro de fuentes' }} noRefsReason={THIS_REPO}>
        <P
          en="Every data and scenario source the plan names is declared with its publisher, landing page, the verbatim fragment of its licence or terms, its class, the cases that read it and the questions the research could not settle at a primary page. The four classes decide everything downstream: mirror-allowed rows may be committed with attribution; from a derived-only source only aggregates, fitted parameters and results are published; a link-only or unusable source is linked from the web and never read by a case."
          es="Cada fuente de datos y de escenarios que nombra el plan se declara con su editor, su página, el fragmento literal de su licencia o sus términos, su clase, los casos que la leen y las preguntas que la investigación no pudo resolver en una fuente primaria. Las cuatro clases deciden todo lo demás: las filas de una fuente espejo pueden comprometerse con atribución; de una fuente solo de derivados se publican solo agregados, parámetros ajustados y resultados; una fuente solo enlace o inutilizable se enlaza desde la web y ningún caso la lee."
        />
      </DocSection>
      <DocSection title={{ en: 'The licence manifest and the lineage', es: 'El manifiesto de licencias y el linaje' }} noRefsReason={THIS_REPO}>
        <L
          items={[
            { en: 'The fetcher writes raw files to the device data root (an environment variable or an argument), never into the repository, and refuses a root inside it.', es: 'El descargador escribe los archivos crudos en la raíz de datos del equipo (una variable de entorno o un argumento), nunca en el repositorio, y rechaza una raíz dentro de él.' },
            { en: 'Every file is hashed while it streams; the committed licence manifest records its URL, date, class, licence text, SHA-256 and bytes, and a later fetch with other bytes fails unless the refresh is explicit.', es: 'Cada archivo se procesa con hash mientras se descarga; el manifiesto de licencias comprometido registra su URL, fecha, clase, texto de licencia, SHA-256 y bytes, y una descarga posterior con otros bytes falla salvo que la actualización sea explícita.' },
            { en: 'Every artifact carries the lineage of its inputs (source, class, file hashes) and its truth status; the export refuses an input that may only be linked, or one never fetched.', es: 'Cada artefacto lleva el linaje de sus entradas (fuente, clase, hashes de archivos) y su estado de verdad; la exportación rechaza una entrada que solo puede enlazarse, o una nunca descargada.' },
          ]}
        />
      </DocSection>
    </>
  );
}

function EnginesAndLanes() {
  return (
    <>
      <DocSection title={{ en: 'The engines', es: 'Los motores' }} noRefsReason={THIS_REPO}>
        <P
          en="The validation tests and, as the cases grow, the regulatory calculators and the reference engines come from riskvalidation, a separate package (MIT, pure NumPy and SciPy) that a validator can audit on its own; this product declares no package. The model rungs are thin, pinned wrappers over the engines the research chose: optbinning and statsmodels for the scorecard, scikit-learn for the penalised rungs and the calibration maps, InterpretML for the EBM, LightGBM and XGBoost for the monotone boosting, SHAP for the reasons, and TabPFN as an optional extra. Each one's licence is verified, and a guard fails on any AGPL, GPL or Business Source licence in the default install."
          es="Las pruebas de validación y, a medida que crecen los casos, las calculadoras regulatorias y los motores de referencia vienen de riskvalidation, un paquete aparte (MIT, NumPy y SciPy puros) que un validador puede auditar por sí solo; este producto no declara ningún paquete. Los peldaños del modelo son envoltorios delgados y fijados sobre los motores que eligió la investigación: optbinning y statsmodels para la scorecard, scikit-learn para los peldaños penalizados y los mapas de calibración, InterpretML para el EBM, LightGBM y XGBoost para el boosting monótono, SHAP para las razones, y TabPFN como extra opcional. La licencia de cada uno está verificada, y una guarda falla ante cualquier licencia AGPL, GPL o Business Source en la instalación por defecto."
        />
      </DocSection>
      <DocSection title={{ en: 'The lanes', es: 'Los carriles' }} noRefsReason={THIS_REPO}>
        <L
          items={[
            { en: 'Offline: the pipeline, canonical, the only lane that writes artifacts.', es: 'Fuera de línea: el pipeline, canónico, el único carril que escribe artefactos.' },
            { en: 'Replay: the web reads the committed artifacts. Gradient-boosting and TabPFN scores are always replayed, since ONNX Runtime Web has no tree-ensemble kernel.', es: 'Reproducción: la web lee los artefactos comprometidos. Los puntajes de gradient boosting y de TabPFN siempre se reproducen, porque ONNX Runtime Web no tiene núcleo de ensambles de árboles.' },
            { en: 'Live: the web recomputes what is light and exact from the committed artifacts: an applicant\'s scorecard and EBM scores, every light under the reader\'s policy, the decision and the IRB capital at any approval rate and LGD (C01); a portfolio\'s drift under a one-year rating matrix towards its TTC portfolio, the PD intervals at a reader\'s default correlation and the IRB risk weight under each default definition (C04); the PD curve of every calibration approach and the low-default bounds (C05); the exact size and power of the count tests for a reader\'s portfolio (C22). Parity tests hold each to the pipeline or to riskvalidation: points and scores exactly, every other number within 1e-9, every committed light under the committed policy.', es: 'En vivo: la web recalcula lo liviano y exacto desde los artefactos comprometidos: los puntajes scorecard y EBM de un solicitante, cada luz con la política del lector, la decisión y el capital IRB con cualquier tasa de aprobación y LGD (C01); la deriva de una cartera bajo una matriz anual de calificaciones hacia su cartera TTC, los intervalos de la PD con la correlación de incumplimiento del lector y el ponderador IRB con cada definición de incumplimiento (C04); la curva de PD de cada enfoque de calibración y las cotas de bajo incumplimiento (C05); el tamaño y la potencia exactos de las pruebas de conteo para la cartera del lector (C22). Pruebas de paridad sujetan cada uno al pipeline o a riskvalidation: puntos y puntajes exactos, todo otro número dentro de 1e-9, cada luz comprometida con la política comprometida.' },
            { en: 'Next: riskvalidation in the browser, in Pyodide, to re-run any test with new segments and windows. It is admitted per feature, only when its cold start and run time are measured under the gate, once the engine is published on PyPI.', es: 'Siguiente: riskvalidation en el navegador, en Pyodide, para volver a correr cualquier prueba con segmentos y ventanas nuevos. Se admite por función, solo cuando su arranque en frío y su tiempo de ejecución se miden bajo la compuerta, una vez publicado el motor en PyPI.' },
          ]}
        />
      </DocSection>
    </>
  );
}

function Gates() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'Tests and guards', es: 'Pruebas y guardas' }} noRefsReason={THIS_REPO}>
        <L
          items={[
            { en: 'Every requirement of the design document names the test or guard that fails when it is violated, and a guard fails on a requirement whose gate does not exist.', es: 'Cada requisito del documento de diseño nombra la prueba o guarda que falla cuando se viola, y una guarda falla ante un requisito cuya compuerta no existe.' },
            { en: 'The pipeline\'s tests run in a sandbox: a test that writes into the committed artifacts fails the session.', es: 'Las pruebas del pipeline corren en un entorno aislado: una prueba que escribe en los artefactos comprometidos hace fallar la sesión.' },
            { en: 'In CI, without installing the pipeline: the artifacts and their manifests agree, every artifact carries true provenance, no raw rows of a non-mirror source anywhere, the licences of the default install, one version, one deploy place, no em-dash or emoji, and every guard proven by a test that plants its failure.', es: 'En CI, sin instalar el pipeline: los artefactos y sus manifiestos coinciden, cada artefacto lleva procedencia verdadera, ninguna fila cruda de una fuente que no es espejo en ningún lugar, las licencias de la instalación por defecto, una versión, un lugar de despliegue, sin rayas largas ni emojis, y cada guarda probada por una prueba que siembra su falla.' },
          ]}
        />
      </DocSection>
      <DocSection title={{ en: 'The measured gate', es: 'La compuerta medida' }} noRefsReason={THIS_REPO}>
        <P
          en="Before a deploy, the gate of the shared shell serves the build as GitHub Pages would and walks every route, group, sub-tab, case and variant at five screen sizes, in both themes and both languages. It fails on what a reader would meet: an error, a broken link, a view that cannot be reached or clicked, a blank or undersized drawing, a view that never settles, a loop at rest, a control that changes nothing, a label cut or overlapped in a drawing (also in a wide fallback font), a decimal point on a Spanish page, a sub-tab list that scrolls away, or text below the WCAG AA contrast."
          es="Antes de un despliegue, la compuerta del shell compartido sirve la compilación como lo haría GitHub Pages y recorre cada ruta, grupo, sub-pestaña, caso y variante en cinco tamaños de pantalla, con ambos temas e idiomas. Falla ante lo que encontraría un lector: un error, un enlace roto, una vista inalcanzable o que no se puede pulsar, un dibujo vacío o demasiado pequeño, una vista que nunca se estabiliza, un ciclo en reposo, un control que no cambia nada, una etiqueta cortada o superpuesta en un dibujo (también con una fuente de reemplazo ancha), un punto decimal en una página en español, una lista de sub-pestañas que se pierde al desplazarse, o un texto bajo el contraste WCAG AA."
        />
        <Figure caption={t('How the web loads a case and keeps every view on the current selection.', 'Cómo carga la web un caso y mantiene cada vista en la selección actual.')}>
          <FlowFigure />
        </Figure>
      </DocSection>
    </>
  );
}

function Deploy() {
  return (
    <DocSection title={{ en: 'Versions and the deploy', es: 'Versiones y despliegue' }} noRefsReason={THIS_REPO}>
      <P
        en="VERSION is the only place the version is written; the pipeline, the web and the changelog read it, and a guard fails when any of them disagrees. Contraste has one deploy place, decided first: GitHub Pages with its own domain, since the repository is public and every capability is static replay or client-side compute. The deploy runs only after CI passes on main and ends by checking the live site: every route answers, a missing file answers 404, the artifact index answers JSON, and build.json names the commit that was pushed."
        es="VERSION es el único lugar donde se escribe la versión; el pipeline, la web y el registro de cambios la leen, y una guarda falla cuando alguno discrepa. Contraste tiene un único lugar de despliegue, decidido primero: GitHub Pages con su propio dominio, porque el repositorio es público y toda capacidad es reproducción estática o cálculo en el cliente. El despliegue corre solo después de que CI pasa en main y termina verificando el sitio en vivo: cada ruta responde, un archivo faltante responde 404, el índice de artefactos responde JSON, y build.json nombra el commit que se empujó."
      />
    </DocSection>
  );
}

export function Implementation() {
  const lang = useShellLang();
  const t = useT();
  return (
    <DocPage
      wide
      title={{ en: 'Implementation', es: 'Implementación' }}
      lede={t('How Contraste is built: the pipeline, the contracts, the data and its licences, the engines and lanes, the gates and the deploy.', 'Cómo está construido Contraste: el pipeline, los contratos, los datos y sus licencias, los motores y carriles, las compuertas y el despliegue.')}
    >
      <Tabs
        ariaLabel={lang === 'es' ? 'Partes de la implementación' : 'Parts of the implementation'}
        tabs={[
          { id: 'pipeline', label: t('Pipeline', 'Pipeline'), content: <Pipeline /> },
          { id: 'contracts', label: t('Contracts', 'Contratos'), content: <Contracts /> },
          { id: 'data', label: t('Data and licences', 'Datos y licencias'), content: <DataAndLicences /> },
          { id: 'engines', label: t('Engines and lanes', 'Motores y carriles'), content: <EnginesAndLanes /> },
          { id: 'gates', label: t('Gates', 'Compuertas'), content: <Gates /> },
          { id: 'deploy', label: t('Deploy', 'Despliegue'), content: <Deploy /> },
        ]}
      />
    </DocPage>
  );
}
