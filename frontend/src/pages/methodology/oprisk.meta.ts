// The metadata of the Methodology section `oprisk`: what the page's tab list needs without loading the section (BL-102).
// The body is oprisk.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'oprisk',
  group: 'capital',
  order: 210,
  title: { en: 'Operational risk', es: 'Riesgo operacional' },
};
