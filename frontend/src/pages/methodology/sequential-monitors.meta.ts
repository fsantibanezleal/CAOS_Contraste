// The metadata of the Methodology section `sequential-monitors`: what the page's tab list needs without loading the section (BL-102).
// The body is sequential-monitors.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'sequential-monitors',
  group: 'market',
  order: 210,
  title: { en: 'Sequential monitors', es: 'Monitores secuenciales' },
};
