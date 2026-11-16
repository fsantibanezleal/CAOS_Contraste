// The metadata of the Methodology section `market`: what the page's tab list needs without loading the section (BL-102).
// The body is market.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'market',
  group: 'market',
  order: 120,
  title: { en: 'Market risk', es: 'Riesgo de mercado' },
};
