// The coverage row of the case unit U9 builds (C12). A later file replaces the row of the same id in base.ts, so the unit
// that builds a case updates its row here and edits nothing else; whether a case is built is read from the readiness and
// the committed index at run time, never typed here. The data text follows the c12 contracts: the US Treasury daily par
// yield curve of each initialisation date (real), the Treasury HQM corporate curve for the counterparty spread (a derived
// proxy), a synthetic USD swap book with its CSA, and ORE 1.8.17.0 as the reference engine the exposure is reconciled
// against. The curve is real and the trades are synthetic, which is the truth status the row states.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { PlannedCase } from './base';

const t = (en: string, es: string): BiText => ({ en, es });

export const CASES: PlannedCase[] = [
  {
    id: 'C12',
    category: 'market-ccr',
    title: t('Swap exposure, CVA and SA-CCR', 'Exposición de swaps, CVA y SA-CCR'),
    data: t(
      'US Treasury daily par yield curves, the Treasury HQM corporate curve as a proxy of the counterparty spread, a synthetic USD swap book with its CSA, and ORE 1.8.17.0 as the reference engine',
      'Curvas diarias de rendimiento par del Tesoro de EE. UU., la curva corporativa HQM del Tesoro como proxy del spread de la contraparte, una cartera sintética de swaps en USD con su CSA, y ORE 1.8.17.0 como motor de referencia',
    ),
    truth: t('real market, synthetic trades', 'mercado real, operaciones sintéticas'),
    unit: 'U9',
  },
];
