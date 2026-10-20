// The coverage rows of the unit U13 builds: C18 is built (its data text follows the c18 contracts) and C19 stays planned, with
// its reason in the row. A later file replaces the row of the same id in base.ts, so the unit that builds a case updates its
// row here and edits nothing else; whether a case is built is read from the readiness and the committed index at run time,
// never typed here. The C19 reason is the main session's decision E1 of the U13 sizing: no Federal Reserve hypothetical
// portfolio type is replicable, so none is built, and the case is revisited when one vintage has an answer key, coefficients
// and inputs that are public.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { PlannedCase } from './base';

const t = (en: string, es: string): BiText => ({ en, es });

export const CASES: PlannedCase[] = [
  {
    id: 'C18',
    category: 'capital-stress',
    title: t('ICAAP and IAPE capital aggregation under macro scenarios', 'Agregación de capital ICAAP e IAPE bajo escenarios macro'),
    data: t(
      'Federal Reserve 2026 severely adverse, EBA and ESRB 2025 adverse and NGFS Phase V delayed transition paths on the synthetic Banco Andino, with satellites fitted on the Federal Reserve charge-off rates before 2020 and back-cast through 2020 to 2025',
      'Trayectorias severamente adversa de la Reserva Federal 2026, adversa de la EBA y la ESRB 2025 y de transición tardía de NGFS Fase V sobre el Banco Andino sintético, con satélites ajustados en las tasas de castigo de la Reserva Federal anteriores a 2020 y retro-proyectados en 2020 a 2025',
    ),
    truth: t('real paths, synthetic bank', 'trayectorias reales, banco sintético'),
    unit: 'U13',
  },
  {
    id: 'C19',
    category: 'capital-stress',
    title: t('Supervisory stress model replication (known answer)', 'Réplica de modelos supervisores de estrés (respuesta conocida)'),
    data: t(
      'Planned, not built: no Federal Reserve hypothetical portfolio type can be replicated yet. The published loss rates name the 2024 severely adverse scenario and a 2025 model vintage, the only public coefficients describe the 2026 proposal, and every type needs inputs outside the 200-loan files. It is revisited when one vintage has an answer key, coefficients and inputs that are public',
      'Planificado, no construido: aún no se puede replicar ningún tipo de cartera hipotética de la Reserva Federal. Las tasas de pérdida publicadas nombran el escenario severamente adverso de 2024 y una versión de modelo de 2025, los únicos coeficientes públicos describen la propuesta de 2026, y cada tipo necesita insumos fuera de los archivos de 200 préstamos. Se retoma cuando una versión tenga clave de respuestas, coeficientes e insumos públicos',
    ),
    truth: t('published answers', 'respuestas publicadas'),
    unit: 'U13',
  },
];
