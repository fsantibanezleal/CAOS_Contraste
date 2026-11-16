// The metadata of the Methodology section `market-conformal`: what the page's tab list needs without loading the section (BL-102).
// The body is market-conformal.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'conformal-var',
  group: 'market',
  order: 150,
  title: { en: 'Adaptive conformal recalibration of the VaR', es: 'Recalibración conforme adaptativa del VaR' },
};
