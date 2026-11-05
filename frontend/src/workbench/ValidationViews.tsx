// The Validation group: what a validator and a supervisor would run on this model, read from riskvalidation's rows
// and re-lit live under the rail's policy (CT-104: thresholds are labelled as policy, never as regulation). Every view
// fills the panel: a table beside or above the drawing of the same numbers (ADR-0071 rule 8).
import { PlotCard, SubTabs, Verdict, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import type { Light, TestRow } from '../lib/contract.types';
import { LIGHT_TEXT, relight, thresholdLabel, type PolicyAlphas } from '../lib/policy';
import { CHAMPION, PORTFOLIO, REPLAY, extra, grid, interp, provenanceOf, rung, shortName, test, unionPoints, value, type Selection } from './model';
import { Pending } from './Pending';
import { WHOLE_PORTFOLIO, segmentName } from './names';

/** The portfolio-level tests of the battery, in the order a validation report reads them; every row names its segment under the
 * test (R5 c01 M3, R4 ruling 3: only the Jeffreys label said "portfolio", the other 14 rows named none). */
const BATTERY: Array<{ id: string; label: BiText; descriptive?: boolean }> = [
  { id: 'disc.auc', label: { en: 'AUC (descriptive)', es: 'AUC (descriptiva)' } },
  { id: 'disc.auc_vs_initial', label: { en: 'AUC against initial validation (ECB)', es: 'AUC contra la validación inicial (BCE)' } },
  { id: 'disc.delong', label: { en: 'DeLong against the champion (a difference in either direction)', es: 'DeLong contra el campeón (una diferencia en cualquier sentido)' } },
  { id: 'disc.ks', label: { en: 'Kolmogorov-Smirnov (descriptive)', es: 'Kolmogorov-Smirnov (descriptiva)' }, descriptive: true },
  { id: 'pd.jeffreys', label: { en: 'Jeffreys (ECB)', es: 'Jeffreys (BCE)' } },
  { id: 'pd.binomial', label: { en: 'Binomial (WP14)', es: 'Binomial (WP14)' } },
  { id: 'pd.binomial_vasicek', label: { en: 'Binomial with asset correlation 4 % (WP14, CRE31.15)', es: 'Binomial con correlación de activos 4 % (WP14, CRE31.15)' } },
  { id: 'pd.chi2_grades', label: { en: 'Chi-square over grades (WP14)', es: 'Chi-cuadrado sobre grados (WP14)' } },
  { id: 'pd.hosmer_lemeshow', label: { en: 'Hosmer-Lemeshow', es: 'Hosmer-Lemeshow' } },
  { id: 'pd.spiegelhalter', label: { en: 'Spiegelhalter', es: 'Spiegelhalter' } },
  { id: 'pd.brier', label: { en: 'Brier score (descriptive)', es: 'Puntaje de Brier (descriptiva)' } },
  { id: 'pd.ece', label: { en: 'Expected calibration error (descriptive)', es: 'Error de calibración esperado (descriptiva)' } },
  { id: 'stability.psi', label: { en: 'PSI against the training slice', es: 'PSI contra la partición de entrenamiento' } },
  { id: 'rating.hhi', label: { en: 'Grade concentration, Herfindahl (ECB)', es: 'Concentración en grados, Herfindahl (BCE)' } },
];

/** The conventional PSI band the engine names (the 0.10 and 0.25 rule of thumb), in the reader's language: the Spanish Stability
 * table printed the engine's English words ("little change"), U16-F13a's sweep of the R5 classes. */
const PSI_BAND: Record<string, BiText> = {
  'little change': { en: 'little change', es: 'cambio pequeño' },
  'moderate change': { en: 'moderate change', es: 'cambio moderado' },
  'significant change': { en: 'significant change', es: 'cambio significativo' },
};
export const bandText = (band: unknown, lang: 'en' | 'es'): string => {
  if (typeof band !== 'string' || band === '') return '';
  return PSI_BAND[band] ? pick(PSI_BAND[band], lang) : band;
};

/** A tests row's segment in words under its name: the segment the document gives ("portfolio" for a portfolio row), and for a
 * row of no segment the whole portfolio (R5 ruling 2). */
export function SegmentDetail({ segment }: { segment: string | null }) {
  const lang = useShellLang();
  const words = segment ? segmentName(segment, { caseId: 'C01' }) ?? { en: segment, es: segment } : WHOLE_PORTFOLIO;
  return (
    <span className="ct-row-detail" data-segment={segment ?? 'none'}>
      {pick(words, lang)}
    </span>
  );
}

/** A test's value (its p-value when it has one) and its light under the rail's policy, as a word: never colour alone. */
export function LightCell({ row, alphas, className, descriptive }: { row: TestRow | undefined; alphas: PolicyAlphas; className?: string; descriptive?: boolean }) {
  const lang = useShellLang();
  if (!row) return <td className={className}>-</td>;
  const light: Light = relight(row, alphas);
  const p = row.p_value;
  // a p-value below the smallest double the engine returns as 0; it is not zero
  // a row the table calls descriptive shows its statistic (the KS distance D), not the p-value it also carries
  const stat = descriptive ? value(row) : null;
  // the DeLong test is two-sided, so its light says the AUCs differ, not which is higher: the direction is named beside it (U16-R2 b01 m3)
  const diff = row.test_id === 'disc.delong' ? extra(row, 'difference') : null;
  const direction = diff === null || diff === 0 ? null : diff > 0 ? 'higher' : 'lower';
  // a p-value that rounds to a threshold it is not on takes a third digit, so it shows which side of the line it falls (R3 c02 m5: 0.049876
  // printed "0.05 amber" under "amber below 0.05")
  const pFormat = (x: number) => {
    const two = x >= 0.1 && x < 1 ? { decimals: 2 } : { digits: 2 };
    const rounded = Number(x.toPrecision(2));
    return (rounded === alphas.amber || rounded === alphas.red) && rounded !== x ? { digits: 3 } : two;
  };
  const shown = stat !== null ? formatNumber(stat, lang, { digits: 3 }) : p === 0 ? '< 1E-300' : p !== null ? formatNumber(p, lang, pFormat(p)) : formatNumber(value(row), lang, { digits: 3 });
  return (
    <td data-light={light} className={`ct-light ct-light-${light}${className ? ` ${className}` : ''}`} title={pick(thresholdLabel(row, alphas), lang)}>
      {shown}
      {light !== 'not_evaluated' && <span className="ct-light-word"> {pick(LIGHT_TEXT[light], lang)}</span>}
      {direction !== null && <span className="ct-note" data-direction={direction}> ({pick(direction === 'higher' ? { en: 'AUC higher', es: 'AUC mayor' } : { en: 'AUC lower', es: 'AUC menor' }, lang)})</span>}
    </td>
  );
}

/** Every portfolio-level test for every rung, the light re-computed under the rail's policy. Where the row has no room
 * for every rung, the champion and the challenger. */
export function BatteryView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  if (!sel) return <Pending />;
  const v = sel.data.variant;
  const cols = v.model.filter((m) => m.id !== 'P0-constant');
  const sample = v.tests.find((t) => t.alpha_amber !== null);
  const room = (id: string) => (id === CHAMPION || id === sel.challenger ? undefined : 'ct-room-only');
  return (
    <PlotCard
      fill
      title={{ en: 'The battery, test by rung', es: 'La batería, prueba por peldaño' }}
      lane="live"
      provenance={provenanceOf(v.provenance.truth_status)}
      dataKey={stateKey}
      note={sample ? thresholdLabel(sample, sel.alphas) : undefined}
    >
      <div className="ct-scroll" data-caos-flow="">
        <table className="caos-table ct-battery">
          <thead>
            <tr>
              <th className="caos-col-text">{pick({ en: 'Test (p-value or value)', es: 'Prueba (valor p o valor)' }, lang)}</th>
              {cols.map((m) => (
                <th key={m.id} title={pick(m.title, lang)} className={room(m.id)}>
                  {pick(shortName(m, m.id), lang)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {BATTERY.map((b) => (
              <tr key={b.id}>
                <td className="caos-col-text" title={test(v, b.id, CHAMPION)?.reference ?? ''}>
                  {pick(b.label, lang)}
                  <SegmentDetail segment={test(v, b.id, CHAMPION)?.segment ?? PORTFOLIO} />
                </td>
                {cols.map((m) => (
                  <LightCell key={m.id} row={test(v, b.id, m.id)} alphas={sel.alphas} className={room(m.id)} descriptive={b.descriptive} />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PlotCard>
  );
}

/** Observed default rate against the PD the rung applied, grade by grade, with the Jeffreys 95% posterior interval. */
export function CalibrationView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const data = useMemo(() => {
    if (!sel) return null;
    const v = sel.data.variant;
    const one = (id: string) => {
      const grades = v.outputs.rungs[id].grades.filter((g) => g.n > 0);
      return { id, rows: grades.map((g) => ({ g, t: test(v, 'pd.jeffreys', id, g.grade) })) };
    };
    return [one(CHAMPION), one(sel.challenger)];
  }, [sel]);
  const chart = useMemo(() => {
    if (!data) return null;
    const u = unionPoints(data.map(({ rows }) => ({ x: rows.map((r) => r.g.pd as number), y: rows.map((r) => r.g.dr as number) })));
    return { x: u.x, champion: u.ys[0], challenger: u.ys[1] };
  }, [data]);
  if (!sel || !data || !chart) return <Pending />;
  const v = sel.data.variant;
  const prov = provenanceOf(v.provenance.truth_status);
  const names = data.map((d) => shortName(rung(v, d.id), d.id));
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'Calibration by grade: Jeffreys test per grade', es: 'Calibración por grado: prueba de Jeffreys por grado' }}
        lane="live"
        provenance={prov}
        dataKey={stateKey}
        note={{ en: 'H0: the PD applied to the grade is not below the true one (ECB 2019, 2.5.3.1). The posterior interval column, which a wide window adds, is the Beta(D + 1/2, N - D + 1/2) posterior.', es: 'H0: la PD aplicada al grado no es menor que la verdadera (BCE 2019, 2.5.3.1). La columna del intervalo posterior, que una ventana ancha agrega, es la posterior Beta(D + 1/2, N - D + 1/2).' }}
      >
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table">
            <thead>
              <tr>
                <th>{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
                <th>{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
                <th className="ct-wide-only">N</th>
                <th className="ct-room-only">D</th>
                <th className="ct-wide-only">{pick({ en: 'PD applied', es: 'PD aplicada' }, lang)}</th>
                <th>{pick({ en: 'Default rate', es: 'Tasa observada' }, lang)}</th>
                <th className="ct-room-only">{pick({ en: '95 % posterior', es: 'Posterior 95 %' }, lang)}</th>
                <th>Jeffreys</th>
              </tr>
            </thead>
            <tbody>
              {data.flatMap((d, k) =>
                d.rows.map(({ g, t }) => (
                  <tr key={`${d.id}-${g.grade}`}>
                    <td>{pick(names[k], lang)}</td>
                    <td>{g.grade}</td>
                    <td className="ct-wide-only">{formatNumber(g.n, lang)}</td>
                    <td className="ct-room-only">{formatNumber(g.d, lang)}</td>
                    <td className="ct-wide-only">{formatNumber(g.pd, lang, { percent: true, decimals: 2 })}</td>
                    <td>{formatNumber(g.dr, lang, { percent: true, decimals: 2 })}</td>
                    <td className="ct-room-only">
                      {formatNumber(extra(t, 'posterior_q025'), lang, { percent: true, decimals: 2 })} - {formatNumber(extra(t, 'posterior_q975'), lang, { percent: true, decimals: 2 })}
                    </td>
                    <LightCell row={t} alphas={sel.alphas} />
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      </PlotCard>
      <PlotCard fill title={{ en: 'Observed against applied PD, by grade', es: 'Observada contra PD aplicada, por grado' }} lane={REPLAY} provenance={prov} dataKey={stateKey} note={{ en: 'On the line: calibrated. Above it: the PD under-estimates the default rate.', es: 'Sobre la línea: calibrado. Encima: la PD subestima la tasa de incumplimiento.' }}>
        <UPlotChart
          height="fill"
          x={{ values: chart.x, label: { en: 'PD applied (grade mean)', es: 'PD aplicada (media del grado)' }, format: { percent: true, decimals: 0 } }}
          y={{ label: { en: 'Observed default rate', es: 'Tasa de incumplimiento observada' }, format: { percent: true, decimals: 0 } }}
          series={[
            { label: { en: 'Perfect calibration', es: 'Calibración perfecta' }, values: chart.x, color: '--color-fg-faint', dash: [4, 4], width: 1 },
            { label: names[0], values: chart.champion, color: '--color-accent', mode: 'points' },
            { label: names[1], values: chart.challenger, color: '--color-magenta', mode: 'points' },
          ]}
        />
      </PlotCard>
    </ViewsRow>
  );
}

/** ROC of the champion and the challenger, the DeLong test between them, and the score distributions. */
export function DiscriminationView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const chart = useMemo(() => {
    if (!sel) return null;
    const v = sel.data.variant;
    const x = grid(0, 1, 101);
    const c = v.outputs.rungs[CHAMPION];
    const h = v.outputs.rungs[sel.challenger];
    return { x, champion: interp(c.roc.fpr, c.roc.tpr, x), challenger: interp(h.roc.fpr, h.roc.tpr, x) };
  }, [sel]);
  const dist = useMemo(() => {
    if (!sel) return null;
    const d = sel.data.variant.outputs.rungs[sel.challenger].distribution;
    const mids = d.log10_pd_edges.slice(0, -1).map((e, i) => 10 ** ((e + d.log10_pd_edges[i + 1]) / 2));
    const nD = d.defaulters.reduce((a, b) => a + b, 0) || 1;
    const nN = d.non_defaulters.reduce((a, b) => a + b, 0) || 1;
    return { x: mids, def: d.defaulters.map((n) => n / nD), non: d.non_defaulters.map((n) => n / nN) };
  }, [sel]);
  if (!sel || !chart || !dist) return <Pending />;
  const v = sel.data.variant;
  const prov = provenanceOf(v.provenance.truth_status);
  const dl = test(v, 'disc.delong', sel.challenger);
  const names = [shortName(rung(v, CHAMPION), CHAMPION), shortName(rung(v, sel.challenger), sel.challenger)];
  const light = dl ? relight(dl, sel.alphas) : null;
  return (
    <>
      <PlotCard title={{ en: "Is the challenger's gain significant?", es: '¿Es significativa la ganancia del retador?' }} lane="live" provenance={prov} dataKey={stateKey}>
        <Verdict
          compact
          title={{ en: 'DeLong, DeLong and Clarke-Pearson (1988)', es: 'DeLong, DeLong y Clarke-Pearson (1988)' }}
          tone={light === 'red' || light === 'amber' ? 'accent' : 'neutral'}
          verdict={
            dl
              ? {
                  en: `AUC ${formatNumber(extra(dl, 'auc_1'), 'en', { decimals: 4 })} against ${formatNumber(extra(dl, 'auc_2'), 'en', { decimals: 4 })} (difference ${formatNumber(extra(dl, 'difference'), 'en', { decimals: 4 })}); p = ${formatNumber(dl.p_value, 'en', { digits: 3 })}, so ${light === 'red' || light === 'amber' ? 'the two AUCs differ under this policy' : 'no significant difference under this policy'}.`,
                  es: `AUC ${formatNumber(extra(dl, 'auc_1'), 'es', { decimals: 4 })} contra ${formatNumber(extra(dl, 'auc_2'), 'es', { decimals: 4 })} (diferencia ${formatNumber(extra(dl, 'difference'), 'es', { decimals: 4 })}); p = ${formatNumber(dl.p_value, 'es', { digits: 3 })}, así que ${light === 'red' || light === 'amber' ? 'las dos AUC difieren con esta política' : 'no hay diferencia significativa con esta política'}.`,
                }
              : { en: 'The champion is not compared with itself.', es: 'El campeón no se compara consigo mismo.' }
          }
        />
        <table className="caos-table">
          <thead>
            <tr>
              <th>{pick({ en: 'Held-out AUC', es: 'AUC fuera de muestra' }, lang)}</th>
              <th>{pick(names[0], lang)}</th>
              <th>{pick(names[1], lang)}</th>
              <th>{pick({ en: 'Difference', es: 'Diferencia' }, lang)}</th>
              <th>{pick({ en: 'DeLong p', es: 'p de DeLong' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                {pick({ en: 'with the 95 % interval', es: 'con el intervalo 95 %' }, lang)}
                <SegmentDetail segment={dl?.segment ?? test(v, 'disc.auc', CHAMPION)?.segment ?? PORTFOLIO} />
              </td>
              <td>
                {formatNumber(value(test(v, 'disc.auc', CHAMPION)), lang, { decimals: 4 })}{' '}
                {/* the interval on every width: at 390 it wraps under the value, the label says it is shown (R3 c01 M1) */}
                <span data-interval="">
                  ({formatNumber(extra(test(v, 'disc.auc', CHAMPION), 'ci95_low'), lang, { decimals: 4 })} - {formatNumber(extra(test(v, 'disc.auc', CHAMPION), 'ci95_high'), lang, { decimals: 4 })})
                </span>
              </td>
              <td>
                {formatNumber(value(test(v, 'disc.auc', sel.challenger)), lang, { decimals: 4 })}{' '}
                <span data-interval="">
                  ({formatNumber(extra(test(v, 'disc.auc', sel.challenger), 'ci95_low'), lang, { decimals: 4 })} - {formatNumber(extra(test(v, 'disc.auc', sel.challenger), 'ci95_high'), lang, { decimals: 4 })})
                </span>
              </td>
              <td>{formatNumber(extra(dl, 'difference'), lang, { decimals: 4 })}</td>
              <td>{dl ? formatNumber(dl.p_value, lang, { digits: 2 }) : '-'}</td>
            </tr>
          </tbody>
        </table>
      </PlotCard>
      <ViewsRow>
        <PlotCard fill title={{ en: 'ROC: champion and challenger', es: 'ROC: campeón y retador' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
          <UPlotChart
            height="fill"
            x={{ values: chart.x, label: { en: 'False positive rate', es: 'Tasa de falsos positivos' }, format: { decimals: 2 } }}
            y={{ label: { en: 'True positive rate', es: 'Tasa de verdaderos positivos' }, range: [0, 1], format: { decimals: 2 } }}
            series={[
              { label: { en: 'Random ranking', es: 'Orden al azar' }, values: chart.x, color: '--color-fg-faint', dash: [4, 4], width: 1 },
              { label: names[0], values: chart.champion, color: '--color-accent', width: 2 },
              { label: names[1], values: chart.challenger, color: '--color-magenta', width: 2 },
            ]}
          />
        </PlotCard>
        <PlotCard fill title={{ en: 'PD of defaulters and non-defaulters, challenger', es: 'PD de incumplidores y no incumplidores, retador' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
          <UPlotChart
            height="fill"
            // log10 PD bins on a log axis, the two groups apart by the dash as well as the colour (R3 c02 m12, m13)
            x={{ values: dist.x, log: true, label: { en: 'PD (bin centre)', es: 'PD (centro del tramo)' }, format: { percent: true, digits: 2 } }}
            y={{ label: { en: 'Share of the group', es: 'Fracción del grupo' }, format: { percent: true, decimals: 0 } }}
            series={[
              { label: { en: 'Defaulters', es: 'Incumplidores' }, values: dist.def, color: '--color-bad' },
              { label: { en: 'Non-defaulters', es: 'No incumplidores' }, values: dist.non, color: '--color-good', dash: [6, 4] },
            ]}
          />
        </PlotCard>
      </ViewsRow>
    </>
  );
}

/** PSI of every rung's PD and CSI of every input against the training slice, with the chi-square benchmark, and where
 * the PD distribution moved: the PSI contribution of each training decile. */
export function StabilityView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  if (!sel) return <Pending />;
  const v = sel.data.variant;
  const prov = provenanceOf(v.provenance.truth_status);
  const psi = v.model.map((m) => ({ m, t: test(v, 'stability.psi', m.id) })).filter((r) => r.t);
  const csi = v.tests.filter((t) => t.test_id === 'stability.csi');
  const contributions = (id: string) => {
    const c = test(v, 'stability.psi', id)?.extras?.contributions;
    return Array.isArray(c) ? c.map((x) => (typeof x === 'number' ? x : null)) : [];
  };
  const champ = contributions(CHAMPION);
  const chall = contributions(sel.challenger);
  const x = champ.map((_, i) => i + 1);
  return (
    <ViewsRow shares={[2, 3]}>
      <>
        <PlotCard
          title={{ en: 'Population stability of the PD', es: 'Estabilidad poblacional de la PD' }}
          lane="live"
          provenance={prov}
          dataKey={stateKey}
          note={{ en: 'The light uses the chi-square benchmark of Yurdakul and Naranjo (2020): PSI > (1/n + 1/m) chi2(1 - alpha, B - 1). The bands 0.10 and 0.25 are a convention with no error control.', es: 'La luz usa el umbral chi-cuadrado de Yurdakul y Naranjo (2020): PSI > (1/n + 1/m) chi2(1 - alfa, B - 1). Las bandas 0,10 y 0,25 son una convención sin control de error.' }}
        >
          <table className="caos-table">
            <thead>
              <tr>
                <th>{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
                <th>PSI</th>
                <th className="ct-room-only">{pick({ en: 'Benchmark at 5 %', es: 'Umbral al 5 %' }, lang)}</th>
                <th className="ct-room-only">{pick({ en: 'Conventional band', es: 'Banda convencional' }, lang)}</th>
                <th>{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {psi.map(({ m, t }) => (
                <tr key={m.id}>
                  <td title={pick(m.title, lang)}>
                    {pick(shortName(m, m.id), lang)}
                    <SegmentDetail segment={t?.segment ?? PORTFOLIO} />
                  </td>
                  <td>{formatNumber(value(t), lang, { decimals: 4 })}</td>
                  <td className="ct-room-only">{formatNumber(extra(t, 'benchmark_05'), lang, { decimals: 4 })}</td>
                  <td className="ct-room-only">{bandText(t?.extras?.band, lang)}</td>
                  <LightCell row={t} alphas={sel.alphas} />
                </tr>
              ))}
            </tbody>
          </table>
        </PlotCard>
        <PlotCard fill title={{ en: 'Stability of each input', es: 'Estabilidad por variable' }} lane="live" provenance={prov} dataKey={stateKey}>
          <div className="ct-scroll" data-caos-flow="">
            <table className="caos-table">
              <thead>
                <tr>
                  <th className="caos-col-text">{pick({ en: 'Characteristic', es: 'Característica' }, lang)}</th>
                  <th>CSI</th>
                  <th>{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {csi.map((t) => (
                  <tr key={t.segment ?? t.inputs_hash}>
                    {/* the input by its codebook name (R3 c01 B2, B4) */}
                    <td className="caos-col-text">{pick(segmentName(t.segment ?? '', { caseId: 'C01' }) ?? { en: t.segment ?? '', es: t.segment ?? '' }, lang)}</td>
                    <td>{formatNumber(value(t), lang, { decimals: 4 })}</td>
                    <LightCell row={t} alphas={sel.alphas} />
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </>
      <PlotCard
        fill
        title={{ en: 'Where the PD distribution moved', es: 'Dónde se movió la distribución de la PD' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: "Each bin's contribution to the PSI, on the training slice's PD deciles; tied values merge deciles, so a rung can have fewer than ten bins. The PSI is their sum.", es: 'La contribución de cada tramo al PSI, sobre los deciles de PD de la partición de entrenamiento; los valores empatados unen deciles, así que un peldaño puede tener menos de diez tramos. El PSI es su suma.' }}
      >
        <UPlotChart
          height="fill"
          x={{ values: x, label: { en: 'Training bin of the PD (1 = lowest; ties merge deciles)', es: 'Tramo de PD de entrenamiento (1 = el más bajo; los empates unen deciles)' }, format: { decimals: 0 } }}
          y={{ label: { en: 'PSI contribution', es: 'Contribución al PSI' }, format: { decimals: 5 } }}
          series={[
            { label: shortName(rung(v, CHAMPION), CHAMPION), values: champ, color: '--color-accent', width: 2 },
            { label: shortName(rung(v, sel.challenger), sel.challenger), values: chall, color: '--color-magenta', width: 2 },
          ]}
        />
      </PlotCard>
    </ViewsRow>
  );
}

/** Discrimination by sex, recorded and not tested (the fairness battery is C21's): the AUC per group, and the ROC of
 * the champion and the challenger within each group. */
export function GroupsView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const chart = useMemo(() => {
    if (!sel) return null;
    const x = grid(0, 1, 101);
    const out: Array<{ label: BiText; values: Array<number | null>; color: '--color-accent' | '--color-magenta'; dash?: number[] }> = [];
    Object.entries(sel.data.variant.outputs.groups).forEach(([g, s], k) => {
      for (const [id, color] of [[CHAMPION, '--color-accent'], [sel.challenger, '--color-magenta']] as const) {
        const roc = s.roc?.[id];
        if (!roc) continue;
        const name = shortName(rung(sel.data.variant, id), id);
        out.push({ label: { en: `${name.en}, ${groupName(g).en}`, es: `${name.es}, ${groupName(g).es}` }, values: interp(roc.fpr, roc.tpr, x), color, dash: k % 2 === 1 ? [6, 4] : undefined });
      }
    });
    return { x, series: out };
  }, [sel]);
  if (!sel || !chart) return <Pending />;
  const v = sel.data.variant;
  const prov = provenanceOf(v.provenance.truth_status);
  const groups = Object.entries(v.outputs.groups);
  return (
    <>
      <PlotCard
        title={{ en: 'AUC by sex (sex is never an input)', es: 'AUC por sexo (el sexo nunca es una entrada)' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: "Recorded for the reader; the fairness tests (separation, acceptance-rate ratios) are case C21's.", es: 'Registrado para el lector; las pruebas de equidad (separación, razones de aprobación) son del caso C21.' }}
      >
        <table className="caos-table">
          <thead>
            <tr>
              <th>{pick({ en: 'Group', es: 'Grupo' }, lang)}</th>
              <th>N</th>
              <th>{pick({ en: 'Default rate', es: 'Tasa de incumplimiento' }, lang)}</th>
              <th>{pick(shortName(rung(v, CHAMPION), CHAMPION), lang)}</th>
              <th>{pick(shortName(rung(v, sel.challenger), sel.challenger), lang)}</th>
            </tr>
          </thead>
          <tbody>
            {groups.map(([g, s]) => (
              <tr key={g}>
                <td>{pick(groupName(g), lang)}</td>
                <td>{formatNumber(s.n, lang)}</td>
                <td>{formatNumber(s.default_rate, lang, { percent: true, decimals: 1 })}</td>
                <td>{formatNumber(s.auc[CHAMPION] ?? null, lang, { decimals: 4 })}</td>
                <td>{formatNumber(s.auc[sel.challenger] ?? null, lang, { decimals: 4 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </PlotCard>
      <PlotCard fill title={{ en: 'ROC within each group', es: 'ROC dentro de cada grupo' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <UPlotChart
          height="fill"
          x={{ values: chart.x, label: { en: 'False positive rate', es: 'Tasa de falsos positivos' }, format: { decimals: 2 } }}
          y={{ label: { en: 'True positive rate', es: 'Tasa de verdaderos positivos' }, range: [0, 1], format: { decimals: 2 } }}
          series={chart.series}
        />
      </PlotCard>
    </>
  );
}

function groupName(g: string): { en: string; es: string } {
  if (g === 'female') return { en: 'female', es: 'mujer' };
  if (g === 'male') return { en: 'male', es: 'hombre' };
  return { en: g, es: g };
}

export function ValidationGroup({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const tabs = [
    { id: 'battery', label: pick({ en: 'Battery', es: 'Batería' }, lang), content: <BatteryView sel={sel} /> },
    { id: 'calibration', label: pick({ en: 'Calibration', es: 'Calibración' }, lang), content: <CalibrationView sel={sel} /> },
    { id: 'discrimination', label: pick({ en: 'Discrimination', es: 'Discriminación' }, lang), content: <DiscriminationView sel={sel} /> },
    { id: 'stability', label: pick({ en: 'Stability', es: 'Estabilidad' }, lang), content: <StabilityView sel={sel} /> },
    { id: 'groups', label: pick({ en: 'By group', es: 'Por grupo' }, lang), content: <GroupsView sel={sel} /> },
  ];
  return <SubTabs ariaLabel={pick({ en: 'Views of the validation', es: 'Vistas de la validación' }, lang)} tabs={tabs} />;
}
