// Any path the router does not know. The static host answers such a path with 404.html (a copy of this app), so a
// mistyped link lands here, says so, and offers the way back, instead of a blank page or the App in disguise.
import { DocPage, DocSection, STANDARD_ROUTES, useShellLang } from '@fasl-work/caos-app-shell';
import { Link } from 'react-router';
import { P, useT } from '../content/bi';

export function NotFound() {
  const lang = useShellLang();
  const t = useT();
  return (
    <DocPage title={{ en: 'Page not found', es: 'Página no encontrada' }} lede={t('This address is not one of the pages of this product.', 'Esta dirección no es una de las páginas de este producto.')}>
      <DocSection title={{ en: 'The pages', es: 'Las páginas' }} noRefsReason={{ en: 'Navigation only.', es: 'Sólo navegación.' }}>
        <P en="The product has six pages:" es="El producto tiene seis páginas:" />
        <ul>
          {STANDARD_ROUTES.map((r) => (
            <li key={r.path}>
              <Link to={r.path}>{lang === 'es' ? r.es : r.en}</Link>
            </li>
          ))}
        </ul>
      </DocSection>
    </DocPage>
  );
}
