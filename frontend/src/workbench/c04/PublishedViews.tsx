// C04's published variant (CT-406; docs/design/features/c04-transitions/web.md, "Published"): three papers recomputed
// by riskvalidation beside their prints. Validation (Papers): Israel, Rosenthal and Wei's (2001) nine distances,
// Schuermann and Hanson's (2004) Table 5 and Engelmann's (2024) section 4, each printed value beside the recomputed one
// with its agreement, and Engelmann's projected PD paths. Model: what each paper computes and why its matrices are not
// shown (derived-only: the agency matrices two of them reprint are read from the data root, used, and never written to
// an artifact). Impact: the intervals of Table 5 recomputed live in the browser at its inputs, 15 defaults of 531,
// against the printed bounds, and along the default correlation at the rail's level.
import { PlotCard, formatNumber, pick, useShellLang, useWorkbenchState, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart, type ChartSeries } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { effectiveN, pdAgrestiCoull, pdJeffreys, pdWald } from '../../engine/transitions';
import type { C04PublishedOutputs, VariantArtifact } from '../../lib/contract.types';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { isPublished, type C04Sel, type PublishedVariant } from './selection';

const LIVE = 'live' as const;
type Lang = 'en' | 'es';
type Both = { en: string; es: string };

/** Table 5's level: Schuermann and Hanson's intervals are at 95% (their section 3.1). */
export const TABLE5_LEVEL = 0.95;
/** The correlations the live chart runs over: 0 to 5% by a quarter of a point (the rail's range), Table 5's 0, 1%
 * and 2% among them exactly (i / 400 is the double nearest each). */
export const RHO_GRID = Array.from({ length: 21 }, (_, i) => i / 400);
/** Israel et al. print their distances to six digits (contract section 3). */
const IRW_DECIMALS = 6;
/** Table 5 prints basis points to two decimals. */
const SR190_DECIMALS = 2;

/** Whether a recomputed value prints as its print: within half a unit of the print's last digit, both ends inclusive,
 * with room for the binary representation; the pipeline's rule (c04_published.prints_as), here in the stored unit. */
export function printsAs(value: number, printed: number, decimals: number): boolean {
  return Math.abs(value - printed) <= 0.5 * 10 ** -decimals + 1e-12;
}

const both = (f: (lang: Lang) => string): Both => ({ en: f('en'), es: f('es') });
/** A probability as a percentage with significant digits. */
const pctd = (lang: Lang, v: number | null | undefined, digits = 3) => formatNumber(v, lang, { percent: true, digits });
/** A correlation as a whole percentage (Table 5's 0, 1% and 2%). */
const pct0 = (lang: Lang, v: number) => formatNumber(v, lang, { percent: true, decimals: 0 });
/** A fraction in basis points at a number of decimals. */
const bp = (lang: Lang, v: number, decimals: number) => formatNumber(v * 1e4, lang, { decimals });
/** "lower to upper" in basis points. */
const bpRange = (lang: Lang, lo: number, hi: number, decimals: number) => `${bp(lang, lo, decimals)} ${lang === 'en' ? 'to' : 'a'} ${bp(lang, hi, decimals)}`;

function publishedOf(sel: C04Sel | null): PublishedVariant | null {
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  return v && isPublished(v) ? v : null;
}

/** What a view of the published variant says on another variant (the instrument shows these on the published one). */
function NotPublished() {
  const lang = useShellLang();
  return <p className="ct-note">{pick({ en: "This view reads the published variant's papers.", es: 'Esta vista lee los artículos de la variante publicada.' }, lang)}</p>;
}

/** A paper's attribution from the manifest's source registry, without a closing full stop (a sentence adds its own). */
function attributionOf(sel: C04Sel, source: string): string {
  return (sel.data.manifest.source_details?.[source]?.attribution ?? source).replace(/\.\s*$/, '');
}

/** The licence classes of the source registry, in words. */
const CLASS_TEXT: Record<string, Both> = {
  'derived-only': { en: 'derived-only', es: 'solo derivados' },
  'mirror-allowed': { en: 'mirror-allowed', es: 'espejo permitido' },
};

const AGREES: Both = { en: 'agrees', es: 'concuerda' };
const DIFFERS: Both = { en: 'does not agree', es: 'no concuerda' };

/** Israel et al.'s three methods, by the paper's equation numbers. */
const IRW_METHOD: Record<string, Both> = {
  jlt: { en: 'JLT (3)', es: 'JLT (3)' },
  diagonal: { en: 'Log series (1), diagonal adjustment (2)', es: 'Serie logarítmica (1), ajuste diagonal (2)' },
  weighted: { en: "Log series (1), weighted adjustment (2')", es: "Serie logarítmica (1), ajuste ponderado (2')" },
};
const INTERVAL_NAME: Record<string, Both> = {
  wald: { en: 'Wald (2.2)', es: 'Wald (2.2)' },
  agresti_coull: { en: 'Agresti-Coull (3.3)', es: 'Agresti-Coull (3.3)' },
};
const N_DAGGER: Both = { en: 'N dagger (3.4)', es: 'N daga (3.4)' };

/** Table 5's correlations, in the order of its rows and of its N dagger. */
const table5Rhos = (o: C04PublishedOutputs) => [...new Set(o.sr190.rows.map((r) => r.rho))];

/** Why an Israel et al. distance does not agree with its print, when the outputs say: the first matrix's JLT distance
 * follows from the paper's printed generator, not from (3) on the printed matrix. Null when no reason is stated. */
export function irwReason(o: C04PublishedOutputs, row: C04PublishedOutputs['irw']['rows'][number]): Both | null {
  const first = o.irw.rows[0]?.matrix;
  if (row.agrees || row.matrix !== first || row.method !== 'jlt' || !printsAs(o.irw.jlt_from_printed_generator, row.printed, IRW_DECIMALS)) return null;
  const d = (l: Lang, x: number) => formatNumber(x, l, { decimals: IRW_DECIMALS });
  return both((l) =>
    l === 'en'
      ? `equation (3) on the printed matrix gives ${d(l, row.recomputed)}; the print follows from the paper's printed generator Q_JLT, whose distance is ${d(l, o.irw.jlt_from_printed_generator)}`
      : `la ecuación (3) sobre la matriz impresa da ${d(l, row.recomputed)}; lo impreso resulta del generador Q_JLT impreso en el artículo, cuya distancia es ${d(l, o.irw.jlt_from_printed_generator)}`,
  );
}

/** One of Engelmann's printed values beside its recomputation, as a table row. */
export interface EngelmannRow {
  key: string;
  label: Both;
  printed: number;
  recomputed: number;
  decimals: number;
  /** a PD, shown in percent; else a share, shown as printed */
  percent: boolean;
  /** how the agreement is judged: at the printed digits, or within the rounding of the printed entries (W hat) */
  check: 'printed digits' | 'entry rounding';
}

/** Every printed Engelmann value: W_ttc's entries, its PD, each starting portfolio's PD and printed extreme. */
export function engelmannRows(o: C04PublishedOutputs): EngelmannRow[] {
  const e = o.engelmann;
  const n = e.w_ttc.printed.length;
  const rows: EngelmannRow[] = e.w_ttc.printed.map((p, k) => ({
    key: `w_ttc-${k + 1}`,
    label: k === n - 1 ? { en: 'W_ttc, default', es: 'W_ttc, incumplimiento' } : { en: `W_ttc, grade ${k + 1}`, es: `W_ttc, grado ${k + 1}` },
    printed: p,
    recomputed: e.w_ttc.recomputed[k],
    decimals: e.w_ttc.decimals[k],
    percent: false,
    check: 'printed digits',
  }));
  rows.push({ key: 'ttc-pd', label: { en: 'TTC PD', es: 'PD TTC' }, printed: e.ttc_pd.printed, recomputed: e.ttc_pd.recomputed, decimals: e.ttc_pd.decimals, percent: true, check: 'printed digits' });
  for (const p of e.portfolios) {
    rows.push({
      key: `${p.name}-pd0`,
      label: { en: `${p.name}, PD of year 1`, es: `${p.name}, PD del año 1` },
      printed: p.pd0.printed,
      recomputed: p.pd0.recomputed,
      decimals: p.pd0.decimals,
      percent: true,
      check: p.pd0.check,
    });
    if (p.extreme) {
      rows.push({
        key: `${p.name}-${p.extreme.kind}`,
        label: p.extreme.kind === 'min' ? { en: `${p.name}, lowest projected PD`, es: `${p.name}, PD proyectada mínima` } : { en: `${p.name}, highest projected PD`, es: `${p.name}, PD proyectada máxima` },
        printed: p.extreme.printed,
        recomputed: p.extreme.recomputed,
        decimals: p.extreme.decimals,
        percent: true,
        check: 'printed digits',
      });
    }
  }
  return rows;
}

/** An Engelmann row's agreement: at the printed digits, or (W hat, which the paper prints from unrounded entries built
 * under a correlation it does not state) within the rounding of its printed entries, as the bake checked it. */
export function engelmannAgreement(r: EngelmannRow, lang: Lang): string {
  if (r.check === 'entry rounding') {
    const gap = formatNumber(Math.abs(r.recomputed - r.printed) * 100, lang, { digits: 2 });
    return lang === 'en'
      ? `agrees within the rounding of its printed entries, ${gap} percentage points apart: the paper builds this portfolio under a correlation it does not state and prints the PD of its unrounded entries`
      : `concuerda dentro del redondeo de sus entradas impresas, a ${gap} puntos porcentuales: el artículo construye esta cartera con una correlación que no declara e imprime la PD de sus entradas sin redondear`;
  }
  return (printsAs(r.recomputed, r.printed, r.decimals) ? AGREES : DIFFERS)[lang];
}

/** A value of Engelmann's at its print's precision (printed) or two digits more (recomputed). */
function engelmannValue(r: EngelmannRow, value: number, extra: number, lang: Lang): string {
  return r.percent ? formatNumber(value, lang, { percent: true, decimals: Math.max(0, r.decimals - 2 + extra) }) : formatNumber(value, lang, { decimals: r.decimals + extra });
}

const PATH_COLOR: ShellColorToken[] = ['--color-accent', '--color-magenta', '--color-accent-2', '--color-good', '--color-warn', '--color-bad'];

/** The index of a path's lowest or highest value. */
function extremeAt(path: readonly number[], kind: 'min' | 'max'): number {
  let k = 0;
  for (let i = 1; i < path.length; i++) if (kind === 'min' ? path[i] < path[k] : path[i] > path[k]) k = i;
  return k;
}

/** Engelmann's projected PD paths by year, the TTC PD they drift to, and a mark at each extreme the paper prints (the
 * year the recomputed path reaches it; the printed value is in the table beside). */
export function pathChart(o: C04PublishedOutputs): { years: number[]; series: ChartSeries[]; marks: Array<{ x: number; label: Both }> } {
  const ps = o.engelmann.portfolios;
  const years = (ps[0]?.pd_path ?? []).map((_, i) => i + 1);
  const ttc = o.engelmann.ttc_pd.recomputed;
  const series: ChartSeries[] = ps.map((p, i) => ({ label: p.name, values: p.pd_path, color: PATH_COLOR[i % PATH_COLOR.length], width: 2 }));
  series.push({ label: both((l) => `${l === 'en' ? 'TTC PD' : 'PD TTC'} ${pctd(l, ttc, 4)}`), values: years.map(() => ttc), color: '--color-fg-subtle', width: 1.4, dash: [6, 4] });
  const marks = ps.flatMap((p) => {
    const ext = p.extreme;
    if (!ext) return [];
    const word = (l: Lang) => (ext.kind === 'min' ? (l === 'en' ? 'min' : 'mín') : l === 'en' ? 'max' : 'máx');
    return [{ x: extremeAt(p.pd_path, ext.kind) + 1, label: both((l) => `${p.name}, ${word(l)}`) }];
  });
  return { years, series: series.filter((s) => s.values.some((x) => x !== null)), marks };
}

// ---------------------------------------------------------------------------------------------------------------------
// Validation: the papers

export function PapersView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = publishedOf(sel);
  const paths = useMemo(() => (v ? pathChart(v.outputs) : null), [v]);
  if (!sel) return <Pending />;
  if (!v || !paths) return <NotPublished />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const irwAgree = o.irw.rows.filter((r) => r.agrees).length;
  const srAgree = o.sr190.rows.filter((r) => r.agrees).length;
  const eRows = engelmannRows(o);
  const t3 = o.irw.theorem3_c.filter(Boolean).length;
  const rhos = table5Rhos(o);
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: 'Three papers: each print beside its recomputation', es: 'Tres artículos: cada valor impreso junto a su recálculo' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Recomputed by riskvalidation ${v.provenance.riskvalidation_version ?? ''} from the papers in the data root; a value agrees within half a unit of the print's last digit. Israel et al.: ${irwAgree} of ${o.irw.rows.length} agree; Theorem 3(c) holds for ${t3} of ${o.irw.theorem3_c.length} matrices (a move reachable but never observed: no exact generator); the log series (1) takes ${o.irw.series_terms} terms to the stated 1e-8, as printed. Schuermann and Hanson: ${srAgree} of ${o.sr190.rows.length} agree at ${o.sr190.defaults} defaults of ${o.sr190.n}, the one count whose Wald lower bound prints as the table's. Engelmann: his matrix (11) as printed (rows sum to 1 within ${formatNumber(o.engelmann.row_sum_deviation, 'en', { digits: 2 })}), at unit balance. The Model group cites each paper.`,
            es: `Recalculados por riskvalidation ${v.provenance.riskvalidation_version ?? ''} desde los artículos en la raíz de datos; un valor concuerda dentro de media unidad del último dígito impreso. Israel et al.: concuerdan ${irwAgree} de ${o.irw.rows.length}; el Teorema 3(c) se cumple en ${t3} de ${o.irw.theorem3_c.length} matrices (un movimiento alcanzable pero nunca observado: no hay generador exacto); la serie logarítmica (1) toma ${o.irw.series_terms} términos hasta el 1e-8 declarado, como está impreso. Schuermann y Hanson: concuerdan ${srAgree} de ${o.sr190.rows.length} con ${o.sr190.defaults} incumplimientos de ${o.sr190.n}, el único conteo cuya cota inferior de Wald se imprime como la de la tabla. Engelmann: su matriz (11) tal como está impresa (filas que suman 1 dentro de ${formatNumber(o.engelmann.row_sum_deviation, 'es', { digits: 2 })}), a saldo unitario. El grupo Modelo cita cada artículo.`,
          }}
        >
          <div className="ct-scroll">
            <p className="ct-sm-title">
              {pick({ en: 'Israel, Rosenthal and Wei (2001), section 4: the L1 distance of exp(Q) to P', es: 'Israel, Rosenthal y Wei (2001), sección 4: la distancia L1 de exp(Q) a P' }, lang)}
            </p>
            <table className="caos-table ct-wrap-head" data-table="irw">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Matrix', es: 'Matriz' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Generator', es: 'Generador' }, lang)}</th>
                  <th>{pick({ en: 'Printed', es: 'Impreso' }, lang)}</th>
                  <th>{pick({ en: 'Recomputed', es: 'Recalculado' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Agreement', es: 'Concordancia' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {o.irw.rows.map((r) => {
                  const why = irwReason(o, r);
                  return (
                    <tr key={`${r.matrix}-${r.method}`} data-row={`${r.matrix}|${r.method}`} data-agrees={r.agrees ? 'yes' : 'no'} className={r.agrees ? undefined : 'ct-current'}>
                      <td className="ct-text">{r.matrix}</td>
                      <td className="ct-text">{pick(IRW_METHOD[r.method] ?? { en: r.method, es: r.method }, lang)}</td>
                      <td>{formatNumber(r.printed, lang, { decimals: IRW_DECIMALS })}</td>
                      <td>{formatNumber(r.recomputed, lang, { decimals: IRW_DECIMALS + 2 })}</td>
                      <td className="ct-text">
                        {r.agrees ? AGREES[lang] : `${DIFFERS[lang]}: ${why ? why[lang] : pick({ en: 'the outputs state no reason', es: 'los resultados no declaran una razón' }, lang)}`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="ct-sm-title">
              {pick(
                {
                  en: `Schuermann and Hanson (2004), Table 5: ${o.sr190.defaults} defaults of ${o.sr190.n}, ${pct0('en', TABLE5_LEVEL)}, in basis points (lower to upper bound; the lengths on a wide screen)`,
                  es: `Schuermann y Hanson (2004), Tabla 5: ${o.sr190.defaults} incumplimientos de ${o.sr190.n}, ${pct0('es', TABLE5_LEVEL)}, en puntos básicos (de la cota inferior a la superior; los largos, en una pantalla ancha)`,
                },
                lang,
              )}
            </p>
            <table className="caos-table ct-wrap-head" data-table="sr190">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Interval', es: 'Intervalo' }, lang)}</th>
                  <th>{pick({ en: 'Correlation', es: 'Correlación' }, lang)}</th>
                  <th>{pick({ en: 'Printed', es: 'Impreso' }, lang)}</th>
                  <th>{pick({ en: 'Recomputed', es: 'Recalculado' }, lang)}</th>
                  <th className="ct-room-only">{pick({ en: 'Length, printed', es: 'Largo, impreso' }, lang)}</th>
                  <th className="ct-room-only">{pick({ en: 'Length, recomputed', es: 'Largo, recalculado' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Agreement', es: 'Concordancia' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {o.sr190.rows.map((r) => (
                  <tr key={`${r.interval}-${r.rho}`} data-row={`${r.interval}|${r.rho}`} data-agrees={r.agrees ? 'yes' : 'no'}>
                    <td className="ct-text">{pick(INTERVAL_NAME[r.interval] ?? { en: r.interval, es: r.interval }, lang)}</td>
                    <td>{pct0(lang, r.rho)}</td>
                    <td>{bpRange(lang, r.printed[0], r.printed[1], SR190_DECIMALS)}</td>
                    <td>{bpRange(lang, r.recomputed[0], r.recomputed[1], SR190_DECIMALS + 1)}</td>
                    <td className="ct-room-only">{bp(lang, r.printed[2], SR190_DECIMALS)}</td>
                    <td className="ct-room-only">{bp(lang, r.recomputed[2], SR190_DECIMALS + 1)}</td>
                    <td className="ct-text">{(r.agrees ? AGREES : DIFFERS)[lang]}</td>
                  </tr>
                ))}
                {o.sr190.n_dagger.printed.map((p, k) => {
                  const rho = rhos[k];
                  const dec = o.sr190.n_dagger.decimals[k];
                  const rec = o.sr190.n_dagger.recomputed[k];
                  const ok = printsAs(rec, p, dec);
                  return (
                    <tr key={`n-dagger-${k}`} data-row={`n_dagger|${k}`} data-agrees={ok ? 'yes' : 'no'}>
                      <td className="ct-text">{pick(N_DAGGER, lang)}</td>
                      <td>{rho === undefined ? '-' : pct0(lang, rho)}</td>
                      <td>{formatNumber(p, lang, { decimals: dec })}</td>
                      <td>{formatNumber(rec, lang, { decimals: dec + 2 })}</td>
                      <td className="ct-room-only" />
                      <td className="ct-room-only" />
                      <td className="ct-text">{(ok ? AGREES : DIFFERS)[lang]}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="ct-sm-title">
              {pick({ en: "Engelmann (2024), section 4: the TTC portfolio (10) and the starting portfolios' PDs", es: 'Engelmann (2024), sección 4: la cartera TTC (10) y las PD de las carteras iniciales' }, lang)}
            </p>
            <table className="caos-table ct-wrap-head" data-table="engelmann">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Quantity', es: 'Cantidad' }, lang)}</th>
                  <th>{pick({ en: 'Printed', es: 'Impreso' }, lang)}</th>
                  <th>{pick({ en: 'Recomputed', es: 'Recalculado' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Agreement', es: 'Concordancia' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {eRows.map((r) => (
                  <tr key={r.key} data-row={r.key} data-check={r.check}>
                    <td className="ct-text">{r.label[lang]}</td>
                    <td>{engelmannValue(r, r.printed, 0, lang)}</td>
                    <td>{engelmannValue(r, r.recomputed, 2, lang)}</td>
                    <td className="ct-text">{engelmannAgreement(r, lang)}</td>
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
          title={{ en: `Engelmann's projected PD paths, ${paths.years.length} years`, es: `Las trayectorias de PD proyectadas de Engelmann, ${paths.years.length} años` }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Engelmann (2024), section 4: each starting portfolio projected by (9) under his unstressed matrix (11) as printed, at unit balance, recomputed; the PD of each year. Dashed: the PD of his TTC portfolio (10), to which every path drifts. Marked: the extremes the paper prints, at the year the path reaches them (their values in the table). The matrix itself is derived-only and not shown.`,
            es: `Engelmann (2024), sección 4: cada cartera inicial proyectada por (9) con su matriz sin estrés (11) tal como está impresa, a saldo unitario, recalculada; la PD de cada año. Segmentada: la PD de su cartera TTC (10), hacia la que deriva toda trayectoria. Marcados: los extremos que imprime el artículo, en el año en que la trayectoria los alcanza (sus valores en la tabla). La matriz misma es solo de derivados y no se muestra.`,
          }}
        >
          <UPlotChart
            height="fill"
            x={{ values: paths.years, label: { en: 'Year of the projection', es: 'Año de la proyección' }, unit: { en: 'years', es: 'años' }, format: { decimals: 0 } }}
            y={{ label: { en: 'PD of the year', es: 'PD del año' }, format: { percent: true, digits: 3 } }}
            series={paths.series}
            marks={paths.marks}
          />
        </PlotCard>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Model: what each paper computes, and why its matrices are not shown

export function PublishedModelView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = publishedOf(sel);
  if (!sel) return <Pending />;
  if (!v) return <NotPublished />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const cls = (source: string) => v.provenance.licence_classes[source] ?? sel.data.manifest.source_details?.[source]?.class ?? '';
  const irwMatrices = [...new Set(o.irw.rows.map((r) => r.matrix))];
  const rhos = table5Rhos(o).filter((r) => r > 0);
  const rhoList = (l: Lang) => rhos.map((r) => pct0(l, r)).join(l === 'en' ? ' and ' : ' y ');
  const ttcPd = (l: Lang) => formatNumber(o.engelmann.ttc_pd.printed, l, { percent: true, decimals: Math.max(0, o.engelmann.ttc_pd.decimals - 2) });
  const years = o.engelmann.portfolios[0]?.pd_path.length ?? 0;
  const papers: Array<{ source: string; title: Both; computes: Both; here: Both; matrices: Both }> = [
    {
      source: 'israel-rosenthal-wei-2001',
      title: { en: 'Israel, Rosenthal and Wei (2001), section 4', es: 'Israel, Rosenthal y Wei (2001), sección 4' },
      computes: {
        en: `Generators Q of one-year rating matrices P, judged by the L1 distance of exp(Q) to P: Jarrow, Lando and Turnbull's (3), and the log series (1) repaired by the diagonal (2) and weighted (2') adjustments, on ${irwMatrices.length} matrices (${irwMatrices.join(', ')}); Theorem 3 gives conditions under which no exact generator exists.`,
        es: `Generadores Q de matrices anuales de calificación P, juzgados por la distancia L1 de exp(Q) a P: el (3) de Jarrow, Lando y Turnbull, y la serie logarítmica (1) reparada por los ajustes diagonal (2) y ponderado (2'), en ${irwMatrices.length} matrices (${irwMatrices.join(', ')}); el Teorema 3 da condiciones bajo las que no existe un generador exacto.`,
      },
      here: {
        en: `The ${o.irw.rows.length} distances from the printed matrices, Theorem 3(c) for each matrix and the ${o.irw.series_terms} terms the series takes on the first; the Validation group sets each beside its print.`,
        es: `Las ${o.irw.rows.length} distancias desde las matrices impresas, el Teorema 3(c) de cada matriz y los ${o.irw.series_terms} términos que toma la serie en la primera; el grupo Validación pone cada una junto a lo impreso.`,
      },
      matrices: {
        en: "The three matrices are S&P's and Moody's data reprinted in the paper: read from the PDF in the data root, used, and never written to an artifact.",
        es: "Las tres matrices son datos de S&P y de Moody's reimpresos en el artículo: se leen desde el PDF en la raíz de datos, se usan y nunca se escriben en un artefacto.",
      },
    },
    {
      source: 'schuermann-hanson-2004',
      title: { en: 'Schuermann and Hanson (2004), Table 5', es: 'Schuermann y Hanson (2004), Tabla 5' },
      computes: {
        en: `The Wald (2.2) and Agresti-Coull (3.2) to (3.3) intervals at ${pct0('en', TABLE5_LEVEL)} for the PD of one grade (BB in 2002, ${o.sr190.n} obligors, the cohort method), with independent defaults and at default correlations of ${rhoList('en')} through the effective number of obligors N dagger (3.4).`,
        es: `Los intervalos de Wald (2.2) y de Agresti-Coull (3.2) a (3.3) al ${pct0('es', TABLE5_LEVEL)} para la PD de un grado (BB en 2002, ${o.sr190.n} deudores, el método de cohortes), con incumplimientos independientes y con correlaciones de incumplimiento de ${rhoList('es')} mediante el número efectivo de deudores N daga (3.4).`,
      },
      here: {
        en: `The ${o.sr190.rows.length * 2} bounds and ${o.sr190.rows.length} lengths at ${o.sr190.defaults} defaults of ${o.sr190.n}, the count the print implies, and the ${o.sr190.n_dagger.printed.length} values of N dagger; the Impact group recomputes them live.`,
        es: `Las ${o.sr190.rows.length * 2} cotas y ${o.sr190.rows.length} largos con ${o.sr190.defaults} incumplimientos de ${o.sr190.n}, el conteo que implica lo impreso, y los ${o.sr190.n_dagger.printed.length} valores de N daga; el grupo Impacto los recalcula en vivo.`,
      },
      matrices: {
        en: "Table 5 holds the paper's own interval computations and no data; it has no matrix to show.",
        es: 'La Tabla 5 contiene los cálculos de intervalos del propio artículo y ningún dato; no tiene matriz que mostrar.',
      },
    },
    {
      source: 'engelmann-2024',
      title: { en: 'Engelmann (2024), section 4', es: 'Engelmann (2024), sección 4' },
      computes: {
        en: `The through-the-cycle portfolio (10) that an unstressed one-year matrix (11) and an origination mix lead to (Theorem 1), and ${o.engelmann.portfolios.length} starting portfolios projected by (9) over ${years} years, whose PD paths show how a projection drifts toward the TTC PD.`,
        es: `La cartera a través del ciclo (10) a la que llevan una matriz anual sin estrés (11) y una mezcla de originación (Teorema 1), y ${o.engelmann.portfolios.length} carteras iniciales proyectadas por (9) a ${years} años, cuyas trayectorias de PD muestran cómo una proyección deriva hacia la PD TTC.`,
      },
      here: {
        en: `W_ttc and its PD (${ttcPd('en')} printed), each starting portfolio's PD and printed extreme, and the ${years}-year paths, at unit balance.`,
        es: `W_ttc y su PD (${ttcPd('es')} impresa), la PD y el extremo impreso de cada cartera inicial, y las trayectorias a ${years} años, a saldo unitario.`,
      },
      matrices: {
        en: 'The matrix (11) is reprinted in the paper from Trueck and Rachev (2009): read, used and never written; only the portfolios, the PDs and the paths are published.',
        es: 'La matriz (11) está reimpresa en el artículo desde Trueck y Rachev (2009): se lee, se usa y nunca se escribe; solo se publican las carteras, las PD y las trayectorias.',
      },
    },
  ];
  // a paper's citation without its address, which goes under a short link (the source's landing page)
  const citation = (source: string) => {
    const text = attributionOf(sel, source).replace(/\s*https?:\/\/\S+$/, '').replace(/\.\s*$/, '');
    return { text: `${text}.`, link: sel.data.manifest.source_details?.[source]?.landing ?? null };
  };
  const w = o.engelmann.w_ttc;
  const k = Math.max(0, w.printed.length - 1);
  // the performing grades of the matrix (11) with half a step of room on each side, so the end points are not cut
  const x = [0.5, ...Array.from({ length: k }, (_, i) => i + 1), k + 0.5];
  const padded = (vals: number[]) => [null, ...vals.slice(0, k), null];
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: 'What each paper computes, and why its matrices are not shown', es: 'Qué calcula cada artículo, y por qué no se muestran sus matrices' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: "Each paper is derived-only: its PDF stays in the data root and only the results recomputed from it are published, so a matrix a paper reprints is never drawn here; the agencies' own matrices are in the S&P, Moody's and Fitch variants, from CEREP.",
            es: "Cada artículo es solo de derivados: su PDF queda en la raíz de datos y solo se publican los resultados recalculados desde él, así que una matriz que un artículo reimprime nunca se dibuja aquí; las matrices propias de las agencias están en las variantes S&P, Moody's y Fitch, desde CEREP.",
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="papers">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Paper', es: 'Artículo' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'What it computes', es: 'Qué calcula' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'What is published here, and its matrices', es: 'Qué se publica aquí, y sus matrices' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {papers.map((p) => (
                  <tr key={p.source} data-source={p.source} data-licence-class={cls(p.source)}>
                    <td className="ct-text">
                      {p.title[lang]}
                      <ul className="ct-evidence">
                        <li>
                          {citation(p.source).text}{' '}
                          {citation(p.source).link && (
                            <a href={citation(p.source).link} target="_blank" rel="noreferrer">
                              {pick({ en: 'source', es: 'fuente' }, lang)}
                            </a>
                          )}
                        </li>
                        <li>{`${pick({ en: 'Licence class', es: 'Clase de licencia' }, lang)}: ${pick(CLASS_TEXT[cls(p.source)] ?? cls(p.source), lang)}`}</li>
                      </ul>
                    </td>
                    <td className="ct-text">{p.computes[lang]}</td>
                    <td className="ct-text">{`${p.here[lang]} ${p.matrices[lang]}`}</td>
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
          title={{ en: "Engelmann's TTC portfolio (10), printed and recomputed", es: 'La cartera TTC (10) de Engelmann, impresa y recalculada' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `What Theorem 1 computes from the matrix (11) and the origination mix: each grade's share of the balance in the TTC portfolio, printed to ${w.decimals[0] ?? 4} decimals (dots) and recomputed (line); default holds none. A result, not the matrix.`,
            es: `Lo que calcula el Teorema 1 desde la matriz (11) y la mezcla de originación: la fracción del saldo de cada grado en la cartera TTC, impresa con ${w.decimals[0] ?? 4} decimales (puntos) y recalculada (línea); el incumplimiento no tiene nada. Un resultado, no la matriz.`,
          }}
        >
          <UPlotChart
            height="fill"
            x={{ values: x, label: { en: 'Grade of the matrix (11), 1 the best', es: 'Grado de la matriz (11), 1 el mejor' }, format: { decimals: 0 } }}
            y={{ label: { en: 'Share of the TTC portfolio', es: 'Fracción de la cartera TTC' }, format: { percent: true, decimals: 0 } }}
            series={[
              { label: { en: 'Printed', es: 'Impresa' }, values: padded(w.printed), color: '--color-fg', mode: 'points' },
              { label: { en: 'Recomputed', es: 'Recalculada' }, values: padded(w.recomputed), color: '--color-accent', width: 2 },
            ]}
          />
        </PlotCard>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Impact: Table 5's intervals, live

/** Table 5's twelve bounds and lengths recomputed live by the ports at its inputs (its level, its three correlations),
 * each row with its agreement with the print in basis points at the printed two decimals. */
export function table5Live(o: C04PublishedOutputs) {
  const { defaults, n } = o.sr190;
  return o.sr190.rows.map((r) => {
    const live = r.interval === 'wald' ? pdWald(defaults, n, { level: TABLE5_LEVEL, rho: r.rho }) : pdAgrestiCoull(defaults, n, { level: TABLE5_LEVEL, rho: r.rho });
    const values = [live.lower, live.upper, live.length];
    return { row: r, live: values, nEffective: live.nEffective, agrees: values.every((x, k) => printsAs(x * 1e4, r.printed[k] * 1e4, SR190_DECIMALS)) };
  });
}

/** The live chart of Table 5's intervals along the default correlation at a level: the Wald and Agresti-Coull bounds
 * through N dagger, and the printed bounds as points at the printed correlations. */
export function table5Chart(o: C04PublishedOutputs, level: number): ChartSeries[] {
  const { defaults, n } = o.sr190;
  const along = RHO_GRID.map((rho) => ({ wald: pdWald(defaults, n, { level, rho }), ac: pdAgrestiCoull(defaults, n, { level, rho }) }));
  const printedAt = (interval: string, k: number) =>
    RHO_GRID.map((x) => {
      const r = o.sr190.rows.find((row) => row.interval === interval && Math.abs(row.rho - x) < 1e-12);
      return r ? r.printed[k] : null;
    });
  const series: ChartSeries[] = [
    { label: { en: 'Wald, upper', es: 'Wald, superior' }, values: along.map((a) => a.wald.upper), color: '--color-warn', width: 2 },
    { label: { en: 'Wald, lower', es: 'Wald, inferior' }, values: along.map((a) => a.wald.lower), color: '--color-warn', width: 1.4, dash: [5, 4] },
    { label: { en: 'Agresti-Coull, upper', es: 'Agresti-Coull, superior' }, values: along.map((a) => a.ac.upper), color: '--color-magenta', width: 2 },
    { label: { en: 'Agresti-Coull, lower', es: 'Agresti-Coull, inferior' }, values: along.map((a) => a.ac.lower), color: '--color-magenta', width: 1.4, dash: [5, 4] },
    { label: { en: 'Table 5, Wald upper', es: 'Tabla 5, Wald superior' }, values: printedAt('wald', 1), color: '--color-warn', mode: 'points' },
    { label: { en: 'Table 5, Wald lower', es: 'Tabla 5, Wald inferior' }, values: printedAt('wald', 0), color: '--color-warn', mode: 'points' },
    { label: { en: 'Table 5, Agresti-Coull upper', es: 'Tabla 5, Agresti-Coull superior' }, values: printedAt('agresti_coull', 1), color: '--color-magenta', mode: 'points' },
    { label: { en: 'Table 5, Agresti-Coull lower', es: 'Tabla 5, Agresti-Coull inferior' }, values: printedAt('agresti_coull', 0), color: '--color-magenta', mode: 'points' },
  ];
  return series.filter((s) => s.values.some((x) => x !== null));
}

export function PublishedImpactView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = publishedOf(sel);
  const level = sel?.level ?? TABLE5_LEVEL;
  const series = useMemo(() => (v ? table5Chart(v.outputs, level) : null), [v, level]);
  if (!sel) return <Pending />;
  if (!v || !series) return <NotPublished />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const { defaults, n } = o.sr190;
  const live = table5Live(o);
  const agree = live.filter((r) => r.agrees).length;
  const rhos = table5Rhos(o);
  const firstRho = rhos.find((r) => r > 0) ?? 0.01;
  const lv = (l: Lang) => pct0(l, level);
  const t5 = (l: Lang) => pct0(l, TABLE5_LEVEL);
  const rhoText = (l: Lang) => formatNumber(sel.rho, l, { percent: true, decimals: 1 });
  const atRail = [
    { key: 'wald', label: { en: 'Wald (2.2)', es: 'Wald (2.2)' }, i: pdWald(defaults, n, { level: sel.level, rho: sel.rho }) },
    { key: 'agresti_coull', label: { en: 'Agresti-Coull (3.3)', es: 'Agresti-Coull (3.3)' }, i: pdAgrestiCoull(defaults, n, { level: sel.level, rho: sel.rho }) },
    { key: 'jeffreys', label: { en: 'Jeffreys (no correlation)', es: 'Jeffreys (sin correlación)' }, i: pdJeffreys(defaults, n, { level: sel.level }) },
  ];
  const offLevel = Math.abs(level - TABLE5_LEVEL) > 1e-12;
  const span = (l: Lang) => `${pct0(l, RHO_GRID[0])} ${l === 'en' ? 'to' : 'a'} ${pct0(l, RHO_GRID[RHO_GRID.length - 1])}`;
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-2">
        <PlotCard
          fill
          title={{ en: `Table 5's intervals along the default correlation, at ${lv('en')}`, es: `Los intervalos de la Tabla 5 según la correlación de incumplimiento, al ${lv('es')}` }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Schuermann and Hanson (2004), Table 5's inputs, ${defaults} defaults of ${n} obligors, recomputed live from ${span('en')} of default correlation at the rail's level: the Wald (2.2) and Agresti-Coull (3.3) bounds through N dagger (3.4); dots, the printed bounds at ${rhos.map((r) => pct0('en', r)).join(', ')}, which are at ${t5('en')}${offLevel ? `, so at ${lv('en')} the lines leave them by design` : ''}. A correlation of ${pct0('en', firstRho)} already cuts N dagger from ${n} to ${formatNumber(effectiveN(n, firstRho), 'en', { digits: 3 })}. Marked: the rail's correlation. ${attributionOf(sel, 'schuermann-hanson-2004')}.`,
            es: `Los insumos de la Tabla 5 de Schuermann y Hanson (2004), ${defaults} incumplimientos de ${n} deudores, recalculados en vivo de ${span('es')} de correlación de incumplimiento al nivel del panel: las cotas de Wald (2.2) y de Agresti-Coull (3.3) mediante N daga (3.4); puntos, las cotas impresas en ${rhos.map((r) => pct0('es', r)).join(', ')}, que están al ${t5('es')}${offLevel ? `, así que al ${lv('es')} las líneas se apartan de ellas por diseño` : ''}. Una correlación de ${pct0('es', firstRho)} ya reduce N daga de ${n} a ${formatNumber(effectiveN(n, firstRho), 'es', { digits: 3 })}. Marcada: la correlación del panel. ${attributionOf(sel, 'schuermann-hanson-2004')}.`,
          }}
        >
          <UPlotChart
            height="fill"
            x={{ values: RHO_GRID, label: { en: 'Default correlation between every pair', es: 'Correlación de incumplimiento entre cada par' }, format: { percent: true, decimals: 2 } }}
            y={{ label: { en: 'PD bound', es: 'Cota de la PD' }, format: { percent: true, decimals: 1 } }}
            series={series}
            marks={[{ x: sel.rho, label: { en: 'rail', es: 'panel' } }]}
          />
        </PlotCard>
      </div>
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: 'Live against the print', es: 'En vivo contra lo impreso' }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `In basis points, lower to upper bound. Table 5 at its own level (${t5('en')}): ${agree} of ${live.length} intervals recomputed in your browser agree with the print to its two decimals (bounds and lengths). Last rows: the three intervals at the rail's correlation (${rhoText('en')}) and level (${lv('en')}); Jeffreys has no correlation correction.`,
            es: `En puntos básicos, de la cota inferior a la superior. La Tabla 5 a su propio nivel (${t5('es')}): ${agree} de ${live.length} intervalos recalculados en su navegador concuerdan con lo impreso a sus dos decimales (cotas y largos). Últimas filas: los tres intervalos a la correlación (${rhoText('es')}) y el nivel (${lv('es')}) del panel; Jeffreys no tiene corrección por correlación.`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="table5-live">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Interval and correlation', es: 'Intervalo y correlación' }, lang)}</th>
                  <th>{pick({ en: 'Printed', es: 'Impreso' }, lang)}</th>
                  <th>{pick({ en: 'Live', es: 'En vivo' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Agreement', es: 'Concordancia' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {live.map(({ row, live: x, agrees }) => (
                  <tr key={`${row.interval}-${row.rho}`} data-row={`${row.interval}|${row.rho}`} data-agrees={agrees ? 'yes' : 'no'}>
                    <td className="ct-text">{`${pick(INTERVAL_NAME[row.interval] ?? { en: row.interval, es: row.interval }, lang)}, ${pct0(lang, row.rho)}`}</td>
                    <td>{bpRange(lang, row.printed[0], row.printed[1], SR190_DECIMALS)}</td>
                    <td>{bpRange(lang, x[0], x[1], SR190_DECIMALS + 1)}</td>
                    <td className="ct-text">{(agrees ? AGREES : DIFFERS)[lang]}</td>
                  </tr>
                ))}
                {o.sr190.n_dagger.printed.map((p, k) => {
                  const rho = rhos[k];
                  const dec = o.sr190.n_dagger.decimals[k];
                  const ne = rho === undefined ? null : effectiveN(n, rho);
                  const ok = ne !== null && printsAs(ne, p, dec);
                  return (
                    <tr key={`n-dagger-${k}`} data-row={`n_dagger|${k}`} data-agrees={ok ? 'yes' : 'no'}>
                      <td className="ct-text">{`${pick(N_DAGGER, lang)}, ${rho === undefined ? '-' : pct0(lang, rho)}`}</td>
                      <td>{formatNumber(p, lang, { decimals: dec })}</td>
                      <td>{ne === null ? '-' : formatNumber(ne, lang, { decimals: dec + 2 })}</td>
                      <td className="ct-text">{(ok ? AGREES : DIFFERS)[lang]}</td>
                    </tr>
                  );
                })}
                {atRail.map((r) => (
                  <tr key={`rail-${r.key}`} data-row={`rail|${r.key}`} className="ct-current">
                    <td className="ct-text">{`${pick(r.label, lang)}, ${pick({ en: 'rail', es: 'panel' }, lang)} ${rhoText(lang)}, ${lv(lang)}`}</td>
                    <td>-</td>
                    <td>{bpRange(lang, r.i.lower, r.i.upper, SR190_DECIMALS + 1)}</td>
                    <td className="ct-text">{`N† ${formatNumber(r.i.nEffective, lang, { digits: 4 })}`}</td>
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

/** Shared with the tests: what the printed bounds read as on the page. */
export const formatBpRange = bpRange;
