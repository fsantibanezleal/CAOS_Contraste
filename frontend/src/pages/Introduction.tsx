import { Cite, DocPage, DocSection } from '@fasl-work/caos-app-shell';
import product from '../../../product.json';
import { L, P, useT } from '../content/bi';

export function Introduction() {
  const t = useT();
  return (
    <DocPage
      title={{ en: 'Introduction', es: 'Introducción' }}
      lede={t(product.tagline.en, product.tagline.es)}
    >
      <DocSection title={{ en: 'What this product is', es: 'Qué es este producto' }} refs={['km1927', 'hethcote2000']}>
        <P
          en={<>This is the CAOS product archetype, built so that every part of a product is present and working on the first day: an offline pipeline that bakes cases, committed artifacts that the web replays, a live engine that re-runs a case in the browser, a workbench on the shared shell, five documentation pages, and a build that is measured before it is deployed. The domain is a placeholder: the classical SIR epidemic model <Cite id="km1927" />, small enough to read in one sitting and rich enough to exercise every lane.</>}
          es={<>Este es el arquetipo de producto CAOS, construido para que cada parte de un producto esté presente y funcionando desde el primer día: un pipeline fuera de línea que precalcula casos, artefactos comprometidos que la web reproduce, un motor en vivo que vuelve a correr un caso en el navegador, un banco de trabajo sobre el shell compartido, cinco páginas de documentación y una compilación que se mide antes de desplegarse. El dominio es un marcador: el modelo epidémico SIR clásico <Cite id="km1927" />, lo bastante pequeño para leerse de una vez y lo bastante rico para ejercitar cada carril.</>}
        />
        <P
          en={<>A product instantiated from this repository replaces the model, the cases and the content with its own, and keeps the structure: the contracts, the lanes, the workbench, the pages and the gates. The model itself is standard; Hethcote&apos;s review <Cite id="hethcote2000" /> covers it and its extensions.</>}
          es={<>Un producto instanciado desde este repositorio reemplaza el modelo, los casos y el contenido por los suyos, y conserva la estructura: los contratos, los carriles, el banco de trabajo, las páginas y las compuertas. El modelo en sí es estándar; la revisión de Hethcote <Cite id="hethcote2000" /> lo cubre junto con sus extensiones.</>}
        />
      </DocSection>
      <DocSection title={{ en: 'How to read the App', es: 'Cómo leer la App' }} noRefsReason={{ en: 'Describes this interface.', es: 'Describe esta interfaz.' }}>
        <P
          en="The App is one workbench. The rail on the left holds what you choose and what you read: the case, its variant, the parameters of the live engine, and the live values. The instrument on the right holds the views of the case, grouped by the question they answer."
          es="La App es un banco de trabajo. El panel de la izquierda contiene lo que se elige y lo que se lee: el caso, su variante, los parámetros del motor en vivo y los valores en vivo. El instrumento de la derecha contiene las vistas del caso, agrupadas por la pregunta que responden."
        />
        <L
          items={[
            { en: 'Dynamics: the three compartments over time, the live run solid and the committed replay dashed.', es: 'Dinámica: los tres compartimentos en el tiempo, la corrida en vivo continua y la reproducción comprometida segmentada.' },
            { en: 'Validation: the two engines compared on the baked case, and the run compared with the final-size relation.', es: 'Validación: los dos motores comparados en el caso precalculado, y la corrida comparada con la relación de tamaño final.' },
            { en: 'Compare immunisation: the case re-run with a share of the population immune from the start.', es: 'Comparar inmunización: el caso vuelto a correr con una fracción de la población inmune desde el inicio.' },
            { en: 'Context: the case, its parameters, the model and how to read each view.', es: 'Contexto: el caso, sus parámetros, el modelo y cómo leer cada vista.' },
          ]}
        />
        <P
          en="Every view carries two badges: its lane (live, computed in your browser; replay, read from a committed artifact; offline, computed by the pipeline and shown as is) and its data (synthetic, real or published). A view still showing an earlier selection says so while it recomputes. A case can be linked directly with ?case= followed by its identifier."
          es="Cada vista lleva dos insignias: su carril (en vivo, calculado en el navegador; reproducción, leído de un artefacto comprometido; fuera de línea, calculado por el pipeline y mostrado tal cual) y sus datos (sintéticos, reales o publicados). Una vista que todavía muestra una selección anterior lo indica mientras recalcula. Un caso se puede enlazar directamente con ?case= seguido de su identificador."
        />
      </DocSection>
      <DocSection title={{ en: 'The six pages', es: 'Las seis páginas' }} noRefsReason={{ en: 'Describes this site.', es: 'Describe este sitio.' }}>
        <L
          items={[
            { en: 'App: the workbench, the landing page.', es: 'App: el banco de trabajo, la página de inicio.' },
            { en: 'Introduction: what the product is and how to read it (this page).', es: 'Introducción: qué es el producto y cómo leerlo (esta página).' },
            { en: 'Methodology: the model, its threshold, its final size and the numerical scheme, with their sources.', es: 'Metodología: el modelo, su umbral, su tamaño final y el esquema numérico, con sus fuentes.' },
            { en: 'Implementation: the pipeline, the contracts, the lanes, the web and the deploy.', es: 'Implementación: el pipeline, los contratos, los carriles, la web y el despliegue.' },
            { en: 'Experiments: every case, read from its artifacts, against the theory.', es: 'Experimentos: cada caso, leído desde sus artefactos, contra la teoría.' },
            { en: 'Benchmark: what each case costs, baked and live, against its budgets.', es: 'Benchmark: lo que cuesta cada caso, precalculado y en vivo, contra sus presupuestos.' },
          ]}
        />
      </DocSection>
      <DocSection title={{ en: 'Making a product from it', es: 'Hacer un producto a partir de él' }} noRefsReason={{ en: 'Describes this repository.', es: 'Describe este repositorio.' }}>
        <P
          en="A new product starts from this repository as a GitHub template. scripts/instantiate.py names it, picks its single deploy place (GitHub Pages or the VPS), sets its licence and visibility, removes the template sentinel and runs the pipeline, the tests and the build once. From then on the residue guard fails the build while any part of the example remains."
          es="Un producto nuevo parte de este repositorio como plantilla de GitHub. scripts/instantiate.py le da nombre, elige su único lugar de despliegue (GitHub Pages o el VPS), fija su licencia y su visibilidad, elimina el centinela de la plantilla y corre una vez el pipeline, las pruebas y la compilación. Desde entonces, la guarda de residuos hace fallar la compilación mientras quede alguna parte del ejemplo."
        />
      </DocSection>
    </DocPage>
  );
}
