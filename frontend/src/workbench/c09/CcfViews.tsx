// C09's CCF group: the conversion-factor estimate of every reference-date design and treatment against the known CCF of
// the generator, and the distribution of the realised CCF with the values outside [0, 1] counted and flagged, never
// clipped. Each draws what the c09-outputs document carries.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { ChartOverTable } from '../c06/format';
import { Flagged, U6TestsTable, p2, useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { DESIGN_TEXT, ESTIMATOR_TEXT, TREATMENT_TEXT, modelLabel, outputsOf, text, type C09Sel } from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

/** The CCF estimated by each design and treatment, drawn beside the CCF the generator draws balances with. */
export function ByDesignView({ sel }: { sel: C09Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const c = o.ccf_by_design;
  const truth = o.generator.true_ccf;
  const yes = pick({ en: 'yes', es: 'sí' }, lang);
  const no = pick({ en: 'no', es: 'no' }, lang);
  // the rail's design only: its treatments under both estimators fit the card (all three designs were 24 bars in a box
  // that scrolled, and the two estimators of a treatment read as one label twice)
  const rows = c.rows.filter((r) => r.design === sel.design);
  const rowLabel = (treatment: string, estimator: string) => ({
    en: `${text(TREATMENT_TEXT, treatment).en}, ${text(ESTIMATOR_TEXT, estimator).en.toLowerCase()}`,
    es: `${text(TREATMENT_TEXT, treatment).es}, ${text(ESTIMATOR_TEXT, estimator).es.toLowerCase()}`,
  });
  const data = [
    { id: 'truth', label: { en: 'Known CCF', es: 'CCF conocido' }, value: truth.value, tone: 'neutral' as const },
    ...rows.map((r) => ({
      id: `${r.design}-${r.treatment}-${r.estimator}`,
      label: rowLabel(r.treatment, r.estimator),
      value: r.estimate.value,
      tone: r.estimate.flag !== 'in-range' ? ('bad' as const) : r.within_tolerance ? ('good' as const) : ('warn' as const),
    })),
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The CCF estimates against the known CCF', es: 'Las estimaciones de CCF contra el CCF conocido' }}
        {...card}
        note={{
          en: 'The generator draws every balance with one CCF, so the estimators can be judged against the truth. Green is an estimate within the tolerance of the truth, amber one outside it, red one outside 0 to 1, which is printed as it is and never clipped. The table gives the bias, the interval and the shares of defaults outside 0 to 1.',
          es: 'El generador simula cada saldo con un solo CCF, así que los estimadores se pueden juzgar contra la verdad. Verde es una estimación dentro de la tolerancia de la verdad, ámbar una fuera de ella, rojo una fuera de 0 a 1, que se imprime tal cual y nunca se recorta. La tabla da el sesgo, el intervalo y las proporciones de incumplimientos fuera de 0 a 1.',
        }}
      >
        <ChartOverTable
          chartMin={`${Math.min(16, data.length * 1.1 + 3)}rem`}
          chart={<BarChart title={{ en: `CCF by treatment and estimator, ${text(DESIGN_TEXT, sel.design).en.toLowerCase()}`, es: `CCF por tratamiento y estimador, ${text(DESIGN_TEXT, sel.design).es.toLowerCase()}` }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Conversion factor', es: 'Factor de conversión' }, format: { percent: true, digits: 2 } }} legend={[
            { tone: 'neutral' as const, label: { en: 'Known CCF', es: 'CCF conocido' } },
            { tone: 'good' as const, label: { en: 'Within the tolerance', es: 'Dentro de la tolerancia' } },
            { tone: 'warn' as const, label: { en: 'Outside the tolerance', es: 'Fuera de la tolerancia' } },
            { tone: 'bad' as const, label: { en: 'Outside 0 to 1', es: 'Fuera de 0 a 1' } },
          ].filter((l) => data.some((d) => d.tone === l.tone)) as Array<{ tone: 'neutral' | 'good' | 'warn' | 'bad'; label: { en: string; es: string } }>} />}
        >
          <p className="ct-note" data-truth={truth.value}>
            {pick(
              {
                en: `Known CCF of the generator: ${p2(truth.value, 'en')}; an estimate counts as recovered within ${p2(c.tolerance, 'en')}, and the light of each test below follows that tolerance on the bias, not its p-value.`,
                es: `CCF conocido del generador: ${p2(truth.value, 'es')}; una estimación cuenta como recuperada dentro de ${p2(c.tolerance, 'es')}, y la luz de cada prueba de abajo sigue esa tolerancia sobre el sesgo, no su valor p.`,
              },
              lang,
            )}
          </p>
          <p className="ct-note">{pick(o.generator.notice, lang)}</p>
          <table className="caos-table ct-wrap-head" data-table="ccf-by-design">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Treatment', es: 'Tratamiento' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Estimator', es: 'Estimador' }, lang)}</th>
                <th>{pick({ en: 'Estimate', es: 'Estimación' }, lang)}</th>
                <th>{pick({ en: 'Bias', es: 'Sesgo' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Interval of the bias', es: 'Intervalo del sesgo' }, lang)}</th>
                <th className="ct-wide-only">RMSE</th>
                <th>{pick({ en: 'Below 0', es: 'Bajo 0' }, lang)}</th>
                <th>{pick({ en: 'Above 1', es: 'Sobre 1' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Within tolerance', es: 'Dentro de la tolerancia' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.design}-${r.treatment}-${r.estimator}`} data-design={r.design} data-treatment={r.treatment} data-estimator={r.estimator} data-tolerance={String(r.within_tolerance)} className={r.treatment === sel.treatment ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(TREATMENT_TEXT, r.treatment), lang)}</td>
                  <td className="ct-text">{pick(text(ESTIMATOR_TEXT, r.estimator), lang)}</td>
                  <td data-estimate-flag={r.estimate.flag}>
                    <Flagged value={r.estimate.value} flag={r.estimate.flag} />
                  </td>
                  <td>{p2(r.bias, lang)}</td>
                  <td className="ct-wide-only">{`${p2(r.ci_low, lang)} ${pick({ en: 'to', es: 'a' }, lang)} ${p2(r.ci_high, lang)}`}</td>
                  <td className="ct-wide-only">{p2(r.rmse, lang)}</td>
                  <td>{p2(r.share_below_zero, lang)}</td>
                  <td>{p2(r.share_above_one, lang)}</td>
                  <td className="ct-text">{r.within_tolerance ? yes : no}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <U6TestsTable variant={sel.data.variant} modelLabel={(id) => pick(modelLabel(o, id), lang)} only={(t) => t.test_id === 'lgd_ead.ccf_estimator_bias' && (!(t.model_id ?? '').startsWith('ccf-') || (t.model_id ?? '').startsWith(`ccf-${sel.design}-`))} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The realised CCF of the defaults, binned over a range wider than [0, 1]: the bins outside it are the flagged ones. */
export function DistributionView({ sel }: { sel: C09Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const d = o.ccf_distribution;
  const to = pick({ en: 'to', es: 'a' }, lang);
  const edge = (v: number, l: 'en' | 'es') => formatNumber(v, l, { percent: true, decimals: 0 });
  const outside = (i: number) => d.edges[i + 1] <= 0 || d.edges[i] >= 1;
  const data = d.counts.map((n, i) => ({
    id: `bin-${i}`,
    label: { en: `${edge(d.edges[i], 'en')} to ${edge(d.edges[i + 1], 'en')}`, es: `${edge(d.edges[i], 'es')} a ${edge(d.edges[i + 1], 'es')}` },
    value: n,
    tone: outside(i) ? ('bad' as const) : ('accent' as const),
  }));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Distribution of the realised CCF', es: 'Distribución del CCF realizado' }}
        {...card}
        note={{
          en: 'The realised CCF of each default in the design in focus. A default whose balance is already at the limit, or that repays before it defaults, has a CCF outside 0 to 1: it is a real observation, kept in a bin of its own range and counted, never clipped.',
          es: 'El CCF realizado de cada incumplimiento en el diseño en foco. Un incumplimiento cuyo saldo ya está en el límite, o que paga antes de incumplir, tiene un CCF fuera de 0 a 1: es una observación real, se conserva en un tramo de su propio rango y se cuenta, nunca se recorta.',
        }}
      >
        <ChartOverTable
          chartMin={`${Math.min(16, data.length * 0.8 + 3)}rem`}
          chart={<BarChart title={{ en: 'Defaults by realised CCF', es: 'Incumplimientos por CCF realizado' }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Number of defaults', es: 'Número de incumplimientos' }, format: { decimals: 0 } }} />}
        >
          <p className="ct-note" data-totals="true">
            {pick(
              {
                en: `${count(d.n, 'en')} defaults in the design: ${count(d.n_below_zero, 'en')} below 0 and ${count(d.n_above_one, 'en')} above 1, kept and not clipped.`,
                es: `${count(d.n, 'es')} incumplimientos en el diseño: ${count(d.n_below_zero, 'es')} bajo 0 y ${count(d.n_above_one, 'es')} sobre 1, conservados y no recortados.`,
              },
              lang,
            )}
          </p>
          <table className="caos-table ct-wrap-head" data-table="ccf-distribution" data-design={d.design}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Realised CCF', es: 'CCF realizado' }, lang)}</th>
                <th>{pick({ en: 'Defaults', es: 'Incumplimientos' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Range', es: 'Rango' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {d.counts.map((n, i) => (
                <tr key={i} data-bin={i}>
                  <td className="ct-text">{`${edge(d.edges[i], lang)} ${to} ${edge(d.edges[i + 1], lang)}`}</td>
                  <td>{count(n, lang)}</td>
                  <td className="ct-text">{outside(i) ? pick(d.edges[i + 1] <= 0 ? { en: 'below 0', es: 'bajo 0' } : { en: 'above 1', es: 'sobre 1' }, lang) : pick({ en: 'in range', es: 'en rango' }, lang)}</td>
                </tr>
              ))}
              <tr data-range="below-zero">
                <td className="ct-text">{pick({ en: 'Below 0, in all', es: 'Bajo 0, en total' }, lang)}</td>
                <td>{count(d.n_below_zero, lang)}</td>
                <td className="ct-text">{pick({ en: 'kept, not clipped', es: 'conservados, no recortados' }, lang)}</td>
              </tr>
              <tr data-range="above-one">
                <td className="ct-text">{pick({ en: 'Above 1, in all', es: 'Sobre 1, en total' }, lang)}</td>
                <td>{count(d.n_above_one, lang)}</td>
                <td className="ct-text">{pick({ en: 'kept, not clipped', es: 'conservados, no recortados' }, lang)}</td>
              </tr>
              <tr data-range="all">
                <td className="ct-text">{pick({ en: 'Defaults in the design', es: 'Incumplimientos en el diseño' }, lang)}</td>
                <td>{count(d.n, lang)}</td>
                <td className="ct-text">{pick(DESIGN_TEXT[d.design] ?? { en: d.design, es: d.design }, lang)}</td>
              </tr>
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
