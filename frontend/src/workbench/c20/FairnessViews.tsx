// C20's labelled fairness battery on the Taiwan model (equalized odds, equal opportunity, calibration within groups, AUC
// by group) and its Impact view, the share of decisions that flip at a stated cut-off under each shift (decision Q10).
// The battery is labelled evidence on one model with outcomes, never a compliance statement; the cut-off is a convention.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { LIGHT_TEXT } from '../../lib/policy';
import { SgcdNotice } from './C20Common';
import { Labelled, LabelledOverTable, barMin, f3, int, pc1, type NamedParam } from './U14Common';
import { ATTRIBUTE_TEXT, FAIR_TESTS, outputsOf, text, type C20Sel } from './selection';
import { testName } from './U14Common';
import { es } from './localise';

/** The battery rows of the document: the gap per test and protected attribute, and the value of each group behind it. */
export function FairnessView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const o = outputsOf(sel);
  const b = o?.fairness_battery ?? null;
  const title: BiText = { en: 'Labelled fairness battery', es: 'Batería de equidad etiquetada' };
  if (!o || !b) {
    return (
      <ViewsRow>
        <PlotCard fill title={title} {...card}>
          <p className="caos-pending" data-state="unavailable">
            {pick({ en: 'Not available: this variant carries no fairness battery; it runs on the variants that fit the Taiwan model.', es: 'No disponible: esta variante no trae batería de equidad; corre en las variantes que ajustan el modelo de Taiwán.' }, lang)}
          </p>
        </PlotCard>
      </ViewsRow>
    );
  }
  const test = FAIR_TESTS.includes(sel.test as (typeof FAIR_TESTS)[number]) ? sel.test : FAIR_TESTS[0];
  const rows = b.rows.filter((r) => r.test_id === test);
  const focus = b.rows.find((r) => r.test_id === test && r.attribute === sel.attribute) ?? rows[0] ?? null;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `${title.en}: ${testName(test).en}`, es: `${title.es}: ${testName(test).es}` }}
        {...card}
        note={{
          en: 'The gap is the largest difference between the groups of the protected attribute on the Taiwan card-default model, which has outcomes. It is labelled evidence, not a compliance statement; the lights are a convention of Contraste.',
          es: 'La brecha es la mayor diferencia entre los grupos del atributo protegido en el modelo de incumplimiento de tarjetas de Taiwán, que tiene resultados. Es evidencia etiquetada, no una declaración de cumplimiento; las luces son una convención de Contraste.',
        }}
      >
        <LabelledOverTable
          head={<Labelled label={b.label} reason={b.notice} />}
          chartMin={barMin(rows.length)}
          chart={
            <BarChart
              title={{ en: 'Gap by protected attribute', es: 'Brecha por atributo protegido' }}
              height="fill"
              orientation="horizontal"
              data={rows.map((r) => ({ id: r.attribute, label: text(ATTRIBUTE_TEXT, r.attribute), value: r.value, highlight: r.attribute === focus?.attribute }))}
              axis={{ label: { en: 'Largest difference between groups', es: 'Mayor diferencia entre grupos' }, format: { decimals: 3 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="fairness-battery" data-test={test}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Attribute', es: 'Atributo' }, lang)}</th>
                <th>{pick({ en: 'Gap', es: 'Brecha' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Groups (rows, value)', es: 'Grupos (filas, valor)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.attribute} data-attribute={r.attribute} data-light={r.light} className={r.attribute === focus?.attribute ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(ATTRIBUTE_TEXT, r.attribute), lang)}</td>
                  <td data-na={r.value === null ? 'true' : undefined}>{r.value === null ? formatNumber(null, lang) : f3(r.value, lang)}</td>
                  <td className={`ct-text ct-light ct-light-${r.light}`}><span className="ct-light-word">{pick(LIGHT_TEXT[r.light], lang)}</span></td>
                  <td className="ct-text">{r.groups.map((g) => `${es(g.group, lang)} (${int(g.n, lang)}, ${g.value === null ? formatNumber(null, lang) : f3(g.value, lang)})`).join('; ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <SgcdNotice sel={sel} />
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The Impact view: the share of decisions that flip at the stated cut-off under each shift. */
/** The name of a shift of the decision-flip view: the shipped shocks of the German data and Contraste's own application of each family. */
export function shiftName(id: string): BiText {
  const m = /^(shipped|applied)-(F\d|numeric-noise)$/.exec(id);
  if (!m) return { en: id, es: id };
  // a family of shocks without a code is named by its words (the raw-id scan: applied-numeric-noise)
  if (m[2] === 'numeric-noise') return m[1] === 'shipped' ? { en: 'Shipped, numeric noise', es: 'Provisto, ruido numérico' } : { en: 'Applied by Contraste, numeric noise', es: 'Aplicado por Contraste, ruido numérico' };
  return m[1] === 'shipped' ? { en: `Shipped, ${m[2]}`, es: `Provisto, ${m[2]}` } : { en: `Applied by Contraste, ${m[2]}`, es: `Aplicado por Contraste, ${m[2]}` };
}

export function DecisionFlipView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const o = outputsOf(sel);
  if (!o) return <Pending />;
  const d = o.impact_detail;
  const param = (o.parameters as unknown as NamedParam[]).find((p) => p.name === 'decision_cutoff_reject_share');
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Decisions that flip under each shift', es: 'Decisiones que cambian bajo cada cambio' }}
        {...card}
        note={{
          en: `The cut-off declines the worst ${pc1(d.cutoff.reject_share, 'en')} of the baseline scores and is held fixed under every shift (a convention); a decision flips when a record crosses it.`,
          es: `El corte rechaza el peor ${pc1(d.cutoff.reject_share, 'es')} de los puntajes base y se mantiene fijo bajo todo cambio (una convención); una decisión cambia cuando un registro lo cruza.`,
        }}
      >
        <LabelledOverTable
          head={<Labelled label={d.label} reason={{ en: 'The decision-rate effect at a stated cut-off.', es: 'El efecto en la tasa de decisiones en un corte declarado.' }} />}
          chartMin={barMin(d.rows.length)}
          chart={
            d.rows.length === 0 ? (
              <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: the document carries no shift row.', es: 'No disponible: el documento no trae ninguna fila de cambio.' }, lang)}</p>
            ) : (
              <BarChart
                title={{ en: 'Share of decisions that flip', es: 'Parte de las decisiones que cambian' }}
                height="fill"
                orientation="horizontal"
                data={d.rows.map((r) => ({ id: r.shift_id, label: shiftName(r.shift_id), value: r.flip_share, tone: 'warn' as const }))}
                axis={{ label: { en: 'Decisions that flip', es: 'Decisiones que cambian' }, format: { percent: true, decimals: 2 } }}
              />
            )
          }
        >
          <table className="caos-table ct-wrap-head" data-table="decision-flip">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Shift', es: 'Cambio' }, lang)}</th>
                <th>{pick({ en: 'Decisions', es: 'Decisiones' }, lang)}</th>
                <th>{pick({ en: 'Flip', es: 'Cambian' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {d.rows.map((r) => (
                <tr key={r.shift_id} data-shift={r.shift_id}>
                  <td className="ct-text">{pick(shiftName(r.shift_id), lang)}</td>
                  <td>{int(r.n_decisions, lang)}</td>
                  <td>{pc1(r.flip_share, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note" data-cutoff={d.cutoff.rule} data-status={d.cutoff.label}>
            {pick({ en: `Cut-off rule (convention): decline ${pc1(d.cutoff.reject_share, 'en')} of the baseline decisions.`, es: `Regla del corte (convención): rechazar ${pc1(d.cutoff.reject_share, 'es')} de las decisiones base.` }, lang)}
            {param ? ` ${es(param.basis, lang)}` : ''}
          </p>
          <SgcdNotice sel={sel} />
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
