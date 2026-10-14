// The coverage row of the case unit U12 builds (C17). A later file replaces the row of the same id in base.ts, so the
// unit that builds a case updates its row here and edits nothing else; whether a case is built is read from the readiness
// and the committed index at run time, never typed here. The data text follows the c17 contracts: a generator of annual
// operational loss histories for a synthetic bank, calibrated to the derived-only BCBS 2008 Loss Data Collection Exercise
// quantiles, whose true annual loss distribution is known.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { PlannedCase } from './base';

const t = (en: string, es: string): BiText => ({ en, es });

export const CASES: PlannedCase[] = [
  {
    id: 'C17',
    category: 'operational',
    title: t('Operational risk: LDA vs SMA', 'Riesgo operacional: LDA vs SMA'),
    data: t(
      'Generator of annual loss histories for a synthetic bank, calibrated to the derived-only BCBS 2008 LDCE quantiles, with a known true annual loss distribution',
      'Generador de historias anuales de pérdidas para un banco sintético, calibrado a los cuantiles derivados del LDCE 2008 del BCBS, con una distribución de pérdida anual verdadera conocida',
    ),
    truth: t('known truth', 'verdad conocida'),
    unit: 'U12',
  },
];
