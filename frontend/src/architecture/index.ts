// The architecture modal (ADR-0058): five tabs, each an inline SVG (imported with ?raw, so it reads the page's
// theme tokens) that carries both languages, and a body in both languages. The shell validates this on mount: at
// least five tabs, inline SVG only, only defined tokens, no hex colours, both languages.
import type { ArchitectureConfig } from '@fasl-work/caos-app-shell';
import app from './01-the-app.svg?raw';
import lanes from './02-lanes.svg?raw';
import flow from './03-web-flow.svg?raw';
import validation from './04-the-validation.svg?raw';
import contracts from './05-data-contracts.svg?raw';

export const SVG = { app, lanes, flow, validation, contracts };

export const architecture: ArchitectureConfig = {
  tabs: [
    {
      id: 'app',
      en: 'The app',
      es: 'La app',
      svg: app,
      body_en:
        'One workbench: the rail holds the case, its variant and the live inputs in three sections (the decision, the policy, one applicant); the instrument holds six groups, named for the validator\'s question: Model, Validation, Impact, Findings, Variants and Context.',
      body_es:
        'Un banco de trabajo: el panel contiene el caso, su variante y las entradas en vivo en tres secciones (la decisión, la política, un solicitante); el instrumento contiene seis grupos, nombrados por la pregunta del validador: Modelo, Validación, Impacto, Hallazgos, Variantes y Contexto.',
    },
    {
      id: 'lanes',
      en: 'Lanes',
      es: 'Carriles',
      svg: lanes,
      body_en:
        'Offline, the Python pipeline fits every rung on a leakage-safe split and runs the battery with the engine riskvalidation; it is the only lane that writes artifacts. The web replays them, and recomputes live only what is light and held to the pipeline by a parity test: an applicant\'s additive scores, the lights under the reader\'s policy, and the decision at any approval rate.',
      body_es:
        'Fuera de línea, el pipeline en Python ajusta cada peldaño en una partición sin fugas y corre la batería con el motor riskvalidation; es el único carril que escribe artefactos. La web los reproduce, y recalcula en vivo solo lo liviano y sujeto al pipeline por una prueba de paridad: los puntajes aditivos de un solicitante, las luces con la política del lector, y la decisión con cualquier tasa de aprobación.',
    },
    {
      id: 'flow',
      en: 'Web flow',
      es: 'Flujo web',
      svg: flow,
      body_en:
        'The index names the cases; a case loads its manifest, then the models artifact of its fit and the artifact of the chosen variant, each once. Every view is drawn for the key of the selection, so a view behind the rail says so. Before a deploy the measured gate walks every route, group, case and variant.',
      body_es:
        'El índice nombra los casos; un caso carga su manifiesto, luego el artefacto de modelos de su ajuste y el de la variante elegida, cada uno una vez. Cada vista se dibuja para la clave de la selección, así una vista atrasada lo indica. Antes de desplegar, la compuerta medida recorre cada ruta, grupo, caso y variante.',
    },
    {
      id: 'validation',
      en: 'The validation',
      es: 'La validación',
      svg: validation,
      body_en:
        'The ladder runs from anchors to the state of the art; the battery reads discrimination, the level and the fit of the calibration, and stability, as the ECB 2019 instructions and BCBS WP14 define them; findings follow a stated severity policy and cite their evidence; the impact compares the champion and the challenger at the same approval rate.',
      body_es:
        'La escalera va de los anclajes al estado del arte; la batería lee la discriminación, el nivel y el ajuste de la calibración, y la estabilidad, como las definen las instrucciones del BCE de 2019 y el WP14 del BCBS; los hallazgos siguen una política de severidad declarada y citan su evidencia; el impacto compara al campeón y al retador con la misma tasa de aprobación.',
    },
    {
      id: 'contracts',
      en: 'Data and contracts',
      es: 'Datos y contratos',
      svg: contracts,
      body_en:
        'Every source carries its licence class; the fetcher hashes every file into the licence manifest; contract 1 decides what may enter, record by record; contract 2 is what the pipeline commits, and its export refuses any artifact whose lineage includes a source that may only be linked.',
      body_es:
        'Cada fuente lleva su clase de licencia; el descargador registra el hash de cada archivo en el manifiesto de licencias; el contrato 1 decide lo que puede entrar, registro por registro; el contrato 2 es lo que el pipeline compromete, y su exportación rechaza todo artefacto cuyo linaje incluya una fuente que solo puede enlazarse.',
    },
  ],
};
