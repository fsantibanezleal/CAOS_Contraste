// Bilingual prose for the documentation pages: every paragraph is written in both languages where it is written.
import { Equation as ShellEquation, useShellLang } from '@fasl-work/caos-app-shell';
import { Fragment, type ReactNode } from 'react';

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
export function WithQuotes({ text, lang = 'en', pageLang }: { text: string; lang?: string; pageLang?: 'en' | 'es' }) {
  const parts = text.split(/("[^"]+")/);
  return (
    <>
      {parts.map((part, i) => {
        if (!(i % 2)) return part;
        // an English quotation on the Spanish page keeps its original, marked, and gives its Spanish rendering beside it (the ruling
        // of 2026-10-27; R4 c28 B6: the C22 published-reproduction quotation)
        const rendering = pageLang === 'es' && lang === 'en' ? QUOTE_ES[part.slice(1, -1)] : undefined;
        return (
          <Fragment key={i}>
            <span translate="no" lang={lang}>
              {part}
            </span>
            {rendering ? ` (en español: «${rendering}»)` : null}
          </Fragment>
        );
      })}
    </>
  );
}

/** The Spanish renderings of the English quotations the documents print, keyed by the quotation as the document writes it. */
export const QUOTE_ES: Record<string, string> = {
  'the significance level for the F-test is close to the nominal 0.05 level, whereas it is 0.001 for the DeLong test':
    'el nivel de significación de la prueba F está cerca del nivel nominal de 0,05, mientras que para la prueba de DeLong es de 0,001',
};

/** The words of the display equations in Spanish (U16-F10p, R3 c25 B1: the Spanish page showed "at least one rejection", "net
 * outflows", K_reduced). A word or phrase set in \text{} or \mathrm{} reads in the page's language; the symbols stay. The key is the
 * argument exactly as the TeX writes it, spaces included. */
export const TEX_ES: Record<string, string> = {
  light: 'luz', red: 'rojo', amber: 'ámbar', green: 'verde',
  'at least one rejection': 'al menos un rechazo',
  ' for each constrained feature ': ' para cada variable restringida ',
  Score: 'Puntaje', Offset: 'Desplazamiento', odds: 'razón', Points: 'Puntos',
  or: 'o', and: 'y', otherwise: 'en otro caso', none: 'ninguno', Tier: 'Nivel',
  full: 'completa', cap: 'tope', nominated: 'designados', 'SA-only': 'solo SA', floor: 'piso', loss: 'pérdida',
  bank: 'banco', voluntary: 'voluntario', severe: 'severo', 'usable buffers and mitigation': 'colchones utilizables y mitigación',
  ' for ': ' para ', 's.t.': 'sujeto a', exposure: 'exposición', horizon: 'horizonte',
  if: 'si', ' if ': ' si ', 'if ': 'si ', 'else ': 'si no, ', 'if the radicand': 'si el radicando',
  reduced: 'reducido', hedged: 'cubierto', high: 'alto', medium: 'medio', low: 'bajo',
  short: 'corto', long: 'largo', steep: 'empinamiento', flat: 'aplanamiento', 'risk measure': 'medida de riesgo',
  cliff: 'quiebre', inflows: 'entradas', outflows: 'salidas', 'net outflows': 'salidas netas', product: 'producto', other: 'otro',
  reprice: 'reprecio', 'the ': 'el cuantil empírico ', ' empirical quantile of ': ' de ', 'flag when ': 'alerta cuando ',
  'unless the internal method has the CMF no-objection': 'salvo que el método interno tenga la no objeción de la CMF',
  'default iff ': 'incumple si y solo si ', ratio: 'razón', 'EUR bn': 'miles de millones de EUR', group: 'grupo',
  reject: 'rechazo', 'reject when': 'rechazar cuando', obs: 'obs', sev: 'sev', Floor: 'Piso', only: 'solo', 'P2,bank': 'P2,banco',
  'green: ': 'verde: ', 'red: ': 'rojo: ', 'amber: otherwise': 'ámbar: en otro caso',
  // the subscripts of the symbols, set in \mathrm{} so they read in Spanish (R4 c30 B2: K_reduced, MWB_upper, AUC_init, Th_rec)
  init: 'inicial', curr: 'actual', upper: 'superior', lower: 'inferior', rec: 'recibe', pay: 'paga',
  // a capital K is masculine (K completo), a rate feminine (λ completa): the K writes \mathrm{full }, which KaTeX draws as "full"
  'full ': 'completo',
};

/** `tex` in the page's language: on the Spanish page each \text{} or \mathrm{} word of TEX_ES in Spanish, and a decimal point a comma. */
export function texIn(tex: string, lang: 'en' | 'es'): string {
  if (lang !== 'es') return tex;
  return tex
    .replace(/\\(text|mathrm|textrm)\{([^{}]*)\}/g, (all, cmd: string, arg: string) => (TEX_ES[arg] !== undefined ? `\\${cmd}{${TEX_ES[arg]}}` : all))
    .replace(/(\d)\.(\d)/g, '$1{,}$2');
}

/** The shell's display equation, its words in the page's language (texIn). */
export function Equation({ tex, caption }: { tex: string; caption?: ReactNode }) {
  const lang = useShellLang();
  return <ShellEquation tex={texIn(tex, lang)} caption={caption} />;
}
