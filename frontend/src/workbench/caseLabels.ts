// The name of a case on the rail's select (BL-090). Shell 0.17.0 shows a case name whole, on as many lines as it needs,
// and sizes the select to the longest name of the list, so the baked titles (up to 82 characters: C12) made every
// rail's head three lines tall and pushed four rails past their height at 1280 x 800 (ADR-0071 rule 6). The rail shows
// the short label below; the baked title is untouched (the manifests, the Context group and the page headings keep it),
// so nothing re-bakes. A case with no entry here (a case added later, a planned one) shows its title as before.
type Bi = { en: string; es: string };

export const CASE_LABEL: Record<string, Bi> = {
  C01: { en: 'Retail cards PD: champion vs challenger', es: 'PD de tarjetas: campeón vs retador' },
  C02: { en: 'Corporate PD, 1 to 5 year horizons', es: 'PD corporativa, 1 a 5 años' },
  C03: { en: 'SME PD by vintage through 2008', es: 'PD de pymes por cosecha hasta 2008' },
  C04: { en: 'Rating transitions and TTC PD by grade', es: 'Transiciones de calificación y PD TTC' },
  C05: { en: 'Low-default portfolios, PD calibration', es: 'Bajo incumplimiento y calibración de PD' },
  C06: { en: 'Lifetime PD, IFRS 9 staging and ECL', es: 'PD de por vida, IFRS 9 y pérdida esperada' },
  C07: { en: 'Chile provisions: CMF B-1, IFRS 9, BdE', es: 'Provisiones en Chile: CMF B-1, IFRS 9, BdE' },
  C08: { en: 'LGD and downturn LGD', es: 'LGD y LGD de recesión' },
  C09: { en: 'EAD and CCF for revolving lines', es: 'EAD y CCF de líneas rotativas' },
  C10: { en: 'Portfolio capital: ASRF, Vasicek, copula', es: 'Capital de cartera: ASRF, Vasicek, cópula' },
  C11: { en: 'Market VaR/ES backtests, 2008 to 2023', es: 'Backtesting de VaR/ES, 2008 a 2023' },
  C12: { en: 'Swap-book counterparty exposure and CVA', es: 'Exposición a la contraparte y CVA de swaps' },
  C13: { en: 'FRTB desk eligibility: PLA, backtesting', es: 'Mesas FRTB: elegibilidad PLA y backtesting' },
  C14: { en: 'IRRBB, six shocks, USD balance sheet', es: 'IRRBB, seis choques, balance en USD' },
  C15: { en: 'IRRBB on a CLP and UF balance sheet', es: 'IRRBB sobre un balance en CLP y UF' },
  C16: { en: 'Liquidity stress, LCR, the March 2023 run', es: 'Estrés de liquidez, LCR y corrida de 2023' },
  C17: { en: 'Operational risk: LDA vs SMA', es: 'Riesgo operacional: LDA vs SMA' },
  C18: { en: 'ICAAP and IAPE capital aggregation', es: 'Agregación de capital ICAAP e IAPE' },
  C19: { en: 'Supervisory stress replication', es: 'Réplica de estrés supervisor' },
  C20: { en: 'ML validation: drift and robustness', es: 'Validación de ML: deriva y robustez' },
  C21: { en: 'Fair-lending disparity testing', es: 'Pruebas de disparidad en crédito justo' },
  C22: { en: 'Validating the validator: size and power', es: 'Validar al validador: tamaño y potencia' },
};

/** The rail's name for a case: the short label when the case has one, else its baked title. */
export function caseLabel(id: string, title: Bi, lang: 'en' | 'es'): string {
  return (CASE_LABEL[id] ?? title)[lang];
}
