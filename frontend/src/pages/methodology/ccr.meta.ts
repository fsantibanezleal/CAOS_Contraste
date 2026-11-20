// The metadata of the Methodology section `ccr`: what the page's tab list needs without loading the section (BL-102).
// The body is ccr.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'ccr',
  group: 'market',
  order: 130,
  title: { en: 'Counterparty credit risk (CCR and CVA)', es: 'Riesgo de crédito de contraparte (CCR y CVA)' },
};
