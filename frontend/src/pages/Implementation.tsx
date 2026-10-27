// How Contraste is built, in six groups of topics (ADR-0017 as amended: at least eight topics, at most six groups):
// the pipeline, the contracts, the data and its licences, the engines and the lanes, the gates, and the deploy.
// Transcribed from SDD sections 2, 3, 7 and 8 and from the feature designs in docs/design/features/.
import { Callout, DocPage, DocSection, Figure, TabGroups, useShellLang } from '@fasl-work/caos-app-shell';
import { ContractsFigure, FlowFigure, OverviewFigure } from '../architecture/figures';
import { Equation, L, P, T, useT } from '../content/bi';
import { ReadinessTable } from '../readiness/ReadinessTable';

const THIS_REPO = { en: 'Describes this repository.', es: 'Describe este repositorio.' };

function Pipeline() {
  const t = useT();
  return (
    <>
      <DocSection area="architecture" title={{ en: 'The stages', es: 'Las etapas' }} noRefsReason={THIS_REPO}>
        <P
          en="The offline pipeline (data-pipeline/, invoked by path, never installed) runs each case through named stages: ingest (a fetched source through contract 1), split (the leakage-safe partition), the fit of every rung, evaluate (the battery and the outputs the views draw) and export (contract 2). It is the only lane that writes artifacts, it runs on a workstation, and never in CI or in the browser. Every generator is seeded, so a second bake of the same release writes the same bytes."
          es="La cadena de cálculo fuera de línea (data-cadena de cálculo/, invocado por ruta, nunca instalado) pasa cada caso por etapas con nombre: ingesta (una fuente descargada a través del contrato 1), partición (la partición sin fugas), el ajuste de cada peldaño, evaluación (la batería y las salidas que dibujan las vistas) y exportación (contrato 2). Es el único carril que escribe artefactos, corre en una estación de trabajo, y nunca en CI ni en el navegador. Todo generador tiene semilla, así un segundo precálculo de la misma versión escribe los mismos bytes."
        />
        <Figure caption={t('Sources, the offline pipeline, the committed artifacts and the web.', 'Fuentes, la cadena de cálculo fuera de línea, los artefactos versionados y la web.')}>
          <OverviewFigure />
        </Figure>
      </DocSection>
      <DocSection area="reproducibility" title={{ en: 'The split and the expectations', es: 'La partición y las expectativas' }} noRefsReason={THIS_REPO}>
        <P
          en="A result is reproduced by baking its case again: every generator is seeded, so a second bake of the same release writes the same bytes; every file is hashed while it streams, so a source that changed is caught by its hash; the version is written in one place; and the expected range of each named result is declared before the bake and checked after it. A reader who doubts a number can recompute it from the committed artifacts or from the source."
          es="Un resultado se reproduce generando de nuevo su caso: cada generador tiene semilla, así que una segunda generación de la misma versión escribe los mismos bytes; cada archivo se le calcula la huella mientras se descarga, así que una fuente que cambió se detecta por su huella; la versión se escribe en un solo lugar; y el rango esperado de cada resultado nombrado se declara antes de la generación y se verifica después. Quien dude de un número puede recalcularlo desde los artefactos versionados o desde la fuente."
        />
        <Callout variant="note" title={<T en="What a rerun does not promise" es="Lo que una repetición no promete" />}>
          <T
            en="Same bytes need the same release, the same seeds and the same source files; a rerun on a refreshed source is a new bake, and its differences are the finding."
            es="Los mismos bytes exigen la misma versión, las mismas semillas y los mismos archivos fuente; una repetición sobre una fuente actualizada es una generación nueva, y sus diferencias son el hallazgo."
          />
        </Callout>
        <L
          items={[
            { en: 'A locked stratified holdout of 30%; a calibration slice of 20% of the rest, disjoint from it; the training slice, where every binning, WoE, rule, hyperparameter and fit is learned.', es: 'Una muestra reservada estratificada del 30 %; un tramo de calibración del 20 % del resto, disjunto de ella; el tramo de entrenamiento, donde se aprende todo tramado, WoE, regla, hiperparámetro y ajuste.' },
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
      <DocSection area="contract" title={{ en: 'Contract 2: what the pipeline commits', es: 'Contrato 2: lo que versiona la cadena de cálculo' }} noRefsReason={THIS_REPO}>
        <P
          en="An index of the cases; one manifest per case (its question, sources and their licences, the contract-1 report of its inputs, its expected ranges, and one entry per artifact); one models artifact per fit (the record of every rung: engine, version, licence, parameters with units, calibration map, and internals such as the points table, the EBM shape functions and the GBM partial dependence); and one artifact per variant (the outputs the views draw, the test-result rows of the battery, the impact, the findings and the provenance). The web declares the same contract and a test reads every committed artifact against it in both directions."
          es="Un índice de los casos; un manifiesto por caso (su pregunta, sus fuentes y sus licencias, el reporte del contrato 1 de sus entradas, sus rangos esperados y una entrada por artefacto); un artefacto de modelos por ajuste (el registro de cada peldaño: motor, versión, licencia, parámetros con unidades, mapa de calibración, e interiores como la tabla de puntos, las funciones de forma del EBM y la dependencia parcial del GBM); y un artefacto por variante (las salidas que dibujan las vistas, las filas de resultados de prueba de la batería, el impacto, los hallazgos y la procedencia). La web declara el mismo contrato y una prueba lee cada artefacto versionado contra él en ambos sentidos."
        />
        <table className="caos-table ct-wrap-head" data-state="ready">
          <thead>
            <tr>
              <th className="caos-col-text">{t('Document', 'Documento')}</th>
              <th className="caos-col-text">{t('Where it is committed', 'Dónde se versiona')}</th>
              <th className="caos-col-text">{t('Schema', 'Esquema')}</th>
            </tr>
          </thead>
          <tbody>
            {[
              [t('Case index', 'Índice de casos'), 'data/derived/manifests/index.json', 'common/case-index.schema.json'],
              [t('Case manifest', 'Manifiesto del caso'), 'data/derived/manifests/<case>.json', 'common/case-manifest.schema.json'],
              [t('Variant artifact', 'Artefacto de variante'), 'data/derived/<case>/<variant>.json', 'common/variant-envelope.schema.json'],
              [t('Models artifact', 'Artefacto de modelos'), 'data/derived/<case>/models-<fit>.json', 'common/models-envelope.schema.json'],
              [t('Readiness', 'Disponibilidad'), 'data/derived/readiness.json', 'common/readiness.schema.json'],
            ].map(([what, where, schema]) => (
              <tr key={where}>
                <td className="caos-col-text">{what}</td>
                <td className="caos-col-text" style={{ overflowWrap: 'anywhere' }}><code>{where}</code></td>
                <td className="caos-col-text" style={{ overflowWrap: 'anywhere' }}><code>{schema}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
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
          es="Cada fuente de datos y de escenarios que nombra el plan se declara con su editor, su página, el fragmento literal de su licencia o sus términos, su clase, los casos que la leen y las preguntas que la investigación no pudo resolver en una fuente primaria. Las cuatro clases deciden todo lo demás: las filas de una fuente espejo pueden versionarse con atribución; de una fuente solo de derivados se publican solo agregados, parámetros ajustados y resultados; una fuente solo enlace o inutilizable se enlaza desde la web y ningún caso la lee."
        />
      </DocSection>
      <DocSection title={{ en: 'The licence manifest and the lineage', es: 'El manifiesto de licencias y el linaje' }} noRefsReason={THIS_REPO}>
        <L
          items={[
            { en: 'The fetcher writes raw files to the device data root (an environment variable or an argument), never into the repository, and refuses a root inside it.', es: 'El descargador escribe los archivos crudos en la raíz de datos del equipo (una variable de entorno o un argumento), nunca en el repositorio, y rechaza una raíz dentro de él.' },
            { en: 'Every file is hashed while it streams; the committed licence manifest records its URL, date, class, licence text, SHA-256 and bytes, and a later fetch with other bytes fails unless the refresh is explicit.', es: 'Cada archivo se le calcula la huella mientras se descarga; el manifiesto de licencias versionado registra su URL, fecha, clase, texto de licencia, SHA-256 y bytes, y una descarga posterior con otros bytes falla salvo que la actualización sea explícita.' },
            { en: 'Every artifact carries the lineage of its inputs (source, class, file hashes) and its truth status; the export refuses an input that may only be linked, or one never fetched.', es: 'Cada artefacto lleva el linaje de sus entradas (fuente, clase, huellas de archivos) y su estado de verdad; la exportación rechaza una entrada que solo puede enlazarse, o una nunca descargada.' },
          ]}
        />
      </DocSection>
    </>
  );
}

function Engines() {
  const t = useT();
  return (
    <DocSection area="engine" title={{ en: 'The engines', es: 'Los motores' }} noRefsReason={THIS_REPO}>
      <P
        en="The validation tests and, as the cases grow, the regulatory calculators and the reference engines come from riskvalidation, a separate package (MIT, pure NumPy and SciPy) that a validator can audit on its own; this product only calls it. The web holds a port of what is light and exact, and a test compares the port with the pipeline's own numbers on every committed sample, so a live view can never drift from the artifact it replays."
        es="Las pruebas de validación y, a medida que crecen los casos, las calculadoras regulatorias y los motores de referencia vienen de riskvalidation, un paquete aparte (MIT, NumPy y SciPy puros) que un validador puede auditar por sí solo; este producto solo lo invoca. La web contiene una adaptación de lo que es liviano y exacto, y una prueba compara la adaptación con los números propios de la cadena de cálculo en cada muestra versionada, de modo que una vista en vivo nunca se aparta del artefacto que reproduce."
      />
      <P
        en="One computation shows the pattern: the exact size and power of the tests that see a portfolio only through its default count integrate a binomial tail over the systematic factor, on a Gauss-Hermite rule of 256 nodes, in the pipeline and in the browser alike, and the two agree to the digits the artifact keeps."
        es="Un cálculo muestra el patrón: el tamaño y la potencia exactos de las pruebas que ven una cartera solo a través de su conteo de incumplimientos integran una cola binomial sobre el factor sistemático, con una regla de Gauss-Hermite de 256 nodos, en la cadena de cálculo y en el navegador por igual, y ambos concuerdan hasta los dígitos que conserva el artefacto."
      />
      <Equation
        tex={String.raw`P(\text{${t('reject', 'rechazo')}}) = \int \Pr\big[\mathrm{Bin}(n, p(x)) \ge k^*\big]\,\varphi(x)\,dx, \qquad p(x) = \Phi\!\left(\frac{\Phi^{-1}(\pi) - \sqrt{\rho}\,x}{\sqrt{1-\rho}}\right)`}
        caption={t('The one-factor mixture: n the number of obligors, k* the critical default count, π the true PD, ρ the true asset correlation, φ the standard normal density and Φ its distribution function.', 'La mezcla de un factor: n el número de deudores, k* el conteo crítico de incumplimientos, π la PD verdadera, ρ la correlación de activos verdadera, φ la densidad normal estándar y Φ su función de distribución.')}
      />
      <Callout variant="honest" title={<T en="What the engine does not do" es="Lo que el motor no hace" />}>
        <T
          en="The tree-ensemble scores (gradient boosting, TabPFN) are replayed, never recomputed in the browser, because ONNX Runtime Web has no tree-ensemble kernel; and a port that cannot be compared with the pipeline is not admitted."
          es="Los puntajes de ensambles de árboles (potenciación del gradiente, TabPFN) se reproducen, nunca se recalculan en el navegador, porque ONNX Runtime Web no tiene un núcleo de ensambles de árboles; y una adaptación que no se pueda comparar con la cadena de cálculo no se admite."
        />
      </Callout>
    </DocSection>
  );
}

function Lanes() {
  return (
    <DocSection area="lanes" title={{ en: 'The lanes', es: 'Los carriles' }} noRefsReason={THIS_REPO}>
      <P
        en="Every view says where its number was computed. The offline lane is the pipeline: canonical, run on a workstation, and the only lane that writes artifacts. The replay lane is the web reading what the pipeline committed, with no computation of its own beyond formatting. The live lane is the web recomputing from those committed artifacts what is light and exact, so that a reader's choice moves a number immediately."
        es="Cada vista dice dónde se calculó su número. El carril fuera de línea es la cadena de cálculo: canónica, se ejecuta en una estación de trabajo y es el único carril que escribe artefactos. El carril de reproducción es la web leyendo lo que la cadena de cálculo versionó, sin más cómputo propio que el formato. El carril en vivo es la web recalculando desde esos artefactos versionados lo que es liviano y exacto, de modo que la elección del lector mueve un número al instante."
      />
      <P
        en="A feature is admitted to the live lane only when its cold start and its run time are measured under the gate and its result is compared with the pipeline's; anything heavier, and everything that depends on a trained ensemble, stays in the replay lane. The live lane is TypeScript ports of the engine's calculators, each held to the engine by a parity test. riskvalidation is published on PyPI and its core needs only NumPy and SciPy, so Pyodide could install it, but Pyodide is admitted only by measurement, feature by feature; no such measurement exists and none is planned."
        es="Una funcionalidad se admite en el carril en vivo solo cuando su arranque en frío y su tiempo de ejecución se miden bajo la compuerta y su resultado se compara con el de la cadena de cálculo; todo lo más pesado, y todo lo que depende de un ensamble entrenado, queda en el carril de reproducción. El carril en vivo son versiones en TypeScript de los calculadores del motor, cada una sujeta al motor por una prueba de paridad. riskvalidation está publicado en PyPI y su núcleo solo necesita NumPy y SciPy, así que Pyodide podría instalarlo, pero Pyodide se admite solo por medición, funcionalidad por funcionalidad; esa medición no existe y no hay ninguna planeada."
      />
      <L
        items={[
          { en: 'Offline: the pipeline, canonical, the only lane that writes artifacts.', es: 'Fuera de línea: la cadena de cálculo, canónica, el único carril que escribe artefactos.' },
          { en: 'Replay: the web reads the committed artifacts. Gradient-boosting and TabPFN scores are always replayed, since ONNX Runtime Web has no tree-ensemble kernel.', es: 'Reproducción: la web lee los artefactos versionados. Los puntajes de potenciación del gradiente y TabPFN siempre se reproducen, porque ONNX Runtime Web no tiene un núcleo de ensambles de árboles.' },
          { en: "Live: the web recomputes what is light and exact from the committed artifacts: an applicant's scorecard and EBM scores, every light under the reader's policy, the decision and the IRB capital at any approval rate.", es: 'En vivo: la web recalcula lo que es liviano y exacto desde los artefactos versionados: las puntuaciones de la tarjeta de puntuación y EBM de un solicitante, cada luz bajo la política del lector, la decisión y el capital IRB a cualquier tasa de aprobación.' },
        ]}
      />
    </DocSection>
  );
}

function Readiness() {
  const t = useT();
  return (
    <DocSection title={{ en: 'What is real in this build', es: 'Qué es real en esta versión' }} noRefsReason={THIS_REPO}>
      <P
        en="The pipeline writes a readiness document beside the data: for every row of the contract catalog it says whether the build is available, partial, stale, provided by a provider, training or missing, with the provenance and a reason in both languages. Every view reads its note from this document and never decides a state itself: a case that is planned and not built yet is listed as such and is shown as not available yet, never as an empty chart."
        es="La cadena de cálculo escribe un documento de disponibilidad junto a los datos: para cada fila del catálogo de contratos dice si la versión está disponible, parcial, desactualizada, provista por un proveedor, en entrenamiento o faltante, con la procedencia y una razón en ambos idiomas. Cada vista lee su nota de este documento y nunca decide un estado por sí misma: un caso planificado y aún no construido figura como tal y se muestra como aún no disponible, nunca como un gráfico vacío."
      />
      <ReadinessTable />
      <p className="ct-note">{t('Read from the readiness document served with the site.', 'Leído del documento de disponibilidad que sirve el sitio.')}</p>
    </DocSection>
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
            { en: 'The pipeline\'s tests run in a sandbox: a test that writes into the committed artifacts fails the session.', es: 'Las pruebas de la cadena de cálculo corren en un entorno aislado: una prueba que escribe en los artefactos versionados hace fallar la sesión.' },
            { en: 'In CI, without installing the pipeline: the artifacts and their manifests agree, every artifact carries true provenance, no raw rows of a non-mirror source anywhere, the licences of the default install, one version, one deploy place, no em-dash or emoji, and every guard proven by a test that plants its failure.', es: 'En CI, sin instalar la cadena de cálculo: los artefactos y sus manifiestos coinciden, cada artefacto lleva procedencia verdadera, ninguna fila cruda de una fuente que no es espejo en ningún lugar, las licencias de la instalación por defecto, una versión, un lugar de despliegue, sin rayas largas ni emojis, y cada guarda probada por una prueba que siembra su falla.' },
          ]}
        />
      </DocSection>
      <DocSection title={{ en: 'The measured gate', es: 'La compuerta medida' }} noRefsReason={THIS_REPO}>
        <P
          en="Before a deploy, the gate of the shared shell serves the build as GitHub Pages would and walks every route, group, sub-tab, case and variant at five screen sizes, in both themes and both languages. It fails on what a reader would meet: an error, a broken link, a view that cannot be reached or clicked, a blank or undersized drawing, a view that never settles, a loop at rest, a control that changes nothing, a label cut or overlapped in a drawing (also in a wide fallback font), a decimal point on a Spanish page, a sub-tab list that scrolls away, or text below the WCAG AA contrast."
          es="Antes de un despliegue, la compuerta del armazón compartido de la interfaz sirve la compilación como lo haría GitHub Pages y recorre cada ruta, grupo, sub-pestaña, caso y variante en cinco tamaños de pantalla, con ambos temas e idiomas. Falla ante lo que encontraría un lector: un error, un enlace roto, una vista inalcanzable o que no se puede pulsar, un dibujo vacío o demasiado pequeño, una vista que nunca se estabiliza, un ciclo en reposo, un control que no cambia nada, una etiqueta cortada o superpuesta en un dibujo (también con una fuente de reemplazo ancha), un punto decimal en una página en español, una lista de sub-pestañas que se pierde al desplazarse, o un texto bajo el contraste WCAG AA."
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
    <DocSection area="deployment" title={{ en: 'Versions and the deploy', es: 'Versiones y despliegue' }} noRefsReason={THIS_REPO}>
      <P
        en="VERSION is the only place the version is written; the pipeline, the web and the changelog read it, and a guard fails when any of them disagrees. Contraste has one deploy place, decided first: GitHub Pages with its own domain, since the repository is public and every capability is static replay or client-side compute. The deploy runs only after CI passes on main and ends by checking the live site: every route answers, a missing file answers 404, the artifact index answers JSON, and build.json names the commit that was pushed."
        es="VERSION es el único lugar donde se escribe la versión; la cadena de cálculo, la web y el registro de cambios la leen, y una guarda falla cuando alguno discrepa. Contraste tiene un único lugar de despliegue, decidido primero: GitHub Pages con su propio dominio, porque el repositorio es público y toda capacidad es reproducción estática o cálculo en el cliente. El despliegue corre solo después de que CI pasa en main y termina verificando el sitio en vivo: cada ruta responde, un archivo faltante responde 404, el índice de artefactos responde JSON, y build.json nombra la versión del repositorio que se publicó."
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
      lede={t(
        'How Contraste is built: the pipeline, the contracts, the data and its licences, the engines, the lanes, what is real in this build, the gates and the deploy, each in its own topic with the exact algorithm, the contract or the rule it follows.',
        'Cómo está construido Contraste: la cadena de cálculo, los contratos, los datos y sus licencias, los motores, los carriles, qué es real en esta versión, las compuertas y el despliegue, cada uno en su propio tema con el algoritmo exacto, el contrato o la regla que sigue.',
      )}
    >
      <TabGroups
        ariaLabel={lang === 'es' ? 'Partes de la implementación' : 'Parts of the implementation'}
        groups={[
          {
            id: 'build',
            label: t('How is a case built?', '¿Cómo se construye un caso?'),
            tabs: [
              { id: 'pipeline', label: t('Pipeline', 'Cadena de cálculo'), content: <Pipeline /> },
              { id: 'contracts', label: t('Contracts', 'Contratos'), content: <Contracts /> },
              { id: 'data', label: t('Data and licences', 'Datos y licencias'), content: <DataAndLicences /> },
            ],
          },
          {
            id: 'run',
            label: t('What runs where?', '¿Qué corre dónde?'),
            tabs: [
              { id: 'engines', label: t('Engines', 'Motores'), content: <Engines /> },
              { id: 'lanes', label: t('Lanes', 'Carriles'), content: <Lanes /> },
              { id: 'readiness', label: t('Readiness', 'Disponibilidad'), content: <Readiness /> },
            ],
          },
          {
            id: 'ship',
            label: t('How is it checked and shipped?', '¿Cómo se verifica y se publica?'),
            tabs: [
              { id: 'gates', label: t('Gates', 'Compuertas'), content: <Gates /> },
              { id: 'deploy', label: t('Deploy', 'Despliegue'), content: <Deploy /> },
            ],
          },
        ]}
      />
    </DocPage>
  );
}
