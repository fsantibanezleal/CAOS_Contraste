// The metadata of the Methodology section `market-pla-complement`: what the page's tab list needs without loading the section (BL-102).
// The body is market-pla-complement.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'pla-complement',
  group: 'market',
  order: 160,
  title: { en: 'Complement to the PLA test', es: 'Complemento de la prueba PLA' },
};
