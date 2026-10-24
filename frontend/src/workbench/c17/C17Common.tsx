// C17's Findings, Variants and Context views, and the live read-outs of its rail (ADR-0017 rule 3: every section shows a
// value that moves with its controls). The Findings card and the fixture notice are the ones C06 and C07 use. The
// context states what the case rests on: a synthetic bank with a known truth, the BCBS 2008 targets labelled
// derived-only with their source, and the infinite-mean flag of a tail index of 1 or more.
import { BarChart, Callout, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable, compactMoney } from '../c06/format';
import { Pending } from '../Pending';
import { LiveReadout, useCard, type Bi } from '../c03/U6Shared';
import {
  AGGREGATION_TEXT, STATUS_TEXT, UNVERIFIED, capitalOf, cellLabel, cellOf, fitOf, outputsOf, rungName, scenarioOf, stabilityAt, text, whole,
  type C17Outputs, type C17Sel,
} from './selection';
import { es } from './localise';

const na = (lang: 'en' | 'es') => formatNumber(null, lang);
const NA_BI = (): Bi => ({ en: formatNumber(null, 'en'), es: formatNumber(null, 'es') });

/** A tail index in words: "Tail index 0.8" / "Índice de cola 0,8". */
export const tailLabel = (xi: number): Bi => ({ en: `Tail index ${formatNumber(xi, 'en', { digits: 3 })}`, es: `Índice de cola ${formatNumber(xi, 'es', { digits: 3 })}` });

export function C17FindingsView({ sel }: { sel: C17Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

/**
 * The tail indices side by side for the cell and the method in focus: how far the capital is from the truth and how much
 * it moves across histories as the tail index nears 1. Pick one to load it. An infinite mean is flagged, not hidden.
 */
export function C17VariantsTable({ variants, sel, onPick, current }: { variants: Array<{ id: string; title: BiText; v: VariantArtifact<C17Outputs> }>; sel: C17Sel | null; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const card = useCard(variants[0]?.v as unknown as VariantArtifact | undefined);
  const years = sel?.years ?? 10;
  const threshold = sel?.threshold ?? 20000;
  const rung = sel?.rung ?? 'lda-splice';
  const rows = variants.map(({ id, title, v }) => {
    const cell = cellOf(v.outputs, years, threshold);
    return { id, title, v, o: v.outputs, summary: capitalOf(cell, rung).summary };
  });
  const label = cellLabel(years, threshold);
  const name = rungName(rung);
  return (
    <PlotCard
      fill
      title={{ en: 'The tail indices', es: 'Los índices de cola' }}
      {...card}
      note={{
        en: `${name.en}, ${label.en}. The closer the tail index gets to 1, the more the capital of one history differs from the capital of the next. The bars give the spread of the capital over the true quantile; a tail index of 1 or more has an infinite mean. Pick a tail index to load it.`,
        es: `${name.es}, ${label.es}. Cuanto más se acerca el índice de cola a 1, más difiere el capital de una historia del de la siguiente. Las barras dan la dispersión del capital sobre el cuantil verdadero; un índice de cola de 1 o más tiene media infinita. Elija un índice de cola para cargarlo.`,
      }}
    >
      <ChartOverTable
        chart={
          <BarChart
            title={{ en: 'Spread of the capital over the truth by tail index', es: 'Dispersión del capital sobre la verdad por índice de cola' }}
            height="fill"
            orientation="vertical"
            data={rows.map((r) => ({ id: r.id, label: r.title, value: r.summary?.iqr_over_truth ?? null, tone: r.o.infinite_mean ? ('warn' as const) : ('accent' as const), highlight: r.id === current }))}
            axis={{ label: { en: 'Interquartile range over the true quantile', es: 'Rango intercuartil sobre el cuantil verdadero' }, format: { percent: true, decimals: 0 } }}
          />
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c17">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Tail index', es: 'Índice de cola' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Mean', es: 'Media' }, lang)}</th>
              <th>{pick({ en: 'True quantile (EUR)', es: 'Cuantil verdadero (EUR)' }, lang)}</th>
              <th>{pick({ en: 'Median capital (EUR)', es: 'Capital mediano (EUR)' }, lang)}</th>
              <th>{pick({ en: 'Median over the truth', es: 'Mediana sobre la verdad' }, lang)}</th>
              <th>{pick({ en: 'Spread over the truth', es: 'Dispersión sobre la verdad' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Histories below the truth', es: 'Historias bajo la verdad' }, lang)}</th>
              {/* how many of the histories give a capital at all: the median and spread are over these (R2b c18 M-2, V17-3) */}
              <th>{pick({ en: 'Histories with a capital', es: 'Historias con capital' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} data-variant={r.id} data-infinite-mean={String(r.o.infinite_mean)} className={r.id === current ? 'ct-current' : undefined}>
                <td className="ct-text">
                  <button type="button" className="ct-linkbutton" onClick={() => onPick(r.id)}>{pick(r.title, lang)}</button>
                </td>
                <td className="ct-text ct-wide-only">{r.o.infinite_mean ? pick({ en: 'infinite', es: 'infinita' }, lang) : pick({ en: 'finite', es: 'finita' }, lang)}</td>
                <td>{whole(r.o.truth.annual_loss_quantile.value_eur, lang)}</td>
                <td>{r.summary ? whole(r.summary.capital_eur.median, lang) : na(lang)}</td>
                <td>{r.summary ? formatNumber(r.summary.ratio_to_truth.median, lang, { digits: 3 }) : na(lang)}</td>
                <td>{r.summary ? formatNumber(r.summary.iqr_over_truth, lang, { percent: true, decimals: 2 }) : na(lang)}</td>
                <td className="ct-wide-only">{r.summary ? formatNumber(r.summary.share_underestimating, lang, { percent: true, decimals: 2 }) : na(lang)}</td>
                <td data-n-defined={r.summary?.n_defined}>{r.summary ? formatNumber(r.summary.n_defined, lang, { decimals: 0 }) : na(lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </ChartOverTable>
    </PlotCard>
  );
}

export function C17VariantsView({ sel, onPick }: { sel: C17Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const variants = (all.data as unknown as Array<VariantArtifact<C17Outputs>>)
    .filter((v) => v.outputs.kind === 'tail-index')
    .sort((a, b) => a.outputs.tail_index - b.outputs.tail_index)
    .map((v) => ({ id: v.variant_id, title: tailLabel(v.outputs.tail_index), v }));
  return (
    <ViewsRow>
      <C17VariantsTable variants={variants} sel={sel} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

/** The case, the generator and its truth, the derived-only calibration targets with their source, and the synthetic bank. */
export function C17ContextView({ sel }: { sel: C17Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const fit = fitOf(sel);
  const t = o.truth;
  const q = t.annual_loss_quantile;
  const cal = o.calibration;
  const tg = cal.targets;
  const bank = o.bank;
  const bi = bank.business_indicator;
  const eur = (x: number) => `${whole(x, lang)} EUR`;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard
        title={{ en: 'The case and its known truth', es: 'El caso y su verdad conocida' }}
        {...card}
        note={{ en: 'Every history is drawn by a generator whose annual loss distribution is known, so each method is judged against the truth.', es: 'Cada historia la simula un generador cuya distribución de pérdida anual se conoce, así que cada método se juzga contra la verdad.' }}
      >
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c17-truth" data-infinite-mean={String(o.infinite_mean)}>
          <dt>{pick({ en: 'Truth status of this variant', es: 'Estado de verdad de esta variante' }, lang)}</dt>
          <dd>{pick({ en: 'Synthetic, with a known truth', es: 'Sintético, con verdad conocida' }, lang)}</dd>
          <dt>{pick({ en: 'Shaped on', es: 'Con la forma de' }, lang)}</dt>
          <dd>{pick({ en: 'the BCBS 2008 Loss Data Collection Exercise', es: 'el Ejercicio de Recolección de Datos de Pérdida 2008 del BCBS' }, lang)}</dd>
          <dt>{pick({ en: 'Frequency', es: 'Frecuencia' }, lang)}</dt>
          <dd>{pick({ en: `Poisson, ${formatNumber(t.frequency.lambda_per_year, 'en', { digits: 4 })} losses per year of ${whole(t.frequency.counted_above_eur, 'en')} EUR or more`, es: `Poisson, ${formatNumber(t.frequency.lambda_per_year, 'es', { digits: 4 })} pérdidas por año de ${whole(t.frequency.counted_above_eur, 'es')} EUR o más` }, lang)}</dd>
          <dt>{pick({ en: 'Severity', es: 'Severidad' }, lang)}</dt>
          <dd>{pick({ en: `generalised Pareto from ${whole(t.severity.location_eur, 'en')} EUR, scale ${whole(t.severity.scale_eur, 'en')} EUR, tail index ${formatNumber(t.severity.tail_index, 'en', { digits: 3 })}`, es: `Pareto generalizada desde ${whole(t.severity.location_eur, 'es')} EUR, escala ${whole(t.severity.scale_eur, 'es')} EUR, índice de cola ${formatNumber(t.severity.tail_index, 'es', { digits: 3 })}` }, lang)}</dd>
          <dt>{pick({ en: 'True 99.9% quantile of the annual loss', es: 'Cuantil verdadero 99,9% de la pérdida anual' }, lang)}</dt>
          <dd data-quantile={q.value_eur}>{pick({ en: `${eur(q.value_eur)} (${text(AGGREGATION_TEXT, q.method).en}, checked by ${whole(q.mc_check.n_years, 'en')} simulated years)`, es: `${eur(q.value_eur)} (${text(AGGREGATION_TEXT, q.method).es}, verificado con ${whole(q.mc_check.n_years, 'es')} años simulados)` }, lang)}</dd>
          <dt>{pick({ en: 'True annual mean', es: 'Media anual verdadera' }, lang)}</dt>
          <dd data-mean={t.annual_loss_mean.value_eur === null ? 'not-available' : 'available'}>
            {t.annual_loss_mean.value_eur === null ? `${na(lang)} (${es(t.annual_loss_mean.reason, lang)})` : eur(t.annual_loss_mean.value_eur)}
          </dd>
          <dt>{pick({ en: 'Notice of the document', es: 'Aviso del documento' }, lang)}</dt>
          <dd>{pick(t.notice, lang)}</dd>
          {fit ? (
            <>
              <dt>{pick({ en: 'Generator', es: 'Generador' }, lang)}</dt>
              <dd>{pick(fit.generator.notice, lang)}</dd>
            </>
          ) : null}
        </dl>
      </PlotCard>
      <PlotCard
        title={{ en: 'Calibration targets, derived only', es: 'Objetivos de calibración, solo derivados' }}
        {...card}
        note={{ en: 'The generator\'s scale is fitted to four published percentiles. They are derived statistics of a regulator\'s survey, labelled as such, and no table of the survey is reproduced.', es: 'La escala del generador se ajusta a cuatro percentiles publicados. Son estadísticas derivadas de una encuesta de un regulador, rotuladas como tales, y no se reproduce ninguna tabla de la encuesta.' }}
      >
        <dl className="ct-defs" data-table="c17-calibration" data-label={tg.label}>
          <dt>{pick({ en: 'Licence class', es: 'Clase de licencia' }, lang)}</dt>
          <dd data-label={tg.label}>{pick({ en: 'Derived only', es: 'Solo derivado' }, lang)}</dd>
          <dt>{pick({ en: 'Source', es: 'Fuente' }, lang)}</dt>
          <dd>
            <a href={tg.source.url} target="_blank" rel="noreferrer">{es(tg.source.title, lang)}</a>
            {` (${tg.source.date}, ${pick({ en: 'table', es: 'tabla' }, lang)} ${tg.source.table})`}
          </dd>
          <dt>{pick({ en: 'Losses counted from', es: 'Pérdidas contadas desde' }, lang)}</dt>
          <dd>{eur(tg.threshold_eur)}</dd>
          <dt>{pick({ en: 'Frequency of the median bank', es: 'Frecuencia del banco mediano' }, lang)}</dt>
          <dd>{pick({ en: `${formatNumber(tg.frequency.per_eur_bn_assets, 'en', { digits: 3 })} losses per year per EUR billion of assets (interquartile range ${formatNumber(tg.frequency.iqr_low, 'en', { digits: 3 })} to ${formatNumber(tg.frequency.iqr_high, 'en', { digits: 3 })})`, es: `${formatNumber(tg.frequency.per_eur_bn_assets, 'es', { digits: 3 })} pérdidas por año por cada mil millones de EUR de activos (rango intercuartil ${formatNumber(tg.frequency.iqr_low, 'es', { digits: 3 })} a ${formatNumber(tg.frequency.iqr_high, 'es', { digits: 3 })})` }, lang)}</dd>
          <dt>{pick({ en: 'Fit of the generator', es: 'Ajuste del generador' }, lang)}</dt>
          <dd>{pick({ en: `tail index ${formatNumber(cal.fit.tail_index, 'en', { digits: 3 })}, scale ${whole(cal.fit.scale_eur, 'en')} EUR; largest log error ${formatNumber(cal.fit.max_abs_log_error, 'en', { digits: 3 })}`, es: `índice de cola ${formatNumber(cal.fit.tail_index, 'es', { digits: 3 })}, escala ${whole(cal.fit.scale_eur, 'es')} EUR; mayor error logarítmico ${formatNumber(cal.fit.max_abs_log_error, 'es', { digits: 3 })}` }, lang)}</dd>
        </dl>
        <table className="caos-table ct-wrap-head" data-table="c17-targets">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Percentile of the severity', es: 'Percentil de la severidad' }, lang)}</th>
              <th>{pick({ en: 'Target (EUR)', es: 'Objetivo (EUR)' }, lang)}</th>
              <th>{pick({ en: 'Generator (EUR)', es: 'Generador (EUR)' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {tg.severity_percentiles.map((p, i) => (
              <tr key={p.p} data-percentile={p.p}>
                <td className="ct-text">{formatNumber(p.p, lang, { percent: true, decimals: 0 })}</td>
                <td>{whole(p.loss_eur, lang)}</td>
                <td>{cal.fit.fitted_quantiles_eur[i] === undefined ? na(lang) : whole(cal.fit.fitted_quantiles_eur[i], lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="ct-note">{pick(tg.caveat, lang)}</p>
      </PlotCard>
      <PlotCard title={{ en: 'The synthetic bank', es: 'El banco sintético' }} {...card}>
        <div data-synthetic={String(bank.synthetic)}>
          <Callout variant="honest" title={pick({ en: 'Synthetic, not a real bank', es: 'Sintético, no un banco real' }, lang)}>
            {pick(bank.notice, lang)}
          </Callout>
          <dl className="ct-defs" data-table="c17-bank">
            <dt>{pick({ en: 'Bank', es: 'Banco' }, lang)}</dt>
            <dd>{pick(bank.label, lang)}</dd>
            <dt>{pick({ en: 'Business indicator', es: 'Indicador de negocio' }, lang)}</dt>
            <dd>{`${eur(bi.bi_eur)} (${eur(bi.ildc_eur)} + ${eur(bi.sc_eur)} + ${eur(bi.fc_eur)})`}</dd>
            <dt>{pick({ en: 'Component and bucket', es: 'Componente y tramo' }, lang)}</dt>
            <dd>{pick({ en: `${eur(bank.bic_eur)}, bucket ${bank.bucket}`, es: `${eur(bank.bic_eur)}, tramo ${bank.bucket}` }, lang)}</dd>
          </dl>
        </div>
      </PlotCard>
    </div>
  );
}

/** The live read-out of the Years section: the histories of this length in the cell chosen. */
export function YearsReadout({ sel }: { sel: C17Sel | null }) {
  const o = outputsOf(sel);
  const cell = o && sel ? cellOf(o, sel.years, sel.threshold) : null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'Histories of this length', es: 'Historias de este largo' }}
      items={[
        { label: { en: 'Histories', es: 'Historias' }, value: cell?.replications.n_replications ?? null, unitless: true, format: { decimals: 0 }, hint: { en: 'Independent simulated loss histories in the cell, each with its own seed.', es: 'Historias de pérdidas simuladas e independientes en la celda, cada una con su semilla.' } },
        { label: { en: 'Failed fits', es: 'Ajustes fallidos' }, value: cell?.replications.n_failed ?? null, unitless: true, format: { decimals: 0 }, hint: { en: 'Histories whose fit did not converge: counted, never dropped silently.', es: 'Historias cuyo ajuste no convergió: se cuentan, no se descartan en silencio.' } },
        { label: { en: 'Losses per history', es: 'Pérdidas por historia' }, value: cell?.replications.n_losses_median ?? null, unitless: true, format: { decimals: 0 }, hint: { en: 'Median number of recorded losses in a history.', es: 'Número mediano de pérdidas registradas en una historia.' } },
      ]}
    />
  );
}

/** The live read-out of the Threshold section: the tail index fitted at the collection threshold of the cell. */
export function ThresholdReadout({ sel }: { sel: C17Sel | null }) {
  const o = outputsOf(sel);
  const cell = o && sel ? cellOf(o, sel.years, sel.threshold) : null;
  const row = cell ? stabilityAt(cell) : null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The tail at this threshold', es: 'La cola en este umbral' }}
      items={[
        { label: { en: 'Tail index, median', es: 'Índice de cola, mediana' }, value: row?.tail_index.median ?? null, unitless: true, format: { digits: 3 }, hint: { en: 'The generalised Pareto tail index fitted above the collection threshold, median over the histories.', es: 'El índice de cola de Pareto generalizada ajustado sobre el umbral de recolección, mediana sobre las historias.' } },
        { label: { en: 'Fits with index of 1 or more', es: 'Ajustes con índice de 1 o más' }, value: row?.share_at_least_one ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'Share of the fits whose tail index implies an infinite mean.', es: 'Proporción de los ajustes cuyo índice de cola implica una media infinita.' } },
        { label: { en: 'Exceedances, median', es: 'Excedencias, mediana' }, value: row?.n_exceedances_median ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'Losses above the threshold that the fit rests on.', es: 'Pérdidas sobre el umbral en que se apoya el ajuste.' } },
      ]}
    />
  );
}

/** The live read-out of the Method section: what the method chosen gives in the cell, against the truth. */
export function RungReadout({ sel }: { sel: C17Sel | null }) {
  const o = outputsOf(sel);
  const cell = o && sel ? cellOf(o, sel.years, sel.threshold) : null;
  const { summary } = cell && sel ? capitalOf(cell, sel.rung) : { summary: null };
  const status = summary?.status ?? (sel?.rung === 'sla-mean-corrected' ? UNVERIFIED : null);
  const amount = compactMoney(summary?.capital_eur.median ?? null, 'EUR');
  const hintNa: BiText = { en: 'This method was not evaluated for this cell.', es: 'Este método no se evaluó para esta celda.' };
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'This method in this cell', es: 'Este método en esta celda' }}
      items={[
        { label: { en: 'Aggregation', es: 'Agregación' }, text: summary ? text(AGGREGATION_TEXT, summary.aggregation) : NA_BI(), hint: { en: 'How the annual loss distribution of the method is computed.', es: 'Cómo se calcula la distribución de pérdida anual del método.' } },
        { label: { en: 'Status', es: 'Estado' }, text: status ? text(STATUS_TEXT, status) : NA_BI(), hint: { en: 'UNVERIFIED marks a form not yet checked against its primary text.', es: 'SIN VERIFICAR marca una forma que aún no se verificó contra su texto primario.' } },
        { label: { en: 'Histories defined', es: 'Historias definidas' }, value: summary?.n_defined ?? null, unitless: true, format: { decimals: 0 }, hint: summary ? { en: 'The histories the median rests on: the method is undefined for the others (a failed fit, or a threshold without enough losses).', es: 'Las historias en que se apoya la mediana: el método no está definido para las demás (un ajuste fallido, o un umbral sin pérdidas suficientes).' } : hintNa },
        { label: { en: 'Median capital', es: 'Capital mediano' }, ...amount, hint: summary ? { en: 'The 99.9 percent capital, median over the histories.', es: 'El capital al 99,9 por ciento, mediana sobre las historias.' } : hintNa },
        { label: { en: 'Median over the truth', es: 'Mediana sobre la verdad' }, value: summary?.ratio_to_truth.median ?? null, unitless: true, format: { digits: 3 }, hint: { en: 'The capital divided by the true quantile: 1 is exact.', es: 'El capital dividido por el cuantil verdadero: 1 es exacto.' } },
        { label: { en: 'Histories below the truth', es: 'Historias bajo la verdad' }, value: summary?.share_underestimating ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'Share of the histories whose capital is under the true quantile.', es: 'Proporción de las historias cuyo capital está bajo el cuantil verdadero.' } },
      ]}
    />
  );
}

/** The live read-out of the Scenario section: the point chosen and its influence on the capital. */
export function ScenarioReadout({ sel }: { sel: C17Sel | null }) {
  const o = outputsOf(sel);
  const s = o && sel ? scenarioOf(o, sel.scenario) : null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'This scenario point', es: 'Este punto de escenario' }}
      items={[
        { label: { en: 'Loss', es: 'Pérdida' }, ...compactMoney(s?.loss_eur ?? null, 'EUR'), hint: { en: 'The loss the expert gives for the scenario.', es: 'La pérdida que el experto da para el escenario.' } },
        { label: { en: 'Exceedances per year', es: 'Excedencias por año' }, value: s?.exceedance_frequency_per_year ?? null, unitless: true, format: { digits: 3 }, hint: { en: 'How often the expert expects a loss of at least that size.', es: 'Cada cuánto espera el experto una pérdida de al menos ese tamaño.' } },
        { label: { en: 'Capital without it', es: 'Capital sin él' }, ...compactMoney(s?.capital_without_eur ?? null, 'EUR'), hint: { en: 'The 99.9 percent capital if this point were left out.', es: 'El capital al 99,9 por ciento si se omitiera este punto.' } },
        { label: { en: 'Influence', es: 'Influencia' }, value: s?.influence ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'The capital with all the points, minus the capital without this one, over the capital with all of them.', es: 'El capital con todos los puntos, menos el capital sin este, sobre el capital con todos.' } },
      ]}
    />
  );
}

