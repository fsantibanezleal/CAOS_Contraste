// C15's Findings, Variants and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every section shows a
// value that moves with its controls). The Findings card and the fixture notice are the ones C06 and C07 use. C15 stays
// on its fixtures until the BCCh account exists (owner prerequisite 7); the labels say what the document says it is: a
// synthetic Banco Andino calibrated to CMF aggregates, BCCh curves fitted by Contraste (an adaptation, BCCh terms).
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { LiveReadout, useCard, type Bi } from '../c03/U6Shared';
import { SOURCE_KIND_TEXT } from '../c14/selection';
import { assumptionValue } from '../c14/C14Common';
import {
  LEG_TEXT, ORIGIN_TEXT, SHOCK_TEXT, BASKET_TEXT, OFFSET_TEXT, amount, axisOf, eveRowOf, fitOf, legOf, moneyDoc, outputsOf, pairTotal, scaleUnit, text, worst,
  type C15Outputs, type C15Sel,
} from './selection';
import { localise } from '../c14/localise';
import { C15_SOURCE_RULES } from './localise';

const NA: BiText = { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') };
const SHARE = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { percent: true, decimals: 2 });
const cell = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

export function C15FindingsView({ sel }: { sel: C15Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

/** The SDD variants side by side: the Annex 1 delta EVE, the rate result of delta NII and the indexation charge apart, and the prioritised-bank flag. Pick one to load it. */
export function C15VariantsTable({ variants, onPick, current }: { variants: Array<{ id: string; title: BiText; v: VariantArtifact<C15Outputs> }>; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const first = variants[0]?.v;
  const card = useCard(first as unknown as VariantArtifact | undefined);
  const doc = first ? moneyDoc(first.outputs) : null;
  const axis = doc ? axisOf(doc, variants.map((e) => e.v.outputs.nii.delta_nii)) : { div: 1, unit: { en: '', es: '' } as BiText };
  const unit = doc ? pick(scaleUnit(doc), lang) : '';
  return (
    <PlotCard
      fill
      title={{ en: 'The variants of the case', es: 'Las variantes del caso' }}
      {...card}
      note={{
        en: 'Each variant is one document of the SDD: a long or short UF book, a CPI surprise, a CLP steepener, the offset on and off, and floors that bind. The bars are the delta NII with the indexation charge; the table keeps the rate result and the charge apart. Pick a variant to load it.',
        es: 'Cada variante es un documento del SDD: un libro largo o corto en UF, una sorpresa de IPC, un empinamiento en CLP, la compensación activa e inactiva, y pisos que rigen. Las barras son el delta NII con el cargo por reajustabilidad; la tabla mantiene aparte el resultado de tasa y el cargo. Elija una variante para cargarla.',
      }}
    >
      <ChartOverTable
        chart={
          <BarChart
            title={{ en: 'Delta NII with the indexation charge, by variant', es: 'Delta NII con el cargo por reajustabilidad, por variante' }}
            height="fill"
            orientation="vertical"
            data={variants.map(({ id, title, v }) => ({ id, label: title, value: v.outputs.nii.delta_nii / axis.div, tone: 'accent' as const, highlight: id === current }))}
            axis={{ label: { en: 'Delta NII, positive is a loss', es: 'Delta NII, positivo es una pérdida' }, unit: axis.unit, format: { digits: 4 } }}
          />
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c15">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
              <th>{pick({ en: `Delta EVE (${unit})`, es: `Delta EVE (${unit})` }, lang)}</th>
              <th>{pick({ en: `Rate result of delta NII (${unit})`, es: `Resultado de tasa del delta NII (${unit})` }, lang)}</th>
              <th>{pick({ en: `Indexation charge (${unit})`, es: `Cargo por reajustabilidad (${unit})` }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Prioritised bank', es: 'Banco priorizado' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(({ id, title, v }) => (
              <tr key={id} data-variant={id} className={id === current ? 'ct-current' : undefined}>
                <td className="ct-text">
                  <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                </td>
                <td>{cell(v.outputs.eve.delta_eve, lang)}</td>
                <td>{cell(v.outputs.nii.max_pair, lang)}</td>
                <td>{cell(v.outputs.nii.indexation_charge, lang)}</td>
                <td className="ct-text" data-prioritised={v.outputs.thresholds.prioritised}>{pick(v.outputs.thresholds.prioritised ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </ChartOverTable>
    </PlotCard>
  );
}

export function C15VariantsView({ sel, onPick }: { sel: C15Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C15Outputs>>)
    .filter((v) => v.outputs.kind === 'annex1-variant')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? v.outputs.variant.label, v }));
  return (
    <ViewsRow>
      <C15VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

const ASSUMPTION_TEXT: Record<string, Bi> = {
  nmd_core_share: { en: 'Core share of non-maturity deposits', es: 'Parte estable de los depósitos sin vencimiento' },
  nmd_core_maturity_years: { en: 'Core maturity of non-maturity deposits', es: 'Plazo de la parte estable de los depósitos sin vencimiento' },
  prepayment_cpr: { en: 'Prepayment rate (CPR)', es: 'Tasa de prepago (CPR)' },
  term_deposit_redemption_rate: { en: 'Early redemption of term deposits', es: 'Rescate anticipado de depósitos a plazo' },
  deposit_beta: { en: 'Deposit beta', es: 'Beta de depósitos' },
};
const PARAMETER_TEXT: Record<string, Bi> = {
  net_uf_position: { en: 'Net UF position', es: 'Posición neta en UF' },
  surprise_pp: { en: 'CPI surprise', es: 'Sorpresa de IPC' },
  net_uf_share_tier1: { en: 'Net UF position, share of Tier 1', es: 'Posición neta en UF, parte del capital de nivel 1' },
  ur_floating_share: { en: 'Floating share of the UF commercial loans', es: 'Parte flotante de los préstamos comerciales en UF' },
  clp_long_asset_share: { en: 'Long share of the CLP fixed commercial loans and securities', es: 'Parte larga de los préstamos comerciales fijos en CLP y los valores' },
  clp_bond_years_scale: { en: 'Scale of the CLP bond maturities', es: 'Escala de los plazos de los bonos en CLP' },
};
const CATEGORY_TEXT: Record<string, Bi> = {
  'retail-operational': { en: 'Retail operational', es: 'Minorista operacional' },
  'retail-non-operational': { en: 'Retail non-operational', es: 'Minorista no operacional' },
  wholesale: { en: 'Wholesale', es: 'Mayorista' },
};

/** A unit of the documents in words in the page language: "millions CLF" is "millones de CLF". */
export function unitText(unit: string, lang: 'en' | 'es'): string {
  if (lang === 'es') {
    const words: Record<string, string> = {
      'share of Tier 1': 'parte del capital de nivel 1',
      'share of the UF commercial loans': 'parte de los préstamos comerciales en UF',
      'share of the CLP fixed commercial loans and securities': 'parte de los préstamos comerciales fijos en CLP y los valores',
      'factor on the maturity': 'factor sobre el plazo',
      'share of the term deposit': 'parte del depósito a plazo',
      'per square-root year': 'por raíz cuadrada del año',
      'share of |PN_UR|': 'parte de |PN_UR|',
    };
    return words[unit] ?? unit.replace(/^millions /, 'millones de ').replace('percentage points', 'puntos porcentuales').replace(/^per year$/, 'por año').replace(/^years$/, 'años');
  }
  return unit;
}

/** The case, the synthetic bank, the UR currency and the UF, the curves as an adaptation, the Annex 1 sizes, and the behavioural assumptions. */
export function C15ContextView({ sel }: { sel: C15Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const fit = fitOf(sel);
  const unit = pick(scaleUnit(moneyDoc(o)), lang);
  const sizeRows = o.eve_shock_sizes;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c15-bank">
          <dt>{pick({ en: 'Bank', es: 'Banco' }, lang)}</dt>
          <dd data-synthetic={o.bank.synthetic}>{pick({ en: `${o.bank.name}: synthetic, calibrated to CMF aggregates`, es: `${o.bank.name}: sintético, calibrado a agregados de la CMF` }, lang)}</dd>
          <dt>{pick({ en: 'Notice of the document', es: 'Aviso del documento' }, lang)}</dt>
          <dd>{pick(o.bank.notice, lang)}</dd>
          <dt>{pick({ en: 'Calibration source and seed', es: 'Fuente de la calibración y semilla' }, lang)}</dt>
          <dd>{`${localise(o.bank.calibration_source, lang, C15_SOURCE_RULES)} (${o.bank.seed})`}</dd>
          <dt>{pick({ en: 'Variant', es: 'Variante' }, lang)}</dt>
          <dd data-variant-id={o.variant.id}>{`${pick(o.variant.label, lang)}. ${pick(o.variant.description, lang)}`}</dd>
          {o.variant.parameters.map((p) => (
            <ParamRow key={p.name} name={p.name} value={p.value} unit={p.unit} />
          ))}
          <dt>{pick({ en: 'Balance sheet and curves', es: 'Balance y curvas' }, lang)}</dt>
          <dd>{pick({ en: `balance sheet of ${o.balance_sheet_month}, curves of ${o.curves_month}, as of ${o.as_of}`, es: `balance de ${o.balance_sheet_month}, curvas de ${o.curves_month}, al ${o.as_of}` }, lang)}</dd>
          <dt>{pick({ en: 'Sign convention', es: 'Convención de signo' }, lang)}</dt>
          <dd>{pick(o.sign_convention.statement, lang)}</dd>
          <dt>{pick({ en: 'Money', es: 'Dinero' }, lang)}</dt>
          <dd>{unit}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The UR currency and the UF', es: 'La moneda UR y la UF' }} {...card} note={{ en: 'Annex 1 treats every UF-indexed flow as one currency, UR. The UR leg is in CLF and is converted to CLP at the UF value of the date.', es: 'El Anexo 1 trata todo flujo reajustable en UF como una sola moneda, UR. El tramo UR está en CLF y se convierte a CLP al valor de la UF de la fecha.' }}>
        <dl className="ct-defs" data-table="c15-ur">
          <dt>{pick({ en: 'Definition', es: 'Definición' }, lang)}</dt>
          <dd>{pick(o.ur_currency.definition, lang)}</dd>
          <dt>{pick({ en: 'Value of one UF (CLP)', es: 'Valor de una UF (CLP)' }, lang)}</dt>
          <dd>{formatNumber(o.ur_currency.uf_value, lang, { decimals: 0 })}</dd>
          <dt>{pick({ en: 'UF date', es: 'Fecha de la UF' }, lang)}</dt>
          <dd>{o.ur_currency.uf_date}</dd>
          <dt>{pick({ en: 'UF source', es: 'Fuente de la UF' }, lang)}</dt>
          <dd>{localise(o.ur_currency.uf_source, lang, C15_SOURCE_RULES)}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The curves', es: 'Las curvas' }} {...card} note={{ en: 'The sovereign yields are the Banco Central de Chile\'s; the fitted zero curve is an adaptation by Contraste, under the BCCh terms of use.', es: 'Los rendimientos soberanos son del Banco Central de Chile; la curva cero ajustada es una adaptación de Contraste, bajo los términos de uso del BCCh.' }}>
        <dl className="ct-defs" data-table="c15-curves">
          {[o.curves.clp, o.curves.ur].map((c) => (
            <CurveRows key={c.curve} curve={c} />
          ))}
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The Annex 1 shock sizes', es: 'Los tamaños de choque del Anexo 1' }} {...card} note={{ en: 'A tabled size is exactly the table\'s. A size that is a Contraste estimate carries its label and its method and is never shown as a regulatory parameter.', es: 'Un tamaño tabulado es exactamente el de la tabla. Un tamaño que es una estimación de Contraste lleva su etiqueta y su método y nunca se muestra como parámetro regulatorio.' }}>
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="c15-sizes">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Currency', es: 'Moneda' }, lang)}</th>
                <th>{pick({ en: 'Parallel', es: 'Paralelo' }, lang)}</th>
                <th>{pick({ en: 'Short rates', es: 'Tasas cortas' }, lang)}</th>
                <th>{pick({ en: 'Long rates', es: 'Tasas largas' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Origin', es: 'Origen' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {sizeRows.map((z) => (
                <tr key={z.currency} data-size-currency={z.currency} data-origin={z.origin}>
                  <td className="ct-text">{z.currency}</td>
                  <td>{`${z.parallel_bp} ${pick({ en: 'bp', es: 'pb' }, lang)}`}</td>
                  <td>{`${z.short_bp} ${pick({ en: 'bp', es: 'pb' }, lang)}`}</td>
                  <td>{`${z.long_bp} ${pick({ en: 'bp', es: 'pb' }, lang)}`}</td>
                  <td className="ct-text">
                    {pick(text(ORIGIN_TEXT, z.origin), lang)}
                    {z.origin === 'contraste-estimate' && z.label ? <span className="ct-note" style={{ display: 'block', whiteSpace: 'normal' }}>{`${pick(z.label, lang)}${z.method ? ` (${z.method})` : ''}`}</span> : null}
                  </td>
                </tr>
              ))}
              {o.nii_shock_sizes.map((z) => (
                <tr key={`nii-${z.currency}`} data-nii-size-currency={z.currency}>
                  <td className="ct-text">{pick({ en: `${z.currency}, delta NII`, es: `${z.currency}, delta NII` }, lang)}</td>
                  <td>{`${z.parallel_bp} ${pick({ en: 'bp', es: 'pb' }, lang)}`}</td>
                  <td data-na="true">{formatNumber(null, lang)}</td>
                  <td data-na="true">{formatNumber(null, lang)}</td>
                  <td className="ct-text">{pick(text(ORIGIN_TEXT, z.origin), lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {fit ? (
            <table className="caos-table ct-wrap-head" data-table="c15-annex1-table">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Annex 1 table', es: 'Tabla del Anexo 1' }, lang)}</th>
                  <th>{pick({ en: 'Parallel (bp)', es: 'Paralelo (pb)' }, lang)}</th>
                  <th>{pick({ en: 'Short (bp)', es: 'Corto (pb)' }, lang)}</th>
                  <th>{pick({ en: 'Long (bp)', es: 'Largo (pb)' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {fit.annex1_table.map((r) => (
                  <tr key={r.basket} data-basket={r.basket}>
                    <td className="ct-text">{pick(text(BASKET_TEXT, r.basket), lang)}</td>
                    <td>{r.parallel_bp}</td>
                    <td data-na={r.short_bp === null ? 'true' : undefined}>{r.short_bp ?? formatNumber(null, lang)}</td>
                    <td data-na={r.long_bp === null ? 'true' : undefined}>{r.long_bp ?? formatNumber(null, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>
      </PlotCard>
      <PlotCard title={{ en: 'The behavioural assumptions', es: 'Los supuestos conductuales' }} {...card} note={{ en: 'Each assumption names where it comes from: a regulatory cap, a fit, or a synthetic value stated here. A request above its cap is capped and shows both the request and the value used.', es: 'Cada supuesto dice de dónde viene: un tope regulatorio, un ajuste, o un valor sintético declarado aquí. Una petición sobre su tope queda con tope y muestra la petición y el valor usado.' }}>
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="c15-assumptions">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Assumption', es: 'Supuesto' }, lang)}</th>
                <th>{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Where it comes from', es: 'De dónde viene' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Source', es: 'Fuente' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {(Object.keys(o.assumptions) as Array<keyof C15Outputs['assumptions']>).map((k) => {
                const a = o.assumptions[k];
                return (
                  <tr key={k} data-assumption={k} data-source-kind={a.source_kind}>
                    <td className="ct-text">{pick(text(ASSUMPTION_TEXT, k), lang)}</td>
                    <td>{assumptionValue(a.value, a.unit, lang)}</td>
                    <td className="ct-text">{pick(text(SOURCE_KIND_TEXT, a.source_kind), lang)}</td>
                    <td className="ct-text ct-wide-only">{localise(a.source, lang, C15_SOURCE_RULES)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c15-nmd">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Deposit category', es: 'Categoría de depósitos' }, lang)}</th>
                <th>{pick({ en: 'Core share requested', es: 'Parte estable pedida' }, lang)}</th>
                <th>{pick({ en: 'Cap', es: 'Tope' }, lang)}</th>
                <th>{pick({ en: 'Used', es: 'Usada' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Cap', es: 'Tope' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.nmd_segments.map((s) => (
                <tr key={s.category} data-category={s.category} data-cap-applied={s.cap_applied}>
                  <td className="ct-text">{pick(text(CATEGORY_TEXT, s.category), lang)}</td>
                  <td>{SHARE(s.requested_core_share, lang)}</td>
                  <td>{SHARE(s.core_share_cap, lang)}</td>
                  <td>{SHARE(s.core_share_used, lang)}</td>
                  <td className="ct-text">{pick(s.cap_applied ? { en: 'capped', es: 'con tope' } : { en: 'within the cap', es: 'dentro del tope' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </div>
  );
}

function ParamRow({ name, value, unit }: { name: string; value: number; unit: string }) {
  const lang = useShellLang();
  return (
    <>
      <dt>{pick(text(PARAMETER_TEXT, name), lang)}</dt>
      <dd data-parameter={name}>{`${formatNumber(value, lang, { digits: 4 })} ${unitText(unit, lang)}`}</dd>
    </>
  );
}

function CurveRows({ curve }: { curve: C15Outputs['curves']['clp'] }) {
  const lang = useShellLang();
  const name = curve.curve === 'CLP' ? 'CLP' : 'UF (UR)';
  return (
    <>
      <dt>{pick({ en: `${name} curve`, es: `Curva ${name}` }, lang)}</dt>
      <dd data-curve={curve.curve}>{`${curve.month} (${curve.date}); ${curve.fit.model === 'svensson' ? 'Svensson' : 'Nelson-Siegel'}, ${pick({ en: 'fit error', es: 'error del ajuste' }, lang)} ${formatNumber(curve.fit.rmse_bp, lang, { digits: 4 })} ${pick({ en: 'bp', es: 'pb' }, lang)}`}</dd>
      <dt>{pick({ en: `${name} source`, es: `Fuente ${name}` }, lang)}</dt>
      <dd>{localise(curve.attribution, lang, C15_SOURCE_RULES)}</dd>
    </>
  );
}

// --- the read-outs of the rail ---------------------------------------------------------------------------------------

/** A read-out title carrying the unit of its money rows once: in the narrow rail a unit on every row wrapped the rows to two lines (ADR-0071 rule 6). */
const withUnit = (title: BiText, unit: BiText): BiText => ({ en: `${pick(title, 'en')} (${pick(unit, 'en')})`, es: `${pick(title, 'es')} (${pick(unit, 'es')})` });

/** The live read-out of the Shock section: the two legs apart and the pair without and with the offset. */
export function ShockReadout({ sel }: { sel: C15Sel | null }) {
  const o = outputsOf(sel);
  const r = eveRowOf(o, sel?.shock ?? '');
  const doc = o ? moneyDoc(o) : null;
  const money = (v: number | null | undefined) => (doc ? amount(doc, v ?? null) : { value: null, unit: NA, format: { digits: 4 } });
  const item = (label: BiText, v: number | null | undefined, hint: BiText) => {
    const a = money(v);
    return { label, value: a.value, unitless: true as const, format: a.format, hint };
  };
  const shockTitle = sel ? text(SHOCK_TEXT, sel.shock) : { en: 'The shock', es: 'El choque' };
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={doc ? withUnit({ en: 'Shock', es: 'Choque' }, money(0).unit) : shockTitle}
      items={[
        item({ en: 'CLP leg', es: 'Tramo CLP' }, r?.clp.delta_eve, { en: 'Delta EVE of the CLP leg under this shock: positive is a loss.', es: 'Delta EVE del tramo CLP bajo este choque: positivo es una pérdida.' }),
        item({ en: 'UF (UR) leg', es: 'Tramo UF (UR)' }, r?.ur.delta_eve, { en: 'Delta EVE of the UF leg, converted to CLP at the UF value.', es: 'Delta EVE del tramo UF, convertido a CLP al valor de la UF.' }),
        item({ en: 'Pair, no offset', es: 'Par, sin comp.' }, r?.pair.without_offset, { en: 'The sum of the positive parts of the two legs.', es: 'La suma de las partes positivas de los dos tramos.' }),
        item({ en: 'Pair, with offset', es: 'Par, con comp.' }, r?.pair.with_offset, { en: 'The pair after half of one leg is offset against the other, when their signs are opposite.', es: 'El par después de compensar la mitad de un tramo contra el otro, cuando sus signos son opuestos.' }),
      ]}
    />
  );
}

/** The live read-out of the Offset section: the Annex 1 measure with and without the offset and the share the rule offsets. */
export function OffsetReadout({ sel }: { sel: C15Sel | null }) {
  const o = outputsOf(sel);
  const doc = o ? moneyDoc(o) : null;
  const money = (v: number | null) => (doc ? amount(doc, v) : { value: null, unit: NA, format: { digits: 4 } });
  const on = o ? money(worst(o.eve.rows, (r) => r.pair, 'on')) : money(null);
  const off = o ? money(worst(o.eve.rows, (r) => r.pair, 'off')) : money(null);
  const state: BiText = o ? (o.offset_rule.state === 'on' ? { en: 'on', es: 'activa' } : o.offset_rule.state === 'off' ? { en: 'off', es: 'inactiva' } : { en: 'both compared', es: 'ambas comparadas' }) : NA;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={doc ? withUnit({ en: 'Offset', es: 'Compensación' }, on.unit) : sel ? text(OFFSET_TEXT, sel.offset) : { en: 'The offset', es: 'La compensación' }}
      items={[
        { label: { en: 'Offset on', es: 'Con comp.' }, value: on.value, unitless: true, format: on.format, hint: { en: 'The largest pair total over the six shocks with the offset applied.', es: 'El mayor total del par entre los seis choques con la compensación aplicada.' } },
        { label: { en: 'Offset off', es: 'Sin comp.' }, value: off.value, unitless: true, format: off.format, hint: { en: 'The largest pair total over the six shocks with no offset.', es: 'El mayor total del par entre los seis choques sin compensación.' } },
        { label: { en: 'Share offset', es: 'Parte compensada' }, value: o?.offset_rule.share ?? null, unitless: true, format: { percent: true, decimals: 0 }, hint: { en: 'The share of one leg that the rule offsets against the other.', es: 'La parte de un tramo que la regla compensa contra el otro.' } },
        { label: { en: 'The document applies', es: 'El documento aplica' }, text: state, hint: { en: 'The state of the offset in the document\'s own measure.', es: 'El estado de la compensación en la medida propia del documento.' } },
      ]}
    />
  );
}

/** The live read-out of the Leg section: the book of the leg in focus, in the currency of the leg. */
export function LegReadout({ sel }: { sel: C15Sel | null }) {
  const o = outputsOf(sel);
  const leg = legOf(o, sel?.leg ?? '');
  const row = eveRowOf(o, sel?.shock ?? '');
  const doc = o ? moneyDoc(o) : null;
  const money = (v: number | null | undefined) => (doc && leg ? amount(doc, v ?? null, leg.currency) : { value: null, unit: NA, format: { digits: 4 } });
  const a = money(leg?.assets_total);
  const l = money(leg?.liabilities_total);
  const n = money(leg?.net_position);
  const floored = row && sel ? (sel.leg === 'CLP' ? row.clp : row.ur).floor_bound_buckets.length : null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={doc && leg ? withUnit(sel ? text(LEG_TEXT, sel.leg) : { en: 'The leg', es: 'El tramo' }, a.unit) : sel ? text(LEG_TEXT, sel.leg) : { en: 'The leg', es: 'El tramo' }}
      items={[
        { label: { en: 'Assets', es: 'Activos' }, value: a.value, unitless: true, format: a.format, hint: { en: 'The assets of the leg in its own currency (CLF for the UF leg).', es: 'Los activos del tramo en su propia moneda (CLF para el tramo UF).' } },
        { label: { en: 'Liabilities', es: 'Pasivos' }, value: l.value, unitless: true, format: l.format, hint: { en: 'The liabilities of the leg in its own currency.', es: 'Los pasivos del tramo en su propia moneda.' } },
        { label: { en: 'Net position', es: 'Posición neta' }, value: n.value, unitless: true, format: n.format, hint: { en: 'Assets minus liabilities; the net UF position drives the indexation charge.', es: 'Activos menos pasivos; la posición neta en UF determina el cargo por reajustabilidad.' } },
        { label: { en: 'Floored buckets', es: 'Tramos con piso' }, value: floored, unitless: true, format: { decimals: 0 }, hint: { en: 'How many of the 19 buckets have the post-shock floor binding for this leg under the shock chosen.', es: 'En cuántos de los 19 tramos el piso posterior al choque rige para este tramo bajo el choque elegido.' } },
      ]}
    />
  );
}

export { pairTotal };
