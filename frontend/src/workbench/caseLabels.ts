// The name of a case on the rail's select (BL-090). Shell 0.17.0 shows a case name whole, on as many lines as it needs,
// and sizes the select to the longest name of the list, so the baked titles (up to 82 characters: C12) made every
// rail's head three lines tall and pushed rails past their height at 1280 x 800 (ADR-0071 rule 6). The English labels fit one line of the
// 182 px select (two lines still left C12, C18 and C20 10 px over); the Spanish ones, longer, fit in two. The rail shows
// the short label below; the baked title is untouched (the manifests, the Context group and the page headings keep it),
// so nothing re-bakes. A case with no entry here (a case added later, a planned one) shows its title as before.
type Bi = { en: string; es: string };

export const CASE_LABEL: Record<string, Bi> = {
  C01: { en: 'Retail cards PD', es: 'PD de tarjetas: campeón vs retador' },
  C02: { en: 'Corporate PD, 1 to 5 years', es: 'PD corporativa, 1 a 5 años' },
  C03: { en: 'SME PD by vintage to 2008', es: 'PD de pymes por cosecha hasta 2008' },
  C04: { en: 'Rating transitions, TTC PD', es: 'Transiciones de calificación y PD TTC' },
  C05: { en: 'Low-default PD calibration', es: 'Bajo incumplimiento y calibración de PD' },
  C06: { en: 'Lifetime PD, IFRS 9, ECL', es: 'PD de por vida, IFRS 9 y pérdida esperada' },
  C07: { en: 'Chile provisions trilogy', es: 'Provisiones en Chile: CMF B-1, IFRS 9, BdE' },
  C08: { en: 'LGD and downturn LGD', es: 'LGD y LGD de recesión' },
  C09: { en: 'EAD and CCF, revolving', es: 'EAD y CCF de líneas rotativas' },
  C10: { en: 'Portfolio capital, copula', es: 'Capital de cartera: ASRF, Vasicek, cópula' },
  C11: { en: 'Market VaR/ES backtests', es: 'Backtesting de VaR/ES, 2008 a 2023' },
  C12: { en: 'Swap-book CVA exposure', es: 'Exposición a la contraparte y CVA de swaps' },
  C13: { en: 'FRTB desk eligibility', es: 'Mesas FRTB: elegibilidad PLA y backtesting' },
  C14: { en: 'IRRBB, USD balance sheet', es: 'IRRBB, seis choques, balance en USD' },
  C15: { en: 'IRRBB, CLP and UF balance', es: 'IRRBB sobre un balance en CLP y UF' },
  C16: { en: 'Liquidity stress and LCR', es: 'Estrés de liquidez, LCR y corrida de 2023' },
  C17: { en: 'Op. risk: LDA vs SMA', es: 'Riesgo operacional: LDA vs SMA' },
  C18: { en: 'ICAAP/IAPE aggregation', es: 'Agregación de capital ICAAP e IAPE' },
  C19: { en: 'Stress replication', es: 'Réplica de estrés' },
  C20: { en: 'ML model validation', es: 'Validación de ML: deriva y robustez' },
  C21: { en: 'Fair-lending disparity', es: 'Pruebas de disparidad en crédito justo' },
  C22: { en: 'Validating the validator', es: 'Validar al validador: tamaño y potencia' },
};

/** The rail's name for a case: the short label when the case has one, else its baked title. */
export function caseLabel(id: string, title: Bi, lang: 'en' | 'es'): string {
  return (CASE_LABEL[id] ?? title)[lang];
}
