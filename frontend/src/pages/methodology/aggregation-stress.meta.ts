// The metadata of the Methodology section `aggregation-stress`: what the page's tab list needs without loading the section (BL-102).
// The body is aggregation-stress.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'aggregation-stress',
  group: 'capital',
  order: 140,
  title: { en: 'Aggregation and stress testing', es: 'Agregación y pruebas de estrés' },
};
