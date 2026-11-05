// C22's Sequential view (BS-15, unit D15): the engine's e-process monitors against the fixed-window tests read every day. It draws what the
// other-families document carries in `outputs.sequential`: the verdict on the three hypotheses with the numbers they were judged on, the
// VaR-hit scenarios (the share of series ever rejected and the median detection day of each monitor) and the PD book (the same by year).
// A median that is null means that more than half of the series were never rejected; it is told in words, never drawn as a day.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import type { C22SeqDetection } from '../../lib/contract.types';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { c22Of } from './Views';
import type { C22Sel } from './selection';

type Lang = 'en' | 'es';

const pct = (lang: Lang, v: number, decimals = 1) => formatNumber(v, lang, { percent: true, decimals });
const whole = (lang: Lang, v: number) => formatNumber(v, lang, { decimals: 0 });
const NEVER: BiText = { en: 'not reached', es: 'no se alcanza' };

/** "ever (median day)" of a monitor in a scenario: the share of series rejected at some point, and the median first-rejection step. */
function detection(d: C22SeqDetection, lang: Lang): string {
  const day = d.median_day === null ? pick(NEVER, lang) : whole(lang, d.median_day);
  return `${pct(lang, d.ever)} (${day})`;
}

export function SequentialView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  const s = v?.outputs.sequential ?? null;
  if (!sel || !v || !s) return <Pending />;
  const card = { lane: REPLAY, provenance: provenanceOf(v.provenance.truth_status), dataKey: stateKey };
  const h = s.hits;
  const p = s.pd_grades;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Sequential monitors against tests read every day', es: 'Monitores secuenciales contra pruebas leídas todos los días' }}
        {...card}
        note={s.method.description}
      >
        <div className="ct-scroll" data-caos-flow="">
          <p className="ct-note" data-sequential-verdict={s.verdict.holds ? 'holds' : 'refuted'}>
            {pick(s.verdict.text, lang)} {pick(s.verdict.scope, lang)}
          </p>
          <table className="caos-table ct-wrap-head" data-table="sequential-hypotheses">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Hypothesis', es: 'Hipótesis' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Rule', es: 'Regla' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Measured', es: 'Medido' }, lang)}</th>
                <th>{pick({ en: 'Holds', es: 'Se sostiene' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {s.hypotheses.map((x) => (
                <tr key={x.id} data-hypothesis={x.id} data-holds={x.holds ? 'yes' : 'no'}>
                  <td className="ct-text">{x.id}</td>
                  <td className="ct-text">{pick(x.rule, lang)}</td>
                  <td className="ct-text">{pick(x.measured, lang)}</td>
                  <td>{pick(x.holds ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">
            {pick(
              {
                en: `VaR hits at ${pct('en', h.alpha, 0)}, ${whole('en', h.horizon)} days, ${whole('en', h.reps)} series per scenario. Each cell is the share of series rejected at some day (the median first-rejection day). The Basel traffic light cannot speak before day ${whole('en', h.window)}; one Kupiec reading at day ${whole('en', h.window)} is the fixed-window comparator of the power column.`,
                es: `Excepciones de VaR al ${pct('es', h.alpha, 0)}, ${whole('es', h.horizon)} días, ${whole('es', h.reps)} series por escenario. Cada celda es la parte de series rechazadas en algún día (el día mediano del primer rechazo). El semáforo de Basilea no puede hablar antes del día ${whole('es', h.window)}; una lectura de Kupiec en el día ${whole('es', h.window)} es el comparador de ventana fija de la columna de potencia.`,
              },
              lang,
            )}
          </p>
          <table className="caos-table ct-wrap-head" data-table="sequential-hits">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                <th>{pick({ en: 'E-process, rate', es: 'Proceso e, tasa' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'E-process, battery', es: 'Proceso e, batería' }, lang)}</th>
                <th>{pick({ en: 'Kupiec, last 250 days', es: 'Kupiec, últimos 250 días' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Kupiec, all days', es: 'Kupiec, todos los días' }, lang)}</th>
                <th>{pick({ en: 'Traffic light', es: 'Semáforo' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Independence, last 250 days', es: 'Independencia, últimos 250 días' }, lang)}</th>
                <th>{pick({ en: 'Power at day 250: one Kupiec / e-process', es: 'Potencia al día 250: un Kupiec / proceso e' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {h.scenarios.map((x) => (
                <tr key={x.id} data-scenario={x.id} data-kind={x.kind}>
                  <td className="ct-text">{pick(x.label, lang)}</td>
                  <td>{detection(x.e_rate, lang)}</td>
                  <td className="ct-wide-only">{detection(x.e_battery, lang)}</td>
                  <td>{detection(x.kupiec_trailing, lang)}</td>
                  <td className="ct-wide-only">{detection(x.kupiec_cumulative, lang)}</td>
                  <td>{detection(x.traffic_light, lang)}</td>
                  <td className="ct-wide-only">{detection(x.independence_trailing, lang)}</td>
                  <td>{x.kind === 'rate' ? `${pct(lang, x.kupiec_one_shot_power)} / ${pct(lang, x.e_rate.by)}` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">
            {pick(
              {
                en: `Five grades (PD ${p.pd.map((x) => pct('en', x, 1)).join(', ')}), ${whole('en', p.obligors_per_grade_year)} obligors per grade and year, ${whole('en', p.years)} yearly steps, ${whole('en', p.reps)} books per scenario. Each cell is the share of books rejected at some year (the median first-rejection year); the chi-square across the grades is read once at year ${whole('en', p.years)} and read every year.`,
                es: `Cinco grados (PD ${p.pd.map((x) => pct('es', x, 1)).join(', ')}), ${whole('es', p.obligors_per_grade_year)} deudores por grado y año, ${whole('es', p.years)} pasos anuales, ${whole('es', p.reps)} carteras por escenario. Cada celda es la parte de carteras rechazadas en algún año (el año mediano del primer rechazo); el chi-cuadrado entre los grados se lee una vez en el año ${whole('es', p.years)} y se lee cada año.`,
              },
              lang,
            )}
          </p>
          <table className="caos-table ct-wrap-head" data-table="sequential-pd">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                <th>{pick({ en: 'E-process, product', es: 'Proceso e, producto' }, lang)}</th>
                <th>{pick({ en: 'E-process, average', es: 'Proceso e, promedio' }, lang)}</th>
                <th>{pick({ en: 'Chi-square, read every year', es: 'Chi-cuadrado, cada año' }, lang)}</th>
                <th>{pick({ en: 'Chi-square, once at the end', es: 'Chi-cuadrado, una vez al final' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {p.scenarios.map((x) => (
                <tr key={x.id} data-scenario={x.id}>
                  <td className="ct-text">{pick(x.label, lang)}</td>
                  <td>{detection(x.e_product, lang)}</td>
                  <td>{detection(x.e_average, lang)}</td>
                  <td>{detection(x.chi2_every_year, lang)}</td>
                  <td>{pct(lang, x.chi2_one_shot_power)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}
