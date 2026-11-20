// The metadata of the Methodology section `irrbb`: what the page's tab list needs without loading the section (BL-102).
// The body is irrbb.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'irrbb',
  group: 'balance',
  order: 120,
  title: { en: 'Interest rate risk (IRRBB)', es: 'Riesgo de tasa (IRRBB)' },
};
