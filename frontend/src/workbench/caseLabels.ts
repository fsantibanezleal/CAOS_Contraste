// The name of a case on the rail's select (BL-090). Shell 0.17.0 shows a case name whole, on as many lines as it needs,
// and sizes the select to the longest name of the list, so the baked titles (up to 82 characters: C12) made every
// rail's head three lines tall and pushed rails past their height at 1280 x 800 (ADR-0071 rule 6). The labels fit one line of the 182 px
// select in both languages (two lines still left C12, C18 and C20 10 px over, and in Spanish, where every label took two,
// the C18 and C22 rails; U16, 2026-10-22), at most 26 characters, the longest English one. The rail shows
// the short label below; the baked title is untouched (the manifests, the Context group and the page headings keep it),
// so nothing re-bakes. A case with no entry here (a case added later, a planned one) shows its title as before.
type Bi = { en: string; es: string };

export const CASE_LABEL: Record<string, Bi> = {
  C01: { en: 'Retail cards PD', es: 'PD de tarjetas' },
  C02: { en: 'Corporate PD, 1 to 5 years', es: 'PD corporativa, 1 a 5 años' },
  C03: { en: 'SME PD by vintage to 2008', es: 'PD pyme por cosecha' },
  C04: { en: 'Rating transitions, TTC PD', es: 'Transiciones y PD TTC' },
  C05: { en: 'Low-default PD calibration', es: 'PD de bajo incumplimiento' },
  C06: { en: 'Lifetime PD, IFRS 9, ECL', es: 'PD de por vida, IFRS 9' },
  C07: { en: 'Chile provisions trilogy', es: 'Provisiones en Chile' },
  C08: { en: 'LGD and downturn LGD', es: 'LGD y LGD de recesión' },
  C09: { en: 'EAD and CCF, revolving', es: 'EAD y CCF rotativos' },
  C10: { en: 'Portfolio capital, copula', es: 'Capital de cartera' },
  C11: { en: 'Market VaR/ES backtests', es: 'Backtesting de VaR/ES' },
  C12: { en: 'Swap-book CVA exposure', es: 'CVA de cartera de swaps' },
  C13: { en: 'FRTB desk eligibility', es: 'Elegibilidad FRTB' },
  C14: { en: 'IRRBB, USD balance sheet', es: 'IRRBB, balance en USD' },
  C15: { en: 'IRRBB, CLP and UF balance', es: 'IRRBB, balance CLP y UF' },
  C16: { en: 'Liquidity stress and LCR', es: 'Estrés de liquidez y LCR' },
  C17: { en: 'Op. risk: LDA vs SMA', es: 'Riesgo op.: LDA vs SMA' },
  C18: { en: 'ICAAP/IAPE aggregation', es: 'Agregación ICAAP/IAPE' },
  C19: { en: 'Stress replication', es: 'Réplica de estrés' },
  C20: { en: 'ML model validation', es: 'Validación de ML' },
  C21: { en: 'Fair-lending disparity', es: 'Disparidad crediticia' },
  C22: { en: 'Validating the validator', es: 'Validar al validador' },
};

/** The rail's name for a case: the short label when the case has one, else its baked title. */
export function caseLabel(id: string, title: Bi, lang: 'en' | 'es'): string {
  return (CASE_LABEL[id] ?? title)[lang];
}
