// The coverage rows of the case unit U14 builds (C02, C20 and C21). A later file replaces the row of the same id in base.ts,
// so the unit that builds a case updates its row here and edits nothing else; whether a case is built is read from the
// readiness and the committed index at run time, never typed here. The data text follows the c02, c20 and c21 contracts:
// the five UCI Polish bankruptcy horizon files (no date, no firm identifier, overlap of firms unknown), the stressed German
// credit data of SantanderAI with the UCI sets and the Federal Reserve 2025 corporate portfolios as shift probes, and the
// HMDA loan-level decisions of one state (the licence sentence of the data stays unverified).
import type { BiText } from '@fasl-work/caos-app-shell';
import type { PlannedCase } from './base';

const t = (en: string, es: string): BiText => ({ en, es });

export const CASES: PlannedCase[] = [
  {
    id: 'C02',
    category: 'credit-scoring',
    title: t('Corporate PD across 1 to 5 year horizons', 'PD corporativa a horizontes de 1 a 5 años'),
    data: t(
      'UCI Polish companies bankruptcy, the five horizon files (no date and no firm identifier, so no out-of-time claim), with the transfer between horizons and the term structure labelled exploratory',
      'Quiebras de empresas polacas de UCI, los cinco archivos de horizonte (sin fecha ni identificador de empresa, así que sin afirmación fuera del tiempo), con la transferencia entre horizontes y la estructura de plazos etiquetadas como exploratorias',
    ),
    truth: t('real outcomes', 'resultados reales'),
    unit: 'U14',
  },
  {
    id: 'C20',
    category: 'ml-ai-risk',
    title: t('ML model validation: drift, robustness, explanation stability', 'Validación de modelos de ML: deriva, robustez, estabilidad de explicaciones'),
    data: t(
      'UCI German, Taiwan and Polish credit sets, the SantanderAI stressed German credit data (research and benchmarking only), and the Federal Reserve 2025 corporate portfolios as shift probes, read both as real drift and as the reference of a synthetic shift',
      'Conjuntos de crédito de UCI (alemán, Taiwán y polaco), los datos de crédito alemán estresados de SantanderAI (solo investigación y comparación) y las carteras corporativas 2025 de la Reserva Federal como sondas de cambio, leídas como deriva real y como referencia de un cambio sintético',
    ),
    truth: t('real outcomes and known shifts', 'resultados reales y cambios conocidos'),
    unit: 'U14',
  },
  {
    id: 'C21',
    category: 'ml-ai-risk',
    title: t('Fair-lending disparity testing', 'Pruebas de disparidad en crédito justo'),
    data: t(
      'HMDA loan-level application decisions of one state for 2018 to 2024 (the data licence sentence is unverified); statistical disparity only, with no legal claim',
      'Decisiones de solicitudes de HMDA a nivel de préstamo de un estado para 2018 a 2024 (la frase de licencia de los datos no está verificada); solo disparidad estadística, sin afirmación legal',
    ),
    truth: t('real decisions', 'decisiones reales'),
    unit: 'U14',
  },
];
