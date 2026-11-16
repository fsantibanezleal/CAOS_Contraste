// The metadata of the Methodology section `lgd-ead`: what the page's tab list needs without loading the section (BL-102).
// The body is lgd-ead.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'lgd-ead',
  group: 'loss',
  order: 110,
  title: { en: 'LGD and EAD', es: 'LGD y EAD' },
};
