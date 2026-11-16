// The metadata of the Methodology section `regulation`: what the page's tab list needs without loading the section (BL-102).
// The body is regulation.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'regulation',
  group: 'capital',
  order: 230,
  title: { en: 'Regulation map (Basel calculators)', es: 'Mapa regulatorio (calculadoras de Basilea)' },
};
