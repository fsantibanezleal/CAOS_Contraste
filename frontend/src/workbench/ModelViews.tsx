// The Model group: what each rung of the ladder is and what it learned. The ladder (every rung's held-out
// discrimination and calibration beside its ROC) and the internals of the rungs: the scorecard's points table with the
// live applicant, the EBM's shape functions, the GBM's monotone partial dependence and reason-code stability, the L1
// regression's coefficients and PLTR's rules, TabPFN. Every view fills the panel with a table beside or above the
// drawing of the same numbers (ADR-0071 rule 8).
import { PlotCard, SubTabs, Verdict, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo, type ReactElement } from 'react';
import type { EbmExport, GbmDetails, ModelRecord, ScorecardDetails } from '../lib/contract.types';
import { liveScores } from './Workbench';
import { CHAMPION, REPLAY, extra, grid, interp, provenanceOf, rung, shortName, test, value, type Selection } from './model';
import { Pending } from './Pending';

const PALETTE = ['--color-fg-subtle', '--color-accent', '--color-accent-2', '--color-magenta', '--color-good', '--color-warn', '--color-bad', '--color-fg'] as const;

function details<T>(sel: Selection, id: string): T | undefined {
  return sel.data.models.model.find((m) => m.id === id)?.details as T | undefined;
}

function record(sel: Selection, id: string): ModelRecord | undefined {
  return sel.data.models.model.find((m) => m.id === id);
}

/** Every rung on this variant: AUC with its 95% interval, the paired DeLong test, Brier, ECE; the ROC curves beside. */
export function LadderView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const rows = useMemo(() => {
    if (!sel) return null;
    const v = sel.data.variant;
    return v.model.map((m) => {
      const auc = test(v, 'disc.auc', m.id);
      return {
        m,
        auc: value(auc),
        lo: extra(auc, 'ci95_low'),
        hi: extra(auc, 'ci95_high'),
        brier: value(test(v, 'pd.brier', m.id)),
        ece: value(test(v, 'pd.ece', m.id)),
        delongP: test(v, 'disc.delong', m.id)?.p_value ?? null,
      };
    });
  }, [sel]);
  const roc = useMemo(() => {
    if (!sel) return null;
    const x = grid(0, 1, 101);
    const series = sel.data.variant.model.map((m, k) => ({
      label: shortName(m, m.id),
      values: interp(sel.data.variant.outputs.rungs[m.id].roc.fpr, sel.data.variant.outputs.rungs[m.id].roc.tpr, x),
      color: PALETTE[k % PALETTE.length],
      width: m.id === CHAMPION ? 2.5 : 1.5,
      dash: m.rung === 'P0' ? [5, 4] : undefined,
    }));
    return { x, series };
  }, [sel]);
  if (!sel || !rows || !roc) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const f = (v: number | null, d = 3) => formatNumber(v, lang, { decimals: d });
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: 'The ladder on this variant', es: 'La escalera en esta variante' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: 'Held-out AUC with its DeLong 95% interval, the paired DeLong test against the scorecard, and the calibration of each rung (Brier, ECE). Engines and licences are in the Context group.',
            es: 'AUC fuera de muestra con su intervalo 95% de DeLong, la prueba pareada de DeLong contra la scorecard y la calibración de cada peldaño (Brier, ECE). Motores y licencias están en el grupo Contexto.',
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table">
              <thead>
                <tr>
                  <th>{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
                  <th>AUC</th>
                  <th className="ct-wide-only">{pick({ en: '95% interval', es: 'Intervalo 95%' }, lang)}</th>
                  <th>{pick({ en: 'DeLong p', es: 'p de DeLong' }, lang)}</th>
                  <th>Brier</th>
                  <th className="ct-wide-only">ECE</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.m.id} data-rung={r.m.id} title={`${pick(r.m.title, lang)}: ${r.m.engine} (${r.m.licence})`}>
                    <td>{pick(shortName(r.m, r.m.id), lang)}</td>
                    <td>{f(r.auc)}</td>
                    <td className="ct-wide-only">{r.lo !== null && r.hi !== null ? `${f(r.lo)} - ${f(r.hi)}` : ''}</td>
                    <td>{r.m.id === CHAMPION ? pick({ en: 'champion', es: 'campeón' }, lang) : formatNumber(r.delongP, lang, { digits: 2 })}</td>
                    <td>{f(r.brier, 4)}</td>
                    <td className="ct-wide-only">{f(r.ece, 4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
      <div className="ct-col ct-share-2">
        <PlotCard
          fill
          title={{ en: 'ROC curves of every rung', es: 'Curvas ROC de cada peldaño' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{ en: 'Defaulters caught against non-defaulters flagged, riskier first. Dashed: the P0 anchors.', es: 'Incumplidores detectados contra no incumplidores marcados, de mayor a menor riesgo. Segmentadas: los anclajes P0.' }}
        >
          <UPlotChart
            height="fill"
            x={{ values: roc.x, label: { en: 'False positive rate', es: 'Tasa de falsos positivos' }, format: { decimals: 2 } }}
            y={{ label: { en: 'True positive rate', es: 'Tasa de verdaderos positivos' }, range: [0, 1], format: { decimals: 2 } }}
            series={roc.series}
          />
        </PlotCard>
      </div>
    </div>
  );
}

/** The scorecard's points table, the variables it dropped and why, the live applicant's points and reasons, and where
 * the applicant's PD sits among the variant's defaulters and non-defaulters. */
export function ScorecardView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const sc = sel ? details<ScorecardDetails>(sel, CHAMPION) : undefined;
  const live = useMemo(() => liveScores(sel), [sel]);
  const reasons = useMemo(() => {
    if (!sc || !live) return null;
    // Regulation B comment 9(b)(2)-5: the characteristics where the applicant fell furthest below the average points
    // of all applicants (here, the training applicants, from the counts of the points table)
    return sc.features
      .map((f, j) => {
        const rows = sc.points_table.filter((r) => r.feature === f);
        const n = rows.reduce((a, r) => a + r.count, 0);
        const avg = rows.reduce((a, r) => a + r.count * r.points, 0) / (n || 1);
        return { feature: f, shortfall: avg - live.card.points[j], points: live.card.points[j], avg };
      })
      .filter((r) => r.shortfall > 0)
      .sort((a, b) => b.shortfall - a.shortfall)
      .slice(0, 4);
  }, [sc, live]);
  const dist = useMemo(() => {
    if (!sel) return null;
    const d = sel.data.variant.outputs.rungs[CHAMPION].distribution;
    const mids = d.log10_pd_edges.slice(0, -1).map((e, i) => 10 ** ((e + d.log10_pd_edges[i + 1]) / 2));
    const nD = d.defaulters.reduce((a, b) => a + b, 0) || 1;
    const nN = d.non_defaulters.reduce((a, b) => a + b, 0) || 1;
    return { x: mids, def: d.defaulters.map((n) => n / nD), non: d.non_defaulters.map((n) => n / nN) };
  }, [sel]);
  if (!sel || !sc || !dist) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const f = (v: number | null, d = 3) => formatNumber(v, lang, { decimals: d });
  const dropped = Object.entries(sc.dropped)
    .map(([k, why]) => `${k} (${why})`)
    .join('; ');
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: 'Points table (WoE, PDO scaling)', es: 'Tabla de puntos (WoE, escala PDO)' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `${formatNumber(sc.scaling.score_ref, 'en', { decimals: 0 })} points at odds ${formatNumber(sc.scaling.odds_ref, 'en', { decimals: 0 })} to 1, ${formatNumber(sc.scaling.pdo, 'en', { decimals: 0 })} points to double the odds; bins fitted on the training slice only. Highlighted: the applicant's bins.${dropped ? ` Not in the scorecard: ${dropped}.` : ''}`,
            es: `${formatNumber(sc.scaling.score_ref, 'es', { decimals: 0 })} puntos con odds ${formatNumber(sc.scaling.odds_ref, 'es', { decimals: 0 })} a 1, ${formatNumber(sc.scaling.pdo, 'es', { decimals: 0 })} puntos para duplicar las odds; tramos ajustados solo con el tramo de entrenamiento. Destacados: los tramos del solicitante.${dropped ? ` Fuera de la scorecard: ${dropped}.` : ''}`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table">
              <thead>
                <tr>
                  <th>{pick({ en: 'Characteristic', es: 'Característica' }, lang)}</th>
                  <th className="caos-col-text">{pick({ en: 'Bin', es: 'Tramo' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Count', es: 'Cantidad' }, lang)}</th>
                  <th>{pick({ en: 'Default rate', es: 'Tasa de incumplimiento' }, lang)}</th>
                  <th className="ct-wide-only">WoE</th>
                  <th>{pick({ en: 'Points', es: 'Puntos' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {sc.points_table
                  .filter((r) => r.count > 0)
                  .map((r) => {
                    const j = sc.features.indexOf(r.feature);
                    const here = live ? live.card.rows[j] === r.row : false;
                    return (
                      <tr key={`${r.feature}-${r.row}`} data-current={here ? 'true' : undefined} className={here ? 'ct-current' : undefined}>
                        <td>{r.feature}</td>
                        <td className="caos-col-text">{r.bin}</td>
                        <td className="ct-wide-only">{formatNumber(r.count, lang)}</td>
                        <td>{formatNumber(r.event_rate, lang, { percent: true, decimals: 1 })}</td>
                        <td className="ct-wide-only">{f(r.woe)}</td>
                        <td>{formatNumber(r.points, lang, { decimals: 0 })}</td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
      <div className="ct-col ct-share-2">
        <PlotCard
          title={{ en: 'The applicant in the rail: principal reasons', es: 'El solicitante del panel: razones principales' }}
          lane="live"
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: 'The four characteristics where the applicant fell furthest below the average points of all applicants (Regulation B, comment 9(b)(2)-5).',
            es: 'Las cuatro características donde el solicitante quedó más bajo el promedio de puntos de todos los solicitantes (Regulation B, comentario 9(b)(2)-5).',
          }}
        >
          {live && reasons ? (
            <table className="caos-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th className="caos-col-text">{pick({ en: 'Characteristic', es: 'Característica' }, lang)}</th>
                  <th>{pick({ en: 'Points', es: 'Puntos' }, lang)}</th>
                  <th>{pick({ en: 'Average', es: 'Promedio' }, lang)}</th>
                  <th>{pick({ en: 'Shortfall', es: 'Brecha' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {reasons.map((r, k) => (
                  <tr key={r.feature}>
                    <td>{k + 1}</td>
                    <td className="caos-col-text">{r.feature}</td>
                    <td>{formatNumber(r.points, lang, { decimals: 0 })}</td>
                    <td>{formatNumber(r.avg, lang, { decimals: 1 })}</td>
                    <td>{formatNumber(r.shortfall, lang, { decimals: 1 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="caos-pending">{pick({ en: 'This variant carries no scored sample: pick the holdout or the German twin.', es: 'Esta variante no trae muestra puntuada: elija la muestra reservada o el gemelo alemán.' }, lang)}</p>
          )}
        </PlotCard>
        <PlotCard
          fill
          title={{ en: 'Where this applicant sits', es: 'Dónde se ubica este solicitante' }}
          lane="live"
          provenance={prov}
          dataKey={stateKey}
          note={{ en: "The scorecard's PD of this variant's defaulters and non-defaulters; the marker is the applicant's live PD.", es: 'La PD de la scorecard de los incumplidores y no incumplidores de esta variante; la marca es la PD en vivo del solicitante.' }}
        >
          <UPlotChart
            height="fill"
            x={{ values: dist.x, label: { en: 'PD (bin centre)', es: 'PD (centro del tramo)' }, format: { percent: true, digits: 2 } }}
            y={{ label: { en: 'Share of the group', es: 'Fracción del grupo' }, format: { percent: true, decimals: 0 } }}
            series={[
              { label: { en: 'Defaulters', es: 'Incumplidores' }, values: dist.def, color: '--color-bad' },
              { label: { en: 'Non-defaulters', es: 'No incumplidores' }, values: dist.non, color: '--color-good' },
            ]}
            marks={live ? [{ x: live.pdScorecard, label: { en: 'applicant', es: 'solicitante' } }] : undefined}
          />
        </PlotCard>
      </div>
    </div>
  );
}

function termImportance(ex: EbmExport): Array<{ name: string; spread: number; index: number }> {
  return ex.terms
    .map((t, index) => {
      const flat = (t.scores as unknown[]).flat(2) as number[];
      return { name: t.name, spread: Math.max(...flat) - Math.min(...flat), index };
    })
    .sort((a, b) => b.spread - a.spread);
}

/** The EBM's six strongest main effects: each term's score over its bins (the "boosted scorecard"), and every term
 * by the spread of its scores. */
export function EbmView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const ex = sel ? details<{ export: EbmExport }>(sel, 'P3-ebm')?.export : undefined;
  const shapes = useMemo(() => {
    if (!ex) return null;
    return termImportance(ex)
      .filter((t) => ex.terms[t.index].features.length === 1)
      .slice(0, 6)
      .map((t) => {
        const term = ex.terms[t.index];
        const feat = ex.features[term.features[0]];
        const lv = feat.levels[0];
        const scores = term.scores as number[];
        if (lv.kind === 'continuous') {
          const cuts = lv.cuts ?? [];
          // bin k (1..cuts+1) covers [cut_(k-1), cut_k); plot each bin at its left edge, the first at the first cut
          const x = [cuts[0] - 1e-9, ...cuts];
          return { name: term.name, x, y: scores.slice(1, cuts.length + 2), categorical: false };
        }
        const cats = Object.entries(lv.categories ?? {}).sort((a, b) => a[1] - b[1]);
        return { name: term.name, x: cats.map((_, i) => i + 1), y: cats.map(([, k]) => scores[k]), categorical: true };
      });
  }, [ex]);
  if (!sel || !ex || !shapes) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const pairs = ex.terms.filter((t) => t.features.length === 2).map((t) => t.name);
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-2">
        <PlotCard
          fill
          title={{ en: 'Shape functions of the six strongest terms', es: 'Funciones de forma de los seis términos más fuertes' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Each panel is one term's contribution to the log-odds of default over its bins; their sum plus the intercept is the model. Pairwise terms: ${pairs.join(', ') || 'none'}.`,
            es: `Cada panel es la contribución de un término a las log-odds de incumplimiento sobre sus tramos; su suma más el intercepto es el modelo. Términos de pares: ${pairs.join(', ') || 'ninguno'}.`,
          }}
        >
          <div className="ct-grid6-fill" data-views="6">
            {shapes.map((s) => (
              <div key={s.name} className="ct-small-multiple">
                <UPlotChart
                  height="fill"
                  x={{ values: s.x, label: { en: s.categorical ? `${s.name} (category)` : s.name, es: s.categorical ? `${s.name} (categoría)` : s.name } }}
                  y={{ label: { en: 'Log-odds', es: 'Log-odds' }, format: { decimals: 2 } }}
                  series={[{ label: { en: s.name, es: s.name }, values: s.y, color: '--color-accent', mode: s.categorical ? 'points' : 'line' }]}
                />
              </div>
            ))}
          </div>
        </PlotCard>
      </div>
      <div className="ct-col">
        <PlotCard fill title={{ en: 'Terms by the spread of their scores', es: 'Términos según la amplitud de sus puntajes' }} lane={REPLAY} provenance={prov} dataKey={stateKey} note={{ en: 'Spread: the largest minus the smallest score of the term, in log-odds.', es: 'Amplitud: el mayor menos el menor puntaje del término, en log-odds.' }}>
          <div className="ct-scroll">
            <table className="caos-table">
              <thead>
                <tr>
                  <th className="caos-col-text">{pick({ en: 'Term', es: 'Término' }, lang)}</th>
                  <th>{pick({ en: 'Spread', es: 'Amplitud' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {termImportance(ex).map((t) => (
                  <tr key={t.name}>
                    <td className="caos-col-text">{t.name}</td>
                    <td>{formatNumber(t.spread, lang, { decimals: 3 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

/** The GBM's partial dependence along every constrained feature (centred), its monotonicity verdict and the stability
 * of its reason codes. */
export function GbmView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const g = sel ? details<GbmDetails>(sel, 'P4-lightgbm') : undefined;
  const xg = sel ? record(sel, 'P4-xgboost') : undefined;
  const chart = useMemo(() => {
    if (!g) return null;
    const feats = Object.entries(g.monotonicity.features);
    const levels = (g.monotonicity as unknown as { levels?: number[] }).levels ?? grid(0, 1, feats[0]?.[1].pdp.length ?? 2);
    const top = feats
      .map(([name, f]) => ({ name, f, range: Math.max(...f.pdp) - Math.min(...f.pdp) }))
      .sort((a, b) => b.range - a.range)
      .slice(0, 6);
    return {
      x: levels,
      series: top.map((t, k) => ({
        label: { en: `${t.name} (${t.f.direction > 0 ? 'raises' : 'lowers'} risk)`, es: `${t.name} (${t.f.direction > 0 ? 'sube' : 'baja'} el riesgo)` },
        values: t.f.pdp.map((v) => v - t.f.pdp[0]),
        color: PALETTE[(k + 1) % PALETTE.length],
      })),
    };
  }, [g]);
  if (!sel || !g || !chart) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const stab = sel.data.models.fit.reason_stability;
  const worst = Math.max(...Object.values(g.monotonicity.features).map((f) => f.max_violation));
  return (
    <>
      <PlotCard title={{ en: 'Monotone gradient boosting: the checks', es: 'Gradient boosting monótono: las verificaciones' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <Verdict
          compact
          title={{ en: 'Monotone in every constrained feature', es: 'Monótono en cada variable restringida' }}
          tone={g.monotonicity.monotone ? 'good' : 'bad'}
          verdict={
            g.monotonicity.monotone
              ? { en: `Yes: no individual expectation curve of ${g.monotonicity.rows} records moves against its declared direction (largest move against it: ${formatNumber(worst, 'en', { digits: 3 })}).`, es: `Sí: ninguna curva de expectativa individual de ${g.monotonicity.rows} registros se mueve contra su dirección declarada (mayor movimiento en contra: ${formatNumber(worst, 'es', { digits: 3 })}).` }
              : { en: 'No: some curve moves against its declared direction.', es: 'No: alguna curva se mueve contra su dirección declarada.' }
          }
        />
        <table className="caos-table">
          <tbody>
            <tr>
              <td>{pick({ en: 'Trees (early stopping on the training folds)', es: 'Árboles (detención temprana en los pliegues de entrenamiento)' }, lang)}</td>
              <td>{formatNumber(g.rounds, lang)}</td>
            </tr>
            <tr>
              <td>{pick({ en: 'Reason codes: mean top-4 overlap with 10 bootstrap refits', es: 'Códigos de razón: coincidencia media del top 4 con 10 reajustes bootstrap' }, lang)}</td>
              <td>{stab ? formatNumber(stab.overlap_mean, lang, { percent: true, decimals: 1 }) : pick({ en: 'not computed', es: 'no calculado' }, lang)}</td>
            </tr>
            {xg && (
              <tr>
                <td>{pick({ en: 'XGBoost cross-check, AUC on this variant', es: 'Contraste con XGBoost, AUC en esta variante' }, lang)}</td>
                <td>{formatNumber(value(test(sel.data.variant, 'disc.auc', 'P4-xgboost')), lang, { decimals: 4 })}</td>
              </tr>
            )}
          </tbody>
        </table>
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'Partial dependence of the six strongest constrained features', es: 'Dependencia parcial de las seis variables restringidas más fuertes' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: "Raw log-odds, centred at the lowest quantile, along each feature's quantiles in the training slice.", es: 'Log-odds crudas, centradas en el cuantil más bajo, a lo largo de los cuantiles de cada variable en el tramo de entrenamiento.' }}
      >
        <UPlotChart
          height="fill"
          x={{ values: chart.x, label: { en: 'Quantile of the feature', es: 'Cuantil de la variable' }, format: { decimals: 2 } }}
          y={{ label: { en: 'Change in log-odds', es: 'Cambio en log-odds' }, format: { decimals: 2 } }}
          series={chart.series}
        />
      </PlotCard>
    </>
  );
}

interface PenalisedDetails {
  C: number;
  selected?: string[];
  coefficients?: Record<string, number>;
  signs_agree_with_woe?: boolean;
  selected_rules?: Array<{ rule: string; coefficient: number }>;
  n_candidate_rules?: number;
  stability?: { bootstraps: number; jaccard_mean: number; jaccard_min: number };
}

/** The penalised rungs: the L1 regression's coefficients on WoE, and PLTR's selected rules with their stability. */
export function PenalisedView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const l1 = sel ? details<PenalisedDetails>(sel, 'P2a-l1') : undefined;
  const pl = sel ? details<PenalisedDetails>(sel, 'P2b-pltr') : undefined;
  if (!sel || !l1 || !pl) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const coefs = Object.entries(l1.coefficients ?? {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const rules = [...(pl.selected_rules ?? [])].sort((a, b) => Math.abs(b.coefficient) - Math.abs(a.coefficient));
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: 'P2a: L1 logistic regression on WoE', es: 'P2a: regresión logística L1 sobre WoE' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Penalty strength C = ${l1.C}, chosen by cross-validated log loss; ${l1.selected?.length ?? 0} of ${coefs.length} variables survive.`,
            es: `Fuerza de penalización C = ${String(l1.C).replace('.', ',')}, elegida por log loss con validación cruzada; sobreviven ${l1.selected?.length ?? 0} de ${coefs.length} variables.`,
          }}
        >
          <div className="ct-stack">
            <Verdict
              compact
              title={{ en: 'Signs agree with WoE', es: 'Signos de acuerdo con el WoE' }}
              tone={l1.signs_agree_with_woe ? 'good' : 'warn'}
              verdict={
                l1.signs_agree_with_woe
                  ? { en: 'Every surviving coefficient is negative on WoE, as a sound scorecard requires.', es: 'Todo coeficiente que sobrevive es negativo sobre el WoE, como exige una scorecard sólida.' }
                  : { en: 'Some coefficient is positive on WoE: a sign the penalty did not remove.', es: 'Algún coeficiente es positivo sobre el WoE: un signo que la penalización no eliminó.' }
              }
            />
            <div className="ct-scroll">
              <table className="caos-table">
                <thead>
                  <tr>
                    <th>{pick({ en: 'Variable (WoE)', es: 'Variable (WoE)' }, lang)}</th>
                    <th>{pick({ en: 'Coefficient', es: 'Coeficiente' }, lang)}</th>
                  </tr>
                </thead>
                <tbody>
                  {coefs.map(([k, b]) => (
                    <tr key={k}>
                      <td>{k}</td>
                      <td>{b === 0 ? pick({ en: '0 (removed)', es: '0 (eliminada)' }, lang) : formatNumber(b, lang, { decimals: 3 })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </PlotCard>
      </div>
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: 'P2b: the selected PLTR rules', es: 'P2b: las reglas PLTR seleccionadas' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `${rules.length} of ${pl.n_candidate_rules ?? 0} candidate rules selected; Jaccard stability of the selection over ${pl.stability?.bootstraps ?? 0} bootstraps: mean ${formatNumber(pl.stability?.jaccard_mean, 'en', { decimals: 2 })}, minimum ${formatNumber(pl.stability?.jaccard_min, 'en', { decimals: 2 })}.`,
            es: `${rules.length} de ${pl.n_candidate_rules ?? 0} reglas candidatas seleccionadas; estabilidad de Jaccard de la selección en ${pl.stability?.bootstraps ?? 0} bootstraps: media ${formatNumber(pl.stability?.jaccard_mean, 'es', { decimals: 2 })}, mínimo ${formatNumber(pl.stability?.jaccard_min, 'es', { decimals: 2 })}.`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table">
              <thead>
                <tr>
                  <th className="caos-col-text">{pick({ en: 'Rule (on the training slice)', es: 'Regla (en el tramo de entrenamiento)' }, lang)}</th>
                  <th>{pick({ en: 'Coefficient', es: 'Coeficiente' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r) => (
                  <tr key={r.rule}>
                    <td className="caos-col-text">{r.rule}</td>
                    <td>{formatNumber(r.coefficient, lang, { decimals: 3 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

/** The foundation-model challenger, with the licence of its weights on the view, and its ROC against the scorecard and
 * the GBM on the same records. */
export function TabPfnView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const r = sel ? record(sel, 'P5-tabpfn') : undefined;
  const chart = useMemo(() => {
    if (!sel || !r) return null;
    const v = sel.data.variant;
    const x = grid(0, 1, 101);
    const ids = [CHAMPION, 'P4-lightgbm', 'P5-tabpfn'].filter((id) => v.outputs.rungs[id]);
    return { x, series: ids.map((id) => ({ id, values: interp(v.outputs.rungs[id].roc.fpr, v.outputs.rungs[id].roc.tpr, x) })) };
  }, [sel, r]);
  if (!sel || !r || !chart) return <Pending />;
  const v = sel.data.variant;
  const d = r.details as { licence: string; attribution: string; n_estimators: number };
  const prov = provenanceOf(v.provenance.truth_status);
  const colors = { [CHAMPION]: '--color-accent', 'P4-lightgbm': '--color-accent-2', 'P5-tabpfn': '--color-magenta' } as const;
  return (
    <>
      <PlotCard title={{ en: 'TabPFN v2, research challenger', es: 'TabPFN v2, retador de investigación' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <Verdict compact title={{ en: 'Weights licence', es: 'Licencia de los pesos' }} tone="warn" verdict={{ en: d.licence, es: d.licence }} />
        <p className="ct-note">{d.attribution}</p>
        <table className="caos-table">
          <tbody>
            <tr>
              <td>{pick({ en: 'AUC on this variant', es: 'AUC en esta variante' }, lang)}</td>
              <td>{formatNumber(value(test(v, 'disc.auc', r.id)), lang, { decimals: 4 })}</td>
            </tr>
            <tr>
              <td>{pick({ en: 'DeLong p against the scorecard', es: 'p de DeLong contra la scorecard' }, lang)}</td>
              <td>{formatNumber(test(v, 'disc.delong', r.id)?.p_value ?? null, lang, { digits: 3 })}</td>
            </tr>
            <tr>
              <td>{pick({ en: 'Ensemble members', es: 'Miembros del ensamble' }, lang)}</td>
              <td>{formatNumber(d.n_estimators, lang)}</td>
            </tr>
          </tbody>
        </table>
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'ROC on the same records: TabPFN, the GBM and the scorecard', es: 'ROC en los mismos registros: TabPFN, el GBM y la scorecard' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: 'Built with PriorLabs-TabPFN.', es: 'Construido con PriorLabs-TabPFN.' }}
      >
        <UPlotChart
          height="fill"
          x={{ values: chart.x, label: { en: 'False positive rate', es: 'Tasa de falsos positivos' }, format: { decimals: 2 } }}
          y={{ label: { en: 'True positive rate', es: 'Tasa de verdaderos positivos' }, range: [0, 1], format: { decimals: 2 } }}
          series={[
            { label: { en: 'Random ranking', es: 'Orden al azar' }, values: chart.x, color: '--color-fg-faint', dash: [4, 4], width: 1 },
            ...chart.series.map((s) => ({ label: shortName(rung(v, s.id), s.id), values: s.values, color: colors[s.id as keyof typeof colors], width: 2 })),
          ]}
        />
      </PlotCard>
    </>
  );
}

export function ModelGroup({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const hasTabPfn = !!sel?.data.models.model.find((m) => m.id === 'P5-tabpfn');
  const tabs: Array<{ id: string; label: BiText; content: ReactElement }> = [
    { id: 'ladder', label: { en: 'Ladder', es: 'Escalera' }, content: <LadderView sel={sel} /> },
    { id: 'scorecard', label: { en: 'Scorecard', es: 'Scorecard' }, content: <ScorecardView sel={sel} /> },
    { id: 'ebm', label: { en: 'EBM', es: 'EBM' }, content: <EbmView sel={sel} /> },
    { id: 'gbm', label: { en: 'GBM', es: 'GBM' }, content: <GbmView sel={sel} /> },
    { id: 'penalised', label: { en: 'L1 and PLTR', es: 'L1 y PLTR' }, content: <PenalisedView sel={sel} /> },
  ];
  if (hasTabPfn) tabs.push({ id: 'tabpfn', label: { en: 'TabPFN', es: 'TabPFN' }, content: <TabPfnView sel={sel} /> });
  return <SubTabs ariaLabel={pick({ en: 'Views of the model', es: 'Vistas del modelo' }, lang)} tabs={tabs.map((t) => ({ ...t, label: pick(t.label, lang) }))} />;
}
