// The Model group: what each rung of the ladder is and what it learned. The ladder (every rung's held-out
// discrimination and calibration beside its ROC) and the internals of the rungs: the scorecard's points table with the
// live applicant, the EBM's shape functions, the GBM's monotone partial dependence and reason-code stability, the L1
// regression's coefficients and PLTR's rules, TabPFN. Every view fills the panel with a table beside or above the
// drawing of the same numbers (ADR-0071 rule 8).
import { BarChart, PlotCard, SubTabs, Verdict, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo, type ReactElement } from 'react';
import type { EbmExport, GbmDetails, ModelRecord, ScorecardDetails } from '../lib/contract.types';
import { liveScores } from './Workbench';
import { CHAMPION, REPLAY, extra, grid, interp, provenanceOf, shortName, test, unionPoints, value, type Selection } from './model';
import { Pending } from './Pending';
import { engineText, ruleText, unitName, type Bi } from './c01Text';
import { inputName, ruleNames, termName } from './names';

const PALETTE = ['--color-fg-subtle', '--color-accent', '--color-accent-2', '--color-magenta', '--color-good', '--color-warn', '--color-bad', '--color-fg'] as const;

function details<T>(sel: Selection, id: string): T | undefined {
  return sel.data.models.model.find((m) => m.id === id)?.details as T | undefined;
}

function record(sel: Selection, id: string): ModelRecord | undefined {
  return sel.data.models.model.find((m) => m.id === id);
}

/** Every rung on this variant: AUC with its 95% interval, the paired DeLong test, Brier, ECE; the ROC curves beside. */

/** A scorecard bin as the page's language writes it: optbinning's interval, its bounds in the page's number format
 * (no thousands group; a Spanish interval separates its bounds with a semicolon, the comma being its decimal sign) and
 * infinity as a sign, and the two special bins named. */

/** Why the scorecard left a feature out, in the page's language and number format: the two reasons the pipeline writes
 * (pipeline/model/scorecard.py, an information value under the threshold and a WoE coefficient of the wrong sign); any
 * other reason as written. */
export function droppedReason(why: string, lang: 'en' | 'es'): string {
  const iv = /^information value (\S+) below (\S+)$/.exec(why);
  if (iv) {
    const value = formatNumber(Number(iv[1]), lang, { decimals: 4 });
    const floor = formatNumber(Number(iv[2]), lang, { digits: 2 });
    return lang === 'es' ? `valor de información ${value} bajo ${floor}` : `information value ${value} below ${floor}`;
  }
  const sign = /^wrong sign on WoE \(coefficient (\S+), p = (\S+)\)$/.exec(why);
  if (sign) {
    const c = Number(sign[1]);
    const coef = `${c > 0 ? '+' : ''}${formatNumber(c, lang, { decimals: 4 })}`;
    const pv = formatNumber(Number(sign[2]), lang, { digits: 3 });
    return lang === 'es' ? `signo equivocado en el WoE (coeficiente ${coef}, p = ${pv})` : `wrong sign on WoE (coefficient ${coef}, p = ${pv})`;
  }
  return why;
}

/** The codes of the UCI Statlog (German Credit Data) file by their meaning in its codebook (attribute descriptions,
 * https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data): the German twin's scorecard bins print the meaning, never the
 * code (U16-R2b c01 B2). */
const GERMAN_CODE_TEXT: Record<string, { en: string; es: string }> = {
  A11: { en: 'under 0 DM', es: 'menos de 0 DM' },
  A12: { en: '0 to under 200 DM', es: 'de 0 a menos de 200 DM' },
  A13: { en: '200 DM or more, or salary assignments for at least 1 year', es: '200 DM o más, o asignación de sueldo por al menos 1 año' },
  A14: { en: 'no checking account', es: 'sin cuenta corriente' },
  A30: { en: 'no credits taken, or all paid back duly', es: 'sin créditos, o todos pagados al día' },
  A31: { en: 'all credits at this bank paid back duly', es: 'todos los créditos de este banco pagados al día' },
  A32: { en: 'existing credits paid back duly till now', es: 'créditos vigentes pagados al día hasta ahora' },
  A33: { en: 'delay in paying off in the past', es: 'atrasos en pagos pasados' },
  A34: { en: 'critical account, or other credits existing', es: 'cuenta crítica, u otros créditos vigentes' },
  A40: { en: 'car (new)', es: 'auto nuevo' },
  A41: { en: 'car (used)', es: 'auto usado' },
  A42: { en: 'furniture or equipment', es: 'muebles o equipamiento' },
  A43: { en: 'radio or television', es: 'radio o televisión' },
  A44: { en: 'domestic appliances', es: 'electrodomésticos' },
  A45: { en: 'repairs', es: 'reparaciones' },
  A46: { en: 'education', es: 'educación' },
  A47: { en: 'vacation', es: 'vacaciones' },
  A48: { en: 'retraining', es: 'recapacitación' },
  A49: { en: 'business', es: 'negocios' },
  A410: { en: 'others', es: 'otros' },
  A61: { en: 'under 100 DM', es: 'menos de 100 DM' },
  A62: { en: '100 to under 500 DM', es: 'de 100 a menos de 500 DM' },
  A63: { en: '500 to under 1,000 DM', es: 'de 500 a menos de 1.000 DM' },
  A64: { en: '1,000 DM or more', es: '1.000 DM o más' },
  A65: { en: 'unknown, or no savings account', es: 'desconocido, o sin cuenta de ahorro' },
  A71: { en: 'unemployed', es: 'desempleado' },
  A72: { en: 'under 1 year', es: 'menos de 1 año' },
  A73: { en: '1 to under 4 years', es: 'de 1 a menos de 4 años' },
  A74: { en: '4 to under 7 years', es: 'de 4 a menos de 7 años' },
  A75: { en: '7 years or more', es: '7 años o más' },
  A101: { en: 'none', es: 'ninguno' },
  A102: { en: 'co-applicant', es: 'codeudor' },
  A103: { en: 'guarantor', es: 'aval' },
  A121: { en: 'real estate', es: 'bienes raíces' },
  A122: { en: 'building society savings or life insurance', es: 'ahorro para vivienda o seguro de vida' },
  A123: { en: 'car or other property', es: 'auto u otro bien' },
  A124: { en: 'unknown, or no property', es: 'desconocido, o sin bienes' },
  A141: { en: 'bank', es: 'banco' },
  A142: { en: 'stores', es: 'tiendas' },
  A143: { en: 'none', es: 'ninguno' },
  A151: { en: 'rent', es: 'arriendo' },
  A152: { en: 'own', es: 'propia' },
  A153: { en: 'for free', es: 'gratuita' },
  A171: { en: 'unemployed or unskilled, non-resident', es: 'desempleado o no calificado, no residente' },
  A172: { en: 'unskilled, resident', es: 'no calificado, residente' },
  A173: { en: 'skilled employee or official', es: 'empleado calificado o funcionario' },
  A174: { en: 'management, self-employed or highly qualified', es: 'gerencia, independiente o altamente calificado' },
  A191: { en: 'none', es: 'ninguno' },
  A192: { en: "yes, registered under the customer's name", es: "sí, registrado a nombre del cliente" },
};

/** The education codes of the UCI Taiwan file by the codebook (X3: 1 graduate school, 2 university, 3 high school, 4 others); the
 * file also carries 0, 5 and 6, which the codebook does not document (R3 c01 B3, c02 B3). */
const EDUCATION_TEXT: Record<string, { en: string; es: string }> = {
  '1': { en: 'graduate school', es: 'posgrado' },
  '2': { en: 'university', es: 'universidad' },
  '3': { en: 'high school', es: 'secundaria' },
  '4': { en: 'others', es: 'otros' },
};

/** A category of a categorical input by its codebook name: a German code (A11) or a Taiwan education code; an undocumented code
 * says so. */
export function categoryName(input: string, code: string): { en: string; es: string } {
  if (GERMAN_CODE_TEXT[code]) return GERMAN_CODE_TEXT[code];
  if (input === 'EDUCATION') return EDUCATION_TEXT[code] ?? { en: `undocumented code ${code}`, es: `código no documentado ${code}` };
  return { en: `code ${code}`, es: `código ${code}` };
}

export function binText(bin: string, lang: 'en' | 'es'): string {
  if (bin === 'Missing') return lang === 'es' ? 'Sin dato' : 'Missing';
  // a set of the German file's category codes: their meanings, joined by "or"
  const codes = /^\{\s*(A\d+(?:\s*,\s*A\d+)*)\s*\}$/.exec(bin);
  if (codes) {
    const ids = codes[1].split(/\s*,\s*/);
    if (ids.every((c) => GERMAN_CODE_TEXT[c])) return ids.map((c) => GERMAN_CODE_TEXT[c][lang]).join(lang === 'es' ? ' o ' : ' or ');
  }
  if (bin === 'Special') return lang === 'es' ? 'Especial' : 'Special';
  const m = /^([[(])\s*(-?inf|-?\d+(?:\.\d+)?)\s*,\s*(-?inf|-?\d+(?:\.\d+)?)\s*([\])])$/.exec(bin);
  if (!m) return bin;
  const bound = (s: string) =>
    s === '-inf' ? '-\u221e' : s === 'inf' ? '\u221e' : formatNumber(Number(s), lang, { decimals: (s.split('.')[1] ?? '').length, grouping: false });
  return `${m[1]}${bound(m[2])}${lang === 'es' ? '; ' : ', '}${bound(m[3])}${m[4]}`;
}

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
  const rel = useMemo(() => {
    if (!sel) return null;
    const v = sel.data.variant;
    const ms = v.model.filter((m) => m.id !== 'P0-constant');
    const u = unionPoints(ms.map((m) => ({ x: v.outputs.rungs[m.id].reliability.map((b) => b.pd), y: v.outputs.rungs[m.id].reliability.map((b) => b.dr) })));
    return { x: u.x, series: ms.map((m, k) => ({ label: shortName(m, m.id), values: u.ys[k], color: PALETTE[(k + 1) % PALETTE.length], mode: 'points' as const })) };
  }, [sel]);
  if (!sel || !rows || !roc || !rel) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const f = (v: number | null, d = 3) => formatNumber(v, lang, { decimals: d });
  return (
    <ViewsRow shares={[3, 2]}>
      <>
        <PlotCard
          fill
          title={{ en: 'The ladder on this variant', es: 'La escalera en esta variante' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: 'Held-out AUC with its DeLong 95 % interval, the paired DeLong test against the scorecard, and the calibration of each rung (Brier, ECE); on a narrow screen the interval and the ECE sit under their value. Engines and licences are in the Context group.',
            es: 'AUC fuera de muestra con su intervalo 95 % de DeLong, la prueba pareada de DeLong contra la tarjeta de puntuación y la calibración de cada peldaño (Brier, ECE); en una pantalla angosta el intervalo y el ECE quedan bajo su valor. Motores y licencias están en el grupo Contexto.',
          }}
        >
          <div className="ct-scroll" data-caos-flow="">
            <table className="caos-table">
              <thead>
                <tr>
                  <th>{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
                  <th>AUC</th>
                  <th className="ct-wide-only ct-repeated">{pick({ en: '95 % interval', es: 'Intervalo 95 %' }, lang)}</th>
                  <th>{pick({ en: 'DeLong p', es: 'p de DeLong' }, lang)}</th>
                  <th>Brier</th>
                  <th className="ct-wide-only ct-repeated">ECE</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.m.id} data-rung={r.m.id} title={`${pick(r.m.title, lang)}: ${engineText(r.m.engine, lang)} (${r.m.licence})`}>
                    <td>{pick(shortName(r.m, r.m.id), lang)}</td>
                    <td>
                      {f(r.auc)}
                      {r.lo !== null && r.hi !== null ? <span className="ct-narrow-only">{`${f(r.lo)} - ${f(r.hi)}`}</span> : null}
                    </td>
                    <td className="ct-wide-only ct-repeated">{r.lo !== null && r.hi !== null ? `${f(r.lo)} - ${f(r.hi)}` : ''}</td>
                    <td>{r.m.id === CHAMPION ? pick({ en: 'champion', es: 'campeón' }, lang) : formatNumber(r.delongP, lang, { digits: 2 })}</td>
                    <td>
                      {f(r.brier, 4)}
                      <span className="ct-narrow-only">{`ECE ${f(r.ece, 4)}`}</span>
                    </td>
                    <td className="ct-wide-only ct-repeated">{f(r.ece, 4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
        <TabPfnCard sel={sel} />
        <div className="ct-tall-only">
          <PlotCard
            fill
            title={{ en: 'Calibration of every rung, by decile of its PD', es: 'Calibración de cada peldaño, por decil de su PD' }}
            lane={REPLAY}
            provenance={prov}
            dataKey={stateKey}
            note={{ en: 'Observed default rate against the mean PD of each decile; on the diagonal, calibrated.', es: 'Tasa observada contra la PD media de cada decil; sobre la diagonal, calibrado.' }}
          >
            <UPlotChart
              height="fill"
              x={{ values: rel.x, label: { en: 'Mean PD of the decile', es: 'PD media del decil' }, format: { percent: true, decimals: 0 } }}
              y={{ label: { en: 'Observed default rate', es: 'Tasa de incumplimiento observada' }, format: { percent: true, decimals: 0 } }}
              series={[{ label: { en: 'Perfect calibration', es: 'Calibración perfecta' }, values: rel.x, color: '--color-fg-faint', dash: [4, 4], width: 1 }, ...rel.series]}
            />
          </PlotCard>
        </div>
      </>
      <PlotCard
        fill
        title={{ en: 'ROC curves of every rung', es: 'Curvas ROC de cada peldaño' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: 'Defaulters caught against non-defaulters flagged, riskier first. Dashed: the P0 anchors.', es: 'Incumplidores detectados contra no incumplidores marcados, de mayor a menor riesgo. Discontinuas: los anclajes P0.' }}
      >
        <UPlotChart
          height="fill"
          x={{ values: roc.x, label: { en: 'False positive rate', es: 'Tasa de falsos positivos' }, format: { decimals: 2 } }}
          y={{ label: { en: 'True positive rate', es: 'Tasa de verdaderos positivos' }, range: [0, 1], format: { decimals: 2 } }}
          series={roc.series}
        />
      </PlotCard>
    </ViewsRow>
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
  // each input by its codebook name, the reason after a colon (R3 c01 B2, B4; c02 m10: no parentheses inside parentheses)
  const dropped = (l: 'en' | 'es') =>
    Object.entries(sc.dropped)
      .map(([k, why]) => `${termName(k, l)}: ${droppedReason(why, l)}`)
      .join('; ');
  // with no scored applicant the card beside the points table shows the four characteristics of highest information value, a replay
  // in the place of the four reasons (R3 c01 M2, m8; c02 m1 to m3)
  const byIv = sc.features
    .map((f) => ({ f, iv: sc.iv[f] }))
    .sort((a, b) => b.iv - a.iv)
    .slice(0, 4);
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'Points table (WoE, PDO scaling)', es: 'Tabla de puntos (WoE, escala PDO)' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `${formatNumber(sc.scaling.score_ref, 'en', { decimals: 0 })} points at odds ${formatNumber(sc.scaling.odds_ref, 'en', { decimals: 0 })} to 1, ${formatNumber(sc.scaling.pdo, 'en', { decimals: 0 })} points to double the odds; bins fitted on the training slice only.${live ? " Highlighted: the applicant's bins." : ''}${dropped('en') ? ` Not in the scorecard: ${dropped('en')}.` : ''}`,
          es: `${formatNumber(sc.scaling.score_ref, 'es', { decimals: 0 })} puntos con razón de probabilidades de ${formatNumber(sc.scaling.odds_ref, 'es', { decimals: 0 })} a 1, ${formatNumber(sc.scaling.pdo, 'es', { decimals: 0 })} puntos para duplicar la razón; tramos ajustados solo con la partición de entrenamiento.${live ? ' Destacados: los tramos del solicitante.' : ''}${dropped('es') ? ` Fuera de la tarjeta de puntuación: ${dropped('es')}.` : ''}`,
        }}
      >
        <div className="ct-scroll" data-caos-flow="">
          {/* the headers wrap at a word too, so the Points column stays in the card at 1280 in Spanish (R3 c01 M3) */}
          <table className="caos-table ct-wrap-head">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Characteristic', es: 'Característica' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Bin', es: 'Tramo' }, lang)}</th>
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
                      {/* the name wraps, so a long one ("Status of the existing checking account") leaves the Points column in the card (R3 c01 M3) */}
                      <td className="ct-text">{pick(inputName(r.feature) ?? { en: r.feature, es: r.feature }, lang)}</td>
                      <td className="ct-text">{binText(r.bin, lang)}</td>
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
      <>
        {/* the column is split by measure, not by the reasons' height (R4 c01 M1, c02 M1: the reasons' two-line Spanish names left the
            distribution a plot of 10 px): the distribution's part keeps its plot's floor (data-plot-floor, measured by layout.ts) and
            the reasons' card gives up the rest, its table scrolling with its cue */}
        <div className="ct-part" style={{ flex: '1 1 auto' }}>
        <PlotCard
          fill
          title={live ? { en: 'The applicant in the rail: principal reasons', es: 'El solicitante del panel: razones principales' } : { en: 'The four strongest characteristics', es: 'Las cuatro características más fuertes' }}
          lane={live ? 'live' : REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={
            live
              ? {
                  // one line, so the chart below keeps its height (R3 c01 M2)
                  en: 'Furthest below the average points of all applicants (Regulation B, comment 9(b)(2)-5).',
                  es: 'Más bajo el promedio de puntos de los solicitantes (Regulation B, comentario 9(b)(2)-5).',
                }
              : {
                  en: "By information value on the training split: this variant's document carries no scored applicants (Holdout and German do).",
                  es: 'Por valor de información en la partición de entrenamiento: el documento de esta variante no trae solicitantes puntuados.',
                }
          }
        >
          <div className="ct-scroll" data-caos-flow="">
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
                    <td className="caos-col-text">{pick(inputName(r.feature) ?? { en: r.feature, es: r.feature }, lang)}</td>
                    <td>{formatNumber(r.points, lang, { decimals: 0 })}</td>
                    <td>{formatNumber(r.avg, lang, { decimals: 1 })}</td>
                    <td>{formatNumber(r.shortfall, lang, { decimals: 1 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <table className="caos-table" data-table="iv">
              <thead>
                <tr>
                  <th className="caos-col-text">{pick({ en: 'Characteristic', es: 'Característica' }, lang)}</th>
                  <th>{pick({ en: 'Information value', es: 'Valor de información' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {byIv.map((r) => (
                  <tr key={r.f}>
                    <td className="caos-col-text">{pick(inputName(r.f) ?? { en: r.f, es: r.f }, lang)}</td>
                    <td>{formatNumber(r.iv, lang, { decimals: 3 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          </div>
        </PlotCard>
        </div>
        <div className="ct-part" data-plot-floor="11rem" data-block="applicant-distribution" style={{ flex: '0 0 auto' }}>
        <PlotCard
          // the chart fills its card in both states (R3 c01 M2: a fixed 220 px chart under a six-row table was cut by its column at 1280 x 800)
          fill
          // with no scored applicant the card shows the two distributions only: titled and laned for what it draws (R2b c01 M2)
          title={live ? { en: 'Where this applicant sits', es: 'Dónde se ubica este solicitante' } : { en: 'PD of defaulters and non-defaulters', es: 'PD de incumplidores y no incumplidores' }}
          lane={live ? 'live' : REPLAY}
          provenance={prov}
          dataKey={stateKey}
          // short notes: the chart keeps its height under the card above (R3 c01 M2)
          note={live ? { en: "The scorecard's PD, log scale; the marker is the applicant.", es: 'PD de la tarjeta, escala logarítmica; la marca es el solicitante.' } : { en: "The scorecard's PD on this variant, log scale.", es: 'PD de la tarjeta en esta variante, escala logarítmica.' }}
        >
          <UPlotChart
            height="fill"
            // the bins are log10 PD bins: drawn on a log axis, and the two groups apart by the dash as well as the colour (R3 c02 m12, m13)
            x={{ values: dist.x, log: true, label: { en: 'PD (bin centre)', es: 'PD (centro del tramo)' }, format: { percent: true, digits: 2 } }}
            y={{ label: { en: 'Share of the group', es: 'Fracción' }, format: { percent: true, decimals: 0 } }}
            series={[
              { label: { en: 'Defaulters', es: 'Incumplidores' }, values: dist.def, color: '--color-bad' },
              { label: { en: 'Non-defaulters', es: 'No incumplidores' }, values: dist.non, color: '--color-good', dash: [6, 4] },
            ]}
            marks={live ? [{ x: live.pdScorecard, label: { en: 'applicant', es: 'solicitante' } }] : undefined}
          />
        </PlotCard>
        </div>
      </>
    </ViewsRow>
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

/** One panel of the EBM view: the term's score over its bins, with the axis label in both languages; a categorical term names each
 * category by its codebook (`categories`, in the order of `y`), never by its code or its position (R3 c01 B3, c02 B3). */
export interface EbmShape {
  name: string;
  x: number[];
  y: number[];
  categorical: boolean;
  xLabel: Bi;
  categories?: Array<{ code: string; label: Bi }>;
}

/**
 * The six strongest main effects as panels. A continuous term plots each bin at its left edge; a categorical term plots
 * each category at its own code (the key of `categories`, whose value is the bin of the score): the code of a category is
 * not its position (U16-R2 B3: EDUCATION 4 was drawn at 5). The axis names the feature's unit from the data dictionary
 * (`fit.features`): a money feature is in NT dollars, or Deutsche Mark for the German twin.
 */
export function ebmShapes(ex: EbmExport, fit?: { features?: Array<{ name: string; unit: string }> }, kind: 'all' | 'continuous' | 'categorical' = 'all'): EbmShape[] {
  const isCategorical = (index: number) => ex.features[ex.terms[index].features[0]].levels[0].kind !== 'continuous';
  return termImportance(ex)
    .filter((t) => ex.terms[t.index].features.length === 1)
    .filter((t) => (kind !== 'continuous' && kind !== 'categorical') || (kind === 'categorical') === isCategorical(t.index))
    .slice(0, kind === 'categorical' ? undefined : 6)
    .map((t) => {
      const term = ex.terms[t.index];
      const feat = ex.features[term.features[0]];
      const lv = feat.levels[0];
      const scores = term.scores as number[];
      // the German money by its symbol on a small axis ("Monto del crédito (marcos alemanes)" was cut at the panel edge)
      const declared = fit?.features?.find((f) => f.name === term.name)?.unit ?? '';
      const unit = declared === 'DM' ? { en: 'DM', es: 'DM' } : unitName(declared);
      if (lv.kind === 'continuous') {
        const cuts = lv.cuts ?? [];
        // bin k (1..cuts+1) covers [cut_(k-1), cut_k); plot each bin at its left edge, the first at the first cut
        const x = [cuts[0] - 1e-9, ...cuts];
        const label = (l: 'en' | 'es') => (unit ? `${termName(term.name, l)} (${unit[l]})` : termName(term.name, l));
        return { name: term.name, x, y: scores.slice(1, cuts.length + 2), categorical: false, xLabel: { en: label('en'), es: label('es') } };
      }
      const cats = Object.entries(lv.categories ?? {}).sort((a, b) => a[1] - b[1]);
      return {
        name: term.name,
        x: cats.map(([code], i) => (Number.isFinite(Number(code)) ? Number(code) : i + 1)),
        y: cats.map(([, bin]) => scores[bin]),
        categorical: true,
        xLabel: { en: termName(term.name, 'en'), es: termName(term.name, 'es') },
        categories: cats.map(([code]) => ({ code, label: categoryName(term.name, code) })),
      };
    });
}

/** The EBM's six strongest continuous main effects: each term's score over its bins (the "boosted scorecard"), and every term
 * by the spread of its scores. The categorical inputs have a view of their own (EbmCategoriesView): one bar per named category
 * needs more height than a small multiple has (R3 c01 B3: ten German purposes in a 200 px panel), and content is split, never cut
 * (ADR-0071 rule 6). */
export function EbmView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const ex = sel ? details<{ export: EbmExport }>(sel, 'P3-ebm')?.export : undefined;
  const fit = sel?.data.models.fit;
  const shapes = useMemo(() => (ex ? ebmShapes(ex, fit, 'continuous') : null), [ex, fit]);
  if (!sel || !ex || !shapes) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const pairs = (l: 'en' | 'es') => ex.terms.filter((t) => t.features.length === 2).map((t) => termName(t.name, l));
  const categorical = ebmShapes(ex, fit, 'categorical').length;
  return (
    <ViewsRow shares={[2, 1]}>
      <PlotCard
        fill
        title={{ en: 'Shape functions of the six strongest continuous main effects', es: 'Funciones de forma de los seis efectos principales continuos más fuertes' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `Each panel is one term's contribution to the log-odds of default over its bins; their sum plus the intercept is the model.${categorical ? ` The ${categorical === 1 ? 'categorical input is' : `${categorical} categorical inputs are`} in the next view, one bar per category.` : ''} Pairwise terms: ${pairs('en').join('; ') || 'none'}.`,
          es: `Cada panel es la contribución de un término al logaritmo de la razón de probabilidades de incumplimiento sobre sus tramos; su suma más el intercepto es el modelo.${categorical ? ` ${categorical === 1 ? 'La variable categórica está' : `Las ${categorical} variables categóricas están`} en la vista siguiente, una barra por categoría.` : ''} Términos de pares: ${pairs('es').join('; ') || 'ninguno'}.`,
        }}
      >
        <div className="ct-grid6-fill" data-caos-flow="" data-views="6">
          {shapes.map((s) => (
            <div key={s.name} className="ct-small-multiple" data-term={s.name}>
              <UPlotChart
                height="fill"
                x={{ values: s.x, label: s.xLabel }}
                y={{ label: { en: 'Log-odds', es: 'Logaritmo de la razón' }, format: { decimals: 2 } }}
                // the series is the term's log-odds, so the screen-reader table does not repeat the x title as its value column (R4 c02 m12)
                series={[{ label: { en: 'Log-odds', es: 'Logaritmo de la razón' }, values: s.y, color: '--color-accent', mode: 'line' }]}
              />
            </div>
          ))}
        </div>
      </PlotCard>
      <PlotCard fill title={{ en: 'Terms by the spread of their scores', es: 'Términos según la amplitud de sus puntajes' }} lane={REPLAY} provenance={prov} dataKey={stateKey} note={{ en: 'Spread: the largest minus the smallest score of the term, in log-odds.', es: 'Amplitud: el mayor menos el menor puntaje del término, en logaritmo de la razón de probabilidades.' }}>
        <div className="ct-scroll" data-caos-flow="">
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
                  <td className="caos-col-text">{termName(t.name, lang)}</td>
                  <td>{formatNumber(t.spread, lang, { decimals: 3 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** The EBM's categorical main effects, strongest first: one horizontal bar per category, each named by the dataset's codebook (the German
 * codes A11 to A410, the Taiwan education codes; R3 c01 B3, c02 B3), at the height its rows need, in a card that scrolls with a fade when
 * they are more than it holds (ADR-0071 rule 6). */
export function EbmCategoriesView({ sel }: { sel: Selection | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const ex = sel ? details<{ export: EbmExport }>(sel, 'P3-ebm')?.export : undefined;
  const fit = sel?.data.models.fit;
  const shapes = useMemo(() => (ex ? ebmShapes(ex, fit, 'categorical') : null), [ex, fit]);
  if (!sel || !ex || !shapes) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  return (
    <PlotCard
      fill
      title={{ en: 'The categorical inputs: the score of each category', es: 'Las variables categóricas: el puntaje de cada categoría' }}
      lane={REPLAY}
      provenance={prov}
      dataKey={stateKey}
      note={{
        en: "Each bar is a category's contribution to the log-odds of default; a code the codebook does not document is labelled undocumented.",
        es: 'Cada barra es la contribución de una categoría al logit (el logaritmo de la razón de probabilidades) de incumplimiento; un código que el libro de códigos no documenta se indica como tal.',
      }}
    >
      {/* the panels fill the stage at every size (a list of fixed-height charts drew 18 % of a 2560 stage, gate G6) */}
      <div className="ct-panels-fill" data-caos-flow="" data-views={String(Math.min(shapes.length, 6))}>
        {shapes.map((s) => (
          <div key={s.name} className="ct-small-multiple" data-term={s.name}>
            <BarChart
              title={s.xLabel}
              orientation="horizontal"
              height="fill"
              data={(s.categories ?? []).map((c, k) => ({ id: c.code, label: c.label, value: s.y[k], tone: 'accent' as const }))}
              axis={{ label: { en: `${s.xLabel.en}: log-odds`, es: `${s.xLabel.es}: logit` }, format: { decimals: 2 } }}
            />
          </div>
        ))}
      </div>
    </PlotCard>
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
        label: { en: `${termName(t.name, 'en')} (${t.f.direction > 0 ? 'raises' : 'lowers'} risk)`, es: `${termName(t.name, 'es')} (${t.f.direction > 0 ? 'sube' : 'baja'} el riesgo)` },
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
      <PlotCard title={{ en: 'Monotone gradient boosting: the checks', es: 'Potenciación de gradiente monótona: las verificaciones' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
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
              <td>{pick({ en: 'Reason codes: mean top-4 overlap with 10 bootstrap refits', es: 'Códigos de razón: coincidencia media de los 4 principales con 10 reajustes por remuestreo' }, lang)}</td>
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
        // the count it draws (R3 c01 m10: "the six strongest" over the German twin's two constrained features)
        title={chart.series.length === 1 ? { en: 'Partial dependence of the constrained feature', es: 'Dependencia parcial de la variable restringida' } : { en: `Partial dependence of the ${COUNT_TEXT[chart.series.length]?.en ?? chart.series.length} strongest constrained features`, es: `Dependencia parcial de las ${COUNT_TEXT[chart.series.length]?.es ?? chart.series.length} variables restringidas más fuertes` }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: "Raw log-odds, centred at the lowest quantile, along each feature's quantiles in the training slice.", es: 'Logaritmo de la razón de probabilidades crudo, centrado en el cuantil más bajo, a lo largo de los cuantiles de cada variable en la partición de entrenamiento.' }}
      >
        <UPlotChart
          height="fill"
          x={{ values: chart.x, label: { en: 'Quantile of the feature', es: 'Cuantil de la variable' }, format: { decimals: 2 } }}
          y={{ label: { en: 'Change in log-odds', es: 'Cambio del logaritmo de la razón' }, format: { decimals: 2 } }}
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
  woe_encoded?: string[];
}

/** A count as a word in a title ("the six strongest"). */
const COUNT_TEXT: Record<number, { en: string; es: string }> = {
  2: { en: 'two', es: 'dos' },
  3: { en: 'three', es: 'tres' },
  4: { en: 'four', es: 'cuatro' },
  5: { en: 'five', es: 'cinco' },
  6: { en: 'six', es: 'seis' },
};

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
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'P2a: L1 logistic regression on WoE', es: 'P2a: regresión logística L1 sobre WoE' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `Penalty strength C = ${formatNumber(l1.C, 'en', { digits: 3 })}, chosen by cross-validated log loss; ${l1.selected?.length ?? 0} of ${coefs.length} variables survive.`,
          es: `Fuerza de penalización C = ${formatNumber(l1.C, 'es', { digits: 3 })}, elegida por la pérdida logarítmica con validación cruzada; sobreviven ${l1.selected?.length ?? 0} de ${coefs.length} variables.`,
        }}
      >
        <div className="ct-stack" data-caos-flow="">
          <Verdict
            compact
            // the title says what the verdict found (R3 c02 m10: "Signs agree with WoE" over "Some coefficient is positive")
            title={l1.signs_agree_with_woe ? { en: 'Signs agree with WoE', es: 'Signos de acuerdo con el WoE' } : { en: 'A sign disagrees with WoE', es: 'Un signo en desacuerdo con el WoE' }}
            tone={l1.signs_agree_with_woe ? 'good' : 'warn'}
            verdict={
              l1.signs_agree_with_woe
                ? { en: 'Every surviving coefficient is negative on WoE, as a sound scorecard requires.', es: 'Todo coeficiente que sobrevive es negativo sobre el WoE, como exige una tarjeta de puntuación sólida.' }
                : { en: 'Some coefficient is positive on WoE: a sign the penalty did not remove.', es: 'Algún coeficiente es positivo sobre el WoE: un signo que la penalización no eliminó.' }
            }
          />
          <div className="ct-scroll" data-caos-flow="">
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
                    <td className="ct-text">{pick(inputName(k) ?? { en: k, es: k }, lang)}</td>
                    <td>{b === 0 ? pick({ en: '0 (removed)', es: '0 (eliminada)' }, lang) : formatNumber(b, lang, { decimals: 3 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'P2b: the selected PLTR rules', es: 'P2b: las reglas PLTR seleccionadas' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `${rules.length} of ${pl.n_candidate_rules ?? 0} candidate rules selected; Jaccard stability of the selection over ${pl.stability?.bootstraps ?? 0} bootstraps: mean ${formatNumber(pl.stability?.jaccard_mean, 'en', { decimals: 2 })}, minimum ${formatNumber(pl.stability?.jaccard_min, 'en', { decimals: 2 })}.${pl.woe_encoded?.length ? ' An input marked (WoE) is cut on its WoE, not on its code.' : ''}`,
          es: `${rules.length} de ${pl.n_candidate_rules ?? 0} reglas candidatas seleccionadas; estabilidad de Jaccard de la selección en ${pl.stability?.bootstraps ?? 0} remuestreos: media ${formatNumber(pl.stability?.jaccard_mean, 'es', { decimals: 2 })}, mínimo ${formatNumber(pl.stability?.jaccard_min, 'es', { decimals: 2 })}.${pl.woe_encoded?.length ? ' Una variable marcada (WoE) se corta en su WoE, no en su código.' : ''}`,
        }}
      >
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table">
            <thead>
              <tr>
                <th className="caos-col-text">{pick({ en: 'Rule (on the training slice)', es: 'Regla (en la partición de entrenamiento)' }, lang)}</th>
                <th>{pick({ en: 'Coefficient', es: 'Coeficiente' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.rule}>
                  <td className="caos-col-text">
                    {ruleNames(ruleText(r.rule, lang, pl.woe_encoded), lang)}
                  </td>
                  <td>{formatNumber(r.coefficient, lang, { decimals: 3 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** The foundation-model challenger, with the licence of its weights on the view, and its ROC against the scorecard and
 * the GBM on the same records. */
/** The Spanish of the TabPFN licence the German twin's document declares; another wording prints as declared. */
const TABPFN_LICENCE_ES: Record<string, string> = {
  'code Apache-2.0; TabPFN v2 weights, Prior Labs License v1.1 (Apache 2.0 plus attribution: Built with PriorLabs-TabPFN)':
    'código bajo Apache-2.0; pesos de TabPFN v2 bajo la Prior Labs License v1.1 (Apache 2.0 más la atribución «Built with PriorLabs-TabPFN»)',
};

/**
 * The research challenger of the German twin: the weights' licence, the attribution its licence asks for and its ensemble. It sits
 * in the Ladder, under the rungs it joins (R4 c01 M4: a seventh peer sub-view broke ADR-0071 rule 5); the Ladder's table and ROC
 * carry its AUC, its DeLong p and its curve with every other rung.
 */
export function TabPfnCard({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const r = sel ? record(sel, 'P5-tabpfn') : undefined;
  if (!sel || !r) return null;
  const v = sel.data.variant;
  const d = r.details as { licence: string; attribution: string; n_estimators: number };
  // the licence in the reader's language, the licences' names as published; the attribution the licence asks for is quoted in its
  // original beside the Spanish rendering (R4 ruling 6)
  const licence = { en: d.licence, es: TABPFN_LICENCE_ES[d.licence] ?? d.licence };
  return (
    <PlotCard
      title={{ en: 'TabPFN v2, research challenger', es: 'TabPFN v2, retador de investigación' }}
      lane={REPLAY}
      provenance={provenanceOf(v.provenance.truth_status)}
      dataKey={stateKey}
      note={{ en: `${d.attribution}.`, es: `Construido con PriorLabs-TabPFN (en el original, «${d.attribution}»).` }}
    >
      <Verdict compact title={{ en: 'Weights licence', es: 'Licencia de los pesos' }} tone="warn" verdict={licence} />
      <p className="ct-note">
        {pick({ en: 'Ensemble members', es: 'Miembros del ensamble' }, lang)}: {formatNumber(d.n_estimators, lang)}.
      </p>
    </PlotCard>
  );
}

export function ModelGroup({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  // six peers on every variant (ADR-0071 rule 5): the German twin's TabPFN is a card of the Ladder (R4 c01 M4)
  const tabs: Array<{ id: string; label: BiText; content: ReactElement }> = [
    { id: 'ladder', label: { en: 'Ladder', es: 'Escalera' }, content: <LadderView sel={sel} /> },
    { id: 'scorecard', label: { en: 'Scorecard', es: 'Tarjeta de puntuación' }, content: <ScorecardView sel={sel} /> },
    { id: 'ebm', label: { en: 'EBM', es: 'EBM' }, content: <EbmView sel={sel} /> },
    { id: 'ebm-categories', label: { en: 'EBM categories', es: 'Categorías EBM' }, content: <EbmCategoriesView sel={sel} /> },
    { id: 'gbm', label: { en: 'GBM', es: 'GBM' }, content: <GbmView sel={sel} /> },
    { id: 'penalised', label: { en: 'L1 and PLTR', es: 'L1 y PLTR' }, content: <PenalisedView sel={sel} /> },
  ];
  return <SubTabs ariaLabel={pick({ en: 'Views of the model', es: 'Vistas del modelo' }, lang)} tabs={tabs.map((t) => ({ ...t, label: pick(t.label, lang) }))} />;
}
