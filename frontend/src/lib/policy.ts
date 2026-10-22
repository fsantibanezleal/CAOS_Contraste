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
/** The tolerance of a row lit by a tolerance on its metric (the CCF estimator bias of C09: its light depends only on the
 * bias against the tolerance, its p-value is informative; engine contract lgd-ead-api), or null. */
export function toleranceOf(row: TestRow): number | null {
  const tol = (row.extras as { thresholds?: { tolerance?: unknown } } | null | undefined)?.thresholds?.tolerance;
  return typeof tol === 'number' && Number.isFinite(tol) ? tol : null;
}

/** True when the row's light comes from a tolerance on its metric, not from its p-value: the policy rail does not move it. */
export function toleranceEvaluated(row: TestRow): boolean {
  return row.alpha_amber !== null && row.alpha_red !== null && row.light !== 'error' && toleranceOf(row) !== null;
}

export function evaluated(row: TestRow): boolean {
  return row.alpha_amber !== null && row.alpha_red !== null && row.light !== 'error' && row.p_value !== null && toleranceOf(row) === null;
}

/** True when the row's alphas are the confidence levels of an acceptance band, not p-value thresholds: it carries
 * them without a p-value (the IFRS 9 lifetime PD backtest's Vasicek band, provisions API contract). The policy rail
 * does not move such a light; it stays the committed one. */
export function bandEvaluated(row: TestRow): boolean {
  return row.alpha_amber !== null && row.alpha_red !== null && row.light !== 'error' && row.p_value === null && !ownPolicyEvaluated(row);
}

/** A packaged battery policy of the engine (riskvalidation 1.0.0, one versioned file per battery): `contraste-<battery>
 * <version>`, with `+custom` when the row was computed with other cut points (D16-17). */
export const PACKAGED_POLICY = /^contraste-[a-z0-9-]+ \d+\.\d+\.\d+(\+custom)?$/;

/** True when a row was lit under its test family's own policy, not the product's: its alphas differ from COMMITTED and
 * its policy_version names that policy, as a packaged battery label (from riskvalidation 1.0.0, the alphas in the row)
 * or, in a document baked before 1.0.0, with the alphas written into the label (C11's market back-tests: Kupiec,
 * Christoffersen and duration amber below 0.10 and red below 0.05, Acerbi-Szekely amber below 0.05 and red below
 * 0.0001, the reviewed engine-market-api levels on which C11's eligibility gates are defined). The policy rail does not
 * move such a light; it stays the committed one. */
export function ownPolicyEvaluated(row: TestRow): boolean {
  return (
    row.alpha_amber !== null && row.alpha_red !== null && row.light !== 'error' && toleranceOf(row) === null &&
    (row.alpha_amber !== COMMITTED.amber || row.alpha_red !== COMMITTED.red) &&
    (PACKAGED_POLICY.test(row.policy_version) || /alpha_amber=/.test(row.policy_version))
  ); // a row the family could not evaluate (an undefined ES) is one too: it keeps its committed not_evaluated
}

/** The light of an evaluated p-value row under the given alphas: red if p < red, amber if p < amber, green otherwise. */
export function lightUnder(row: TestRow, alphas: PolicyAlphas): Light {
  if (!evaluated(row)) return row.light;
  const p = row.p_value as number;
  if (!Number.isFinite(p)) return 'not_evaluated';
  if (p < alphas.red) return 'red';
  return p < alphas.amber ? 'amber' : 'green';
}

/** The light a row shows under the rail's alphas: re-computed for a row of the product policy, the committed one otherwise. */
export function relight(row: TestRow, alphas: PolicyAlphas): Light {
  return ownPolicyEvaluated(row) ? row.light : lightUnder(row, alphas);
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
  if (toleranceEvaluated(row)) {
    const tol = toleranceOf(row) as number;
    return {
      en: `Policy tolerance, not regulatory: the light compares the metric with a tolerance of ${tol} (${row.policy_version}); the policy rail does not change it`,
      es: `Tolerancia de política, no regulatoria: la luz compara la métrica con una tolerancia de ${String(tol).replace('.', ',')} (${row.policy_version}); el control de política no la cambia`,
    };
  }
  if (ownPolicyEvaluated(row))
    return {
      en: `Policy threshold of its test family, not regulatory: amber below ${row.alpha_amber}, red below ${row.alpha_red} (${row.policy_version}); the policy rail does not change it`,
      es: `Umbral de política de su familia de pruebas, no regulatorio: ámbar bajo ${String(row.alpha_amber).replace('.', ',')}, rojo bajo ${String(row.alpha_red).replace('.', ',')} (${row.policy_version}); el control de política no lo cambia`,
    };
  if (bandEvaluated(row))
    return {
      en: `Policy acceptance band, not regulatory: amber outside the ${row.alpha_amber} band, red outside the ${row.alpha_red} band (${row.policy_version}); the policy rail does not change it`,
      es: `Banda de aceptación de política, no regulatoria: ámbar fuera de la banda ${String(row.alpha_amber).replace('.', ',')}, rojo fuera de la banda ${String(row.alpha_red).replace('.', ',')} (${row.policy_version}); el control de política no la cambia`,
    };
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
