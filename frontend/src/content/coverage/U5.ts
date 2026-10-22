// The coverage rows of the cases unit U5 builds (C06 and C07). A later file replaces the row of the same id in base.ts,
// so the unit that builds a case updates its row here and edits nothing else; whether a case is built is read from the
// readiness and the committed index at run time, never typed here. The data text follows the c06 and c07 contracts:
// the SBA 7(a) public loans are the primary twin of C06 and Freddie Mac (derived-only) is used when it is available.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { PlannedCase } from './base';

const t = (en: string, es: string): BiText => ({ en, es });

export const CASES: PlannedCase[] = [
  {
    id: 'C06',
    category: 'provisions',
    title: t('Mortgage lifetime PD, IFRS 9 staging and ECL', 'PD de vida de hipotecas, etapas y PCE de IFRS 9'),
    data: t('SBA 7(a) public loans as the primary twin, Freddie Mac (derived-only) when available, and Fed scenario paths', 'Préstamos públicos SBA 7(a) como gemelo principal, Freddie Mac (solo derivados) cuando esté disponible, y trayectorias de escenarios de la Fed'),
    truth: t('real outcomes', 'resultados reales'),
    unit: 'U5',
  },
  {
    id: 'C07',
    category: 'provisions',
    title: t('Chile provisions trilogy: CMF B-1, IFRS 9, BdE Annex 9', 'Trilogía de provisiones en Chile: CMF B-1, IFRS 9, Anexo 9 del BdE'),
    data: t('Synthetic Banco Andino calibrated to CMF aggregates', 'Banco Andino sintético calibrado a agregados de la CMF'),
    truth: t('synthetic calibrated', 'sintético calibrado'),
    unit: 'U5',
  },
];
