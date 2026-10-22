// The words the C08 to C13 views put on screen for the ids and the English strings of their documents (U16-R2): a view never prints a
// raw id or an English sentence in the Spanish page. A map holds only what the documents carry; an id without an entry is shown as it is
// (the one fallback, so a new id is visible, never hidden).
/** A text in both languages. */
export type Words = { en: string; es: string };

/** What each truth status of a variant is called. */
export const TRUTH_TEXT: Record<string, Words> = {
  'real-outcomes': { en: 'Real outcomes', es: 'Resultados reales' },
  'synthetic-known-truth': { en: 'Synthetic, with a known truth', es: 'Sintético, con una verdad conocida' },
  'synthetic-calibrated': { en: 'Synthetic, calibrated to public aggregates', es: 'Sintético, calibrado a agregados públicos' },
  'published-answer': { en: 'A published answer', es: 'Una respuesta publicada' },
};

/** The words of an id from a map, the id itself when the map lacks it. */
export const wordsOf = (map: Record<string, Words>, id: string): Words => map[id] ?? { en: id, es: id };

/** The truth status of a variant in the language. */
export const truthText = (id: string, lang: 'en' | 'es'): string => wordsOf(TRUTH_TEXT, id)[lang];

/** A paragraph range of a framework ("CRE32.58 to CRE32.59") in the language: the connective is translated, the references stay. */
export const rangeText = (reference: string, lang: 'en' | 'es'): string => (lang === 'es' ? reference.replace(/ to /g, ' a ').replace(/ and /g, ' y ') : reference);

/** A list of references ("CRE32.36, CRE32.64 and CRE32.33") in the language. */
export const referenceText = rangeText;

export const YEAR_FORMAT = { decimals: 0, grouping: false } as const;
