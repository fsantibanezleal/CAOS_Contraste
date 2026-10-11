// The coverage matrix of SDD section 5: the 22 cases, their category, data, truth status and the unit that builds
// them (plan section 9). Whether a case is built is read from the committed index at run time, never typed here.
import type { BiText } from '@fasl-work/caos-app-shell';

export interface PlannedCase {
  id: string;
  category: string;
  title: BiText;
  data: BiText;
  truth: BiText;
  unit: string;
}

const t = (en: string, es: string): BiText => ({ en, es });

export const CATEGORY_TITLES: Record<string, BiText> = {
  'credit-scoring': t('Credit scoring', 'Scoring de crédito'),
  'ratings-calibration': t('Ratings and calibration', 'Calificaciones y calibración'),
  provisions: t('Provisions', 'Provisiones'),
  'lgd-ead': t('LGD and EAD', 'LGD y EAD'),
  'portfolio-capital': t('Portfolio capital', 'Capital de cartera'),
  'market-ccr': t('Market and counterparty risk', 'Riesgo de mercado y de contraparte'),
  'balance-sheet': t('Balance sheet: IRRBB and liquidity', 'Balance: IRRBB y liquidez'),
  operational: t('Operational risk', 'Riesgo operacional'),
  'capital-stress': t('Capital and stress testing', 'Capital y pruebas de tensión'),
  'ml-ai-risk': t('ML and AI model risk', 'Riesgo de modelos de ML e IA'),
  validator: t('Validating the validator', 'Validar al validador'),
};

export const CASES: PlannedCase[] = [
  { id: 'C01', category: 'credit-scoring', title: t('Retail cards PD, champion vs challenger', 'PD de tarjetas, campeón vs retador'), data: t('UCI Taiwan, German twin (mirror-allowed)', 'UCI Taiwán, gemelo alemán (espejo permitido)'), truth: t('real outcomes', 'resultados reales'), unit: 'U1' },
  { id: 'C02', category: 'credit-scoring', title: t('Corporate PD across 1 to 5 year horizons', 'PD corporativa a horizontes de 1 a 5 años'), data: t('UCI Polish bankruptcy (mirror-allowed)', 'UCI quiebras polacas (espejo permitido)'), truth: t('real outcomes', 'resultados reales'), unit: 'U14' },
  { id: 'C03', category: 'credit-scoring', title: t('SME PD by vintage through 2008', 'PD pyme por cosecha a través de 2008'), data: t('SBA 7(a) FOIA (mirror-allowed)', 'SBA 7(a) FOIA (espejo permitido)'), truth: t('real outcomes', 'resultados reales'), unit: 'U6' },
  { id: 'C04', category: 'ratings-calibration', title: t('Rating transitions and TTC PD by grade', 'Transiciones de calificación y PD TTC por grado'), data: t('ESMA CEREP (mirror-allowed) and a CTMC generator', 'ESMA CEREP (espejo permitido) y un generador CTMC'), truth: t('real aggregates and known truth', 'agregados reales y verdad conocida'), unit: 'U4' },
  { id: 'C05', category: 'ratings-calibration', title: t('Low-default portfolios and PD calibration', 'Carteras de bajo incumplimiento y calibración de PD'), data: t('Published tables and a Vasicek generator', 'Tablas publicadas y un generador de Vasicek'), truth: t('published answers and known truth', 'respuestas publicadas y verdad conocida'), unit: 'U2' },
  { id: 'C06', category: 'provisions', title: t('Mortgage lifetime PD, IFRS 9 staging and ECL', 'PD de vida de hipotecas, etapas y PCE de IFRS 9'), data: t('Freddie Mac (derived-only) and Fed scenarios; SBA twin', 'Freddie Mac (solo derivados) y escenarios de la Fed; gemelo SBA'), truth: t('real outcomes', 'resultados reales'), unit: 'U5' },
  { id: 'C07', category: 'provisions', title: t('Chile provisions trilogy: CMF B-1, IFRS 9, BdE Annex 9', 'Trilogía de provisiones en Chile: CMF B-1, IFRS 9, Anejo 9 del BdE'), data: t('Synthetic Banco Andino calibrated to CMF aggregates', 'Banco Andino sintético calibrado a agregados de la CMF'), truth: t('synthetic calibrated', 'sintético calibrado'), unit: 'U5' },
  { id: 'C08', category: 'lgd-ead', title: t('LGD and downturn LGD', 'LGD y LGD de recesión'), data: t('Freddie Mac loss fields; SBA charge-off twin', 'Campos de pérdida de Freddie Mac; gemelo de castigos SBA'), truth: t('real outcomes', 'resultados reales'), unit: 'U6' },
  { id: 'C09', category: 'lgd-ead', title: t('EAD and CCF for revolving lines', 'EAD y CCF de líneas rotativas'), data: t('Generator shaped on the Fed card portfolios', 'Generador con la forma de las carteras de tarjetas de la Fed'), truth: t('known truth', 'verdad conocida'), unit: 'U6' },
  { id: 'C10', category: 'portfolio-capital', title: t('Portfolio credit capital: ASRF, Vasicek fit, copula MC', 'Capital de crédito de cartera: ASRF, ajuste de Vasicek, cópulas MC'), data: t('Fed charge-off rates, FDIC failures and a simulator', 'Tasas de castigo de la Fed, quiebras FDIC y un simulador'), truth: t('real aggregates and known truth', 'agregados reales y verdad conocida'), unit: 'U7' },
  { id: 'C11', category: 'market-ccr', title: t('Market VaR/ES backtesting across 2008, 2020, 2022, 2023', 'Backtesting de VaR/ES en 2008, 2020, 2022, 2023'), data: t('Kenneth French (derived-only), Treasury, H.10', 'Kenneth French (solo derivados), Tesoro, H.10'), truth: t('real outcomes', 'resultados reales'), unit: 'U8' },
  { id: 'C12', category: 'market-ccr', title: t('Swap exposure, CVA and SA-CCR', 'Exposición de swaps, CVA y SA-CCR'), data: t('Treasury curves and synthetic trades; ORE', 'Curvas del Tesoro y operaciones sintéticas; ORE'), truth: t('real market, synthetic trades', 'mercado real, operaciones sintéticas'), unit: 'U9' },
  { id: 'C13', category: 'market-ccr', title: t('FRTB desk eligibility: PLA and desk backtesting', 'Elegibilidad FRTB de mesas: PLA y backtesting'), data: t('Generator with planted model deficiencies', 'Generador con deficiencias de modelo sembradas'), truth: t('known truth', 'verdad conocida'), unit: 'U8' },
  { id: 'C14', category: 'balance-sheet', title: t('IRRBB six shocks on a USD balance sheet (SVB 2022)', 'IRRBB con seis shocks en un balance en USD (SVB 2022)'), data: t('FDIC call reports, Treasury curve', 'Reportes FDIC, curva del Tesoro'), truth: t('real aggregates, synthetic behaviour', 'agregados reales, comportamiento sintético'), unit: 'U10' },
  { id: 'C15', category: 'balance-sheet', title: t('IRRBB on a CLP/UF balance sheet (RAN 21-13 Annex 1)', 'IRRBB en un balance CLP/UF (RAN 21-13 Anexo 1)'), data: t('CMF, BCCh F022 and Banco Andino', 'CMF, BCCh F022 y Banco Andino'), truth: t('real aggregates, synthetic bank', 'agregados reales, banco sintético'), unit: 'U10' },
  { id: 'C16', category: 'balance-sheet', title: t('Liquidity stress, LCR and the March 2023 run', 'Estrés de liquidez, LCR y la corrida de marzo de 2023'), data: t('FDIC, H.8, the Fed SVB review and a depositor generator', 'FDIC, H.8, la revisión de la Fed sobre SVB y un generador de depositantes'), truth: t('real event, synthetic deposits', 'evento real, depósitos sintéticos'), unit: 'U11' },
  { id: 'C17', category: 'operational', title: t('Operational risk: LDA vs SMA', 'Riesgo operacional: LDA vs SMA'), data: t('Generator calibrated to BCBS LDCE 2008', 'Generador calibrado al LDCE 2008 del BCBS'), truth: t('synthetic calibrated', 'sintético calibrado'), unit: 'U12' },
  { id: 'C18', category: 'capital-stress', title: t('ICAAP and IAPE capital aggregation under macro scenarios', 'Agregación de capital ICAAP e IAPE bajo escenarios macro'), data: t('Fed 2026, EBA/ESRB 2025, NGFS paths; Banco Andino', 'Trayectorias Fed 2026, EBA/ESRB 2025, NGFS; Banco Andino'), truth: t('real paths, synthetic bank', 'trayectorias reales, banco sintético'), unit: 'U13' },
  { id: 'C19', category: 'capital-stress', title: t('Supervisory stress model replication (known answer)', 'Réplica de modelos supervisores de estrés (respuesta conocida)'), data: t('Fed hypothetical portfolios and published loss rates', 'Carteras hipotéticas de la Fed y tasas de pérdida publicadas'), truth: t('published answers', 'respuestas publicadas'), unit: 'U13' },
  { id: 'C20', category: 'ml-ai-risk', title: t('ML model validation: drift, robustness, explanation stability', 'Validación de modelos de ML: deriva, robustez, estabilidad de explicaciones'), data: t('UCI, SantanderAI SGCD, Fed portfolios as shift probes', 'UCI, SGCD de SantanderAI, carteras de la Fed como sondas de cambio'), truth: t('real outcomes and known shifts', 'resultados reales y cambios conocidos'), unit: 'U14' },
  { id: 'C21', category: 'ml-ai-risk', title: t('Fair-lending disparity testing', 'Pruebas de disparidad en crédito justo'), data: t('HMDA (mirror-allowed)', 'HMDA (espejo permitido)'), truth: t('real decisions', 'decisiones reales'), unit: 'U14' },
  { id: 'C22', category: 'validator', title: t('Validating the validator: size and power of every test', 'Validar al validador: tamaño y potencia de cada prueba'), data: t("riskvalidation's generators with planted defects; the WP14 and Yurdakul-Naranjo tables as published answers (derived-only)", 'Generadores de riskvalidation con defectos plantados; las tablas de WP14 y de Yurdakul-Naranjo como respuestas publicadas (solo derivados)'), truth: t('known truth', 'verdad conocida'), unit: 'U3' },
];
