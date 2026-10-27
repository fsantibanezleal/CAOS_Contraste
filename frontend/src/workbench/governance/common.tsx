// What every governance tab shares: the document wrapper with the declared states (loading, not available yet with its
// reason, error), the source line, the tag of a convention, and the basis of a convention kept in the language its
// document wrote it in. Not a test file; the tabs and the opinion block use it.
import { pick, useShellLang } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import type { Text } from '../../lib/contract.types';
import { Pending, Unavailable } from '../Pending';
import { CONVENTION_NOTE, NOT_YET, TAG_NAME, useGovernance } from './model';
import { readerWords } from './readerText';

/** One governance document in its declared state: the view is drawn only from a document that was read. */
export function GovernanceDoc<T>({ file, children, label }: { file: string; children: (doc: T) => ReactNode; label?: Text }) {
  const lang = useShellLang();
  const doc = useGovernance<T>(file);
  if (doc.state === 'loading') return <Pending label={label ?? { en: 'Loading the governance document', es: 'Cargando el documento de gobernanza' }} />;
  if (doc.state === 'unavailable') return <Unavailable reason={{ en: `${NOT_YET.en}. ${doc.reason.en}`, es: `${NOT_YET.es}. ${doc.reason.es}` }} />;
  if (doc.state === 'error')
    return (
      <p className="caos-pending" data-state="unavailable">
        {pick({ en: `${NOT_YET.en}. The governance document could not be read.`, es: `${NOT_YET.es}. No se pudo leer el documento de gobernanza.` }, lang)}
      </p>
    );
  return <>{children(doc.data)}</>;
}

/** Prose a document wrote in both languages. On the Spanish page it is already Spanish, and it may quote a reference such as "A D2 3.5" that is not a decimal: it is marked translate="no" so the page's Spanish-number check reads it as the reference it is. */
export function Doc({ t, capital = false }: { t: Text; capital?: boolean }) {
  const lang = useShellLang();
  // in reader words: no plan or decision code, the engine keys in words (R3 c23 B3, B5)
  const read = readerWords(t[lang], lang);
  const words = capital ? read.replace(/^\s*(\p{L})/u, (m, c: string) => m.replace(c, c.toUpperCase())) : read;
  return <span translate={lang === 'es' ? 'no' : undefined}>{words}</span>;
}

/** The as-of date of a document and what it is: a date with its label, never the date of publication unless the basis says so. */
export function AsOf({ asOf, basis }: { asOf: string; basis: { label: string; basis: Text } }) {
  const lang = useShellLang();
  return (
    <p className="ct-note" data-as-of={asOf}>
      {pick({ en: 'As of', es: 'Al' }, lang)} {asOf} ({pick(TAG_NAME[basis.label] ?? { en: basis.label, es: basis.label }, lang)}): {readerWords(pick(basis.basis, lang), lang)}
    </p>
  );
}

/** The convention note every governance tab carries (dossier 06 UNVERIFIED item 30). */
export function ConventionNote() {
  const lang = useShellLang();
  return <p className="ct-note" data-convention-note>{pick(CONVENTION_NOTE, lang)}</p>;
}

/** The tag of a value: a convention, or read from a document. */
export function Tag({ tag }: { tag: string }) {
  const lang = useShellLang();
  return <span data-tag={tag}>{pick(TAG_NAME[tag] ?? { en: tag, es: tag }, lang)}</span>;
}

/** The basis of a convention is the sentence its document wrote, in English; it is shown as written, folded, and marked as English. */
export function Basis({ label, text }: { label: string; text: string }) {
  const lang = useShellLang();
  return (
    <details className="ct-note" data-basis>
      <summary>
        {label}: {pick({ en: 'the stated basis', es: 'la base declarada' }, lang)} {lang === 'es' ? '(texto de la fuente, en inglés)' : ''}
      </summary>
      <span lang="en" translate="no">
        {readerWords(text, 'en')}
      </span>
    </details>
  );
}
