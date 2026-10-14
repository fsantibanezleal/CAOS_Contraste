// The coverage row of the case unit U7 builds (C10). A later file replaces the row of the same id in base.ts, so the
// unit that builds a case updates its row here and edits nothing else; whether the case is built is read from the
// readiness and the committed index at run time, never typed here. The data text follows the c10 contracts: the
// Federal Reserve charge-off rates by loan type, fitted on 1985 to 2006 and evaluated on 2007 to 2012, an illustrative
// portfolio for the loss distributions (never a bank's), and a Vasicek simulator with a known correlation for the exact
// size and power of the correlation estimates.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { PlannedCase } from './base';

const t = (en: string, es: string): BiText => ({ en, es });

export const CASES: PlannedCase[] = [
  {
    id: 'C10',
    category: 'portfolio-capital',
    title: t('Portfolio credit capital: ASRF, Vasicek fit, copula MC', 'Capital de crédito de cartera: ASRF, ajuste de Vasicek, cópulas MC'),
    data: t('Federal Reserve charge-off rates by loan type, 1985 to 2012, an illustrative portfolio and a simulator with a known correlation', 'Tasas de castigo de la Reserva Federal por tipo de crédito, 1985 a 2012, una cartera ilustrativa y un simulador con una correlación conocida'),
    truth: t('real aggregates and known truth', 'agregados reales y verdad conocida'),
    unit: 'U7',
  },
];
