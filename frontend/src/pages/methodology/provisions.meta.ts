// The metadata of the Methodology section `provisions`: what the page's tab list needs without loading the section (BL-102).
// The body is provisions.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'provisions',
  group: 'loss',
  order: 100,
  title: { en: 'Provisions', es: 'Provisiones' },
};
