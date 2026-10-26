// C21's Rates group: the approval rate of each group of the protected attribute with the adverse impact ratio against the
// reference group, the four-fifths line against the highest-rate group (labelled an employment benchmark from 29 CFR
// 1607.4(D), never a credit-law threshold; the flag is the document's, decided on the counts in exact arithmetic), and the
// two-sample proportion z-test and Fisher exact test. The rates are indicators only. Every view says "no legal claim" and
// carries the three legal sentences of the addendum.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { useCard } from '../c03/U6Shared';
import { C21TestsTable, Marked } from './Marked';
import { Pending } from '../Pending';
import { UnavailableCard } from '../c14/C14Common';
import { LabelledOverTable, barMin, f2, f3, int, pc1, sig, testsOf } from '../c20/U14Common';
import { LegalSentences, NoLegalClaim, legalOf } from './C21Common';
import { FIELD_TEXT, attributeFor, groupBi, outputsOf, text, type C21Sel } from './selection';
import { es } from './localise';

const noAttribute = (sel: C21Sel | null, title: BiText) => (
  <UnavailableCard sel={sel} title={title} reason={{ en: 'Not available: this document carries no protected attribute.', es: 'No disponible: este documento no trae ningún atributo protegido.' }} />
);

/** The approval rate of each group, the reference group marked, and the impact ratio of each against it. */
export function RatesView({ sel }: { sel: C21Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const a = attributeFor(sel);
  const title: BiText = { en: 'Approval rate by group', es: 'Tasa de aprobación por grupo' };
  if (!sel || !o) return <Pending />;
  if (!a) return noAttribute(sel, title);
  const n = a.groups.length + a.excluded_groups.length;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `${title.en}: ${text(FIELD_TEXT, a.field).en.toLowerCase()}`, es: `${title.es}: ${text(FIELD_TEXT, a.field).es.toLowerCase()}` }}
        {...card}
        note={{
          en: `The share of the decided applications that were approved, by group of ${text(FIELD_TEXT, a.field).en.toLowerCase()}, for ${o.fit_year}. The reference group is ${groupBi(a.reference_group).en}. The rates are indicators only: gross HMDA disparities are not an adverse-impact finding.`,
          es: `La parte de las solicitudes decididas que se aprobó, por grupo de ${text(FIELD_TEXT, a.field).es.toLowerCase()}, en ${o.fit_year}. El grupo de referencia es ${groupBi(a.reference_group).es}. Las tasas son solo indicadores: las disparidades brutas de HMDA no son una constatación de impacto adverso.`,
        }}
      >
        {/* the table of a handful of groups shows every row at 1280 (R2b c21: 5 of 6): a taller box, a drawing of 1.6 rem a bar */}
        <div className="ct-c21-tall">
        <LabelledOverTable
          head={<NoLegalClaim legal={legalOf(sel)} />}
          chartMin={`${a.groups.length * 1.6 + 3.5}rem`}
          chart={
            <BarChart
              title={{ en: 'Approval rate by group', es: 'Tasa de aprobación por grupo' }}
              height="fill"
              orientation="horizontal"
              data={a.groups.map((g) => ({ id: g.group, label: groupBi(g.group) as BiText, value: g.selection_rate, highlight: g.group === a.reference_group, hint: { en: `${int(g.n, 'en')} decided applications`, es: `${int(g.n, 'es')} solicitudes decididas` } as BiText }))}
              axis={{ label: { en: 'Share approved', es: 'Parte aprobada' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="rates" data-field={a.field}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Group', es: 'Grupo' }, lang)}</th>
                <th>{pick({ en: 'Decided', es: 'Decididas' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Approved', es: 'Aprobadas' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Denied', es: 'Rechazadas' }, lang)}</th>
                <th>{pick({ en: 'Rate', es: 'Tasa' }, lang)}</th>
                <th>{pick({ en: 'Impact ratio', es: 'Razón de impacto' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {a.groups.map((g) => {
                const c = a.contrasts.find((x) => x.group === g.group);
                return (
                  <tr key={g.group} data-group={g.group} data-reference={g.group === a.reference_group} className={g.group === sel.group ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(groupBi(g.group), lang)}{g.group === a.reference_group ? ` (${pick({ en: 'reference', es: 'referencia' }, lang)})` : ''}</td>
                    <td>{int(g.n, lang)}</td>
                    <td className="ct-wide-only">{int(g.n_approved, lang)}</td>
                    <td className="ct-wide-only">{int(g.n_denied, lang)}</td>
                    <td>{pc1(g.selection_rate, lang)}</td>
                    <td data-na={c?.adverse_impact_ratio.value == null ? 'true' : undefined}>{c ? (c.adverse_impact_ratio.value === null ? formatNumber(null, lang) : f3(c.adverse_impact_ratio.value, lang)) : '-'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {a.excluded_groups.length > 0 ? (
            <p className="ct-note" data-excluded={a.excluded_groups.length}>
              {pick({ en: `${n - a.groups.length} category(ies) kept out of the pairwise tests: `, es: `${n - a.groups.length} categoría(s) fuera de las pruebas de a pares: ` }, lang)}
              {a.excluded_groups.map((e) => `${e.group} (${int(e.n, lang)}; ${pick(e.reason, lang)})`).join('; ')}
            </p>
          ) : null}
          <C21TestsTable tests={sel.data.variant.tests} only={testsOf('fair.demographic', 'fair.adverse')} />
          <LegalSentences legal={legalOf(sel)} />
        </LabelledOverTable>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** The four-fifths line: each group's rate over the highest group's, the line at 0.8 an employment benchmark, the flag the document's. */
export function FourFifthsView({ sel }: { sel: C21Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const a = attributeFor(sel);
  const title: BiText = { en: 'The four-fifths line', es: 'La línea de cuatro quintos' };
  if (!sel || !o) return <Pending />;
  if (!a) return noAttribute(sel, title);
  const f = a.four_fifths;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `${title.en}: ${text(FIELD_TEXT, a.field).en.toLowerCase()}`, es: `${title.es}: ${text(FIELD_TEXT, a.field).es.toLowerCase()}` }}
        {...card}
        note={{
          en: `Each group's rate over the rate of the highest-rate group (${groupBi(f.highest_rate_group).en}). The line at ${formatNumber(f.threshold, 'en', { decimals: 1 })} is the four-fifths rule (its citation is above the chart), an employment-selection benchmark and not a credit-law threshold. The flag is decided on the counts in exact arithmetic: ${f.rule}.`,
          es: `La tasa de cada grupo sobre la del grupo de mayor tasa (${groupBi(f.highest_rate_group).es}). La línea en ${formatNumber(f.threshold, 'es', { decimals: 1 })} es la regla de cuatro quintos (su cita está sobre el gráfico), una referencia de selección laboral y no un umbral de la ley de crédito. La alerta se decide sobre los conteos en aritmética exacta: ${es(f.rule, 'es')}.`,
        }}
      >
        <LabelledOverTable
          head={
            <>
              <NoLegalClaim legal={legalOf(sel)} />
              <p className="ct-note" data-label="employment-benchmark" data-credit-law={String(f.is_credit_law_threshold)}>
                <strong>{pick({ en: 'Employment benchmark.', es: 'Referencia de selección laboral.' }, lang)}</strong>{' '}
                <Marked>{pick({ en: `${f.citation}; not a credit-law threshold.`, es: `${f.citation}; no es un umbral de la ley de crédito.` }, lang)}</Marked>
              </p>
            </>
          }
          chartMin={barMin(f.groups.length + 1)}
          chart={
            <BarChart
              title={{ en: 'Rate over the highest rate', es: 'Tasa sobre la mayor tasa' }}
              height="fill"
              orientation="horizontal"
              data={[
                ...f.groups.map((g) => ({ id: g.group, label: groupBi(g.group) as BiText, value: g.ratio_to_highest, tone: g.flag ? ('bad' as const) : ('good' as const), highlight: g.group === sel.group })),
                { id: 'line', label: { en: 'Four-fifths line (employment benchmark)', es: 'Línea de cuatro quintos (referencia laboral)' } as BiText, value: f.threshold, tone: 'neutral' as const },
              ]}
              axis={{ label: { en: 'Rate over the highest group rate', es: 'Tasa sobre la mayor tasa de grupo' }, format: { decimals: 2 }, range: [0, 1.1] }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="four-fifths" data-highest={f.highest_rate_group}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Group', es: 'Grupo' }, lang)}</th>
                <th>{pick({ en: 'Over the highest', es: 'Sobre la mayor' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Flag', es: 'Alerta' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {f.groups.map((g) => (
                <tr key={g.group} data-group={g.group} data-flag={g.flag} className={g.group === sel.group ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(groupBi(g.group), lang)}{g.group === f.highest_rate_group ? ` (${pick({ en: 'highest', es: 'mayor' }, lang)})` : ''}</td>
                  <td data-na={g.ratio_to_highest === null ? 'true' : undefined}>{g.ratio_to_highest === null ? formatNumber(null, lang) : f3(g.ratio_to_highest, lang)}</td>
                  <td className="ct-text">{pick(g.flag ? { en: 'below four-fifths', es: 'bajo cuatro quintos' } : { en: 'not flagged', es: 'sin alerta' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <LegalSentences legal={legalOf(sel)} />
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The two-sample proportion z-test and the Fisher exact test of every group against the reference group. */
export function TestsView({ sel }: { sel: C21Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const a = attributeFor(sel);
  const title: BiText = { en: 'Tests on the rates', es: 'Pruebas sobre las tasas' };
  if (!sel || !o) return <Pending />;
  if (!a) return noAttribute(sel, title);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `${title.en}: ${text(FIELD_TEXT, a.field).en.toLowerCase()}`, es: `${title.es}: ${text(FIELD_TEXT, a.field).es.toLowerCase()}` }}
        {...card}
        note={{
          en: 'The pooled two-proportion z-test and the Fisher exact test compare each group with the reference group. A small p-value says the rates differ more than chance explains; a small difference can be significant in a large file, and neither test says why the rates differ.',
          es: 'La prueba z de dos proporciones agrupada y la prueba exacta de Fisher comparan cada grupo con el grupo de referencia. Un valor p pequeño dice que las tasas difieren más de lo que explica el azar; una diferencia pequeña puede ser significativa en un archivo grande, y ninguna prueba dice por qué difieren las tasas.',
        }}
      >
        <LabelledOverTable
          head={<NoLegalClaim legal={legalOf(sel)} />}
          chartMin={barMin(a.contrasts.length + 1)}
          chart={
            <BarChart
              title={{ en: 'Approval rate of each group and of the reference', es: 'Tasa de aprobación de cada grupo y de la referencia' }}
              height="fill"
              orientation="horizontal"
              data={[
                { id: 'reference', label: { en: `${groupBi(a.reference_group).en} (reference)`, es: `${groupBi(a.reference_group).es} (referencia)` } as BiText, value: a.contrasts[0]?.selection_rate_reference ?? null, tone: 'neutral' as const },
                ...a.contrasts.map((c) => ({ id: c.group, label: groupBi(c.group) as BiText, value: c.selection_rate_group, highlight: c.group === sel.group })),
              ]}
              axis={{ label: { en: 'Share approved (an indicator only)', es: 'Parte aprobada (solo un indicador)' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="rate-tests">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Group', es: 'Grupo' }, lang)}</th>
                <th>{pick({ en: 'Parity gap', es: 'Brecha de paridad' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Parity ratio', es: 'Razón de paridad' }, lang)}</th>
                <th>z</th>
                <th>{pick({ en: 'p (z)', es: 'p (z)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Odds ratio', es: 'Razón de odds' }, lang)}</th>
                <th>{pick({ en: 'p (Fisher)', es: 'p (Fisher)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {a.contrasts.map((c) => (
                <tr key={c.group} data-group={c.group} className={c.group === sel.group ? 'ct-current' : undefined}>
                  <td className="ct-text">{`${pick(groupBi(c.group), lang)} / ${pick(groupBi(c.reference_group), lang)}`}</td>
                  <td>{pc1(Math.abs(c.parity_gap) < 5e-4 ? 0 : c.parity_gap, lang)}</td>
                  <td className="ct-wide-only" data-na={c.parity_ratio === null ? 'true' : undefined}>{c.parity_ratio === null ? formatNumber(null, lang) : f3(c.parity_ratio, lang)}</td>
                  <td>{f2(c.z_test.statistic, lang)}</td>
                  <td>{sig(c.z_test.p_value, lang)}</td>
                  <td className="ct-wide-only" data-na={c.fisher_exact.odds_ratio === null ? 'true' : undefined}>{c.fisher_exact.odds_ratio === null ? formatNumber(null, lang) : f3(c.fisher_exact.odds_ratio, lang)}</td>
                  <td>{sig(c.fisher_exact.p_value, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <C21TestsTable tests={sel.data.variant.tests} only={testsOf('fair.two_proportion', 'fair.fisher')} />
          <LegalSentences legal={legalOf(sel)} />
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
