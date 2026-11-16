// The metadata of the Methodology section `ml-validation`: what the page's tab list needs without loading the section (BL-102).
// The body is ml-validation.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'ml-validation',
  group: 'tests',
  order: 100,
  title: { en: 'ML validation and fairness', es: 'Validación de ML y equidad' },
};
