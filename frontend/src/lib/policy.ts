// The live policy (SDD section 3, CT-104): the thresholds that turn a test's p-value into a light are an
// institution's choice, not regulation (the ECB's 2019 validation-reporting instructions define the tests and set no
// pass or fail thresholds; riskvalidation's policy file says so). The rail lets a reader set them; every light is
// re-computed here with the same rule as riskvalidation's Threshold.classify for kind "p_value": red if p < red,
// amber if p < amber, green otherwise. With the committed alphas the result equals the committed light exactly
// (engine/parity.test.ts).
import type { Light, TestRow, Text } from './contract.types';

export interface PolicyAlphas {
  amber: number;
  red: number;
}

/** The policy the committed artifacts were evaluated under (riskvalidation-default 2026.10.0). */
export const COMMITTED: PolicyAlphas = { amber: 0.05, red: 0.01 };

/** True when the committed row was evaluated by a p-value threshold (a descriptive test carries none). */
export function evaluated(row: TestRow): boolean {
  return row.alpha_amber !== null && row.alpha_red !== null && row.light !== 'error';
}

export function relight(row: TestRow, alphas: PolicyAlphas): Light {
  if (!evaluated(row)) return row.light;
  const p = row.p_value;
  if (p === null || !Number.isFinite(p)) return 'not_evaluated';
  if (p < alphas.red) return 'red';
  return p < alphas.amber ? 'amber' : 'green';
}

/** A regulatory paragraph a row carries for its threshold, if any (none does today: no regulation fixes them). */
export function regulatoryReference(row: TestRow): string | null {
  const ref = row.extras?.regulatory_threshold_reference;
  return typeof ref === 'string' && ref.trim() ? ref : null;
}

/** How a threshold is labelled on screen: as the policy it is, unless the row carries a regulatory reference. */
export function thresholdLabel(row: TestRow, alphas: PolicyAlphas): Text {
  const reg = regulatoryReference(row);
  if (reg) return { en: `Regulatory threshold (${reg})`, es: `Umbral regulatorio (${reg})` };
  if (!evaluated(row)) return { en: 'Descriptive: no threshold in the policy', es: 'Descriptiva: sin umbral en la política' };
  return {
    en: `Policy threshold, not regulatory: amber below ${alphas.amber}, red below ${alphas.red} (${row.policy_version})`,
    es: `Umbral de política, no regulatorio: ámbar bajo ${String(alphas.amber).replace('.', ',')}, rojo bajo ${String(alphas.red).replace('.', ',')} (${row.policy_version})`,
  };
}

export const LIGHT_TEXT: Record<Light, Text> = {
  green: { en: 'green', es: 'verde' },
  amber: { en: 'amber', es: 'ámbar' },
  red: { en: 'red', es: 'rojo' },
  not_evaluated: { en: 'not evaluated', es: 'no evaluada' },
  error: { en: 'error', es: 'error' },
};

export const LIGHT_TONE: Record<Light, 'good' | 'warn' | 'bad' | 'neutral'> = {
  green: 'good',
  amber: 'warn',
  red: 'bad',
  not_evaluated: 'neutral',
  error: 'bad',
};
