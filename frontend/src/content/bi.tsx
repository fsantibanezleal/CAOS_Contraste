// Bilingual prose for the documentation pages: every paragraph is written in both languages where it is written.
import { useShellLang } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';

/** A translator for the current language: `t('English', 'Español')`. */
export function useT(): (en: string, es: string) => string {
  const lang = useShellLang();
  return (en, es) => (lang === 'es' ? es : en);
}

/** One paragraph in the current language. */
export function P({ en, es }: { en: ReactNode; es: ReactNode }) {
  const lang = useShellLang();
  return <p>{lang === 'es' ? es : en}</p>;
}

/** A bulleted list, item by item in the current language. */
export function L({ items }: { items: { en: ReactNode; es: ReactNode }[] }) {
  const lang = useShellLang();
  return (
    <ul>
      {items.map((it, i) => (
        <li key={i}>{lang === 'es' ? it.es : it.en}</li>
      ))}
    </ul>
  );
}

/** One run of text in the current language: a caption or a cell written in JSX for each language. */
export function T({ en, es }: { en: ReactNode; es: ReactNode }) {
  const lang = useShellLang();
  return <>{lang === 'es' ? es : en}</>;
}

/** A source's own reference, kept as the source writes it: an equation, section or theorem number ("(2.8)", "3.12")
 * or a licence's version ("Apache 2.0"), which is not a decimal. A Spanish page writes decimals with a comma; the gate's Spanish-number check (G11) reads
 * nothing marked translate="no", and nothing else is marked. */
export function Ref({ children }: { children: ReactNode }) {
  return <span translate="no">{children}</span>;
}

/** A note that quotes its source: each "..." passage is the source's own words, kept as written in the source's
 * language (translate="no", lang), the rest in the page's. */
export function WithQuotes({ text, lang = 'en' }: { text: string; lang?: string }) {
  const parts = text.split(/("[^"]+")/);
  return (
    <>
      {parts.map((part, i) =>
        i % 2 ? (
          <span key={i} translate="no" lang={lang}>
            {part}
          </span>
        ) : (
          part
        ),
      )}
    </>
  );
}
