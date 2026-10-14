// The coverage rows of the cases unit U8 builds (C11 and C13). A later file replaces the row of the same id in base.ts,
// so the unit that builds a case updates its row here and edits nothing else; whether a case is built is read from the
// readiness and the committed index at run time, never typed here. The data text follows the c11 and c13 contracts: C11
// runs the VaR and ES ladder on public daily series in six windows (the Kenneth French library is derived-only, the
// Treasury par curve and the Federal Reserve H.10 exchange rates are mirror-allowed), strictly rolling, with the
// hyperparameters fixed on 1995 to 2003; C13 runs the FRTB desk tests on a generator of desk P&L with planted model
// deficiencies, whose truth is known.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { PlannedCase } from './base';

const t = (en: string, es: string): BiText => ({ en, es });

export const CASES: PlannedCase[] = [
  {
    id: 'C11',
    category: 'market-ccr',
    title: t('Market VaR/ES backtesting across 2008, 2020, 2022, 2023', 'Backtesting de VaR/ES de mercado en 2008, 2020, 2022 y 2023'),
    data: t(
      'Kenneth French daily returns (derived results only), the US Treasury par curve and the Federal Reserve H.10 exchange rates, in six windows, forecast one day ahead with hyperparameters fixed on 1995 to 2003',
      'Retornos diarios de Kenneth French (solo resultados derivados), la curva par del Tesoro de EE.UU. y los tipos de cambio H.10 de la Reserva Federal, en seis ventanas, pronosticadas un día adelante con hiperparámetros fijados en 1995 a 2003',
    ),
    truth: t('real outcomes', 'resultados reales'),
    unit: 'U8',
  },
  {
    id: 'C13',
    category: 'market-ccr',
    title: t('FRTB desk eligibility: PLA and desk backtesting', 'Elegibilidad FRTB de mesas: PLA y backtesting de mesa'),
    data: t(
      'Generator of desk P&L with a known risk model and six planted model deficiencies, replicated on independent seeds',
      'Generador de P&L de mesa con un modelo de riesgo conocido y seis deficiencias de modelo sembradas, replicado con semillas independientes',
    ),
    truth: t('known truth', 'verdad conocida'),
    unit: 'U8',
  },
];
