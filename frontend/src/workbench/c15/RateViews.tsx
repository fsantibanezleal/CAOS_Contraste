// C15's Rate and indexation group: the delta NII of Annex 1 as two parts kept apart, the rate result (the larger of the
// two parallel shocks of the pair, with the CLP and CLF offset) and the standardised indexation charge (2.5 percent of
// the absolute net UF position), and the indexation charge and the CPI-surprise scenario derived from the net UF position.
// The charge is never folded into the rate result: the chart, the parts table and the sentence all show them apart.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { ChartOverTable } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { SHOCK_TEXT, ORIGIN_TEXT, axisOf, documentOffset, moneyDoc, outputsOf, scaleUnit, text, worst, type C15Sel } from './selection';
import { IrrbbTestsTable } from '../c14/C14Common';
import { localise } from '../c14/localise';
import { FORMULA_RULES } from './localise';

const cell = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });
const SHARE = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { percent: true, decimals: 2 });

/** Delta NII under the two parallel shocks of 300 bp, the legs apart, the pair without and with the offset, and the measure as the rate result plus the charge. */
export function NiiView({ sel }: { sel: C15Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const n = o.nii;
  const doc = moneyDoc(o);
  const unit = pick(scaleUnit(doc), lang);
  const rate = worst(n.rows, (r) => r.pair, sel.offset);
  const sameAsDocument = sel.offset === documentOffset(o);
  const axis = axisOf(doc, [rate, n.indexation_charge, n.delta_nii]);
  const bars = [
    { id: 'rate', label: { en: 'Rate result', es: 'Resultado de tasa' }, value: rate / axis.div, tone: 'accent' as const },
    { id: 'indexation', label: { en: 'Indexation charge', es: 'Cargo por reajustabilidad' }, value: n.indexation_charge / axis.div, tone: 'warn' as const },
    { id: 'total', label: { en: 'Delta NII', es: 'Delta NII' }, value: sameAsDocument ? n.delta_nii / axis.div : null, tone: 'bad' as const },
  ];
  const sizes = o.nii_shock_sizes.map((z) => `${z.currency} ${z.parallel_bp} ${pick({ en: 'bp', es: 'pb' }, lang)} (${pick(text(ORIGIN_TEXT, z.origin), lang)})`).join('; ');
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Delta NII: the rate result and the indexation charge', es: 'Delta NII: el resultado de tasa y el cargo por reajustabilidad' }}
        {...card}
        note={{
          en: `${o.sign_convention.statement.en} Annex 1 takes the larger of the two parallel shocks of the pair and adds the standardised indexation (reajustabilidad) charge; the two are kept apart here. Sizes: ${sizes}.`,
          es: `${o.sign_convention.statement.es} El Anexo 1 toma el mayor de los dos choques paralelos del par y suma el cargo estándar por reajustabilidad; aquí se mantienen aparte. Tamaños: ${sizes}.`,
        }}
      >
        <ChartOverTable
          chartMin="11rem"
          chart={
            <BarChart
              title={{ en: 'The parts of delta NII', es: 'Las partes del delta NII' }}
              height="fill"
              orientation="horizontal"
              data={bars}
              axis={{ label: { en: 'Delta NII, positive is a loss', es: 'Delta NII, positivo es una pérdida' }, unit: axis.unit, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="nii-parts" data-offset={sel.offset}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Part', es: 'Parte' }, lang)}</th>
                <th>{pick({ en: `Amount (${unit})`, es: `Monto (${unit})` }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'What it is', es: 'Qué es' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              <tr data-part="rate">
                <td className="ct-text">{pick({ en: 'Rate result', es: 'Resultado de tasa' }, lang)}</td>
                <td>{cell(rate, lang)}</td>
                <td className="ct-text ct-wide-only">{pick({ en: 'The larger of the two parallel shocks of the pair, under the offset chosen.', es: 'El mayor de los dos choques paralelos del par, con la compensación elegida.' }, lang)}</td>
              </tr>
              <tr data-part="indexation">
                <td className="ct-text">{pick({ en: 'Indexation charge', es: 'Cargo por reajustabilidad' }, lang)}</td>
                <td>{cell(n.indexation_charge, lang)}</td>
                <td className="ct-text ct-wide-only">{pick({ en: '2.5 percent of the absolute net UF position.', es: '2,5 por ciento de la posición neta en UF en valor absoluto.' }, lang)}</td>
              </tr>
              <tr data-part="total" data-na={sameAsDocument ? undefined : 'true'}>
                <td className="ct-text">{pick({ en: 'Delta NII', es: 'Delta NII' }, lang)}</td>
                <td>{sameAsDocument ? cell(n.delta_nii, lang) : formatNumber(null, lang)}</td>
                <td className="ct-text ct-wide-only">
                  {sameAsDocument
                    ? `${pick({ en: 'The rate result plus the charge', es: 'El resultado de tasa más el cargo' }, lang)}; ${SHARE(n.delta_nii_share_tier1, lang)} ${pick({ en: 'of Tier 1', es: 'del capital N1' }, lang)}.`
                    : pick({ en: 'The document gives the total under its own offset state only.', es: 'El documento da el total solo con su propio estado de compensación.' }, lang)}
                </td>
              </tr>
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="nii-by-shock">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Parallel shock', es: 'Choque paralelo' }, lang)}</th>
                <th data-leg="CLP">{pick({ en: `CLP leg (${unit})`, es: `Tramo CLP (${unit})` }, lang)}</th>
                <th data-leg="UR">{pick({ en: `UF (UR) leg (${unit})`, es: `Tramo UF (UR) (${unit})` }, lang)}</th>
                <th>{pick({ en: 'No offset', es: 'Sin compensación' }, lang)}</th>
                <th>{pick({ en: 'With offset', es: 'Con compensación' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {n.rows.map((r) => (
                <tr key={r.shock} data-shock={r.shock} data-opposite={r.pair.opposite_signs} className={r.shock === sel.shock ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(SHOCK_TEXT, r.shock), lang)}</td>
                  <td>{cell(r.clp.delta_nii, lang)}</td>
                  <td>{cell(r.ur.delta_nii, lang)}</td>
                  <td>{cell(r.pair.without_offset, lang)}</td>
                  <td>{cell(r.pair.with_offset, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <IrrbbTestsTable variant={sel.data.variant} only={(t) => t.test_id === 'irrbb.cmf_annex1_goldens'} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The indexation charge from the net UF position, beside the rate result, and the CPI-surprise scenario when the variant carries one. */
export function IndexationView({ sel }: { sel: C15Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const c = o.indexation_charge;
  const s = o.cpi_scenario;
  const doc = moneyDoc(o);
  const unit = pick(scaleUnit(doc), lang);
  const axis = axisOf(doc, [c.charge, s?.effect ?? 0, o.nii.max_pair]);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The indexation charge and the CPI surprise', es: 'El cargo por reajustabilidad y la sorpresa de IPC' }}
        {...card}
        note={{
          en: 'A book indexed to the UF carries inflation risk that a parallel rate shock does not capture. Annex 1 charges 2.5 percent of the absolute net UF position, an implied inflation surprise. The CPI scenario, when the variant has one, applies a stated surprise to the same position: a negative effect is a gain.',
          es: 'Un libro indexado a la UF lleva un riesgo de inflación que un choque paralelo de tasas no captura. El Anexo 1 cobra el 2,5 por ciento de la posición neta en UF en valor absoluto, una sorpresa de inflación implícita. El escenario de IPC, cuando la variante lo trae, aplica una sorpresa declarada sobre la misma posición: un efecto negativo es una ganancia.',
        }}
      >
        <ChartOverTable
          chartMin="11rem"
          chart={
            <BarChart
              title={{ en: 'Indexation charge, CPI effect and rate result', es: 'Cargo por reajustabilidad, efecto del IPC y resultado de tasa' }}
              height="fill"
              orientation="horizontal"
              data={[
                { id: 'rate', label: { en: 'Rate result', es: 'Resultado de tasa' }, value: o.nii.max_pair / axis.div, tone: 'accent' as const },
                { id: 'charge', label: { en: 'Standard charge', es: 'Cargo estándar' }, value: c.charge / axis.div, tone: 'warn' as const },
                { id: 'cpi', label: { en: 'CPI surprise effect', es: 'Efecto de la sorpresa de IPC' }, value: s ? s.effect / axis.div : null, tone: s && s.effect > 0 ? ('bad' as const) : ('good' as const) },
              ]}
              axis={{ label: { en: 'Loss, positive is a loss', es: 'Pérdida, positivo es una pérdida' }, unit: axis.unit, format: { digits: 4 } }}
            />
          }
        >
          <dl className="ct-defs" data-table="indexation">
            <dt>{pick({ en: `Net UF position (${pick(scaleUnit({ ...moneyDoc(o), currency: 'UF' }), 'en')})`, es: `Posición neta en UF (${pick(scaleUnit({ ...moneyDoc(o), currency: 'UF' }), 'es')})` }, lang)}</dt>
            <dd>{formatNumber(c.net_position_uf_units, lang, { digits: 4 })}</dd>
            <dt>{pick({ en: 'Value of one UF (CLP)', es: 'Valor de una UF (CLP)' }, lang)}</dt>
            <dd>{formatNumber(o.ur_currency.uf_value, lang, { decimals: 0 })}</dd>
            <dt>{pick({ en: `Net UF position in CLP (${unit})`, es: `Posición neta en UF en CLP (${unit})` }, lang)}</dt>
            <dd>{cell(c.pn_ur, lang)}</dd>
            <dt>{pick({ en: `Absolute position (${unit})`, es: `Posición en valor absoluto (${unit})` }, lang)}</dt>
            <dd>{cell(c.abs_pn_ur, lang)}</dd>
            <dt>{pick({ en: 'Rate of the charge', es: 'Tasa del cargo' }, lang)}</dt>
            <dd>{SHARE(c.rate, lang)}</dd>
            <dt>{pick({ en: `Indexation charge (${unit})`, es: `Cargo por reajustabilidad (${unit})` }, lang)}</dt>
            <dd>{cell(c.charge, lang)}</dd>
            <dt>{pick({ en: 'Formula', es: 'Fórmula' }, lang)}</dt>
            <dd translate="no">{localise(c.formula, lang, FORMULA_RULES)}</dd>
            <dt>{pick({ en: 'In words', es: 'En palabras' }, lang)}</dt>
            <dd>{pick(c.note, lang)}</dd>
            <dt>{pick({ en: `Rate result of delta NII (${unit})`, es: `Resultado de tasa del delta NII (${unit})` }, lang)}</dt>
            <dd>{cell(o.nii.max_pair, lang)}</dd>
            <dt>{pick({ en: `Delta NII with the charge (${unit})`, es: `Delta NII con el cargo (${unit})` }, lang)}</dt>
            <dd>{cell(o.nii.delta_nii, lang)}</dd>
          </dl>
          {s ? (
            <dl className="ct-defs" data-table="cpi-scenario" data-cpi="present">
              <dt>{pick({ en: 'CPI surprise (percentage points)', es: 'Sorpresa de IPC (puntos porcentuales)' }, lang)}</dt>
              <dd>{formatNumber(s.surprise_pp, lang, { digits: 4 })}</dd>
              <dt>{pick({ en: `Effect (${unit}); positive is a loss`, es: `Efecto (${unit}); positivo es una pérdida` }, lang)}</dt>
              <dd>{cell(s.effect, lang)}</dd>
              <dt>{pick({ en: 'Formula', es: 'Fórmula' }, lang)}</dt>
              <dd translate="no">{localise(s.formula, lang, FORMULA_RULES)}</dd>
            </dl>
          ) : (
            <p className="ct-note" data-table="cpi-scenario" data-cpi="absent" data-na="true" data-state="unavailable">
              {`${formatNumber(null, lang)}: ${pick({ en: 'this variant carries no CPI surprise scenario; only the standardised charge applies.', es: 'esta variante no trae un escenario de sorpresa de IPC; solo rige el cargo estándar.' }, lang)}`}
            </p>
          )}
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
