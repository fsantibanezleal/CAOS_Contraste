// C21's Controlled group (the disparity after the permitted underwriting controls and the rate-spread disparity, each with
// its interval and its missing controls named) and its Replication group (the same estimate on the next year, and the
// situation-testing panel, ceteris paribus only, the counterfactual test shown as not run with its reason). The controlled
// estimate is an approximation of comparative evidence, never a finding of a violation; HMDA has no performance outcome,
// so no outcome-conditioned view exists. Every view says "no legal claim" and carries the three legal sentences.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useCard } from '../c03/U6Shared';
import { C21TestsTable } from './Marked';
import { Pending } from '../Pending';
import { UnavailableCard } from '../c14/C14Common';
import { LabelledOverTable, barMin, f2, f3, int, pc1, testsOf } from '../c20/U14Common';
import { LegalSentences, NoLegalClaim, legalOf } from './C21Common';
import { CONTROL_TEXT, FIELD_TEXT, attributeFor, groupBi, outputsOf, text, type C21Sel } from './selection';
import { es } from './localise';

const controls = (ids: string[], lang: 'en' | 'es') => ids.map((c) => pick(text(CONTROL_TEXT, c), lang)).join(', ');

type Which = 'controlled' | 'rate_spread';

/** The x axis of the group charts (b10 m3): one named tick per group, the group's name as the table writes it (with its reference
 * when two contrasts share a group, so no label repeats), and half a step of room at each end. */
export function groupAxis(contrasts: Array<{ group: string; reference_group: string }>) {
  const twice = (g: string) => contrasts.filter((c) => c.group === g).length > 1;
  const ticks = contrasts.map((c, i) => {
    const g = groupBi(c.group);
    const r = groupBi(c.reference_group);
    return { value: i + 1, label: twice(c.group) ? { en: `${g.en} / ${r.en}`, es: `${g.es} / ${r.es}` } : g };
  });
  return { values: contrasts.map((_, i) => i + 1), ticks, range: [0.5, contrasts.length + 0.5] as [number, number], label: { en: 'Group', es: 'Grupo' }, format: { decimals: 0 } };
}

function EstimateCard({ sel, which }: { sel: C21Sel; which: Which }) {
  const lang = useShellLang();
  const card = useCard(sel.data.variant);
  const a = attributeFor(sel);
  const title: BiText = which === 'controlled' ? { en: 'Approval disparity after the controls', es: 'Disparidad de aprobación tras los controles' } : { en: 'Rate-spread disparity', es: 'Disparidad en el diferencial de tasa' };
  if (!a) return <UnavailableCard sel={sel} title={title} reason={{ en: 'Not available: this document carries no protected attribute.', es: 'No disponible: este documento no trae ningún atributo protegido.' }} />;
  const rows = a.contrasts.map((c) => ({ c, e: c[which] }));
  const have = rows.filter((r) => r.e.estimate !== null);
  const note: BiText = which === 'controlled'
    ? {
        en: 'The coefficient of the group in a logistic decision model of approval with the permitted underwriting controls HMDA publishes, with its 95% interval: negative means lower odds of approval than the reference group at the same controls. The public data carry no credit score, so every estimate names it as a missing control. An approximation of comparative evidence.',
        es: 'El coeficiente del grupo en un modelo logístico de decisión de aprobación con los controles de suscripción permitidos que publica HMDA, con su intervalo de 95 %: negativo significa menores odds de aprobación que el grupo de referencia con los mismos controles. Los datos públicos no traen puntaje de crédito, así que cada estimación lo nombra como control faltante. Una aproximación de evidencia comparativa.',
      }
    : {
        en: 'The coefficient of the group in a linear model of the rate spread of the approved loans with the same controls, in percentage points of rate spread, with its 95% interval: positive means a higher spread than the reference group. An approximation of comparative evidence.',
        es: 'El coeficiente del grupo en un modelo lineal del diferencial de tasa de los préstamos aprobados con los mismos controles, en puntos porcentuales de diferencial, con su intervalo de 95 %: positivo significa un diferencial mayor que el del grupo de referencia. Una aproximación de evidencia comparativa.',
      };
  return (
    <PlotCard fill title={{ en: `${title.en}: ${text(FIELD_TEXT, a.field).en.toLowerCase()}`, es: `${title.es}: ${text(FIELD_TEXT, a.field).es.toLowerCase()}` }} {...card} note={note}>
      <LabelledOverTable
        head={<NoLegalClaim legal={legalOf(sel)} />}
        chart={
          have.length === 0 ? (
            <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: no group carries this estimate.', es: 'No disponible: ningún grupo trae esta estimación.' }, lang)}</p>
          ) : (
            <UPlotChart
              height="fill"
              x={groupAxis(have.map((r) => r.c))}
              y={{ label: which === 'controlled' ? { en: 'Coefficient (log-odds)', es: 'Coeficiente (log-odds)' } : { en: 'Coefficient (percentage points)', es: 'Coeficiente (puntos porcentuales)' }, format: { decimals: 2 } }}
              series={[
                { label: { en: 'Estimate', es: 'Estimación' }, values: have.map((r) => r.e.estimate!.coefficient), color: '--color-accent', mode: 'points', size: 11 },
                { label: { en: 'Interval, upper', es: 'Intervalo, superior' }, values: have.map((r) => r.e.estimate!.ci.hi), color: '--color-magenta', dash: [3, 3], width: 1, mode: 'points', size: 6 },
                { label: { en: 'Interval, lower', es: 'Intervalo, inferior' }, values: have.map((r) => r.e.estimate!.ci.lo), color: '--color-magenta', dash: [3, 3], width: 1, mode: 'points', size: 6 },
                { label: { en: 'No difference', es: 'Sin diferencia' }, values: have.map(() => 0), color: '--color-fg-faint', dash: [4, 4], width: 1 },
              ]}
            />
          )
        }
      >
        <table className="caos-table ct-wrap-head" data-table={which === 'controlled' ? 'controlled' : 'rate-spread'}>
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Group', es: 'Grupo' }, lang)}</th>
              <th>{pick({ en: 'Coefficient', es: 'Coeficiente' }, lang)}</th>
              <th>{pick({ en: '95% interval', es: 'Intervalo 95 %' }, lang)}</th>
              <th className="ct-wide-only">{which === 'controlled' ? pick({ en: 'Odds ratio', es: 'Razón de odds' }, lang) : pick({ en: 'Unit', es: 'Unidad' }, lang)}</th>
              <th className="ct-wide-only">N</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ c, e }) =>
              e.estimate ? (
                <tr key={c.group} data-group={c.group} data-label={e.estimate.label} className={c.group === sel.group ? 'ct-current' : undefined}>
                  <td className="ct-text">{`${pick(groupBi(c.group), lang)} / ${pick(groupBi(c.reference_group), lang)}`}</td>
                  <td>{f3(e.estimate.coefficient, lang)}</td>
                  <td>{`${f3(e.estimate.ci.lo, lang)} ${pick({ en: 'to', es: 'a' }, lang)} ${f3(e.estimate.ci.hi, lang)}`}</td>
                  <td className="ct-wide-only">{'odds_ratio' in e.estimate ? f3(e.estimate.odds_ratio, lang) : lang === 'es' ? es(e.estimate.unit, lang) : e.estimate.unit.replace('rate_spread', 'rate spread')}</td>
                  <td className="ct-wide-only">{int(e.estimate.n, lang)}</td>
                </tr>
              ) : (
                <tr key={c.group} data-group={c.group} data-na="true">
                  <td className="ct-text">{`${pick(groupBi(c.group), lang)} / ${pick(groupBi(c.reference_group), lang)}`}</td>
                  <td colSpan={4} className="ct-text">{`${formatNumber(null, lang)} (${e.reason ?? pick({ en: 'no reason given', es: 'sin razón dada' }, lang)})`}</td>
                </tr>
              ),
            )}
          </tbody>
        </table>
        {have[0]?.e.estimate ? (
          <p className="ct-note" data-controls={have[0].e.estimate.controls.length}>
            {pick({ en: `Controls: ${controls(have[0].e.estimate.controls, 'en')}. Missing control: ${controls(have[0].e.estimate.missing_controls, 'en')}.`, es: `Controles: ${controls(have[0].e.estimate.controls, 'es')}. Control faltante: ${controls(have[0].e.estimate.missing_controls, 'es')}.` }, lang)}
          </p>
        ) : null}
        <C21TestsTable tests={sel.data.variant.tests} only={testsOf(which === 'controlled' ? 'fair.conditional' : 'fair.rate_spread')} />
        <LegalSentences legal={legalOf(sel)} />
      </LabelledOverTable>
    </PlotCard>
  );
}

export function ControlledView({ sel }: { sel: C21Sel | null }) {
  if (!sel || !outputsOf(sel)) return <Pending />;
  return (
    <ViewsRow>
      <EstimateCard sel={sel} which="controlled" />
    </ViewsRow>
  );
}

export function RateSpreadView({ sel }: { sel: C21Sel | null }) {
  if (!sel || !outputsOf(sel)) return <Pending />;
  return (
    <ViewsRow>
      <EstimateCard sel={sel} which="rate_spread" />
    </ViewsRow>
  );
}

/** The year-pair replication panel: the estimate fitted on year t and refitted on year t+1, its sign and its size. */
export function ReplicationView({ sel }: { sel: C21Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const a = attributeFor(sel);
  const title: BiText = { en: 'Replication on the next year', es: 'Replicación en el año siguiente' };
  if (!sel || !o) return <Pending />;
  if (!a) return <UnavailableCard sel={sel} title={title} reason={{ en: 'Not available: this document carries no protected attribute.', es: 'No disponible: este documento no trae ningún atributo protegido.' }} />;
  const rows = a.contrasts.map((c) => ({ c, e: c.confirmation.estimate }));
  const have = rows.filter((r) => r.e !== null);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `${title.en} (${o.fit_year} to ${o.confirm_year}): ${text(FIELD_TEXT, a.field).en.toLowerCase()}`, es: `${title.es} (${o.fit_year} a ${o.confirm_year}): ${text(FIELD_TEXT, a.field).es.toLowerCase()}` }}
        {...card}
        note={{
          en: `The controlled estimate fitted on ${o.fit_year} and the same estimate refitted on ${o.confirm_year}. A finding is stable when the sign holds; the size ratio is the later coefficient over the earlier one. Stability across a year is a check, not a proof, and no legal claim follows from it.`,
          es: `La estimación controlada ajustada en ${o.fit_year} y la misma estimación reajustada en ${o.confirm_year}. Un hallazgo es estable cuando el signo se mantiene; la razón de tamaño es el coeficiente posterior sobre el anterior. La estabilidad de un año es una verificación, no una prueba, y de ella no se sigue ninguna afirmación legal.`,
        }}
      >
        <LabelledOverTable
          head={<NoLegalClaim legal={legalOf(sel)} />}
          chartMin={barMin(have.length * 2)}
          chart={
            have.length === 0 ? (
              <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: no group carries a confirmation.', es: 'No disponible: ningún grupo trae una confirmación.' }, lang)}</p>
            ) : (
              <UPlotChart
                height="fill"
                x={groupAxis(have.map((r) => r.c))}
                y={{ label: { en: 'Coefficient (log-odds of approval)', es: 'Coeficiente (log-odds de aprobación)' }, format: { decimals: 2 } }}
                series={[
                  { label: { en: `Fitted on ${o.fit_year}`, es: `Ajustado en ${o.fit_year}` }, values: have.map((r) => r.e!.fit_coefficient), color: '--color-accent', mode: 'points', size: 11 },
                  { label: { en: `Refitted on ${o.confirm_year}`, es: `Reajustado en ${o.confirm_year}` }, values: have.map((r) => r.e!.confirm_coefficient), color: '--color-magenta', mode: 'points', size: 11 },
                  { label: { en: 'No difference', es: 'Sin diferencia' }, values: have.map(() => 0), color: '--color-fg-faint', dash: [4, 4], width: 1 },
                ]}
              />
            )
          }
        >
          <table className="caos-table ct-wrap-head" data-table="replication">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Group', es: 'Grupo' }, lang)}</th>
                <th>{o.fit_year}</th>
                <th>{o.confirm_year}</th>
                <th className="ct-text">{pick({ en: 'Sign', es: 'Signo' }, lang)}</th>
                <th>{pick({ en: 'Size ratio', es: 'Razón de tamaño' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ c, e }) =>
                e ? (
                  <tr key={c.group} data-group={c.group} data-same-sign={e.same_sign} className={c.group === sel.group ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(groupBi(c.group), lang)}</td>
                    <td>{f3(e.fit_coefficient, lang)}</td>
                    <td>{f3(e.confirm_coefficient, lang)}</td>
                    <td className="ct-text">{pick(e.same_sign ? { en: 'held', es: 'se mantuvo' } : { en: 'changed', es: 'cambió' }, lang)}</td>
                    <td data-na={e.size_ratio === null ? 'true' : undefined}>{e.size_ratio === null ? formatNumber(null, lang) : f2(e.size_ratio, lang)}</td>
                  </tr>
                ) : (
                  <tr key={c.group} data-group={c.group} data-na="true">
                    <td className="ct-text">{pick(groupBi(c.group), lang)}</td>
                    <td colSpan={4} className="ct-text">{`${formatNumber(null, lang)} (${c.confirmation.reason ?? pick({ en: 'no reason given', es: 'sin razón dada' }, lang)})`}</td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
          <C21TestsTable tests={sel.data.variant.tests} only={testsOf('fair.replication')} />
          <LegalSentences legal={legalOf(sel)} />
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The situation-testing panel: ceteris paribus comparators only; the counterfactual test is shown as not run, with its reason. */
export function SituationView({ sel }: { sel: C21Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'Situation testing', es: 'Pruebas de situación' };
  if (!sel || !o) return <Pending />;
  const s = o.situation_testing;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `${title.en}: ${text(FIELD_TEXT, s.attribute).en.toLowerCase()}`, es: `${title.es}: ${text(FIELD_TEXT, s.attribute).es.toLowerCase()}` }}
        {...card}
        note={{
          en: `Each complainant is compared with its ${s.k} nearest neighbours of each group under a range-normalised distance (a convention), at level ${formatNumber(s.alpha, 'en', { decimals: 2 })} with the one-sided Wald interval. A case is significant when the neighbours of the other group were treated better; this is individual comparative evidence and no legal claim.`,
          es: `Cada demandante se compara con sus ${s.k} vecinos más cercanos de cada grupo bajo una distancia normalizada por rango (una convención), al nivel ${formatNumber(s.alpha, 'es', { decimals: 2 })} con el intervalo de Wald unilateral. Un caso es significativo cuando los vecinos del otro grupo fueron tratados mejor; es evidencia comparativa individual y no una afirmación legal.`,
        }}
      >
        <LabelledOverTable
          head={
            <>
              <NoLegalClaim legal={legalOf(sel)} />
              <p className="ct-note" data-counterfactual-run={String(s.counterfactual_test.run)}>
                <strong>{pick({ en: 'Counterfactual test: not run.', es: 'Prueba contrafactual: no se ejecutó.' }, lang)}</strong> {pick(s.counterfactual_test.reason, lang)}
              </p>
            </>
          }
          chartMin={barMin(3)}
          chart={
            <BarChart
              title={{ en: 'Complainants, cases and significant cases', es: 'Demandantes, casos y casos significativos' }}
              height="fill"
              orientation="horizontal"
              data={[
                { id: 'complainants', label: { en: 'Complainants', es: 'Demandantes' }, value: s.n_complainants },
                { id: 'cases', label: { en: 'Cases tested', es: 'Casos evaluados' }, value: s.n_cases },
                { id: 'significant', label: { en: 'Significant cases', es: 'Casos significativos' }, value: s.n_significant, tone: 'warn' },
              ]}
              axis={{ label: { en: 'Applications', es: 'Solicitudes' }, format: { decimals: 0 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="situation" data-comparator={s.comparator}>
            <tbody>
              <tr><td className="ct-text">{pick({ en: 'Comparator', es: 'Comparador' }, lang)}</td><td className="ct-text">{pick({ en: 'ceteris paribus only', es: 'solo ceteris paribus' }, lang)}</td></tr>
              <tr><td className="ct-text">{pick({ en: 'Neighbours per group (k)', es: 'Vecinos por grupo (k)' }, lang)}</td><td>{int(s.k, lang)}</td></tr>
              <tr><td className="ct-text">{pick({ en: 'Level (alpha)', es: 'Nivel (alfa)' }, lang)}</td><td>{f2(s.alpha, lang)}</td></tr>
              <tr><td className="ct-text">{pick({ en: 'Complainants', es: 'Demandantes' }, lang)}</td><td>{int(s.n_complainants, lang)}</td></tr>
              <tr><td className="ct-text">{pick({ en: 'Cases tested', es: 'Casos evaluados' }, lang)}</td><td>{int(s.n_cases, lang)}</td></tr>
              <tr data-measure="significant"><td className="ct-text">{pick({ en: 'Significant cases', es: 'Casos significativos' }, lang)}</td><td>{`${int(s.n_significant, lang)}${s.n_cases > 0 ? ` (${pc1(s.n_significant / s.n_cases, lang)})` : ''}`}</td></tr>
              <tr data-status={s.label_parameters}><td className="ct-text">{pick({ en: 'Distance and level', es: 'Distancia y nivel' }, lang)}</td><td className="ct-text">{pick({ en: `${s.distance_normalization} normalisation; convention`, es: `normalización ${es(s.distance_normalization, 'es')}; convención` }, lang)}</td></tr>
            </tbody>
          </table>
          <p className="ct-note">{es(s.interval, lang)}</p>
          <C21TestsTable tests={sel.data.variant.tests} only={testsOf('fair.situation')} />
          <LegalSentences legal={legalOf(sel)} />
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
