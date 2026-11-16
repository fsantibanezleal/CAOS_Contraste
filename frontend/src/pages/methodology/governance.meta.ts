// The metadata of the Methodology section `governance`: what the page's tab list needs without loading the section (BL-102).
// The body is governance.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'governance',
  group: 'models',
  order: 300,
  title: { en: 'Model governance', es: 'Gobernanza de modelos' },
};
