// The publications of Contraste on the Introduction's technical view (CAOS_MANAGE GUIDE R-C4, conventions/method-tiers-and-manuscripts.md
// section 2: the Introduction's technical view links the concept DOIs). The list is product.json's `manuscripts`, so a new version
// or a new title is shown the day product.json carries it. The internal claim ids an entry covers are never shown (R-B6); a title is
// the published English title, in a span marked lang="en" and translate="no" (a title is not translated, and the Spanish number checks skip it).
import { DocSection } from '@fasl-work/caos-app-shell';
import product from '../../../product.json';
import { P, T } from '../content/bi';

export interface Publication {
  kind: string;
  concept_doi: string;
  title: string;
  version: string;
}

/** The technical report first, then the manuscripts in product.json's order. */
export const PUBLICATIONS: Publication[] = [...(product.manuscripts as Publication[])].sort(
  (a, b) => Number(b.kind === 'technical-report') - Number(a.kind === 'technical-report'),
);

export function Publications() {
  return (
    <DocSection
      title={{ en: 'The publications', es: 'Las publicaciones' }}
      noRefsReason={{ en: "Lists this product's own records.", es: 'Enumera los registros propios de este producto.' }}
    >
      <P
        en="The technical report and a manuscript for each method and measurement Contraste proposes are published on Zenodo, each under its own concept DOI, which always opens its latest version. They are written in English."
        es="El informe técnico y un manuscrito por cada método y medición que propone Contraste están publicados en Zenodo, cada uno con su propio DOI de concepto, que siempre abre su versión más reciente. Están escritos en inglés."
      />
      <ul data-publications="">
        {PUBLICATIONS.map((m) => (
          <li key={m.concept_doi} data-doi={m.concept_doi}>
            <T en={m.kind === 'technical-report' ? 'Technical report' : 'Manuscript'} es={m.kind === 'technical-report' ? 'Informe técnico' : 'Manuscrito'} />
            {': '}
            <a href={`https://doi.org/${m.concept_doi}`}>
              <span lang="en" translate="no">
                {m.title}
              </span>
            </a>
          </li>
        ))}
      </ul>
    </DocSection>
  );
}
