// The metadata of the Methodology section `liquidity`: what the page's tab list needs without loading the section (BL-102).
// The body is liquidity.tsx, loaded when its tab opens; the registry pairs the two files by this stem.
import type { MethodologySectionMeta } from '../methodologyRegistry';

export const methodologyMeta: MethodologySectionMeta = {
  id: 'liquidity',
  group: 'balance',
  order: 130,
  title: { en: 'Liquidity (LCR and stress)', es: 'Liquidez (LCR y estrés)' },
};
