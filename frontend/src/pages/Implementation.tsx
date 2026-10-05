import { DocPage, DocSection } from '@fasl-work/caos-app-shell';
import { L, P, useT } from '../content/bi';

const THIS_REPO = { en: 'Describes this repository.', es: 'Describe este repositorio.' };

export function Implementation() {
  const t = useT();
  return (
    <DocPage title={{ en: 'Implementation', es: 'Implementación' }} lede={t('How the product is built: the pipeline, the contracts, the lanes, the web and the deploy.', 'Cómo está construido el producto: el pipeline, los contratos, los carriles, la web y el despliegue.')}>
      <DocSection title={{ en: 'The pipeline', es: 'El pipeline' }} noRefsReason={THIS_REPO}>
        <P
          en="The offline pipeline (data-pipeline/) runs every case of the registry through named stages: preprocess, feature extraction, train, infer, evaluate and export. The ingestion contract validates each case's inputs before anything runs: a bad value is rejected with its reason, never coerced, and an unusual one is flagged and carried into the manifest. Every random generator is seeded, so a second bake writes the same bytes."
          es="El pipeline fuera de línea (data-pipeline/) pasa cada caso del registro por etapas con nombre: preprocesamiento, extracción de atributos, entrenamiento, inferencia, evaluación y exportación. El contrato de ingesta valida las entradas de cada caso antes de que algo corra: un valor inválido se rechaza con su razón, nunca se fuerza, y uno inusual se marca y se lleva al manifiesto. Cada generador aleatorio tiene semilla, así que un segundo precálculo escribe los mismos bytes."
        />
      </DocSection>
      <DocSection title={{ en: 'The artifacts', es: 'Los artefactos' }} noRefsReason={THIS_REPO}>
        <P
          en="The pipeline writes the artifact contract into data/derived/, and the repository commits it: an index of the cases (with the case the App opens on), one manifest per case (parameters, seed, engine and version, the artifact, the lane verdict and the evaluation metrics), and one trace per case (200 points of the trajectory and its summary). Every reader-facing string in them is bilingual."
          es="El pipeline escribe el contrato de artefactos en data/derived/, y el repositorio lo compromete: un índice de los casos (con el caso en que abre la App), un manifiesto por caso (parámetros, semilla, motor y versión, el artefacto, el veredicto de carril y las métricas de evaluación) y una traza por caso (200 puntos de la trayectoria y su resumen). Cada texto para el lector es bilingüe."
        />
        <P
          en="The web declares the same contract in TypeScript, and a test reads every committed artifact against that declaration in both directions: a key the pipeline writes and the web does not read fails, a key the web reads and the pipeline does not write fails, and a boolean where a number is expected fails."
          es="La web declara el mismo contrato en TypeScript, y una prueba lee cada artefacto comprometido contra esa declaración en ambas direcciones: falla una clave que el pipeline escribe y la web no lee, falla una clave que la web lee y el pipeline no escribe, y falla un booleano donde se espera un número."
        />
      </DocSection>
      <DocSection title={{ en: 'The lanes', es: 'Los carriles' }} noRefsReason={THIS_REPO}>
        <L
          items={[
            { en: 'Offline: the Python pipeline, run on a workstation; its results are committed.', es: 'Fuera de línea: el pipeline en Python, corrido en una estación de trabajo; sus resultados se comprometen.' },
            { en: 'Replay: the web reads the committed artifacts; nothing is recomputed.', es: 'Reproducción: la web lee los artefactos comprometidos; nada se recalcula.' },
            { en: 'Live: the TypeScript engine re-runs a case in the browser with the reader\'s values. A parity test holds it to the baked traces, so the two engines cannot drift apart unnoticed.', es: 'En vivo: el motor en TypeScript vuelve a correr un caso en el navegador con los valores del lector. Una prueba de paridad lo sujeta a las trazas precalculadas, así que los dos motores no pueden separarse sin que se note.' },
          ]}
        />
      </DocSection>
      <DocSection title={{ en: 'The web', es: 'La web' }} noRefsReason={THIS_REPO}>
        <P
          en="The frontend is built on the shared CAOS app shell: the header, the theme and language toggles, the workbench with its rail and instrument, the documentation page, the chart, and the measured gate. A build copies exactly the artifacts the index declares into the site (and fails on a missing one), fetches them with the version in the address so a release never reads an old cached file, writes every route as its own page so a deep link answers directly, and writes build.json with the version and the commit."
          es="El frontend está construido sobre el shell compartido de las apps CAOS: el encabezado, los selectores de tema e idioma, el banco de trabajo con su panel e instrumento, la página de documentación, el gráfico y la compuerta medida. Una compilación copia al sitio exactamente los artefactos que declara el índice (y falla si falta uno), los pide con la versión en la dirección para que una versión nueva nunca lea un archivo antiguo en caché, escribe cada ruta como su propia página para que un enlace directo responda, y escribe build.json con la versión y el commit."
        />
        <P
          en="Before a deploy, the gate serves the build as GitHub Pages would and walks every route, tab and case at five screen sizes, in both themes and both languages, and fails on what a reader would meet: an error, a broken link, something that cannot be scrolled to or clicked, a blank or undersized drawing, a view that never settles, a loop at rest, or a control that changes nothing."
          es="Antes de un despliegue, la compuerta sirve la compilación como lo haría GitHub Pages y recorre cada ruta, pestaña y caso en cinco tamaños de pantalla, con ambos temas y ambos idiomas, y falla ante lo que encontraría un lector: un error, un enlace roto, algo a lo que no se puede llegar ni hacer clic, un dibujo en blanco o demasiado pequeño, una vista que nunca se estabiliza, un ciclo en reposo o un control que no cambia nada."
        />
      </DocSection>
      <DocSection title={{ en: 'Versions and deploy', es: 'Versiones y despliegue' }} noRefsReason={THIS_REPO}>
        <P
          en="VERSION is the only place the version is written; the pipeline, the web and the changelog read it, and a guard fails when any of them disagrees or falls behind the latest tag. Each product has one deploy place, decided at instantiation and written in deploy/TARGET; this template deploys to GitHub Pages, and the deploy job checks the live site afterwards: every route answers, a missing file answers 404, and build.json names the commit that was pushed."
          es="VERSION es el único lugar donde se escribe la versión; el pipeline, la web y el registro de cambios la leen, y una guarda falla cuando alguno discrepa o queda detrás de la última etiqueta. Cada producto tiene un único lugar de despliegue, decidido al instanciar y escrito en deploy/TARGET; esta plantilla despliega en GitHub Pages, y el trabajo de despliegue verifica después el sitio en vivo: cada ruta responde, un archivo faltante responde 404, y build.json nombra el commit que se empujó."
        />
      </DocSection>
    </DocPage>
  );
}
