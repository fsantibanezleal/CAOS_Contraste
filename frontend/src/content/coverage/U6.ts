// The coverage rows of the cases unit U6 builds (C03, C08 and C09). A later file replaces the row of the same id in base.ts,
// so the unit that builds a case updates its row here and edits nothing else; whether a case is built is read from the
// readiness and the committed index at run time, never typed here. The data text follows the c03, c08 and c09 contracts:
// the SBA 7(a) public loans are the primary twin of C03 and C08 (Freddie Mac loss fields only when the owner's account
// exists), and the revolving lines of C09 come from a generator with a known CCF shaped on the Fed 2025 card portfolios.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { PlannedCase } from './base';

const t = (en: string, es: string): BiText => ({ en, es });

export const CASES: PlannedCase[] = [
  {
    id: 'C03',
    category: 'credit-scoring',
    title: t('SME PD by vintage through 2008', 'PD pyme por cosecha a través de 2008'),
    data: t('SBA 7(a) public loans by approval fiscal year, the 5-year target read only at each vintage\'s mark', 'Préstamos públicos SBA 7(a) por año fiscal de aprobación, con el objetivo a 5 años leído solo en la marca de cada cosecha'),
    truth: t('real outcomes', 'resultados reales'),
    unit: 'U6',
  },
  {
    id: 'C08',
    category: 'lgd-ead',
    title: t('LGD and downturn LGD', 'LGD y LGD de recesión'),
    data: t('SBA 7(a) charge-off twin as the primary data (a charge-off LGD proxy with its bias stated); Freddie Mac loss fields when the account exists', 'Gemelo de castigos SBA 7(a) como dato principal (un proxy de LGD por castigo con su sesgo declarado); campos de pérdida de Freddie Mac cuando exista la cuenta'),
    truth: t('real outcomes', 'resultados reales'),
    unit: 'U6',
  },
  {
    id: 'C09',
    category: 'lgd-ead',
    title: t('EAD and CCF for revolving lines', 'EAD y CCF de líneas rotativas'),
    data: t('Generator of revolving lines with a known CCF, shaped on the Fed card portfolios', 'Generador de líneas rotativas con un CCF conocido, con la forma de las carteras de tarjetas de la Fed'),
    truth: t('known truth', 'verdad conocida'),
    unit: 'U6',
  },
];
