// C09's CCF group: the conversion-factor estimate of every reference-date design and treatment against the known CCF of
// the generator, and the distribution of the realised CCF with the values outside [0, 1] counted and flagged, never
// clipped. Each draws what the c09-outputs document carries.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { ChartOverTable } from '../c06/format';
import { Flagged, U6TestsTable, p2, useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { DESIGN_TEXT, ESTIMATOR_TEXT, TREATMENT_TEXT, modelLabel, outputsOf, text, type C09Sel } from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });
/** The bar labels of the estimates: two decimals, so a known 71.42 % and an estimate of 71.28 % do not both read 71 % (R3 c10 m10). */
const BAR_FORMAT = { percent: true, decimals: 2 } as const;

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
    { id: 'truth', label: { en: 'Known CCF', es: 'CCF conocido' }, value: truth.value, format: BAR_FORMAT, tone: 'neutral' as const },
    ...rows.map((r) => ({
      id: `${r.design}-${r.treatment}-${r.estimator}`,
      label: rowLabel(r.treatment, r.estimator),
      value: r.estimate.value,
      format: BAR_FORMAT,
      tone: r.estimate.flag !== 'in-range' ? ('bad' as const) : r.within_tolerance ? ('good' as const) : ('warn' as const),
    })),
  ];
  // the shares of defaults outside 0 to 1 are the design's, the same on every row: then the note states them once and the table
  // drops the two columns, so its 8 rows read on one line each at 1280 (R3 c10 M2)
  const sameShares = rows.length > 0 && rows.every((r) => r.share_below_zero === rows[0].share_below_zero && r.share_above_one === rows[0].share_above_one);
  const shares: { en: string; es: string } = sameShares
    ? { en: ` In this design ${p2(rows[0].share_below_zero, 'en')} of the defaults are below 0 and ${p2(rows[0].share_above_one, 'en')} above 1, the same for every estimator.`, es: ` En este diseño ${p2(rows[0].share_below_zero, 'es')} de los incumplimientos están bajo 0 y ${p2(rows[0].share_above_one, 'es')} sobre 1, igual para todo estimador.` }
    : { en: '', es: '' };
  return (
    // split, not scrolled (ADR-0071 rule 6; R3 c10 M2: the estimates and the tests shared one 42 % box that showed one row): the drawing
    // fills a card of its own beside the estimates, whole at 1280; the tests are a sub-view of their own (EstimatorTestsView).
    // The estimates take two thirds of the row and the tolerance sentence is the card's note.
    <ViewsRow shares={[1, 2]}>
      <PlotCard
        fill
        // the title and the note in fewer lines: the legend under the chart names the tones, so the note does not repeat them, and
        // the chart keeps the height its bars, axis title and legend need (R4 c11 M1: in Spanish the stack lost 36 px and the host
        // scrolled, cutting the axis title)
        title={{ en: 'The CCF estimates against the known CCF', es: 'El CCF estimado y el conocido' }}
        {...card}
        note={{
          en: 'The generator draws every balance with one CCF, so the estimators are judged against the truth; an estimate outside 0 to 1 is printed as it is, never clipped.',
          es: 'El generador simula cada saldo con un solo CCF, así que los estimadores se juzgan contra la verdad; una estimación fuera de 0 a 1 se imprime tal cual.',
        }}
      >
        <ChartOverTable
          chartMin={`${data.length * 1.5 + 3}rem`}
          chart={<BarChart title={{ en: `CCF by treatment and estimator, ${text(DESIGN_TEXT, sel.design).en.toLowerCase()}`, es: `CCF por tratamiento y estimador, ${text(DESIGN_TEXT, sel.design).es.toLowerCase()}` }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Conversion factor', es: 'Factor de conversión' }, format: { percent: true, digits: 2 } }} legend={[
            { tone: 'neutral' as const, label: { en: 'Known CCF', es: 'CCF conocido' } },
            { tone: 'good' as const, label: { en: 'Within the tolerance', es: 'Dentro de la tolerancia' } },
            { tone: 'warn' as const, label: { en: 'Outside the tolerance', es: 'Fuera de la tolerancia' } },
            { tone: 'bad' as const, label: { en: 'Outside 0 to 1', es: 'Fuera de 0 a 1' } },
          ].filter((l) => data.some((d) => d.tone === l.tone)) as Array<{ tone: 'neutral' | 'good' | 'warn' | 'bad'; label: { en: string; es: string } }>} />}
        />
      </PlotCard>
      <PlotCard fill title={{ en: 'The estimates of this design', es: 'Las estimaciones de este diseño' }} {...card} note={{
          // the light rule of the tests is the Tests sub-view's note and the bar tones are the chart's legend: stated once each, so the
          // eight rows show at 1280 in Spanish too (R4 c11 M2)
          en: `The bias, its interval and the shares of defaults outside 0 to 1 of each treatment and estimator. Known CCF of the generator: ${p2(truth.value, 'en')}; an estimate counts as recovered within ${p2(c.tolerance, 'en')}.${shares.en}`,
          es: `El sesgo, su intervalo y las proporciones de incumplimientos fuera de 0 a 1 de cada tratamiento y estimador. CCF conocido del generador: ${p2(truth.value, 'es')}; una estimación cuenta como recuperada dentro de ${p2(c.tolerance, 'es')}.${shares.es}`,
        }}>
        <div className="ct-scroll" data-caos-flow="">
            <table className="caos-table ct-wrap-head" data-table="ccf-by-design" data-truth={truth.value}>
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Treatment', es: 'Tratamiento' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Estimator', es: 'Estimador' }, lang)}</th>
                  <th>{pick({ en: 'Estimate', es: 'Estimación' }, lang)}</th>
                  <th>{pick({ en: 'Bias', es: 'Sesgo' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Interval of the bias', es: 'Intervalo del sesgo' }, lang)}</th>
                  <th className="ct-wide-only">RMSE</th>
                  {sameShares ? null : <th>{pick({ en: 'Below 0', es: 'Bajo 0' }, lang)}</th>}
                  {sameShares ? null : <th>{pick({ en: 'Above 1', es: 'Sobre 1' }, lang)}</th>}
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
                    {sameShares ? null : <td>{p2(r.share_below_zero, lang)}</td>}
                    {sameShares ? null : <td>{p2(r.share_above_one, lang)}</td>}
                    <td className="ct-text">{r.within_tolerance ? yes : no}</td>
                  </tr>
                ))}
              </tbody>
            </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** The estimator-bias tests of the design in focus, a sub-view of their own (R3 c10 M2): the light of each follows the tolerance on the bias. */
export function EstimatorTestsView({ sel }: { sel: C09Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const c = o.ccf_by_design;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `The estimator tests, ${text(DESIGN_TEXT, sel.design).en.toLowerCase()}`, es: `Las pruebas de los estimadores, ${text(DESIGN_TEXT, sel.design).es.toLowerCase()}` }}
        {...card}
        note={{
          en: `The light of each test follows the tolerance of ${p2(c.tolerance, 'en')} on the bias, not its p-value: green within it, amber up to twice it and red beyond.`,
          es: `La luz de cada prueba sigue la tolerancia de ${p2(c.tolerance, 'es')} sobre el sesgo, no su valor p: verde dentro de ella, ámbar hasta el doble y rojo más allá.`,
        }}
      >
        <div className="ct-scroll" data-caos-flow="">
            <U6TestsTable variant={sel.data.variant} modelLabel={(id) => pick(modelLabel(o, id), lang)} only={(t) => t.test_id === 'lgd_ead.ccf_estimator_bias' && (!(t.model_id ?? '').startsWith('ccf-') || (t.model_id ?? '').startsWith(`ccf-${sel.design}-`))} />
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** The realised CCF of the defaults, binned over a range wider than [0, 1]: the bins outside it are the flagged ones. */
export function DistributionView({ sel }: { sel: C09Sel | null }) {
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const d = o.ccf_distribution;
  const edge = (v: number, l: 'en' | 'es') => formatNumber(v, l, { percent: true, decimals: 0 });
  const outside = (i: number) => d.edges[i + 1] <= 0 || d.edges[i] >= 1;
  const flag = (i: number, l: 'en' | 'es') => (outside(i) ? ` (${d.edges[i + 1] <= 0 ? (l === 'en' ? 'below 0' : 'bajo 0') : l === 'en' ? 'above 1' : 'sobre 1'})` : '');
  const data = d.counts.map((n, i) => ({
    id: `bin-${i}`,
    label: { en: `${edge(d.edges[i], 'en')} to ${edge(d.edges[i + 1], 'en')}${flag(i, 'en')}`, es: `${edge(d.edges[i], 'es')} a ${edge(d.edges[i + 1], 'es')}${flag(i, 'es')}` },
    value: n,
    tone: outside(i) ? ('bad' as const) : ('accent' as const),
  }));
  const design = DESIGN_TEXT[d.design] ?? { en: d.design, es: d.design };
  // the drawing is the view: 1.5 rem a bin, so no bin and not the value axis scroll inside it at 1280 (R3 c10 M1, a regression of
  // 66cd0d4). Each bin's count is its bar's label and a row of the chart's data table, and its range is in its label; the totals
  // are the card's note, so no table box under the drawing takes its height
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Distribution of the realised CCF', es: 'Distribución del CCF realizado' }}
        {...card}
        note={{
          en: `${count(d.n, 'en')} defaults in the design: ${count(d.n_below_zero, 'en')} below 0 and ${count(d.n_above_one, 'en')} above 1, kept and not clipped (${design.en.toLowerCase()}). A default whose balance is already at the limit, or that repays before it defaults, has a CCF outside 0 to 1: it is a real observation, kept in a bin of its own range and counted, never clipped.`,
          es: `${count(d.n, 'es')} incumplimientos en el diseño: ${count(d.n_below_zero, 'es')} bajo 0 y ${count(d.n_above_one, 'es')} sobre 1, conservados y no recortados (${design.es.toLowerCase()}). Un incumplimiento cuyo saldo ya está en el límite, o que paga antes de incumplir, tiene un CCF fuera de 0 a 1: es una observación real, se conserva en un tramo de su propio rango y se cuenta, nunca se recorta.`,
        }}
      >
        <ChartOverTable
          chartMin={`${data.length * 1.5 + 3}rem`}
          chart={<BarChart title={{ en: 'Defaults by realised CCF', es: 'Incumplimientos por CCF realizado' }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Number of defaults', es: 'Número de incumplimientos' }, format: { decimals: 0 } }} />}
        />
      </PlotCard>
    </ViewsRow>
  );
}
