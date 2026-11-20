// The metadata of the Methodology section `reject-inference`: what the page's tab list needs without loading the section (BL-102).
// The body is reject-inference.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'reject-inference',
  group: 'models',
  order: 400,
  title: { en: 'Reject inference', es: 'Inferencia de rechazados' },
};
