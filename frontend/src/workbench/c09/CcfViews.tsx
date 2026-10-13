// C09's CCF group: the conversion-factor estimate of every reference-date design and treatment against the known CCF of
// the generator, and the distribution of the realised CCF with the values outside [0, 1] counted and flagged, never
// clipped. Each draws what the c09-outputs document carries.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { ChartOverTable } from '../c06/format';
import { Flagged, U6TestsTable, p2, useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { DESIGN_TEXT, TREATMENT_TEXT, modelLabel, outputsOf, text, type C09Sel } from './selection';

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
  const rowLabel = (design: string, treatment: string) => ({
    en: `${text(DESIGN_TEXT, design).en}, ${text(TREATMENT_TEXT, treatment).en.toLowerCase()}`,
    es: `${text(DESIGN_TEXT, design).es}, ${text(TREATMENT_TEXT, treatment).es.toLowerCase()}`,
  });
  const data = [
    { id: 'truth', label: { en: 'Known CCF', es: 'CCF conocido' }, value: truth.value, tone: 'neutral' as const },
    ...c.rows.map((r) => ({
      id: `${r.design}-${r.treatment}`,
      label: rowLabel(r.design, r.treatment),
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
          chart={<BarChart title={{ en: 'CCF by design and treatment', es: 'CCF por diseño y tratamiento' }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Conversion factor', es: 'Factor de conversión' }, format: { percent: true, digits: 2 } }} />}
        >
          <p className="ct-note" data-truth={truth.value}>
            {pick(
              {
                en: `Known CCF of the generator: ${p2(truth.value, 'en')}; an estimate counts as recovered within ${p2(c.tolerance, 'en')}.`,
                es: `CCF conocido del generador: ${p2(truth.value, 'es')}; una estimación cuenta como recuperada dentro de ${p2(c.tolerance, 'es')}.`,
              },
              lang,
            )}
          </p>
          <p className="ct-note">{pick(o.generator.notice, lang)}</p>
          <table className="caos-table ct-wrap-head" data-table="ccf-by-design">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Design', es: 'Diseño' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Treatment', es: 'Tratamiento' }, lang)}</th>
                <th>{pick({ en: 'Estimate', es: 'Estimación' }, lang)}</th>
                <th>{pick({ en: 'Bias', es: 'Sesgo' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Interval', es: 'Intervalo' }, lang)}</th>
                <th className="ct-wide-only">RMSE</th>
                <th>{pick({ en: 'Below 0', es: 'Bajo 0' }, lang)}</th>
                <th>{pick({ en: 'Above 1', es: 'Sobre 1' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Within tolerance', es: 'Dentro de la tolerancia' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {c.rows.map((r) => (
                <tr key={`${r.design}-${r.treatment}`} data-design={r.design} data-treatment={r.treatment} data-tolerance={String(r.within_tolerance)} className={r.design === sel.design && r.treatment === sel.treatment ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(DESIGN_TEXT, r.design), lang)}</td>
                  <td className="ct-text">{pick(text(TREATMENT_TEXT, r.treatment), lang)}</td>
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
          <U6TestsTable variant={sel.data.variant} modelLabel={(id) => pick(modelLabel(o, id), lang)} only={(t) => !t.test_id.includes('ead')} />
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
          chart={<BarChart title={{ en: 'Defaults by realised CCF', es: 'Incumplimientos por CCF realizado' }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Number of defaults', es: 'Número de incumplimientos' }, format: { decimals: 0 } }} />}
        >
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
