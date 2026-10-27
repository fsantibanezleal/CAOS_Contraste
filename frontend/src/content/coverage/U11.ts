// The coverage row of the case unit U11 builds (C16). A later file replaces the row of the same id in base.ts, so the unit
// that builds a case updates its row here and edits nothing else; whether a case is built is read from the readiness and
// the committed index at run time, never typed here. The data text follows the c16 contracts: the FDIC call reports of the
// bank that failed on 2023-03-10 read up to 2022-12-31 (the last report before the run, with 2021-12-31 and 2022-06-30 as a
// time block), the Federal Reserve H.8 weekly record, the Board's review of the supervision of the bank, the BCBS Table A.1
// rows and the ECB LiST 2019 parameters as transcribed constants, and a depositor generator with a known truth.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { PlannedCase } from './base';

const t = (en: string, es: string): BiText => ({ en, es });

export const CASES: PlannedCase[] = [
  {
    id: 'C16',
    category: 'balance-sheet',
    title: t('Liquidity stress, LCR and the March 2023 run', 'Estrés de liquidez, LCR y la corrida de marzo de 2023'),
    data: t(
      'FDIC call reports of the failed bank read up to 2022-12-31, the Federal Reserve H.8 and review of the supervision of the bank, the BCBS Table A.1 rows and the ECB LiST 2019 parameters as transcribed constants, and a depositor generator with a known truth',
      'Reportes de condición de la FDIC del banco quebrado leídos hasta el 31 de diciembre de 2022, el H.8 y la revisión de la supervisión del banco de la Reserva Federal, las filas de la Tabla A.1 del BCBS y los parámetros de ECB LiST 2019 como constantes transcritas, y un generador de depositantes con verdad conocida',
    ),
    truth: t('real event, synthetic deposits', 'evento real, depósitos sintéticos'),
    unit: 'U11',
  },
];
