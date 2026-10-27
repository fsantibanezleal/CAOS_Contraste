// The references of unit U15 (model governance: the inventory, the tiering, the findings register, the validation report
// and the model risk appetite). Every entry is transcribed from the U15 research addendum (D6), where each page was opened
// at its primary source on 2026-10-20. SR 26-2, PRA SS1/23, OSFI E-23, the ECB reporting instructions (ecb2019), the ECB
// TRIM report (ecbtrim) and SR 11-7 are already registered in other files and are not repeated here.
import type { Citation } from '@fasl-work/caos-app-shell';

export const CITATIONS: Citation[] = [
  {
    id: 'osfibackgrounder',
    label: { en: 'OSFI E-23 backgrounder', es: 'Nota de antecedentes de la OSFI E-23' },
    citation: 'Office of the Superintendent of Financial Institutions. Backgrounder: Guideline E-23, Model Risk Management. States that the guideline will come into effect in May 2027, following an 18-month transition period, and that pension plans are excluded from its scope.',
    url: 'https://www.osfi-bsif.gc.ca/en/news/backgrounder-guideline-e-23-model-risk-management',
  },
  {
    id: 'osfie23letter',
    label: { en: 'OSFI E-23 letter', es: 'Carta de la OSFI sobre la E-23' },
    citation: 'Office of the Superintendent of Financial Institutions (2025-09-11). Letter: Guideline E-23, Model Risk Management (2027); takes effect for all federally regulated financial institutions on 2027-05-01.',
    url: 'https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/guideline-e-23-model-risk-management-2027-letter',
  },
];
