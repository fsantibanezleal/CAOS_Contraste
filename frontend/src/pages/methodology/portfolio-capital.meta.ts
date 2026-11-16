// The metadata of the Methodology section `portfolio-capital`: what the page's tab list needs without loading the section (BL-102).
// The body is portfolio-capital.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'portfolio-capital',
  group: 'capital',
  order: 120,
  title: { en: 'Portfolio credit capital', es: 'Capital de crédito de cartera' },
};
