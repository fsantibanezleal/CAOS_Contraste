// The words of C01's views that the artifacts hold as English identifiers or as a code string: the currency a case's
// money is in, the unit of a feature, a PLTR rule, a design limit. A Spanish view prints each in Spanish, with the
// decimal sign and the grouping of the shell's es-CL (U16-R2, PR-C01); a name this file does not know prints as written.
import { formatNumber } from '@fasl-work/caos-app-shell';

/** A text in both languages. */
export type Bi = { en: string; es: string };

const same = (t: string): Bi => ({ en: t, es: t });

const CURRENCY: Record<string, Bi> = {
  'NT dollars': { en: 'NT dollars', es: 'nuevos dólares taiwaneses' },
  DM: { en: 'Deutsche Mark', es: 'marcos alemanes' },
};

/** The name of the money a case's impact is in (the artifact's `unit`: 'NT dollars' for Taiwan, 'DM' for the German twin). */
export function currencyName(unit: string): Bi {
  return CURRENCY[unit] ?? same(unit);
}

const FEATURE_UNIT: Record<string, Bi> = {
  'months of delay': { en: 'months of delay', es: 'meses de atraso' },
  months: { en: 'months', es: 'meses' },
  count: { en: 'count', es: 'conteo' },
  'rate class 1 to 4': { en: 'rate class 1 to 4', es: 'clase de tasa 1 a 4' },
  'years class 1 to 4': { en: 'years class 1 to 4', es: 'clase de años 1 a 4' },
};

/** The unit of a feature as the data dictionary states it, in both languages; null for a feature with none. */
export function unitName(unit: string): Bi | null {
  if (!unit) return null;
  return CURRENCY[unit] ?? FEATURE_UNIT[unit] ?? same(unit);
}

const ENGINE_ES: Record<string, string> = {
  own: 'propio',
  'own on optbinning': 'propio sobre optbinning',
  'scikit-learn trees and LogisticRegression, own rule extraction': 'árboles de scikit-learn y regresión logística, extracción de reglas propia',
};

/** The engine of a rung as the models artifact states it (English), in the page's language; a library name is the same in both. */
export function engineText(engine: string, lang: 'en' | 'es'): string {
  return lang === 'es' ? ENGINE_ES[engine] ?? engine : engine;
}

const CONDITION = /^([A-Za-z_]\w*) (<=|>=|<|>|==) (-?\d+(?:\.\d+)?)$/;

/**
 * A PLTR rule, written from its conditions: `PAY_0 <= 1.5 and PAY_2 <= 1.5` reads `PAY_0 <= 1,5 y PAY_2 <= 1,5` in Spanish,
 * the threshold in the language's number format (as many decimals as the engine wrote). A condition that does not parse is
 * kept as written.
 */
export function ruleText(rule: string, lang: 'en' | 'es'): string {
  if (lang === 'en') return rule;
  return rule
    .split(' and ')
    .map((part) => {
      const m = CONDITION.exec(part);
      if (!m) return part;
      const decimals = m[3].includes('.') ? m[3].split('.')[1].length : 0;
      return `${m[1]} ${m[2]} ${formatNumber(Number(m[3]), lang, { decimals })}`;
    })
    .join(' y ');
}

const DESIGN_LIMIT: Record<string, Bi> = {
  'single-snapshot': { en: 'the data is a single snapshot', es: 'los datos son una sola foto' },
};

/** A design limit a finding cites (`design:<id>`) in words; an id not listed here prints as written. */
export function designLimit(id: string): Bi {
  return DESIGN_LIMIT[id] ?? same(id);
}

const UCI_CC_BY = 'This dataset is licensed under a Creative Commons Attribution 4.0 International (CC BY 4.0) license.';

/** The Spanish of a source's licence sentence, kept with the English it translates: a registry wording that has moved on is shown as declared,
 * never as a stale translation. The sentence of a licence is a gloss for the reader; the name of the licence stays as published. */
const LICENCE_ES: Record<string, [string, string]> = {
  'uci-taiwan': [UCI_CC_BY, 'Este conjunto de datos tiene licencia Creative Commons Atribución 4.0 Internacional (CC BY 4.0).'],
  'uci-german': [UCI_CC_BY, 'Este conjunto de datos tiene licencia Creative Commons Atribución 4.0 Internacional (CC BY 4.0).'],
  'uci-polish': [UCI_CC_BY, 'Este conjunto de datos tiene licencia Creative Commons Atribución 4.0 Internacional (CC BY 4.0).'],
};

/** A source's licence in the language: the Spanish of the known sentence, else the sentence as declared. */
export function licenceText(sourceId: string, declared: string, lang: 'en' | 'es'): string {
  const known = LICENCE_ES[sourceId];
  return lang === 'es' && known && known[0] === declared ? known[1] : declared;
}
