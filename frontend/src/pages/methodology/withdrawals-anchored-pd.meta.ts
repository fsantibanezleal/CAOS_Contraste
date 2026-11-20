// The metadata of the Methodology section `withdrawals-anchored-pd`: what the page's tab list needs without loading the section (BL-102).
// The body is withdrawals-anchored-pd.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'withdrawals-anchored-pd',
  group: 'loss',
  order: 200,
  title: { en: 'PD under informative withdrawals', es: 'PD con retiros informativos' },
};
