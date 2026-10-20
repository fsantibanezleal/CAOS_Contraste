// What the three U14 instruments (C02, C20 and C21) share: the words of the tests of the ML and fairness engines, the
// tests table (a test that did not run shows its reason, never a number), the label of an exploratory block, the named
// parameters (each a convention, never a regulatory threshold; 06 I.6 l.1268-1270) and the number formats. Nothing here
// computes a statistic.
import { formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import type { TestRow } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import type { Bi } from '../c03/U6Shared';

export type Lang = 'en' | 'es';

export const f2 = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { decimals: 2 });
export const f3 = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { decimals: 3 });
export const f4 = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { decimals: 4 });
export const pc = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { percent: true, decimals: 2 });
export const pc1 = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { percent: true, decimals: 1 });
export const sig = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { digits: 2 });
export const int = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { decimals: 0 });

/** The height a horizontal bar chart of `rows` rows needs (about 1.8 rem a row and the axis): below it the rows scroll in the drawing. */
export const barMin = (rows: number): string => `${Math.max(9, 3.6 + rows * 1.8)}rem`;

/** The words of the tests the ML validation and fairness engines return; an id without an entry is shown as it is. */
export const TEST_TEXT: Record<string, Bi> = {
  'disc.auc': { en: 'AUC (descriptive)', es: 'AUC (descriptiva)' },
  'disc.delong': { en: 'DeLong against the champion', es: 'DeLong contra el campeón' },
  'disc.ks': { en: 'Kolmogorov-Smirnov (descriptive)', es: 'Kolmogorov-Smirnov (descriptiva)' },
  'pd.hosmer_lemeshow': { en: 'Hosmer-Lemeshow', es: 'Hosmer-Lemeshow' },
  'pd.brier': { en: 'Brier score (descriptive)', es: 'Puntaje de Brier (descriptiva)' },
  'pd.ece': { en: 'Expected calibration error (descriptive)', es: 'Error de calibración esperado (descriptiva)' },
  'stability.psi': { en: 'PSI against the training slice', es: 'PSI contra el tramo de entrenamiento' },
  'stability.csi': { en: 'CSI of each input', es: 'CSI de cada variable' },
  'ml.robustness': { en: 'Robustness to input noise', es: 'Robustez ante ruido en las entradas' },
  'ml.shift_resilience': { en: 'Resilience to distribution shift', es: 'Resiliencia ante un cambio de distribución' },
  'ml.seed_stability': { en: 'Stability across retraining seeds', es: 'Estabilidad entre semillas de reentrenamiento' },
  'ml.reason_code_stability': { en: 'Stability of the reason codes', es: 'Estabilidad de los códigos de razón' },
  'ml.effect_agreement': { en: 'Agreement of attributions and effect curves', es: 'Acuerdo entre atribuciones y curvas de efecto' },
  'ml.additivity': { en: 'Additivity of the attributions', es: 'Aditividad de las atribuciones' },
  'ml.overfit': { en: 'Overfit gap', es: 'Brecha de sobreajuste' },
  'ml.weak_spot': { en: 'Weak spots by slice', es: 'Puntos débiles por segmento' },
  'ml.conformal_coverage': { en: 'Conformal coverage', es: 'Cobertura conforme' },
  'ml.data_quality': { en: 'Data quality', es: 'Calidad de datos' },
  'ml.cbpe_estimate': { en: 'Label-free performance estimate (CBPE)', es: 'Estimación de desempeño sin etiquetas (CBPE)' },
  'ml.challenger_brier': { en: 'Challenger: paired Brier difference', es: 'Retador: diferencia pareada de Brier' },
  'ml.leakage_screen.temporal_order': { en: 'Leakage screen: temporal order', es: 'Filtro de fuga: orden temporal' },
  'ml.leakage_screen.single_feature_auc': { en: 'Leakage screen: single-feature AUC', es: 'Filtro de fuga: AUC de una sola variable' },
  'ml.leakage_screen.entity_overlap': { en: 'Leakage screen: entity overlap', es: 'Filtro de fuga: solapamiento de entidades' },
  'ml.leakage_screen.resemblance_auc': { en: 'Leakage screen: resemblance AUC', es: 'Filtro de fuga: AUC de parecido' },
  'fair.demographic_parity': { en: 'Demographic parity', es: 'Paridad demográfica' },
  'fair.adverse_impact': { en: 'Adverse impact ratio', es: 'Razón de impacto adverso' },
  'fair.two_proportion_z': { en: 'Two-proportion z-test', es: 'Prueba z de dos proporciones' },
  'fair.fisher_exact': { en: 'Fisher exact test', es: 'Prueba exacta de Fisher' },
  'fair.conditional_disparity': { en: 'Disparity after the permitted controls', es: 'Disparidad tras los controles permitidos' },
  'fair.rate_spread_disparity': { en: 'Rate-spread disparity', es: 'Disparidad en el diferencial de tasa' },
  'fair.replication': { en: 'Replication on the next year', es: 'Replicación en el año siguiente' },
  'fair.situation_testing': { en: 'Situation testing', es: 'Pruebas de situación' },
  'fair.equalized_odds': { en: 'Equalized odds', es: 'Probabilidades igualadas' },
  'fair.equal_opportunity': { en: 'Equal opportunity', es: 'Igualdad de oportunidades' },
  'fair.calibration_within_groups': { en: 'Calibration within groups', es: 'Calibración dentro de los grupos' },
  'fair.auc_by_group': { en: 'AUC by group', es: 'AUC por grupo' },
};
export const testName = (id: string): Bi => TEST_TEXT[id] ?? { en: id, es: id };

/** The names of the named parameters (the contract's `name` enum), in words. */
export const PARAM_TEXT: Record<string, Bi> = {
  perturbation_grid: { en: 'Noise scales of the perturbation grid', es: 'Escalas de ruido de la grilla de perturbación' },
  perturbation_tolerance: { en: 'Tolerated AUC degradation under noise', es: 'Degradación de AUC tolerada bajo ruido' },
  n_seeds: { en: 'Retraining seeds', es: 'Semillas de reentrenamiento' },
  n_bootstrap_refits: { en: 'Bootstrap refits for the reason codes', es: 'Reajustes bootstrap de los códigos de razón' },
  overfit_tolerance: { en: 'Overfit tolerance', es: 'Tolerancia de sobreajuste' },
  weak_spot_multiple: { en: 'Weak-spot multiple of the average error', es: 'Múltiplo del error medio para un punto débil' },
  shift_score: { en: 'Shift score ranking the subsamples', es: 'Puntaje de cambio que ordena las submuestras' },
  worst_subsample_share: { en: 'Share of the evaluation rows in the worst subsample', es: 'Parte de las filas de evaluación en la peor submuestra' },
  decision_cutoff_reject_share: { en: 'Share of baseline decisions declined at the cut-off', es: 'Parte de las decisiones base rechazadas en el corte' },
};

/** A named parameter's value in its own unit: a number, a list of numbers, or the name of a score. */
export function paramValue(value: unknown, lang: Lang): string {
  if (Array.isArray(value)) return value.map((v) => formatNumber(v as number, lang, { digits: 3 })).join(', ');
  if (typeof value === 'number') return formatNumber(value, lang, { digits: 4 });
  return String(value);
}

export interface NamedParam {
  name: string;
  value: unknown;
  unit: string;
  label: string;
  basis: string;
}

/** The named parameters of a document, each with the word "convention" (never a regulatory threshold) and where its value comes from. */
export function ParamTable({ params, only }: { params: NamedParam[]; only?: string[] }) {
  const lang = useShellLang();
  const rows = only ? params.filter((p) => only.includes(p.name)) : params;
  return (
    <table className="caos-table ct-wrap-head" data-table="parameters">
      <thead>
        <tr>
          <th className="ct-text">{pick({ en: 'Parameter', es: 'Parámetro' }, lang)}</th>
          <th>{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
          <th className="ct-text">{pick({ en: 'Status', es: 'Estatus' }, lang)}</th>
          <th className="ct-text ct-wide-only">{pick({ en: 'Where it comes from', es: 'De dónde viene' }, lang)}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((p) => (
          <tr key={p.name} data-parameter={p.name} data-status={p.label}>
            <td className="ct-text">{pick(PARAM_TEXT[p.name] ?? { en: p.name, es: p.name }, lang)}</td>
            <td>{`${paramValue(p.value, lang)} ${p.unit === 'name of the score' ? '' : p.unit}`.trim()}</td>
            <td className="ct-text">{p.label === 'convention' ? pick({ en: 'convention', es: 'convención' }, lang) : p.label}</td>
            <td className="ct-text ct-wide-only">{p.basis}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** The words of the labels the documents put on a block that is a reading and not a result. */
export const LABEL_TEXT: Record<string, Bi> = {
  exploratory: { en: 'Exploratory', es: 'Exploratorio' },
  estimate: { en: 'Estimate, not a measurement', es: 'Estimación, no una medición' },
  convention: { en: 'Convention', es: 'Convención' },
  'real-drift-no-model': { en: 'Real drift, no model', es: 'Deriva real, sin modelo' },
  'synthetic-shift-fed-reference': { en: 'Synthetic shift', es: 'Cambio sintético' },
  'labelled-fairness-battery': { en: 'Labelled evidence', es: 'Evidencia etiquetada' },
  'decision-flip': { en: 'Decision flips', es: 'Decisiones que cambian' },
};

/** The label of a block that is a reading and not a result: exploratory, with its reason, said before the content. */
export function Labelled({ label, reason, children }: { label: string; reason: BiText; children?: ReactNode }) {
  const lang = useShellLang();
  const word = LABEL_TEXT[label] ?? { en: label, es: label };
  return (
    <p className="ct-note" data-label={label}>
      <strong>{pick(word, lang)}.</strong> {pick(reason, lang)}
      {children}
    </p>
  );
}

/**
 * A drawing over its tables inside one filling card, with an optional label first (exploratory, a convention, a notice):
 * the label takes its own height, the drawing the height the tables leave and the tables scroll under it, so the card
 * never overflows (ADR-0071 rule 8). `chartMin` is the drawing's least height: a horizontal bar chart needs about
 * 1.8 rem a row or its rows scroll inside the drawing.
 */
export function LabelledOverTable({ head, chart, children, chartMin = '15rem' }: { head?: ReactNode; chart?: ReactNode; children?: ReactNode; chartMin?: string }) {
  return (
    <div className="ct-stack">
      {head}
      {chart ? <div style={{ flex: '1 1 0', minHeight: chartMin, display: 'flex', flexDirection: 'column' }}>{chart}</div> : null}
      {children ? <div style={chart ? { flex: '0 1 auto', maxHeight: '42%', overflow: 'auto', minHeight: 0 } : { flex: '1 1 0', overflow: 'auto', minHeight: 0 }}>{children}</div> : null}
    </div>
  );
}

/** The rows the engine returned for the tests of this variant, under the drawing they belong to: a test that did not run says why and shows no number. */
export function U14TestsTable({ tests, modelLabel, only }: { tests: TestRow[]; modelLabel?: (id: string) => string; only?: (t: TestRow) => boolean }) {
  const lang = useShellLang();
  const rows = only ? tests.filter(only) : tests;
  return (
    <div data-block="tests">
      <p className="ct-note">
        {pick({ en: 'The tests the engine returned: the statistic when it ran, the light under the committed policy and its reference. A test that did not run says why and shows no number.', es: 'Las pruebas que devolvió el motor: el estadístico cuando corrió, la luz bajo la política comprometida y su referencia. Una prueba que no corrió dice por qué y no muestra número.' }, lang)}
      </p>
      {rows.length === 0 ? (
        <p className="ct-note" data-state="unavailable">{pick({ en: 'This variant carries no test row for this view.', es: 'Esta variante no trae filas de pruebas para esta vista.' }, lang)}</p>
      ) : (
        <table className="caos-table ct-wrap-head" data-table="tests">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
              <th>{pick({ en: 'Statistic', es: 'Estadístico' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Reason or note', es: 'Razón o nota' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t, i) => {
              const ran = t.light !== 'not_evaluated' && t.light !== 'error';
              return (
                <tr key={`${t.test_id}-${t.model_id}-${t.segment}-${i}`} data-test={t.test_id} data-light={t.light}>
                  <td className="ct-text">{pick(testName(t.test_id), lang)}</td>
                  <td className="ct-text ct-wide-only">{t.model_id === null ? '-' : (modelLabel?.(t.model_id) ?? t.model_id)}</td>
                  <td data-na={ran && t.statistic !== null ? undefined : 'true'}>{ran && t.statistic !== null ? formatNumber(t.statistic, lang, { digits: 4 }) : formatNumber(null, lang)}</td>
                  <td className={`ct-text ct-light ct-light-${t.light}`}>
                    <span className="ct-light-word">{pick(LIGHT_TEXT[t.light], lang)}</span>
                  </td>
                  <td className="ct-text">{t.notes ?? t.reference}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
