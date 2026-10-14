// C10's Capital group: the loss distribution of the illustrative portfolio by rung, with the expected loss, the VaR and
// the expected shortfall marked and their Monte Carlo error beside them and the large homogeneous portfolio drawn over
// it as the infinitely granular approximation; the rungs side by side; the Euler contributions of the groups; and the
// granularity adjustment against the number of names. The portfolio is illustrative and says so on every view; a rung
// that did not run says why and draws no number.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, alignTo, unionX } from '../c06/format';
import { Pending } from '../Pending';
import { useCard, type Bi } from '../c03/U6Shared';
import { C10TestsTable, IllustrativeNotice } from './C10Common';
import { barMin, fullMoney, moneyAxis } from './format';
import {
  ESTIMATOR_KIND_TEXT, EULER_METHOD_TEXT, VAR_METHOD_TEXT, eulerLevelOf, eulerOf, groupLabel, levelBi, measureOf, outputsOf, rungOf, text,
  type C10Rung, type C10Sel,
} from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

export interface LossMark {
  kind: 'el' | 'var' | 'es';
  x: number;
  label: Bi;
}

/** The markers of a rung at a level: EL, VaR and ES in money, the VaR and ES with their Monte Carlo error when sampled. */
export function lossMarks(rung: C10Rung | undefined, level: number, currency: string): LossMark[] {
  const m = measureOf(rung, level);
  if (!rung || !rung.evaluated || !m) return [];
  const both = (build: (lang: 'en' | 'es') => string): Bi => ({ en: build('en'), es: build('es') });
  const lv = levelBi(level);
  // one unit for the three markers, chosen by the largest, so 0.14 m and 0.87 m and 1.04 m read side by side
  const { div, unit } = moneyAxis(Math.max(m.el, m.var, m.es ?? 0), currency);
  const amount = (v: number, lang: 'en' | 'es') => `${formatNumber(v / div, lang, { digits: 4 })} ${unit[lang]}`;
  const err = (lang: 'en' | 'es', se: number | null) => (se === null ? '' : ` ± ${formatNumber(se / div, lang, { digits: 3 })}`);
  const marks: LossMark[] = [
    { kind: 'el', x: m.el, label: both((l) => `${l === 'en' ? 'EL' : 'PE'} ${amount(m.el, l)}`) },
    { kind: 'var', x: m.var, label: both((l) => `VaR ${lv[l]} ${amount(m.var, l)}${err(l, m.var_se)}`) },
  ];
  if (m.es !== null) marks.push({ kind: 'es', x: m.es, label: both((l) => `ES ${lv[l]} ${amount(m.es as number, l)}${err(l, m.es_se)}`) });
  return marks;
}

function NoRung({ sel, reason }: { sel: C10Sel; reason: string }) {
  const lang = useShellLang();
  const card = useCard(sel.data.variant);
  return (
    <ViewsRow>
      <PlotCard fill title={{ en: 'The loss distribution of this rung', es: 'La distribución de pérdidas de este escalón' }} {...card}>
        <p className="caos-pending" data-state="unavailable">
          {pick({ en: 'This rung did not run, so it draws no distribution and shows no number. Why: ', es: 'Este escalón no corrió, así que no dibuja distribución ni muestra número. Motivo: ' }, lang)}
          {reason}
        </p>
      </PlotCard>
    </ViewsRow>
  );
}

/** The loss density of the rung in focus with EL, VaR and ES marked, and the LHP density over it. */
export function LossView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const rung = rungOf(o, sel.rung);
  if (!rung || !rung.evaluated || !rung.distribution) return <NoRung sel={sel} reason={rung?.reason ?? ''} />;
  const ccy = o.currency;
  const lhp = rung.id === 'c1-lhp' ? undefined : rungOf(o, 'c1-lhp');
  const overlay = lhp?.evaluated && lhp.distribution ? lhp.distribution : null;
  const d = rung.distribution;
  const grid = unionX(d.loss, overlay?.loss ?? []);
  const { div, unit } = moneyAxis(grid[grid.length - 1] ?? 0, ccy);
  const own = alignTo(d.loss, d.density, grid).map((v) => (v === null ? null : v * div));
  const lhpLine = overlay ? alignTo(overlay.loss, overlay.density, grid).map((v) => (v === null ? null : v * div)) : null;
  const marks = lossMarks(rung, sel.level, ccy);
  const m = measureOf(rung, sel.level);
  const lhpM = lhp ? measureOf(lhp, sel.level) : null;
  const lv = levelBi(sel.level);
  const sampled = rung.estimator === 'monte-carlo';
  const row = (key: string, label: BiText, v: number | null, se: number | null | undefined) => (
    <tr key={key} data-marker={key}>
      <td className="ct-text">{pick(label, lang)}</td>
      <td>{v === null ? formatNumber(null, lang) : fullMoney(v, lang)}</td>
      <td>{se === null || se === undefined ? (sampled ? formatNumber(null, lang) : pick({ en: 'none, analytic', es: 'ninguno, analítico' }, lang)) : fullMoney(se, lang)}</td>
    </tr>
  );
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The loss distribution of the portfolio', es: 'La distribución de pérdidas de la cartera' }}
        {...card}
        note={{
          en: `${rung.label.en}: the density of the one-year portfolio loss in ${unit.en}, with the expected loss, the VaR and the expected shortfall at ${lv.en} marked and, for a sampled rung, their Monte Carlo standard error. The dashed curve is the large homogeneous portfolio of the first rung: the infinitely granular approximation, which has no name concentration, never the true loss distribution of this portfolio.`,
          es: `${rung.label.es}: la densidad de la pérdida de la cartera en un año en ${unit.es}, con la pérdida esperada, el VaR y el déficit esperado al ${lv.es} marcados y, para un escalón muestreado, su error estándar de Monte Carlo. La curva punteada es la cartera homogénea grande del primer escalón: la aproximación infinitamente granular, que no tiene concentración por nombre, nunca la distribución de pérdidas verdadera de esta cartera.`,
        }}
      >
        <IllustrativeNotice notice={o.portfolio.notice} />
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: grid.map((v) => v / div), label: { en: `Portfolio loss (${unit.en})`, es: `Pérdida de la cartera (${unit.es})` }, format: { decimals: div > 1 ? 2 : 0 } }}
              y={{ label: { en: `Density per ${unit.en}`, es: `Densidad por ${unit.es}` }, format: { decimals: 1 } }}
              series={[
                { label: { en: rung.label.en, es: rung.label.es }, values: own, color: '--color-accent', width: 2.4 },
                ...(lhpLine ? [{ label: { en: 'LHP: the infinitely granular approximation', es: 'LHP: la aproximación infinitamente granular' }, values: lhpLine, color: '--color-magenta' as const, width: 1.8, dash: [6, 4] }] : []),
              ]}
              marks={marks.map((k) => ({ x: k.x / div, label: k.label }))}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c10-measures" data-rung={rung.id} data-overlay={overlay ? 'lhp' : 'none'}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: `Measure at ${lv.en}, ${ccy}`, es: `Medida al ${lv.es}, ${ccy}` }, lang)}</th>
                <th>{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
                <th>{pick({ en: 'Monte Carlo error', es: 'Error de Monte Carlo' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {row('el', { en: 'Expected loss', es: 'Pérdida esperada' }, m?.el ?? null, null)}
              {row('var', { en: 'VaR', es: 'VaR' }, m?.var ?? null, m?.var_se)}
              {m && m.es === null ? (
                <tr data-marker="es" data-na="true">
                  <td className="ct-text">{pick({ en: 'Expected shortfall', es: 'Déficit esperado' }, lang)}</td>
                  <td colSpan={2}>{`${formatNumber(null, lang)} (${m.es_reason ?? ''})`}</td>
                </tr>
              ) : (
                row('es', { en: 'Expected shortfall', es: 'Déficit esperado' }, m?.es ?? null, m?.es_se)
              )}
              {row('ec', { en: 'Economic capital: VaR less expected loss', es: 'Capital económico: VaR menos pérdida esperada' }, m?.ec ?? null, null)}
              {overlay ? row('lhp-var', { en: 'VaR of the LHP, infinitely granular', es: 'VaR de la LHP, infinitamente granular' }, lhpM?.var ?? null, null) : null}
            </tbody>
          </table>
          <p className="ct-note" data-simulation={sampled ? 'sampled' : 'analytic'}>
            {rung.simulation
              ? pick(
                  {
                    en: `${count(rung.simulation.n_scenarios, 'en')} scenarios, seed ${rung.simulation.seed}, chunks of ${count(rung.simulation.chunk_size, 'en')}.`,
                    es: `${count(rung.simulation.n_scenarios, 'es')} escenarios, semilla ${rung.simulation.seed}, bloques de ${count(rung.simulation.chunk_size, 'es')}.`,
                  },
                  lang,
                )
              : pick({ en: 'An analytic rung: no scenarios, no sampling error.', es: 'Un escalón analítico: sin escenarios y sin error de muestreo.' }, lang)}
          </p>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The rungs of the ladder side by side at the level in focus: VaR as a bar, every measure and its error in the table. */
export function RungsView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const ccy = o.currency;
  const lv = levelBi(sel.level);
  const vars = o.rungs.map((r) => measureOf(r, sel.level)?.var ?? 0);
  const { div, unit } = moneyAxis(Math.max(0, ...vars), ccy);
  const data = o.rungs.map((r) => {
    const m = measureOf(r, sel.level);
    return { id: r.id, label: { en: r.label.en, es: r.label.es } as BiText, value: m ? m.var / div : null, tone: 'accent' as const, highlight: r.id === sel.rung, hint: r.evaluated ? undefined : { en: r.reason ?? '', es: r.reason ?? '' } };
  });
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The rungs of the ladder', es: 'Los escalones de la escalera' }}
        {...card}
        note={{
          en: `The VaR at ${lv.en} of the same illustrative portfolio under each model of the ladder, in ${unit.en}. The expected loss is the same in all of them; what changes is the tail: the copulas add dependence, CreditRisk+ a Gamma factor, the granularity adjustment the name concentration that the infinitely granular portfolio leaves out. A rung that did not run says why and has no bar.`,
          es: `El VaR al ${lv.es} de la misma cartera ilustrativa con cada modelo de la escalera, en ${unit.es}. La pérdida esperada es la misma en todos; lo que cambia es la cola: las cópulas agregan dependencia, CreditRisk+ un factor Gamma, el ajuste de granularidad la concentración por nombre que la cartera infinitamente granular omite. Un escalón que no corrió dice por qué y no tiene barra.`,
        }}
      >
        <IllustrativeNotice notice={o.portfolio.notice} />
        <ChartOverTable
          chartMin={barMin(data.length)}
          chart={<BarChart title={{ en: `VaR at ${lv.en} by rung`, es: `VaR al ${lv.es} por escalón` }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: `VaR (${unit.en})`, es: `VaR (${unit.es})` }, format: { decimals: div > 1 ? 2 : 0 } }} />}
        >
          <table className="caos-table ct-wrap-head" data-table="c10-rungs">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Rung', es: 'Escalón' }, lang)}</th>
                <th>{pick({ en: `EL, ${ccy}`, es: `PE, ${ccy}` }, lang)}</th>
                <th>{pick({ en: `VaR, ${ccy}`, es: `VaR, ${ccy}` }, lang)}</th>
                <th>{pick({ en: `ES, ${ccy}`, es: `ES, ${ccy}` }, lang)}</th>
                <th>{pick({ en: 'Error of the VaR', es: 'Error del VaR' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Error of the ES', es: 'Error del ES' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Scenarios and diagnostics', es: 'Escenarios y diagnósticos' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.rungs.map((r) => {
                const m = measureOf(r, sel.level);
                const na = formatNumber(null, lang);
                const none = pick({ en: 'none', es: 'ninguno' }, lang);
                return (
                  <tr key={r.id} data-rung={r.id} data-evaluated={String(r.evaluated)} className={r.id === sel.rung ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(r.label, lang)}</td>
                    {r.evaluated && m ? (
                      <>
                        <td>{fullMoney(m.el, lang)}</td>
                        <td>{fullMoney(m.var, lang)}</td>
                        <td data-na={m.es === null ? 'true' : undefined}>{m.es === null ? na : fullMoney(m.es, lang)}</td>
                        <td>{m.var_se === null ? none : fullMoney(m.var_se, lang)}</td>
                        <td className="ct-wide-only">{m.es_se === null ? none : fullMoney(m.es_se, lang)}</td>
                        <td className="ct-text ct-wide-only">
                          {[pick(text(ESTIMATOR_KIND_TEXT, r.estimator), lang), r.simulation ? `${count(r.simulation.n_scenarios, lang)} ${pick({ en: 'scenarios', es: 'escenarios' }, lang)}` : null, ...r.diagnostics.map((x) => `${x.name} ${formatNumber(x.value, lang, { digits: 4 })} ${x.unit}`)].filter(Boolean).join('; ')}
                        </td>
                      </>
                    ) : (
                      <>
                        <td colSpan={4} className="ct-text" data-na="true">{na}</td>
                        <td className="ct-wide-only" />
                        <td className="ct-wide-only" />
                      </>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
          {o.rungs
            .filter((r) => r.evaluated && measureOf(r, sel.level)?.es === null)
            .map((r) => (
              <p key={`es-${r.id}`} className="ct-note" data-state="unavailable" data-es-reason={r.id}>
                <strong>{pick(r.label, lang)}</strong>
                {`: ${pick({ en: 'no expected shortfall. Why: ', es: 'sin déficit esperado. Motivo: ' }, lang)}${measureOf(r, sel.level)?.es_reason ?? ''}`}
              </p>
            ))}
          {o.rungs
            .filter((r) => !r.evaluated)
            .map((r) => (
              <p key={r.id} className="ct-note" data-state="unavailable" data-rung-reason={r.id}>
                <strong>{pick(r.label, lang)}</strong>
                {`: ${pick({ en: 'did not run, so it has no number. Why: ', es: 'no corrió, así que no tiene número. Motivo: ' }, lang)}${r.reason ?? ''}`}
              </p>
            ))}
          <C10TestsTable variant={sel.data.variant} only={(t) => t.test_id === 'portfolio.mc_convergence' || t.test_id === 'portfolio.crp_recursion_vs_mc'} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The Euler contributions of the groups to the VaR and the ES at the level, with the asymptotic anchor. */
export function ContributionsView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const rung = rungOf(o, sel.rung);
  const own = eulerOf(o, rung);
  const block = own ?? o.euler[0] ?? null;
  const lvl = eulerLevelOf(block, sel.level);
  if (!block || !lvl) {
    return (
      <ViewsRow>
        <PlotCard fill title={{ en: 'The Euler contributions', es: 'Las contribuciones de Euler' }} {...card}>
          <p className="caos-pending" data-state="unavailable">{pick({ en: 'This document carries no Euler contributions at this level.', es: 'Este documento no trae contribuciones de Euler en este nivel.' }, lang)}</p>
        </PlotCard>
      </ViewsRow>
    );
  }
  const lv = levelBi(sel.level);
  const ccy = block.currency;
  const names = (id: string) => groupLabel(o.portfolio.groups, id);
  const anchorRow = (id: string) => lvl.anchor?.rows.find((r) => r.group_id === id)?.rc_var ?? null;
  const data = lvl.rows.flatMap((r) => [
    { id: `var-${r.group_id}`, label: { en: `${names(r.group_id).en}: VaR`, es: `${names(r.group_id).es}: VaR` } as BiText, value: r.share_var, tone: 'accent' as const, highlight: r.group_id === sel.group },
    { id: `es-${r.group_id}`, label: { en: `${names(r.group_id).en}: ES`, es: `${names(r.group_id).es}: ES` } as BiText, value: r.share_es, tone: 'neutral' as const, highlight: r.group_id === sel.group },
  ]);
  const method = text(EULER_METHOD_TEXT, block.rung_method);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Who carries the tail', es: 'Quién carga la cola' }}
        {...card}
        note={{
          en: `The Euler contribution of each group of the illustrative portfolio to the VaR and to the expected shortfall at ${lv.en}, from the ${method.en} rung: the expected loss of the group given the portfolio is at the VaR, or beyond it. They add up to the total. A group's share of the tail can be far from its share of the exposure.`,
          es: `La contribución de Euler de cada grupo de la cartera ilustrativa al VaR y al déficit esperado al ${lv.es}, del escalón ${method.es}: la pérdida esperada del grupo dado que la cartera está en el VaR, o más allá. Suman el total. La parte de un grupo en la cola puede estar lejos de su parte en la exposición.`,
        }}
      >
        <IllustrativeNotice notice={o.portfolio.notice} />
        {own ? null : (
          <p className="ct-note" data-state="fallback">
            {pick({ en: 'The rung in focus carries no Euler contributions (only the sampled rungs do); this view shows the first rung that does.', es: 'El escalón en foco no trae contribuciones de Euler (solo los escalones muestreados); esta vista muestra el primero que las trae.' }, lang)}
          </p>
        )}
        <ChartOverTable
          chartMin={barMin(data.length)}
          chart={<BarChart title={{ en: `Share of the VaR and of the ES at ${lv.en}`, es: `Parte del VaR y del ES al ${lv.es}` }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Share of the total', es: 'Parte del total' }, format: { percent: true, decimals: 0 } }} />}
        >
          <table className="caos-table ct-wrap-head" data-table="c10-euler" data-euler={block.rung_method}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Group', es: 'Grupo' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `Exposure, ${ccy}`, es: `Exposición, ${ccy}` }, lang)}</th>
                <th>{pick({ en: `VaR, ${ccy}`, es: `VaR, ${ccy}` }, lang)}</th>
                <th>{pick({ en: 'Share', es: 'Parte' }, lang)}</th>
                <th>{pick({ en: `ES, ${ccy}`, es: `ES, ${ccy}` }, lang)}</th>
                <th>{pick({ en: 'Share', es: 'Parte' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `Infinitely granular VaR, ${ccy}`, es: `VaR infinitamente granular, ${ccy}` }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {lvl.rows.map((r) => (
                <tr key={r.group_id} data-group={r.group_id} className={r.group_id === sel.group ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(names(r.group_id), lang)}</td>
                  <td className="ct-wide-only">{fullMoney(r.ead, lang)}</td>
                  <td>{fullMoney(r.rc_var, lang)}</td>
                  <td>{formatNumber(r.share_var, lang, { percent: true, decimals: 2 })}</td>
                  <td>{fullMoney(r.rc_es, lang)}</td>
                  <td>{formatNumber(r.share_es, lang, { percent: true, decimals: 2 })}</td>
                  <td className="ct-wide-only" data-na={anchorRow(r.group_id) === null ? 'true' : undefined}>{anchorRow(r.group_id) === null ? formatNumber(null, lang) : fullMoney(anchorRow(r.group_id), lang)}</td>
                </tr>
              ))}
              <tr data-row="total">
                <td className="ct-text">{pick({ en: 'Total of the portfolio', es: 'Total de la cartera' }, lang)}</td>
                <td className="ct-wide-only" />
                <td>{fullMoney(lvl.var_total, lang)}</td>
                <td />
                <td>{fullMoney(lvl.es_total, lang)}</td>
                <td />
                <td className="ct-wide-only" data-na={lvl.anchor ? undefined : 'true'}>{lvl.anchor ? fullMoney(lvl.anchor.asrf_var, lang) : formatNumber(null, lang)}</td>
              </tr>
            </tbody>
          </table>
          <p className="ct-note" data-euler-methods={`${lvl.var_method}|${lvl.es_method}`}>
            {pick(
              {
                en: `VaR contributions by ${text(VAR_METHOD_TEXT, lvl.var_method).en}, ES contributions from the tail sample; they add up to the totals within ${formatNumber(lvl.var_sum_tolerance, 'en', { percent: true, decimals: 2 })} for the VaR and ${formatNumber(lvl.es_sum_tolerance, 'en', { percent: true, decimals: 4 })} for the ES.`,
                es: `Contribuciones al VaR por ${text(VAR_METHOD_TEXT, lvl.var_method).es}, contribuciones al ES de la muestra de la cola; suman los totales dentro de ${formatNumber(lvl.var_sum_tolerance, 'es', { percent: true, decimals: 2 })} para el VaR y ${formatNumber(lvl.es_sum_tolerance, 'es', { percent: true, decimals: 4 })} para el ES.`,
              },
              lang,
            )}
          </p>
          {lvl.anchor ? (
            <p className="ct-note" data-anchor="asrf-asymptotic">
              {pick(
                {
                  en: 'The last column is the asymptotic one-factor contribution (Gordy 2003; the first term of Emmer and Tasche 2005): the infinitely granular portfolio, so the sample VaR sits near it, not on it.',
                  es: 'La última columna es la contribución asintótica de un factor (Gordy 2003; el primer término de Emmer y Tasche 2005): la cartera infinitamente granular, así que el VaR de la muestra queda cerca de ella, no sobre ella.',
                },
                lang,
              )}
            </p>
          ) : (
            <p className="ct-note" data-state="unavailable">{`${pick({ en: 'No asymptotic anchor for this rung. Why: ', es: 'Sin ancla asintótica para este escalón. Motivo: ' }, lang)}${lvl.anchor_reason ?? ''}`}</p>
          )}
          <C10TestsTable variant={sel.data.variant} only={(t) => t.test_id === 'portfolio.euler_additivity'} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The points without a recursion check, grouped by the reason the document gives, in order of first appearance. */
function truthGaps(rows: Array<{ n_names: number; truth_ga: number | null; truth_reason: string | null }>): Array<[string, Array<{ n_names: number }>]> {
  const groups = new Map<string, Array<{ n_names: number }>>();
  for (const r of rows) if (r.truth_ga === null) groups.set(r.truth_reason ?? '', [...(groups.get(r.truth_reason ?? '') ?? []), r]);
  return [...groups];
}

/** The granularity adjustment: per level for the illustrative portfolio, and against the number of names. */
export function GranularityView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const gr = o.granularity;
  const rows = gr.by_n_names;
  const lv = levelBi(gr.by_n_names_level);
  const p = (v: number | null, d = 3) => formatNumber(v, lang, { percent: true, decimals: d });
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'What granularity adds to the capital', es: 'Qué agrega la granularidad al capital' }}
        {...card}
        note={{
          en: `The granularity adjustment of Gordy and Lutkebohmert is added to the VaR of the infinitely granular portfolio and is a share of the EAD. The curve is the adjustment of n identical names of the portfolio's mix at ${lv.en}: it falls as 1 over n, and the CreditRisk+ recursion of the same single-factor model is drawn beside it as the check. A point the recursion was not run for has no check and says why.`,
          es: `El ajuste de granularidad de Gordy y Lutkebohmert se suma al VaR de la cartera infinitamente granular y es una parte de la EAD. La curva es el ajuste de n nombres idénticos de la mezcla de la cartera al ${lv.es}: cae como 1 sobre n, y la recursión de CreditRisk+ del mismo modelo de un factor se dibuja al lado como verificación. Un punto para el que no se corrió la recursión no tiene verificación y dice por qué.`,
        }}
      >
        <IllustrativeNotice notice={o.portfolio.notice} />
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: rows.map((r) => r.n_names), label: { en: 'Number of names', es: 'Número de nombres' }, log: true, format: { decimals: 0 } }}
              y={{ label: { en: 'Adjustment, share of the EAD', es: 'Ajuste, parte de la EAD' }, format: { percent: true, decimals: 2 } }}
              series={[
                { label: { en: 'Granularity adjustment', es: 'Ajuste de granularidad' }, values: rows.map((r) => r.ga), color: '--color-accent', width: 2.4 },
                { label: { en: 'CreditRisk+ recursion', es: 'Recursión de CreditRisk+' }, values: rows.map((r) => r.truth_ga), color: '--color-magenta', mode: 'points', size: 9 },
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c10-ga-names">
            <thead>
              <tr>
                <th>{pick({ en: 'Names', es: 'Nombres' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Concentration index', es: 'Índice de concentración' }, lang)}</th>
                <th>{pick({ en: 'Adjustment', es: 'Ajuste' }, lang)}</th>
                <th>{pick({ en: 'CreditRisk+ recursion', es: 'Recursión de CreditRisk+' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.n_names} data-names={r.n_names}>
                  <td>{count(r.n_names, lang)}</td>
                  <td className="ct-wide-only">{formatNumber(r.hhi, lang, { digits: 3 })}</td>
                  <td>{p(r.ga, 4)}</td>
                  <td data-na={r.truth_ga === null ? 'true' : undefined} title={r.truth_ga === null ? (r.truth_reason ?? undefined) : undefined}>{r.truth_ga === null ? formatNumber(null, lang) : p(r.truth_ga, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c10-ga-levels">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Level', es: 'Nivel' }, lang)}</th>
                <th>{pick({ en: 'Gamma quantile', es: 'Cuantil Gamma' }, lang)}</th>
                <th>delta</th>
                <th>{pick({ en: 'Adjustment, share of the EAD', es: 'Ajuste, parte de la EAD' }, lang)}</th>
                <th>{pick({ en: `Adjustment, ${gr.currency}`, es: `Ajuste, ${gr.currency}` }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {gr.levels.map((l) => (
                <tr key={l.q} data-ga-level={l.q}>
                  <td className="ct-text">{pick(levelBi(l.q), lang)}</td>
                  <td>{formatNumber(l.alpha_q, lang, { digits: 4 })}</td>
                  <td>{formatNumber(l.delta, lang, { digits: 4 })}</td>
                  <td>{p(l.ga, 4)}</td>
                  <td>{fullMoney(l.ga_money, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {truthGaps(rows).map(([reason, group]) => (
            <p key={reason} className="ct-note" data-state="unavailable" data-names-reason={group.map((r) => r.n_names).join(',')}>
              {`${group.map((r) => count(r.n_names, lang)).join(', ')} ${pick({ en: 'names, no recursion check. Why: ', es: 'nombres, sin verificación por recursión. Motivo: ' }, lang)}${reason}`}
            </p>
          ))}
          <p className="ct-note" data-ga="parameters">
            {pick(
              {
                en: `Gamma factor with shape and rate ${formatNumber(gr.xi, 'en', { digits: 3 })}, loss-given-default dispersion ${formatNumber(gr.gamma, 'en', { digits: 3 })}, portfolio capital K* ${p(gr.k_star, 3)} from the IRB formula at the regulatory correlation. Reference value: delta ${formatNumber(gr.delta_reference, 'en', { digits: 3 })} at xi 0.25 and level ${levelBi(0.999).en} (${gr.delta_reference_source}).`,
                es: `Factor Gamma con forma y tasa ${formatNumber(gr.xi, 'es', { digits: 3 })}, dispersión de la pérdida dado el incumplimiento ${formatNumber(gr.gamma, 'es', { digits: 3 })}, capital de la cartera K* ${p(gr.k_star, 3)} con la fórmula IRB a la correlación regulatoria. Valor de referencia: delta ${formatNumber(gr.delta_reference, 'es', { digits: 3 })} con xi 0,25 y nivel ${levelBi(0.999).es} (${gr.delta_reference_source}).`,
              },
              lang,
            )}
          </p>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
