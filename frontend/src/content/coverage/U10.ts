// The coverage rows of the cases unit U10 builds (C14 and C15). A later file replaces the row of the same id in base.ts,
// so the unit that builds a case updates its row here and edits nothing else; whether a case is built is read from the
// readiness and the committed index at run time, never typed here. The data text follows the c14 and c15 contracts: C14
// reads the FDIC call reports of the failed bank for three valuation dates and the Treasury par curve of each, with
// synthetic deposit behaviour stated; C15 is the synthetic Banco Andino calibrated to CMF aggregates with the Banco
// Central de Chile curves fitted by Contraste (an adaptation), and stays on its fixtures until the BCCh account exists.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { PlannedCase } from './base';

const t = (en: string, es: string): BiText => ({ en, es });

export const CASES: PlannedCase[] = [
  {
    id: 'C14',
    category: 'balance-sheet',
    title: t('IRRBB six shocks on a USD balance sheet (SVB 2022)', 'IRRBB con seis choques en un balance en USD (SVB 2022)'),
    data: t('FDIC call reports of the failed bank for 2021-Q4, 2022-Q2 and 2022-Q4, read only up to each valuation date, and the Treasury par curve of each date', 'Reportes de condición de la FDIC del banco quebrado para 2021-T4, 2022-T2 y 2022-T4, leídos solo hasta cada fecha de valoración, y la curva par del Tesoro de cada fecha'),
    truth: t('real aggregates, synthetic behaviour', 'agregados reales, comportamiento sintético'),
    unit: 'U10',
  },
  {
    id: 'C15',
    category: 'balance-sheet',
    title: t('IRRBB on a CLP/UF balance sheet (RAN 21-13 Annex 1)', 'IRRBB en un balance CLP/UF (RAN 21-13 Anexo 1)'),
    data: t('Synthetic Banco Andino calibrated to CMF aggregates, and the BCCh F022 CLP and UF sovereign yields of one month fitted to zero curves (an adaptation under the BCCh terms)', 'Banco Andino sintético calibrado a agregados de la CMF, y los rendimientos soberanos CLP y UF F022 del BCCh de un mes ajustados a curvas cero (una adaptación bajo los términos del BCCh)'),
    truth: t('synthetic bank, real curves', 'banco sintético, curvas reales'),
    unit: 'U10',
  },
];
