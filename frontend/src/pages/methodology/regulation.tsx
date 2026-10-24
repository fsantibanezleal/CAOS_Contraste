// The Methodology section on the regulation map (U9-W2): the Basel calculators that belong to no case, each as theory and as a
// live calculator on the regulatory-calculators document. Five parts, as sub-tabs of one `method` section (ADR-0017 section
// 2.1): the standardised credit risk weights of CRE20 with the LTV step charts (dossier 01, C); the output floor with the
// RBC90.1 phase-in (C.1); the sensitivities-based method of the FRTB standardised approach with its three correlation
// scenarios and the MAR21.4(5)(b) fallback (D.2, and the U9 research addendum R7 for the GIRR parameters); the
// liquidity-horizon cascade of the internal models approach (D.3); and SA-CCR and BA-CVA with the parameter tables of
// CRE52.72 and MAR50.16 and the five CRE99 worked examples (E.1, E.2). Every constant and formula is transcribed from those
// files, each read at its BIS page on 2026-10-04 or 2026-10-17 and 2026-10-18; what they mark UNVERIFIED stays marked in the
// callout. Every display equation carries a caption that defines its symbols. Each calculator is a TypeScript port
// (engine/regulatory.ts) held to the document at 1e-9 relative by engine/regulatory.test.ts; every parameter it shows
// carries its paragraph and the in-force date of the chapter (dossier 01, M.3 item 8). The registry mounts the section as
// one tab of the `capital` group; one file exports one section, with one honest callout for the topic.
import {
  BarChart,
  Callout,
  ChipGroup,
  Cite,
  DocSection,
  Equation,
  Figure,
  Knob,
  PlotCard,
  SubTabs,
  formatNumber,
  pick,
  useShellLang,
  type BiText,
  type ChipOption,
  type Tone,
} from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useState, type ReactNode } from 'react';
import { ArtifactUnavailable, getJSON, useArtifact } from '../../api/artifacts';
import { P, Ref, T, useT } from '../../content/bi';
import {
  SCENARIOS,
  adjustForCurrencyMismatch,
  cascadeTerms,
  creditEquivalentRwa,
  entryById,
  findCell,
  floorBreakdown,
  gridRows,
  liquidityCascadeEs,
  ltvRow,
  ltvSteps,
  matrixOf,
  numberOf,
  parameterTable,
  phaseInRow,
  sbmAggregate,
  scenarioRho,
  subsetMembership,
  vectorOf,
  type ExposureClass,
  type GridRow,
  type ParameterTable,
  type RegulatoryDoc,
  type RegulatoryEntry,
  type Scenario,
} from '../../engine/regulatory';
import { loadReadiness, unavailableRow } from '../../readiness/readiness';
import { RailSelect } from '../../workbench/c06/RailSelect';
import { Pending, Unavailable } from '../../workbench/Pending';
import type { MethodologySection } from '../methodologyRegistry';

// ---------------------------------------------------------------------------------------------------------------------
// the document: loaded once, or declared absent with its reason (a missing artifact is a state, never an empty chart)

const PATH = 'regulatory/calculators.json';

/** A reason in both languages, the shape every "not available" state carries. */
type Reason = { en: string; es: string };

const NOT_PUBLISHED: Reason = {
  en: 'Not available yet: the regulatory calculators document (regulatory/calculators.json) has not been written by the regulatory bake, so the live calculators wait for it. The theory above does not depend on it.',
  es: 'Aún no disponible: el proceso que hornea las calculadoras regulatorias no ha escrito su documento (regulatory/calculators.json), así que las calculadoras en vivo lo esperan. La teoría no depende de él.',
};

const LOADING: Reason = { en: 'Loading the regulatory calculators', es: 'Cargando las calculadoras regulatorias' };

let cached: Promise<RegulatoryDoc> | null = null;

/** The document, fetched once per page load; the readiness document may declare it absent first. */
function loadRegulatory(): Promise<RegulatoryDoc> {
  if (!cached) {
    cached = (async () => {
      const row = unavailableRow(await loadReadiness(), PATH);
      if (row) throw new ArtifactUnavailable(PATH, row.reason ?? NOT_PUBLISHED);
      return getJSON<RegulatoryDoc>(PATH);
    })();
    cached.catch(() => {
      cached = null;
    });
  }
  return cached;
}

/** A document undefined while it loads, null when it is absent (with the reason a reader can read). */
interface DocProps {
  doc: RegulatoryDoc | null | undefined;
  reason?: Reason;
}

/** True when the document says it stands on a fixture: its inputs carry the class `fixture` (a contract example, not a bake). */
function isFixture(doc: RegulatoryDoc): boolean {
  return doc.provenance.inputs.some((i) => i.class === 'fixture');
}

/** The notice of a document that is a fixture: said once at the top of a part, never as a callout (the topic has exactly one). */
function FixtureNote({ doc }: { doc: RegulatoryDoc | null | undefined }) {
  const t = useT();
  if (!doc || !isFixture(doc)) return null;
  return (
    <p className="ct-note" data-fixture="true">
      {t(
        'The numbers of the calculators below are read from the contract fixture of the regulatory-calculators document: the published values of the framework, recomputed by the engine, standing in until the regulatory bake writes the document. They are not a measurement of any bank.',
        'Los números de las calculadoras de abajo se leen del ejemplo de contrato del documento de calculadoras regulatorias: los valores publicados del marco, recalculados por el motor, que lo reemplazan hasta que el proceso regulatorio escriba el documento. No son una medición de ningún banco.',
      )}
    </p>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// the words of the tables: the document's keys in words, never an internal id in a title or a control

const bi = (en: string, es: string): BiText => ({ en, es });

const CLASS_TEXT: Record<string, BiText> = {
  sovereign: bi('Sovereigns and central banks', 'Soberanos y bancos centrales'),
  eca: bi('Sovereigns by export credit agency score', 'Soberanos por puntaje de agencia de crédito a la exportación'),
  'bank-ecra': bi('Banks, external ratings (ECRA)', 'Bancos, calificaciones externas (ECRA)'),
  'bank-scra': bi('Banks, standardised assessment (SCRA)', 'Bancos, evaluación estandarizada (SCRA)'),
  corporate: bi('Corporates', 'Empresas'),
  retail: bi('Retail', 'Minorista'),
  equity: bi('Equity and subordinated debt', 'Acciones y deuda subordinada'),
  'residential-re': bi('Residential real estate', 'Inmuebles residenciales'),
  'commercial-re': bi('Commercial real estate', 'Inmuebles comerciales'),
  defaulted: bi('Defaulted exposures', 'Exposiciones en incumplimiento'),
};

const CLASS_ORDER = Object.keys(CLASS_TEXT) as ExposureClass[];

const KEY_TEXT: Record<string, BiText> = {
  unrated: bi('Unrated', 'Sin calificación'),
  'investment-grade-unrated': bi('Investment grade where ratings are not allowed', 'Grado de inversión donde no se permiten calificaciones'),
  'sme-unrated': bi('Unrated SME', 'Pyme sin calificación'),
  'regulatory-retail-sme': bi('Regulatory retail SME', 'Pyme minorista regulatoria'),
  regulatory: bi('Regulatory retail', 'Minorista regulatorio'),
  transactor: bi('Transactors', 'Transactores'),
  other: bi('Other retail', 'Otro minorista'),
  equity: bi('Equity', 'Acciones'),
  'speculative-unlisted': bi('Speculative unlisted equity', 'Acciones especulativas no listadas'),
  'legislated-programme': bi('Legislated programmes', 'Programas legislados'),
  'subordinated-debt': bi('Subordinated debt and capital instruments', 'Deuda subordinada e instrumentos de capital'),
  'provision-below-20pct': bi('Specific provisions below 20 %', 'Provisiones específicas bajo 20 %'),
  'provision-at-least-20pct': bi('Specific provisions of 20 % or more', 'Provisiones específicas de 20 % o más'),
  'residential-non-cash-flow-dependent': bi('Residential, not cash-flow dependent', 'Residencial, no dependiente de flujos de caja'),
  'direct-credit-substitute': bi('Direct credit substitutes', 'Sustitutos directos de crédito'),
  repo: bi('Repurchase agreements', 'Operaciones de recompra'),
  'securities-lending': bi('Securities lending', 'Préstamo de valores'),
  'forward-purchase': bi('Forward purchases', 'Compras a plazo'),
  'nif-ruf': bi('Note issuance and revolving underwriting facilities', 'Facilidades de emisión de pagarés y de aseguramiento rotativo'),
  'transaction-related-contingent': bi('Transaction-related contingents', 'Contingentes ligados a transacciones'),
  commitment: bi('Commitments', 'Compromisos'),
  'trade-letter-of-credit': bi('Short-term self-liquidating trade letters of credit', 'Cartas de crédito comerciales de corto plazo con autoliquidación'),
  'unconditionally-cancellable': bi('Unconditionally cancellable commitments', 'Compromisos cancelables incondicionalmente'),
};

/** A rating bucket or grade of the document in words: "AAA to AA-" reads "AAA a AA-", "below B-" reads "bajo B-". */
function ratingText(key: string, cls: string, lang: 'en' | 'es'): string | null {
  if (KEY_TEXT[key]) return pick(KEY_TEXT[key], lang);
  if (cls === 'eca') return lang === 'es' ? `Puntaje ${key}` : `Score ${key}`;
  if (cls === 'bank-scra') return lang === 'es' ? `Grado ${key}` : `Grade ${key}`;
  const range = key.match(/^(.+) to (.+)$/);
  if (range) return lang === 'es' ? `${range[1]} a ${range[2]}` : key;
  const below = key.match(/^below (.+)$/);
  if (below) return lang === 'es' ? `Bajo ${below[1]}` : key.replace(/^below/, 'Below');
  return null;
}

const humanize = (id: string) => {
  const s = id.replace(/[-_]/g, ' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
};

/** The table name in the page's language: "CRE20 Table 11" reads "CRE20 Tabla 11" in Spanish. */
const tableText = (table: string, lang: 'en' | 'es') => (lang === 'es' ? table.replace(/\bTable\b/, 'Tabla') : table);

const UNIT_TEXT: Record<string, BiText> = {
  'USD thousands': bi('USD thousands', 'miles de USD'),
  'index points': bi('index points', 'puntos índice'),
  USD: 'USD',
  days: bi('days', 'días'),
};

const unitText = (unit: string, lang: 'en' | 'es') => (UNIT_TEXT[unit] ? pick(UNIT_TEXT[unit], lang) : '');

/** The paragraphs of an entry ("CRE52.10 to CRE52.57", "MAR33.4 Table 1 and MAR33.12") with their joining words in the page's language. */
const rangeText = (text: string, lang: 'en' | 'es') => (lang === 'es' ? text.replace(/\bto\b/g, 'a').replace(/\band\b/g, 'y').replace(/\bTable\b/g, 'Tabla') : text);

/** A text of the document in both languages with the Spanish one written with decimal commas (a point between digits becomes a comma; a paragraph such as MAR21.4 is left as it is). */
const docText = (text: { en: string; es: string }): { en: string; es: string } => ({ en: text.en, es: text.es.replace(/(?<![A-Za-z\d.])(\d+)\.(\d+)/g, '$1,$2') });

// ---------------------------------------------------------------------------------------------------------------------
// a live card and its parts

/** The frame of one live calculator: loading while the document is on its way, "not available" with its reason when it is absent. */
function LiveCard({ view, title, doc, reason, note, children }: DocProps & { view: string; title: BiText; note?: BiText; children: (d: RegulatoryDoc) => ReactNode }) {
  if (doc === undefined) return <Pending label={LOADING} />;
  if (doc === null) return <Unavailable reason={reason ?? NOT_PUBLISHED} />;
  return (
    <PlotCard title={title} lane="live" provenance="published" note={note}>
      <div className="ct-context" data-view={view} data-state="ready">
        {children(doc)}
      </div>
    </PlotCard>
  );
}

/** A reason a reader can read, in both languages. */
const gap = (en: string, es: string) => <Unavailable reason={{ en, es }} />;

const YES_NO: ChipOption[] = [
  { id: 'no', label: bi('No', 'No') },
  { id: 'yes', label: bi('Yes', 'Sí') },
];

const pc = (lang: 'en' | 'es', v: number | null | undefined, decimals?: number) => formatNumber(v, lang, { percent: true, ...(decimals === undefined ? {} : { decimals }) });

/** Label and value rows of a result, as a two-column table that stacks its text at phone width; the data attributes say what it shows. */
interface FactsProps {
  rows: Array<[ReactNode, ReactNode]>;
  [attr: `data-${string}`]: string | undefined;
}

function Facts({ rows, ...attrs }: FactsProps) {
  return (
    <table className="caos-table ct-wrap-head" {...attrs}>
      <tbody>
        {rows.map(([k, v], i) => (
          <tr key={i}>
            <th scope="row" className="caos-col-text">
              {k}
            </th>
            <td className="caos-col-text">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// CRE20: the lookup, the LTV steps, the credit equivalent and the RWA

export interface Cre20Init {
  cls?: ExposureClass;
  key?: string;
  shortTerm?: boolean;
  cashFlowDependent?: boolean;
  ltv?: number;
  counterpartyWeight?: number;
  mismatch?: boolean;
  ccf?: string;
}

/** The band of a cell in words: an LTV band from its neighbours, a rating bucket or grade from the keys' words. */
function bandText(row: GridRow, steps: ReturnType<typeof ltvSteps>, lang: 'en' | 'es'): string {
  const i = steps.findIndex((s) => s.row === row);
  if (i >= 0) {
    const pct = (v: number) => pc(lang, v, 0);
    if (i === 0) return lang === 'es' ? `LTV hasta ${pct(steps[0].upTo)}` : `LTV up to ${pct(steps[0].upTo)}`;
    if (i === steps.length - 1) return lang === 'es' ? `LTV sobre ${pct(steps[i - 1].upTo)}` : `LTV above ${pct(steps[i - 1].upTo)}`;
    return lang === 'es' ? `LTV sobre ${pct(steps[i - 1].upTo)} hasta ${pct(steps[i].upTo)}` : `LTV above ${pct(steps[i - 1].upTo)} up to ${pct(steps[i].upTo)}`;
  }
  return ratingText(row.key, row.exposure_class, lang) ?? humanize(row.key);
}

function flagsText(row: GridRow, lang: 'en' | 'es'): string {
  const out: string[] = [];
  if (row.short_term) out.push(lang === 'es' ? 'corto plazo' : 'short-term');
  if (row.cash_flow_dependent) out.push(lang === 'es' ? 'dependiente de flujos de caja' : 'cash-flow dependent');
  if (row.counterparty_weight !== null) out.push(lang === 'es' ? `ponderador de la contraparte ${pc(lang, row.counterparty_weight, 0)}` : `counterparty weight ${pc(lang, row.counterparty_weight, 0)}`);
  return out.join(', ');
}

export function Cre20Card({ doc, reason, initial }: DocProps & { initial?: Cre20Init }) {
  return (
    <LiveCard view="cre20" title={bi('The standardised risk weight of an exposure', 'El ponderador estandarizado de una exposición')} doc={doc} reason={reason}>
      {(d) => <Cre20Body grid={d.cre20_grid} initial={initial} />}
    </LiveCard>
  );
}

function Cre20Body({ grid, initial }: { grid: GridRow[]; initial?: Cre20Init }) {
  const lang = useShellLang();
  const t = useT();
  const classes = CLASS_ORDER.filter((c) => gridRows(grid, c).length > 0);
  const [cls, setCls] = useState<ExposureClass>(initial?.cls ?? (classes.includes('residential-re') ? 'residential-re' : (classes[0] ?? 'sovereign')));
  const [key, setKey] = useState<string | undefined>(initial?.key);
  const [shortTerm, setShortTerm] = useState(initial?.shortTerm ?? false);
  const [cfd, setCfd] = useState(initial?.cashFlowDependent ?? false);
  const [ltv, setLtv] = useState(initial?.ltv ?? 0.8);
  const [cp, setCp] = useState<number | undefined>(initial?.counterpartyWeight);
  const [mismatch, setMismatch] = useState(initial?.mismatch ?? false);
  const ccfRows = gridRows(grid, 'ccf');
  const [ccfKey, setCcfKey] = useState<string | undefined>(initial?.ccf);

  const isRe = cls === 'residential-re' || cls === 'commercial-re';
  const isBank = cls === 'bank-ecra' || cls === 'bank-scra';
  const classRows = gridRows(grid, cls);
  const cps = [...new Set(gridRows(grid, 'commercial-re').filter((r) => !r.cash_flow_dependent && r.counterparty_weight !== null).map((r) => r.counterparty_weight as number))].sort((a, b) => a - b);
  const cpNow = cls === 'commercial-re' && !cfd ? (cp !== undefined && cps.includes(cp) ? cp : (cps[0] ?? null)) : null;
  const stOnly = isBank && shortTerm;
  const bands = isRe ? [] : classRows.filter((r) => r.short_term === stOnly);
  const keyNow = key !== undefined && bands.some((r) => r.key === key) ? key : bands[0]?.key;
  const steps = isRe ? ltvSteps(grid, cls, { cashFlowDependent: cfd, counterpartyWeight: cpNow }) : [];
  const row = isRe ? ltvRow(grid, cls, ltv, { cashFlowDependent: cfd, counterpartyWeight: cpNow }) : keyNow === undefined ? null : findCell(grid, cls, keyNow, { shortTerm: stOnly });
  const ccfRow = (ccfKey !== undefined ? findCell(grid, 'ccf', ccfKey) : null) ?? ccfRows[0] ?? null;
  const mismatchOn = mismatch && (cls === 'retail' || cls === 'residential-re');
  const mm = mismatchOn && row ? adjustForCurrencyMismatch(grid, row.risk_weight) : null;
  const weight = row ? (mm ? mm.adjusted : row.risk_weight) : null;
  const calc = row && ccfRow && weight !== null ? creditEquivalentRwa({ exposure: 100, ccf: ccfRow.risk_weight, weight }) : null;

  const classOptions = classes.map((c) => ({ id: c, label: CLASS_TEXT[c] }));
  const bandOptions = bands.map((r) => ({ id: r.key, label: bi(bandText(r, steps, 'en'), bandText(r, steps, 'es')) }));

  return (
    <>
      <div className="ct-grid6">
        <RailSelect id="reg-cre20-class" label={bi('Exposure class', 'Clase de exposición')} options={classOptions} value={classes.includes(cls) ? cls : ''} onChange={(v) => setCls(v as ExposureClass)} />
        {isRe ? (
          <Knob id="reg-cre20-ltv" label={bi('Loan to value', 'Relación préstamo-valor')} value={ltv} min={0} max={1.6} step={0.01} format={{ percent: true, decimals: 0 }} hint={bi('The loan over the value of the property; the upper edge of a band belongs to it', 'El préstamo sobre el valor de la propiedad; el borde superior de un tramo le pertenece')} onChange={setLtv} />
        ) : (
          <RailSelect id="reg-cre20-band" label={bi('Rating bucket or grade', 'Tramo de calificación o grado')} options={bandOptions} value={keyNow ?? ''} onChange={setKey} />
        )}
        {isBank && <ChipGroup id="reg-cre20-short" label={bi('Short-term exposure', 'Exposición de corto plazo')} options={YES_NO} value={shortTerm ? 'yes' : 'no'} onChange={(v) => setShortTerm(v === 'yes')} />}
        {isRe && <ChipGroup id="reg-cre20-cfd" label={bi('Depends on the property cash flows', 'Depende de los flujos de caja de la propiedad')} options={YES_NO} value={cfd ? 'yes' : 'no'} onChange={(v) => setCfd(v === 'yes')} />}
        {cls === 'commercial-re' && !cfd && cps.length > 0 && (
          <ChipGroup id="reg-cre20-cp" label={bi('Weight of the counterparty', 'Ponderador de la contraparte')} options={cps.map((c) => ({ id: String(c), label: pc(lang, c, 0) }))} value={String(cpNow)} onChange={(v) => setCp(Number(v))} />
        )}
      </div>
      {!row || (isRe && steps.length === 0) ? (
        gap(
          `Not available: the document has no cell of ${pick(CLASS_TEXT[cls], 'en').toLowerCase()} for this choice, so no weight is drawn.`,
          `No disponible: el documento no tiene una celda de ${pick(CLASS_TEXT[cls], 'es').toLowerCase()} para esta elección, así que no se dibuja ningún ponderador.`,
        )
      ) : (
        <>
          <Facts data-result="cre20" data-class={cls} data-weight={String(row.risk_weight)} data-paragraph={row.paragraph} data-table={row.table} data-in-force={row.in_force_date} rows={[
          [<>{t('Risk weight', 'Ponderador de riesgo')}</>, <>{pc(lang, row.risk_weight)}</>],
          [<>{t('Band', 'Tramo')}</>, <>{[bandText(row, steps, lang), flagsText(row, lang)].filter(Boolean).join(', ')}</>],
          [<>{t('Table', 'Tabla')}</>, <><Ref>{tableText(row.table, lang)}</Ref></>],
          [<>{t('Paragraph', 'Párrafo')}</>, <><Ref>{row.paragraph}</Ref></>],
          [<>{t('In force since', 'Vigente desde')}</>, <>{row.in_force_date}</>],
        ]} />
          {isRe ? <LtvSteps grid={grid} cls={cls} cfd={cfd} cps={cps} cpNow={cpNow} ltv={ltv} /> : <WeightBars rows={bands} row={row} />}
          <RwaBlock grid={grid} ccfRows={ccfRows} ccfRow={ccfRow} onCcf={setCcfKey} canMismatch={cls === 'retail' || cls === 'residential-re'} mismatch={mismatch} onMismatch={setMismatch} mm={mm} weight={weight} calc={calc} />
          <ClassTable rows={classRows} current={row} />
        </>
      )}
    </>
  );
}

/** The step chart of a real estate class: the weight against the LTV for each variant of the table, the reader's LTV marked. */
function LtvSteps({ grid, cls, cfd, cps, cpNow, ltv }: { grid: GridRow[]; cls: ExposureClass; cfd: boolean; cps: number[]; cpNow: number | null; ltv: number }) {
  const lang = useShellLang();
  const xs = Array.from({ length: 161 }, (_, i) => i / 100);
  const variants: Array<{ label: BiText; cashFlowDependent: boolean; counterpartyWeight: number | null; current: boolean }> =
    cls === 'residential-re'
      ? [
          { label: bi('Not cash-flow dependent', 'No dependiente de flujos de caja'), cashFlowDependent: false, counterpartyWeight: null, current: !cfd },
          { label: bi('Cash-flow dependent', 'Dependiente de flujos de caja'), cashFlowDependent: true, counterpartyWeight: null, current: cfd },
        ]
      : [
          { label: bi('Cash-flow dependent', 'Dependiente de flujos de caja'), cashFlowDependent: true, counterpartyWeight: null, current: cfd },
          ...cps.map((c) => ({ label: bi(`Not cash-flow dependent, counterparty ${pc('en', c, 0)}`, `No dependiente de flujos de caja, contraparte ${pc('es', c, 0)}`), cashFlowDependent: false, counterpartyWeight: c, current: !cfd && c === cpNow })),
        ];
  const series = variants
    .filter((v) => ltvSteps(grid, cls, v).length > 0)
    .map((v) => ({
      label: v.label,
      values: xs.map((x) => ltvRow(grid, cls, x, v)?.risk_weight ?? null),
      width: v.current ? 3 : 1.5,
      ...(v.current ? {} : { dash: [5, 3] }),
    }));
  if (series.length === 0) return null;
  return (
    <div data-steps={cls} data-series={String(series.length)}>
      <UPlotChart
        x={{ label: bi('Loan to value', 'Relación préstamo-valor'), values: xs, format: { percent: true, decimals: 0 } }}
        y={{ label: bi('Risk weight', 'Ponderador de riesgo'), format: { percent: true, decimals: 0 }, range: [0, 1.2] }}
        series={series}
        marks={[{ x: ltv, label: `LTV ${pc(lang, ltv, 0)}` }]}
        height={230}
      />
    </div>
  );
}

/** The weights of a class by band as horizontal bars, the chosen band highlighted. */
function WeightBars({ rows, row }: { rows: GridRow[]; row: GridRow }) {
  if (rows.length < 2) return null;
  return (
    <BarChart
      title={bi('The risk weight of each band of the class', 'El ponderador de cada tramo de la clase')}
      orientation="horizontal"
      data={rows.map((r) => ({ id: r.key, label: bi(bandText(r, [], 'en'), bandText(r, [], 'es')), value: r.risk_weight * 100, tone: 'accent' as Tone, highlight: r === row }))}
      axis={{ label: bi('Risk weight', 'Ponderador de riesgo'), unit: '%', format: { digits: 4 } }}
    />
  );
}

/** The credit equivalent and the RWA per 100 of exposure: the conversion factor, the currency mismatch and the weight, each with its paragraph. */
function RwaBlock(p: {
  grid: GridRow[];
  ccfRows: GridRow[];
  ccfRow: GridRow | null;
  onCcf: (k: string) => void;
  canMismatch: boolean;
  mismatch: boolean;
  onMismatch: (v: boolean) => void;
  mm: ReturnType<typeof adjustForCurrencyMismatch>;
  weight: number | null;
  calc: ReturnType<typeof creditEquivalentRwa> | null;
}) {
  const lang = useShellLang();
  const t = useT();
  return (
    <div className="ct-context">
      <h4 className="ct-sub">{t('From the weight to the risk-weighted amount', 'Del ponderador al monto ponderado por riesgo')}</h4>
      <div className="ct-grid6">
        {p.ccfRows.length > 0 && <RailSelect id="reg-cre20-ccf" label={bi('Off-balance-sheet item', 'Partida fuera de balance')} options={p.ccfRows.map((r) => ({ id: r.key, label: KEY_TEXT[r.key] ?? humanize(r.key) }))} value={p.ccfRow?.key ?? ''} onChange={p.onCcf} />}
        {p.canMismatch && <ChipGroup id="reg-cre20-mismatch" label={bi('Unhedged currency mismatch', 'Descalce de moneda sin cobertura')} options={YES_NO} value={p.mismatch ? 'yes' : 'no'} onChange={(v) => p.onMismatch(v === 'yes')} />}
      </div>
      {p.ccfRow && p.calc && p.weight !== null ? (
        <Facts data-result="rwa"
          data-ccf={String(p.ccfRow.risk_weight)}
          data-ccf-paragraph={p.ccfRow.paragraph}
          data-adjusted-weight={String(p.weight)}
          data-rwa={String(p.calc.rwa)}
          {...(p.mm ? { 'data-mismatch-paragraph': p.mm.multiplier.paragraph } : {})} rows={[
          [<>{t('Conversion factor', 'Factor de conversión')}</>, <>{pc(lang, p.ccfRow.risk_weight, 0)} (<Ref>{p.ccfRow.paragraph}</Ref>, {p.ccfRow.in_force_date})</>],
          [<>{t('Weight used', 'Ponderador usado')}</>, <>{pc(lang, p.weight)}
            {p.mm && (
              <>
                {' '}
                ({t('currency mismatch', 'descalce de moneda')}: {formatNumber(p.mm.multiplier.risk_weight, lang)} {t('times, at most', 'veces, a lo más')} {pc(lang, p.mm.cap.risk_weight, 0)}, <Ref>{p.mm.multiplier.paragraph}</Ref>, {p.mm.multiplier.in_force_date})
              </>
            )}</>],
          [<>{t('Credit equivalent per 100 of exposure', 'Equivalente de crédito por 100 de exposición')}</>, <>{formatNumber(p.calc.creditEquivalent, lang, { decimals: 2 })}</>],
          [<>{t('Risk-weighted amount per 100 of exposure', 'Monto ponderado por riesgo por 100 de exposición')}</>, <>{formatNumber(p.calc.rwa, lang, { decimals: 2 })}</>],
        ]} />
      ) : (
        gap('Not available: the document has no conversion factor row, so no risk-weighted amount is drawn.', 'No disponible: el documento no tiene una fila de factor de conversión, así que no se calcula el monto ponderado por riesgo.')
      )}
    </div>
  );
}

/** The cells of the class as the table prints them, each with its table, paragraph and in-force date. */
function ClassTable({ rows, current }: { rows: GridRow[]; current: GridRow }) {
  const lang = useShellLang();
  const t = useT();
  return (
    <table className="caos-table ct-wrap-head" data-table="cre20-cells">
      <thead>
        <tr>
          <th className="caos-col-text">{t('Band', 'Tramo')}</th>
          <th>{t('Weight', 'Ponderador')}</th>
          <th className="caos-col-text">{t('Table', 'Tabla')}</th>
          <th className="caos-col-text">{t('Paragraph', 'Párrafo')}</th>
          <th>{t('In force', 'Vigente')}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => {
          const own = ltvSteps(rows, r.exposure_class, { cashFlowDependent: r.cash_flow_dependent, counterpartyWeight: r.counterparty_weight });
          return (
            <tr key={i} className={r === current ? 'ct-current' : undefined} data-cell={r.key} data-paragraph={r.paragraph} data-in-force={r.in_force_date}>
              <td className="caos-col-text">{[bandText(r, own, lang), flagsText(r, lang)].filter(Boolean).join(', ')}</td>
              <td>{pc(lang, r.risk_weight)}</td>
              <td className="caos-col-text">
                <Ref>{tableText(r.table, lang)}</Ref>
              </td>
              <td className="caos-col-text">
                <Ref>{r.paragraph}</Ref>
              </td>
              <td>{r.in_force_date}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// the output floor

export interface FloorInit {
  year?: number;
  nominated?: number;
  saOnly?: number;
  capped?: boolean;
}

export function FloorCard({ doc, reason, initial }: DocProps & { initial?: FloorInit }) {
  return (
    <LiveCard view="floor" title={bi('The output floor', 'El piso de salida (output floor)')} doc={doc} reason={reason}>
      {(d) => <FloorBody doc={d} initial={initial} />}
    </LiveCard>
  );
}

const FLOOR_UNIT: BiText = { en: 'index points', es: 'puntos índice' };

function FloorBody({ doc, initial }: { doc: RegulatoryDoc; initial?: FloorInit }) {
  const lang = useShellLang();
  const t = useT();
  const phase = [...doc.output_floor_phase_in].sort((a, b) => a.year - b.year);
  const plain = entryById(doc, 'rbc20-13-output-floor');
  const capped = entryById(doc, 'rbc20-13-output-floor-capped');
  const capShare = capped ? numberOf(capped.inputs, 'cap_share') : null;
  const [year, setYear] = useState(initial?.year ?? phase[phase.length - 1]?.year ?? 2028);
  const [nominated, setNominated] = useState(initial?.nominated ?? (plain ? numberOf(plain.inputs, 'rwa_nominated') : 76));
  const [saOnly, setSaOnly] = useState(initial?.saOnly ?? (plain ? numberOf(plain.inputs, 'rwa_sa_only') : 140));
  const [useCap, setUseCap] = useState(initial?.capped ?? false);
  if (phase.length === 0) return gap('Not available: the document has no output-floor phase-in rows, so no factor is drawn.', 'No disponible: el documento no tiene filas del calendario de implementación del piso, así que no se dibuja ningún factor.');
  const row = phaseInRow(phase, year) ?? phase[0];
  const cap = useCap && capShare !== null ? capShare : null;
  const b = floorBreakdown(nominated, saOnly, row.factor, cap);
  // the result equals a worked example of the document when its inputs are the reader's
  const same = (e: RegulatoryEntry | undefined, withCap: boolean) =>
    !!e && numberOf(e.inputs, 'rwa_nominated') === nominated && numberOf(e.inputs, 'rwa_sa_only') === saOnly && numberOf(e.inputs, 'floor_factor') === row.factor && withCap === (cap !== null);
  const match = same(plain, false) ? plain : same(capped, true) ? capped : undefined;
  const unit = pick(FLOOR_UNIT, lang);
  const yearOptions = phase.map((r) => ({ id: String(r.year), label: formatNumber(r.year, lang, { grouping: false }) }));
  const tones: Tone[] = ['neutral', b.floorBinds ? 'warn' : 'neutral', 'good'];
  return (
    <>
      <div className="ct-grid6">
        <RailSelect id="reg-floor-year" label={bi('Phase-in year (BCBS schedule)', 'Año de implementación (calendario del BCBS)')} options={yearOptions} value={String(row.year)} onChange={(v) => setYear(Number(v))} />
        <Knob id="reg-floor-nominated" label={bi('RWA from the bank’s own approaches', 'RWA de los enfoques propios del banco')} value={nominated} min={0} max={300} step={0.5} unit={FLOOR_UNIT} format={{ digits: 4 }} hint={bi('The RWA of the internal approaches before the floor (the pre-floor RWA)', 'Los RWA de los enfoques internos antes del piso (RWA previos al piso)')} onChange={setNominated} />
        <Knob id="reg-floor-sa" label={bi('RWA by the standardised approaches only', 'RWA solo por los enfoques estandarizados')} value={saOnly} min={0} max={300} step={0.5} unit={FLOOR_UNIT} format={{ digits: 4 }} hint={bi('The floor base: standardised approaches only (RBC20.11 to RBC20.12)', 'La base del piso: solo enfoques estandarizados (RBC20.11 a RBC20.12)')} onChange={setSaOnly} />
        {capShare !== null && <ChipGroup id="reg-floor-cap" label={bi('Optional cap on the increase', 'Tope opcional del aumento')} options={[{ id: 'no', label: bi('No cap', 'Sin tope') }, { id: 'yes', label: bi(`Cap ${pc('en', capShare, 0)}`, `Tope ${pc('es', capShare, 0)}`) }]} value={useCap ? 'yes' : 'no'} onChange={(v) => setUseCap(v === 'yes')} />}
      </div>
      <Facts data-result="floor"
        data-rwa={String(b.rwa)}
        data-factor={String(row.factor)}
        data-year={String(row.year)}
        data-paragraph={row.paragraph}
        data-in-force={row.in_force_date}
        data-floor-binds={String(b.floorBinds)}
        data-cap-binds={String(b.capBinds)}
        {...(match ? { 'data-matches-document': match.id } : {})} rows={[
          [<>{t('Floor factor', 'Factor del piso')}</>, <>{pc(lang, row.factor)} ({t('paragraph', 'párrafo')} <Ref>{row.paragraph}</Ref>, {t('in force since', 'vigente desde')} {row.in_force_date})</>],
          [<>{t('Floor base', 'Base del piso')}</>, <>{`${formatNumber(b.floor, lang)} ${unit}`}</>],
          [<>{t('RWA after the floor', 'RWA tras el piso')}</>, <>{`${formatNumber(b.rwa, lang)} ${unit}`}</>],
          [<>{t('Increase over the pre-floor RWA', 'Aumento sobre los RWA previos al piso')}</>, <>{`${formatNumber(b.increase, lang)} ${unit}`}</>],
          [<>{t('Reading', 'Lectura')}</>, <>{b.floorBinds ? t('The floor binds: the standardised approaches set the RWA.', 'El piso es vinculante: los enfoques estandarizados fijan los RWA.') : t('The floor does not bind: the bank’s own approaches set the RWA.', 'El piso no es vinculante: los enfoques propios del banco fijan los RWA.')}{' '}
          {b.capBinds ? t('The optional cap binds.', 'El tope opcional es vinculante.') : ''}
          {match ? ` ${t('This equals the worked example of the document', 'Esto es igual al ejemplo resuelto del documento')} (` : ''}
          {match && (
            <>
              <Ref>{rangeText(match.paragraph_range, lang)}</Ref>)
            </>
          )}</>],
        ]} />
      <BarChart
        title={bi('The RWA before and after the output floor', 'Los RWA antes y después del piso de salida')}
        orientation="horizontal"
        data={[
          { id: 'nominated', label: bi('Own approaches (pre-floor)', 'Enfoques propios (previo al piso)'), value: nominated, tone: tones[0] },
          { id: 'floor', label: bi('Floor: factor times the standardised RWA', 'Piso: factor por los RWA estandarizados'), value: b.floor, tone: tones[1] },
          { id: 'result', label: bi('After the floor', 'Tras el piso'), value: b.rwa, tone: tones[2], highlight: true },
        ]}
        axis={{ label: bi('Risk-weighted assets', 'RWA'), unit: FLOOR_UNIT, format: { digits: 4 } }}
      />
      <table className="caos-table ct-wrap-head" data-table="floor-phase-in">
        <thead>
          <tr>
            <th>{t('Year', 'Año')}</th>
            <th>{t('Applies from', 'Aplica desde')}</th>
            <th>{t('Factor', 'Factor')}</th>
            <th className="caos-col-text">{t('Table', 'Tabla')}</th>
            <th className="caos-col-text">{t('Paragraph', 'Párrafo')}</th>
            <th>{t('In force', 'Vigente')}</th>
          </tr>
        </thead>
        <tbody>
          {phase.map((r) => (
            <tr key={r.year} className={r.year === row.year ? 'ct-current' : undefined} data-phase-in={r.year} data-paragraph={r.paragraph} data-in-force={r.in_force_date}>
              <td>{formatNumber(r.year, lang, { grouping: false })}</td>
              <td>{r.effective_from}</td>
              <td>{pc(lang, r.factor)}</td>
              <td className="caos-col-text">
                <Ref>{tableText(r.table, lang)}</Ref>
              </td>
              <td className="caos-col-text">
                <Ref>{r.paragraph}</Ref>
              </td>
              <td>{r.in_force_date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// the SBM aggregator

export interface SbmInit {
  preset?: string;
  gamma?: number;
  scale?: number;
  rho?: number;
}

const SBM_PRESETS = ['sbm-bucket-and-cross-bucket-aggregation', 'sbm-cross-bucket-fallback'];

export function SbmCard({ doc, reason, initial }: DocProps & { initial?: SbmInit }) {
  return (
    <LiveCard view="sbm" title={bi('The sensitivities-based aggregation', 'La agregación por sensibilidades')} doc={doc} reason={reason}>
      {(d) => <SbmBody doc={d} initial={initial} />}
    </LiveCard>
  );
}

function SbmBody({ doc, initial }: { doc: RegulatoryDoc; initial?: SbmInit }) {
  const lang = useShellLang();
  const t = useT();
  const presets = SBM_PRESETS.map((id) => entryById(doc, id)).filter((e): e is RegulatoryEntry => !!e && e.calculator === 'frtb-sbm');
  const rhoCase = entryById(doc, 'sbm-low-and-high-scenarios');
  const first = presets.find((e) => e.id === initial?.preset) ?? presets[0];
  const [preset, setPreset] = useState(first?.id ?? '');
  const entry = presets.find((e) => e.id === preset) ?? first;
  const [gamma, setGamma] = useState(initial?.gamma ?? (entry ? numberOf(entry.inputs, 'gamma') : 0.5));
  const [scale, setScale] = useState(initial?.scale ?? 1);
  const [rho, setRho] = useState(initial?.rho ?? (rhoCase ? numberOf(rhoCase.inputs, 'rho') : 0.5));
  if (!entry) return gap('Not available: the document has no sensitivities-based cases, so no aggregation is drawn.', 'No disponible: el documento no tiene casos del método de sensibilidades, así que no se dibuja ninguna agregación.');
  const pick1 = (id: string) => {
    const e = presets.find((x) => x.id === id);
    if (!e) return;
    setPreset(id);
    setGamma(numberOf(e.inputs, 'gamma'));
    setScale(1);
  };
  const ws = [vectorOf(entry.inputs, 'ws_1'), vectorOf(entry.inputs, 'ws_2').map((x) => x * scale)];
  const res = sbmAggregate({ ws, rho: [matrixOf(entry.inputs, 'rho_1'), matrixOf(entry.inputs, 'rho_2')], gamma });
  const out = entry.outputs.find((o) => o.name === 'sbm_charge');
  const unit = 'USD';
  const rhoOut = rhoCase?.outputs.find((o) => o.name === 'rho_low');
  const list = (v: number[]) => v.map((x) => formatNumber(x, lang, { digits: 4 })).join('; ');
  return (
    <>
      <div className="ct-grid6">
        <RailSelect id="reg-sbm-case" label={bi('Case of the document', 'Caso del documento')} options={presets.map((e) => ({ id: e.id, label: docText(e.title) }))} value={entry.id} onChange={pick1} />
        <Knob id="reg-sbm-gamma" label={bi('Correlation between buckets, gamma', 'Correlación entre buckets, gamma')} value={gamma} min={0} max={1} step={0.05} format={{ percent: true, decimals: 0 }} hint={bi('The medium-scenario gamma between every two buckets (MAR21.50 sets 50 percent for GIRR)', 'La gamma del escenario medio entre cada par de buckets (MAR21.50 fija 50 por ciento para GIRR)')} onChange={setGamma} />
        <Knob id="reg-sbm-scale" label={bi('Scale of the second bucket', 'Escala del segundo bucket')} value={scale} min={-2} max={2} step={0.1} format={{ digits: 3 }} hint={bi('Multiplies every weighted sensitivity of bucket 2: a negative scale turns it into an offsetting position', 'Multiplica cada sensibilidad ponderada del bucket 2: una escala negativa la vuelve una posición compensatoria')} onChange={setScale} />
      </div>
      <Facts data-inputs="sbm" rows={[
          [<>{t('Weighted sensitivities, bucket 1', 'Sensibilidades ponderadas, bucket 1')}</>, <>{`${list(ws[0])} ${unit}`}</>],
          [<>{t('Weighted sensitivities, bucket 2', 'Sensibilidades ponderadas, bucket 2')}</>, <>{`${list(ws[1])} ${unit}`}</>],
        ]} />
      <Facts data-result="sbm" data-charge={String(res.charge)} data-binding={res.binding} data-paragraph={out?.paragraph ?? entry.paragraph} data-in-force={entry.in_force_date} rows={[
          [<>{t('Capital charge, the maximum of the three scenarios', 'Cargo de capital, el máximo de los tres escenarios')}</>, <>{`${formatNumber(res.charge, lang, { digits: 6 })} ${unit}`}</>],
          [<>{t('Binding scenario', 'Escenario vinculante')}</>, <>{pick(SCENARIO_TEXT[res.binding], lang)}</>],
          [<>{t('Paragraph', 'Párrafo')}</>, <><Ref>{out?.paragraph ?? entry.paragraph}</Ref> ({t('in force since', 'vigente desde')} {entry.in_force_date})</>],
        ]} />
      <BarChart
        title={bi('The cross-bucket charge under each correlation scenario', 'El cargo entre buckets bajo cada escenario de correlación')}
        orientation="horizontal"
        data={SCENARIOS.map((s) => ({
          id: s,
          label: SCENARIO_TEXT[s],
          value: res.scenarios[s].charge,
          tone: (s === res.binding ? 'accent' : res.scenarios[s].fallback ? 'warn' : 'neutral') as Tone,
          highlight: s === res.binding,
          hint: res.scenarios[s].fallback ? bi('The fallback of MAR21.4(5)(b) applied', 'Se aplicó el recurso de MAR21.4(5)(b)') : undefined,
        }))}
        axis={{ label: bi('Cross-bucket charge', 'Cargo entre buckets'), unit, format: { digits: 4 } }}
      />
      <table className="caos-table ct-wrap-head" data-table="sbm-scenarios">
        <thead>
          <tr>
            <th className="caos-col-text">{t('Scenario', 'Escenario')}</th>
            <th>{t('Bucket 1 charge', 'Cargo del bucket 1')}</th>
            <th>{t('Bucket 2 charge', 'Cargo del bucket 2')}</th>
            <th>{t('Cross-bucket charge', 'Cargo entre buckets')}</th>
            <th className="caos-col-text">{t('MAR21.4(5)(b) fallback', 'Recurso de MAR21.4(5)(b)')}</th>
          </tr>
        </thead>
        <tbody>
          {SCENARIOS.map((s) => (
            <tr key={s} className={s === res.binding ? 'ct-current' : undefined} data-scenario={s} data-charge={String(res.scenarios[s].charge)} data-fallback={String(res.scenarios[s].fallback)}>
              <td className="caos-col-text">{pick(SCENARIO_TEXT[s], lang)}</td>
              <td>{formatNumber(res.scenarios[s].kb[0], lang, { digits: 5 })}</td>
              <td>{formatNumber(res.scenarios[s].kb[1], lang, { digits: 5 })}</td>
              <td>{formatNumber(res.scenarios[s].charge, lang, { digits: 5 })}</td>
              <td className="caos-col-text">{res.scenarios[s].fallback ? t('used: the radicand was negative', 'usado: el radicando era negativo') : t('not needed', 'no hizo falta')}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rhoCase && (
        <>
          <Knob id="reg-sbm-rho" label={bi('A prescribed correlation, rho', 'Una correlación prescrita, rho')} value={rho} min={0} max={1} step={0.05} format={{ percent: true, decimals: 0 }} hint={bi('Any prescribed correlation of the medium scenario (MAR21.6)', 'Cualquier correlación prescrita del escenario medio (MAR21.6)')} onChange={setRho} />
          <Facts data-result="rho" data-low={String(scenarioRho(rho, 'low'))} data-medium={String(scenarioRho(rho, 'medium'))} data-high={String(scenarioRho(rho, 'high'))} data-paragraph={rhoOut?.paragraph ?? rhoCase.paragraph} data-in-force={rhoCase.in_force_date} rows={[
            ...SCENARIOS.map((sc): [ReactNode, ReactNode] => [pick(SCENARIO_TEXT[sc], lang), pc(lang, scenarioRho(rho, sc), 1)]),
            [<>{t('Paragraph', 'Párrafo')}</>, <><Ref>{rhoOut?.paragraph ?? rhoCase.paragraph}</Ref> ({t('in force since', 'vigente desde')} {rhoCase.in_force_date})</>],
          ]} />
        </>
      )}
    </>
  );
}

const SCENARIO_TEXT: Record<Scenario, BiText> = {
  low: bi('Low correlation', 'Correlación baja'),
  medium: bi('Medium correlation', 'Correlación media'),
  high: bi('High correlation', 'Correlación alta'),
};

// ---------------------------------------------------------------------------------------------------------------------
// the liquidity-horizon cascade and the parameter tables

export interface CascadeInit {
  preset?: string;
  es?: number[];
}

const CASCADE_PRESETS: Array<{ id: string; label: BiText }> = [
  { id: 'cascade-two-horizons', label: bi('Two horizons (document)', 'Dos horizontes (documento)') },
  { id: 'cascade-all-lh-ten', label: bi('Every factor at 10 days (document)', 'Todo factor a 10 días (documento)') },
];

const FACTOR_TEXT: Record<string, BiText> = {
  'interest-rate-specified-currencies': bi('Interest rate, specified currencies', 'Tasa de interés, monedas especificadas'),
  'interest-rate-other': bi('Interest rate, other currencies', 'Tasa de interés, otras monedas'),
  'interest-rate-volatility': bi('Interest rate volatility', 'Volatilidad de tasa de interés'),
  'credit-spread-sovereign-investment-grade': bi('Credit spread, sovereign, investment grade', 'Spread de crédito, soberano, grado de inversión'),
  'credit-spread-sovereign-high-yield': bi('Credit spread, sovereign, high yield', 'Spread de crédito, soberano, alto rendimiento'),
  'credit-spread-corporate-investment-grade': bi('Credit spread, corporate, investment grade', 'Spread de crédito, empresa, grado de inversión'),
  'credit-spread-corporate-high-yield': bi('Credit spread, corporate, high yield', 'Spread de crédito, empresa, alto rendimiento'),
  'credit-spread-volatility': bi('Credit spread volatility', 'Volatilidad de spread de crédito'),
  'equity-large-cap': bi('Equity, large capitalisation', 'Acciones, gran capitalización'),
  'equity-small-cap': bi('Equity, small capitalisation', 'Acciones, pequeña capitalización'),
  'equity-large-cap-volatility': bi('Equity volatility, large capitalisation', 'Volatilidad de acciones, gran capitalización'),
  'equity-small-cap-volatility': bi('Equity volatility, small capitalisation', 'Volatilidad de acciones, pequeña capitalización'),
  'fx-specified-pairs': bi('Foreign exchange, specified pairs', 'Tipo de cambio, pares especificados'),
  'fx-other-pairs': bi('Foreign exchange, other pairs', 'Tipo de cambio, otros pares'),
  'fx-volatility': bi('Foreign exchange volatility', 'Volatilidad de tipo de cambio'),
  'commodity-energy-and-carbon': bi('Commodity, energy and carbon', 'Materias primas, energía y carbono'),
  'commodity-precious-and-non-ferrous-metals': bi('Commodity, precious and non-ferrous metals', 'Materias primas, metales preciosos y no ferrosos'),
  'commodity-other': bi('Commodity, other', 'Materias primas, otras'),
  // SA-CCR (CRE52.72 Table 2)
  'interest-rate': bi('Interest rate', 'Tasa de interés'),
  fx: bi('Foreign exchange', 'Tipo de cambio'),
  'credit-index-IG': bi('Credit index, investment grade', 'Índice de crédito, grado de inversión'),
  'credit-index-SG': bi('Credit index, speculative grade', 'Índice de crédito, grado especulativo'),
  'equity-single-name': bi('Equity, single name', 'Acciones, entidad individual'),
  'equity-index': bi('Equity index', 'Índice accionario'),
  'commodity-electricity': bi('Commodity, electricity', 'Materias primas, electricidad'),
  'commodity-oil-gas-metals-agricultural-other': bi('Commodity, oil and gas, metals, agricultural and other', 'Materias primas, petróleo y gas, metales, agrícolas y otras'),
  // BA-CVA (MAR50.16 Table 1)
  'sovereigns-central-banks-mdbs': bi('Sovereigns, central banks and multilateral development banks', 'Soberanos, bancos centrales y bancos multilaterales de desarrollo'),
  'local-government-public': bi('Local government, government-backed non-financials, education, public administration', 'Gobierno local, no financieras con respaldo estatal, educación, administración pública'),
  financials: bi('Financials', 'Financieras'),
  'basic-materials-energy-industrials': bi('Basic materials, energy, industrials, agriculture, manufacturing, mining', 'Materiales básicos, energía, industria, agricultura, manufactura, minería'),
  'consumer-transport-administrative': bi('Consumer goods and services, transport, administrative', 'Bienes y servicios de consumo, transporte, servicios administrativos'),
  'technology-telecoms': bi('Technology, telecoms', 'Tecnología, telecomunicaciones'),
  'health-care-utilities-professional': bi('Health care, utilities, professional', 'Salud, servicios públicos, servicios profesionales'),
  other: bi('Other', 'Otros'),
};

function factorText(key: string, lang: 'en' | 'es'): string {
  const credit = key.match(/^credit-single-name-(.+)$/);
  if (credit) return lang === 'es' ? `Crédito, entidad individual, ${credit[1]}` : `Credit, single name, ${credit[1]}`;
  const horizon = key.match(/^j(\d+)$/);
  if (horizon) return `j = ${horizon[1]}`;
  return FACTOR_TEXT[key] ? pick(FACTOR_TEXT[key], lang) : humanize(key);
}

const PARAMETER_TEXT: Record<string, BiText> = {
  supervisory_factor: bi('Supervisory factor', 'Factor supervisor'),
  correlation: bi('Correlation', 'Correlación'),
  option_volatility: bi('Option volatility', 'Volatilidad de opciones'),
  risk_weight_investment_grade: bi('Investment grade', 'Grado de inversión'),
  risk_weight_high_yield_or_not_rated: bi('High yield or not rated', 'Alto rendimiento o sin calificación'),
  liquidity_horizon_days: bi('Liquidity horizon', 'Horizonte de liquidez'),
};

/** A parameter table of the document as a table: one row per key, one column per parameter, every row with its paragraph and in-force date. */
export function ParameterCard({ doc, reason, id, lhs }: DocProps & { id: ParameterTable['id']; lhs?: number[] }) {
  const lang = useShellLang();
  const t = useT();
  if (doc === undefined) return <Pending label={LOADING} />;
  if (doc === null) return <Unavailable reason={reason ?? NOT_PUBLISHED} />;
  const table = parameterTable(doc, id);
  if (!table || table.rows.length === 0) return gap(`Not available: the document does not carry the table ${id}, so no parameter is drawn.`, `No disponible: el documento no trae la tabla ${id}, así que no se dibuja ningún parámetro.`);
  const params = [...new Set(table.rows.map((r) => r.parameter))];
  const keys = [...new Set(table.rows.map((r) => r.key))];
  const unitOf = (p: string) => table.rows.find((r) => r.parameter === p)?.unit ?? '';
  const cell = (p: string, v: number) => (unitOf(p) === 'decimal' ? pc(lang, v) : unitOf(p) === 'days' ? `${formatNumber(v, lang)} ${t('days', 'días')}` : formatNumber(v, lang));
  const horizon = (k: string) => table.rows.find((r) => r.key === k && r.parameter === 'liquidity_horizon_days')?.value;
  return (
    <div data-view="parameters" data-state="ready" data-table-id={id}>
      <h4 className="ct-sub">
        {pick(docText(table.title), lang)} (<Ref>{tableText(table.table, lang)}</Ref>, {t('in force since', 'vigente desde')} {table.in_force_date})
      </h4>
      <table className="caos-table ct-wrap-head" data-table={id}>
        <thead>
          <tr>
            <th className="caos-col-text">{t('Class', 'Clase')}</th>
            {params.map((p) => (
              <th key={p}>{PARAMETER_TEXT[p] ? pick(PARAMETER_TEXT[p], lang) : humanize(p)}</th>
            ))}
            {lhs && <th className="caos-col-text">{t('Subsets', 'Subconjuntos')}</th>}
            <th className="caos-col-text">{t('Paragraph', 'Párrafo')}</th>
            <th>{t('In force', 'Vigente')}</th>
          </tr>
        </thead>
        <tbody>
          {keys.map((k) => {
            const lh = horizon(k);
            const subsets = lhs && lh !== undefined ? subsetMembership(lhs, lh) : null;
            const values = Object.fromEntries(table.rows.filter((r) => r.key === k).map((r) => [`data-v-${r.parameter}`, String(r.value)]));
            return (
              <tr key={k} data-parameter-row={k} data-paragraph={table.paragraph} data-in-force={table.in_force_date} {...values} {...(subsets ? { 'data-subsets': subsets.join(',') } : {})}>
                <td className="caos-col-text">{factorText(k, lang)}</td>
                {params.map((p) => {
                  const r = table.rows.find((x) => x.key === k && x.parameter === p);
                  return <td key={p}>{r ? cell(p, r.value) : formatNumber(null, lang)}</td>;
                })}
                {subsets && <td className="caos-col-text">{subsets.length === 0 ? formatNumber(null, lang) : subsets.map((j) => `Q${j}`).join(', ')}</td>}
                <td className="caos-col-text">
                  <Ref>{table.paragraph}</Ref>
                </td>
                <td>{table.in_force_date}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function CascadeCard({ doc, reason, initial }: DocProps & { initial?: CascadeInit }) {
  return (
    <LiveCard view="cascade" title={bi('The liquidity-adjusted expected shortfall', 'El déficit esperado ajustado por liquidez')} doc={doc} reason={reason}>
      {(d) => <CascadeBody doc={d} initial={initial} reason={reason} />}
    </LiveCard>
  );
}

function CascadeBody({ doc, initial, reason }: { doc: RegulatoryDoc; initial?: CascadeInit; reason?: Reason }) {
  const lang = useShellLang();
  const t = useT();
  const horizons = parameterTable(doc, 'mar33-4-table-1');
  const presets = CASCADE_PRESETS.filter((p) => entryById(doc, p.id));
  const startId = initial?.preset ?? presets[0]?.id;
  const presetEs = (id: string | undefined): number[] => {
    const e = id ? entryById(doc, id) : undefined;
    if (!e) return [10, 0, 0, 0, 0];
    return [numberOf(e.inputs, 'es_t_p'), e.inputs.some((v) => v.name === 'es_t_p_2') ? numberOf(e.inputs, 'es_t_p_2') : 0, 0, 0, 0];
  };
  const [es, setEs] = useState<number[]>(initial?.es ?? presetEs(startId));
  if (!horizons || horizons.rows.length < 2) return gap('Not available: the document does not carry MAR33.4 Table 1, so no cascade is drawn.', 'No disponible: el documento no trae la tabla 1 de MAR33.4, así que no se dibuja ninguna cascada.');
  const lhs = horizons.rows.map((r) => r.value);
  const entry = entryById(doc, startId ?? '') ?? entryById(doc, 'cascade-two-horizons');
  const tDays = entry ? numberOf(entry.inputs, 't') : 10;
  const terms = cascadeTerms(es[0], es.slice(1), lhs, tDays);
  const total = liquidityCascadeEs(es[0], es.slice(1), lhs, tDays);
  const same = (e: RegulatoryEntry | undefined) => {
    if (!e) return false;
    const want = presetEs(e.id);
    return want.length === es.length && want.every((v, i) => v === es[i]);
  };
  const match = presets.find((p) => same(entryById(doc, p.id)));
  const matchEntry = match ? entryById(doc, match.id) : undefined;
  const out = entry?.outputs.find((o) => o.name === 'es');
  const setAt = (i: number, v: number) => setEs((cur) => cur.map((x, k) => (k === i ? v : x)));
  return (
    <>
      <div className="ct-grid6">
        <RailSelect id="reg-cascade-case" label={bi('Case of the document', 'Caso del documento')} options={presets.map((p) => ({ id: p.id, label: p.label }))} value={match?.id ?? ''} onChange={(id) => setEs(presetEs(id))} />
        {lhs.map((lh, i) => (
          <Knob
            key={i}
            id={`reg-cascade-es-${i + 1}`}
            label={i === 0 ? bi('ES of all risk factors, ES_T(P)', 'ES de todos los factores, ES_T(P)') : bi(`ES of the factors with LH of at least ${lh} days`, `ES de los factores con LH de al menos ${lh} días`)}
            value={es[i] ?? 0}
            min={0}
            max={30}
            step={0.5}
            unit="USD"
            format={{ digits: 4 }}
            hint={i === 0 ? bi('The 10-day ES with every risk factor shocked', 'El ES a 10 días con todos los factores sometidos a choque') : bi(`The 10-day ES shocking only the factors whose liquidity horizon is at least ${lh} days, the others held constant`, `El ES a 10 días con choque solo a los factores cuyo horizonte de liquidez es de al menos ${lh} días, los demás constantes`)}
            onChange={(v) => setAt(i, v)}
          />
        ))}
      </div>
      <Facts data-result="cascade" data-es={String(total)} data-paragraph={out?.paragraph ?? horizons.paragraph} data-in-force={horizons.in_force_date} {...(matchEntry ? { 'data-matches-document': matchEntry.id } : {})} rows={[
          [<>{t('Liquidity-adjusted ES', 'ES ajustado por liquidez')}</>, <>{`${formatNumber(total, lang, { digits: 6 })} USD`}</>],
          [<>{t('Against the plain 10-day ES', 'Frente al ES simple a 10 días')}</>, <>{es[0] > 0 ? pc(lang, total / es[0] - 1, 1) : formatNumber(null, lang)}</>],
          [<>{t('Paragraph', 'Párrafo')}</>, <><Ref>{out?.paragraph ?? horizons.paragraph}</Ref> ({t('in force since', 'vigente desde')} {horizons.in_force_date})</>],
        ]} />
      <BarChart
        title={bi('The terms of the cascade before the square root', 'Los términos de la cascada antes de la raíz cuadrada')}
        orientation="horizontal"
        data={[
          ...terms.map((x) => ({ id: `j${x.j}`, label: bi(`Subset ${x.j}, horizon ${x.lh} days`, `Subconjunto ${x.j}, horizonte ${x.lh} días`), value: x.term, tone: 'accent' as Tone })),
          { id: 'total', label: bi('Cascade ES (square root of the sum of squares)', 'ES de la cascada (raíz de la suma de cuadrados)'), value: total, tone: 'good' as Tone, highlight: true },
        ]}
        axis={{ label: bi('Term of the cascade', 'Término de la cascada'), unit: 'USD', format: { digits: 4 } }}
      />
      <table className="caos-table ct-wrap-head" data-table="cascade-terms">
        <thead>
          <tr>
            <th>{t('Subset j', 'Subconjunto j')}</th>
            <th>{t('Horizon LH', 'Horizonte LH')}</th>
            <th>{t('Weight', 'Peso')}</th>
            <th>{t('ES of the subset', 'ES del subconjunto')}</th>
            <th>{t('Term', 'Término')}</th>
            <th className="caos-col-text">{t('Paragraph', 'Párrafo')}</th>
            <th>{t('In force', 'Vigente')}</th>
          </tr>
        </thead>
        <tbody>
          {terms.map((x) => (
            <tr key={x.j} data-horizon={x.lh} data-paragraph={horizons.paragraph} data-in-force={horizons.in_force_date}>
              <td>{x.j}</td>
              <td>{`${formatNumber(x.lh, lang)} ${t('days', 'días')}`}</td>
              <td>{x.weight === null ? '1' : formatNumber(x.weight, lang, { digits: 4 })}</td>
              <td>{formatNumber(x.es, lang)}</td>
              <td>{formatNumber(x.term, lang, { digits: 4 })}</td>
              <td className="caos-col-text">
                <Ref>{horizons.paragraph}</Ref>
              </td>
              <td>{horizons.in_force_date}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ParameterCard doc={doc} reason={reason} id="mar33-12-table-2" lhs={lhs} />
      <p className="ct-note">
        {t(
          'The row of commodity volatility is not transcribed: the dossier reads its horizon as 60 or 120 days and the document does not decide it.',
          'La fila de volatilidad de materias primas no se transcribe: el dossier lee su horizonte como 60 o 120 días y el documento no lo decide.',
        )}
      </p>
    </>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// the worked examples

export function WorkedExamplesCard({ doc, reason }: DocProps) {
  const lang = useShellLang();
  const t = useT();
  if (doc === undefined) return <Pending label={LOADING} />;
  if (doc === null) return <Unavailable reason={reason ?? NOT_PUBLISHED} />;
  const sets = doc.official_examples.filter((e) => e.calculator === 'sa-ccr');
  const invariants = doc.invariant_cases;
  if (sets.length === 0) return gap('Not available: the document has no SA-CCR worked examples, so none is listed.', 'No disponible: el documento no tiene ejemplos resueltos de SA-CCR, así que no se lista ninguno.');
  const pub = (e: RegulatoryEntry, name: string) => e.published.find((p) => p.name === name)?.value;
  const outv = (e: RegulatoryEntry, name: string) => e.outputs.find((o) => o.name === name)?.value;
  const money = unitText('USD thousands', lang);
  return (
    <div data-view="examples" data-state="ready">
      <h4 className="ct-sub">{`${t('The five SA-CCR netting sets of CRE99', 'Los cinco conjuntos de neteo de SA-CCR de CRE99')} (${money})`}</h4>
      <table className="caos-table ct-wrap-head" data-table="cre99-examples">
        <thead>
          <tr>
            <th className="caos-col-text">{t('Netting set', 'Conjunto de neteo')}</th>
            <th>{t('Replacement cost', 'Costo de reposición')}</th>
            <th>{t('Aggregate add-on', 'Recargo agregado')}</th>
            <th>{t('Multiplier', 'Multiplicador')}</th>
            <th>{t('EAD published', 'EAD publicado')}</th>
            <th>{t('EAD recomputed', 'EAD recalculado')}</th>
            <th className="caos-col-text">{t('Paragraph', 'Párrafo')}</th>
            <th>{t('In force', 'Vigente')}</th>
          </tr>
        </thead>
        <tbody>
          {sets.map((e) => {
            const ead = outv(e, 'ead');
            return (
              <tr key={e.id} data-example={e.id} data-paragraph={e.paragraph} data-in-force={e.in_force_date} data-published-ead={String(pub(e, 'ead') ?? '')} data-engine-ead={String(typeof ead === 'number' ? ead : '')}>
                <td className="caos-col-text">{pick(docText(e.title), lang)}</td>
                <td>{formatNumber(pub(e, 'rc') ?? null, lang)}</td>
                <td>{formatNumber(pub(e, 'addon_aggregate') ?? null, lang)}</td>
                <td>{formatNumber(pub(e, 'multiplier') ?? null, lang)}</td>
                <td>{formatNumber(pub(e, 'ead') ?? null, lang)}</td>
                <td>{formatNumber(typeof ead === 'number' ? ead : null, lang, { decimals: 2 })}</td>
                <td className="caos-col-text">
                  <Ref>{rangeText(e.paragraph_range, lang)}</Ref>
                </td>
                <td>{e.in_force_date}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="ct-note">{t('The published EAD is the integer the framework prints; the recomputed one is the engine value from the trade inputs, which rounds to it exactly.', 'El EAD publicado es el entero que imprime el marco; el recalculado es el valor del motor desde los datos de las operaciones, que se redondea exactamente a él.')}</p>
      <h4 className="ct-sub">{t('The invariants the live ports are held to', 'Las invariantes a las que se sujetan los puertos en vivo')}</h4>
      <table className="caos-table ct-wrap-head" data-table="invariants">
        <thead>
          <tr>
            <th className="caos-col-text">{t('Statement', 'Enunciado')}</th>
            <th className="caos-col-text">{t('Paragraphs', 'Párrafos')}</th>
            <th>{t('In force', 'Vigente')}</th>
            <th className="caos-col-text">{t('Holds', 'Se cumple')}</th>
          </tr>
        </thead>
        <tbody>
          {invariants.map((e) => (
            <tr key={e.id} data-invariant={e.id} data-paragraph={e.paragraph} data-in-force={e.in_force_date}>
              <td className="caos-col-text">{pick(docText(e.statement ?? e.title), lang)}</td>
              <td className="caos-col-text">
                <Ref>{rangeText(e.paragraph_range, lang)}</Ref>
              </td>
              <td>{e.in_force_date}</td>
              <td className="caos-col-text">{e.holds === null ? formatNumber(null, lang) : e.holds ? t('yes', 'sí') : t('no', 'no')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// the figures: inline SVG on the shell's dg-* tokens, labelled in both languages, illustrative of the idea

const r1 = (x: number): string => String(Math.round(x * 10) / 10);
const FW = 480;
const FH = 262;

/** Tables 11 and 12 of CRE20 side by side: the residential weights by LTV band, with and without dependence on the property's cash flows. */
function CreditFigure() {
  const lang = useShellLang();
  const t = useT();
  const plain = [0.2, 0.25, 0.3, 0.4, 0.5, 0.7];
  const cash = [0.3, 0.35, 0.45, 0.6, 0.75, 1.05];
  const edges = [t('up to 50', 'hasta 50'), '60', '80', '90', '100', t('above 100', 'sobre 100')];
  const X0 = 56;
  const X1 = 456;
  const Y0 = 204;
  const Y1 = 40;
  const slot = (X1 - X0) / 6;
  const y = (v: number) => Y0 - (v / 1.1) * (Y0 - Y1);
  const n = (v: number) => formatNumber(Math.round(v * 100), lang, { decimals: 0 });
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${FW} ${FH}`} role="img" aria-label={t('Twelve bars: the CRE20 risk weights of a residential loan in six LTV bands, 20, 25, 30, 40, 50 and 70 percent when repayment does not depend on the property cash flows, and 30, 35, 45, 60, 75 and 105 percent when it does', 'Doce barras: los ponderadores de CRE20 de un préstamo residencial en seis tramos de LTV, 20, 25, 30, 40, 50 y 70 por ciento cuando el pago no depende de los flujos de caja de la propiedad, y 30, 35, 45, 60, 75 y 105 por ciento cuando sí depende')}>
      <line className="dg-axis" x1={X0} y1={Y0} x2={X1} y2={Y0} />
      <line className="dg-axis" x1={X0} y1={Y0} x2={X0} y2={Y1 - 6} />
      <rect className="dg-bar" x={X0 + 6} y={12} width={12} height={12} />
      <text className="dg-bar-label" x={X0 + 24} y={22}>{t('Not cash-flow dependent', 'No dependiente de flujos de caja')}</text>
      <rect className="dg-bar-2" x={X0 + 214} y={12} width={12} height={12} />
      <text className="dg-bar-label" x={X0 + 232} y={22}>{t('Cash-flow dependent', 'Dependiente de flujos de caja')}</text>
      {plain.map((v, i) => (
        <g key={i}>
          <rect className="dg-bar" x={r1(X0 + i * slot + slot * 0.12)} y={r1(y(v))} width={r1(slot * 0.36)} height={r1(Y0 - y(v))} />
          <rect className="dg-bar-2" x={r1(X0 + i * slot + slot * 0.5)} y={r1(y(cash[i]))} width={r1(slot * 0.36)} height={r1(Y0 - y(cash[i]))} />
          <text className="dg-bar-label" x={r1(X0 + i * slot + slot * 0.3)} y={r1(y(v) - 4)} textAnchor="middle">{n(v)}</text>
          <text className="dg-bar-label" x={r1(X0 + i * slot + slot * 0.68)} y={r1(y(cash[i]) - 4)} textAnchor="middle">{n(cash[i])}</text>
          <text className="dg-bar-label" x={r1(X0 + i * slot + slot / 2)} y={Y0 + 15} textAnchor="middle">{edges[i]}</text>
        </g>
      ))}
      <text className="dg-axis-label" x={(X0 + X1) / 2} y={Y0 + 36} textAnchor="middle">{t('LTV, upper edge of the band (percent)', 'LTV, borde superior del tramo (por ciento)')}</text>
      <text className="dg-note" x={FW - 8} y={FH - 6} textAnchor="end">{t('CRE20 Tables 11 and 12, as published', 'CRE20 Tablas 11 y 12, como se publican')}</text>
    </svg>
  );
}

/** The RBC20.13 example as bars: the bank's own RWA, the floor base and the result with and without the optional cap. */
function FloorFigure() {
  const lang = useShellLang();
  const t = useT();
  const bars: Array<{ v: number; cls: string; l1: string; l2: string }> = [
    { v: 76, cls: 'dg-bar', l1: t('Own approaches', 'Enfoques propios'), l2: t('(pre-floor)', '(previo al piso)') },
    { v: 101.5, cls: 'dg-bar-2', l1: t('72.5 % of the', '72,5 % de los'), l2: t('standardised RWA', 'RWA estandarizados') },
    { v: 95, cls: 'dg-bar', l1: t('With the 25 % cap', 'Con el tope de 25 %'), l2: t('on the increase', 'sobre el aumento') },
  ];
  const Y0 = 196;
  const Y1 = 34;
  const y = (v: number) => Y0 - (v / 110) * (Y0 - Y1);
  const cx = [120, 240, 360];
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${FW} ${FH}`} role="img" aria-label={t('Three bars of the RBC20.13 example in index points: the RWA of the bank own approaches 76, the floor base of 72.5 percent of the standardised RWA of 140, which is 101.5, and the result with the optional cap on the increase at 25 percent of the pre-floor RWA, which is 95', 'Tres barras del ejemplo de RBC20.13 en puntos índice: los RWA de los enfoques propios del banco 76, la base del piso de 72,5 por ciento de los RWA estandarizados de 140, que es 101,5, y el resultado con el tope opcional del aumento en 25 por ciento de los RWA previos al piso, que es 95')}>
      <line className="dg-axis" x1={40} y1={Y0} x2={440} y2={Y0} />
      {bars.map((b, i) => (
        <g key={i}>
          <rect className={b.cls} x={cx[i] - 38} y={r1(y(b.v))} width={76} height={r1(Y0 - y(b.v))} />
          <text className="dg-bar-label" x={cx[i]} y={r1(y(b.v) - 6)} textAnchor="middle">{formatNumber(b.v, lang)}</text>
          <text className="dg-bar-label" x={cx[i]} y={Y0 + 16} textAnchor="middle">{b.l1}</text>
          <text className="dg-bar-label" x={cx[i]} y={Y0 + 30} textAnchor="middle">{b.l2}</text>
        </g>
      ))}
      <line className="dg-marker" x1={40} y1={r1(y(76))} x2={440} y2={r1(y(76))} />
      <text className="dg-axis-label" x={FW - 8} y={14} textAnchor="end">{t('Index points', 'Puntos índice')}</text>
      <text className="dg-note" x={FW - 8} y={FH - 6} textAnchor="end">{t('RBC20.13 example, as published', 'Ejemplo de RBC20.13, como se publica')}</text>
    </svg>
  );
}

/** The aggregation tree of MAR21.4: weighted sensitivities into bucket charges, bucket charges across buckets, the maximum of three scenarios. */
function SbmFigure() {
  const t = useT();
  const leaf = (cx: number, label: string) => (
    <g key={label}>
      <rect className="dg-box" x={cx - 24} y={206} width={48} height={26} rx={5} />
      <text className="dg-node-label" x={cx} y={223} textAnchor="middle">{label}</text>
    </g>
  );
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${FW} ${FH}`} role="img" aria-label={t('A tree: four weighted sensitivities, two in each bucket, aggregate with the within-bucket correlation rho into one charge per bucket; the two bucket charges aggregate across buckets with the correlation gamma and the signed sums into one charge per correlation scenario; the capital charge is the maximum of the three scenarios', 'Un árbol: cuatro sensibilidades ponderadas, dos en cada bucket, se agregan con la correlación interna rho en un cargo por bucket; los dos cargos se agregan entre buckets con la correlación gamma y las sumas con signo en un cargo por escenario de correlación; el cargo de capital es el máximo de los tres escenarios')}>
      {[55, 125, 295, 365].map((cx) => (
        <line key={cx} className="dg-edge" x1={cx} y1={206} x2={cx < 200 ? 90 : 330} y2={160} />
      ))}
      {[90, 330].map((cx) => (
        <line key={cx} className="dg-edge" x1={cx} y1={130} x2={cx < 200 ? 190 : 290} y2={92} />
      ))}
      <line className="dg-edge" x1={240} y1={60} x2={240} y2={38} />
      {leaf(55, 'WS1')}
      {leaf(125, 'WS2')}
      {leaf(295, 'WS3')}
      {leaf(365, 'WS4')}
      <text className="dg-edge-label" x={40} y={184} textAnchor="end">ρ</text>
      <text className="dg-edge-label" x={420} y={184} textAnchor="start">ρ</text>
      <rect className="dg-box accent" x={30} y={130} width={120} height={30} rx={6} />
      <text className="dg-box-title accent" x={90} y={149} textAnchor="middle">{t('Bucket 1: Kb1', 'Bucket 1: Kb1')}</text>
      <rect className="dg-box accent" x={270} y={130} width={120} height={30} rx={6} />
      <text className="dg-box-title accent" x={330} y={149} textAnchor="middle">{t('Bucket 2: Kb2', 'Bucket 2: Kb2')}</text>
      <text className="dg-edge-label" x={130} y={108} textAnchor="end">Sb</text>
      <text className="dg-edge-label" x={350} y={108} textAnchor="start">Sb</text>
      <rect className="dg-box" x={110} y={60} width={260} height={32} rx={6} />
      <text className="dg-box-title" x={240} y={80} textAnchor="middle">{t('Across buckets: gamma, Sb', 'Entre buckets: gamma, Sb')}</text>
      <rect className="dg-box good" x={90} y={6} width={300} height={32} rx={6} />
      <text className="dg-box-title" x={240} y={26} textAnchor="middle">{t('Maximum of low, medium and high', 'Máximo de bajo, medio y alto')}</text>
      <text className="dg-note" x={FW - 8} y={FH - 6} textAnchor="end">{t('MAR21.4 to MAR21.7, schematic', 'MAR21.4 a MAR21.7, esquema')}</text>
    </svg>
  );
}

/** The nested subsets of the cascade: all factors, then those with a horizon of at least 20, 40, 60 and 120 days, each with its weight. */
function CascadeFigure() {
  const lang = useShellLang();
  const t = useT();
  const boxes = [
    { j: 1, lh: 10, x: 20, y: 8, w: 440, h: 244, w1: null as number | null },
    { j: 2, lh: 20, x: 60, y: 52, w: 360, h: 200, w1: 1 },
    { j: 3, lh: 40, x: 100, y: 96, w: 280, h: 156, w1: 2 },
    { j: 4, lh: 60, x: 140, y: 140, w: 200, h: 112, w1: 2 },
    { j: 5, lh: 120, x: 180, y: 184, w: 120, h: 68, w1: 6 },
  ];
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${FW} ${FH}`} role="img" aria-label={t('Five nested boxes: all risk factors with a liquidity horizon of at least 10 days, then the subsets with at least 20, 40, 60 and 120 days, each inside the one before; the subsets after the first enter the expected shortfall with the weights square root of 1, 2, 2 and 6 for a base horizon of 10 days', 'Cinco cajas anidadas: todos los factores de riesgo con horizonte de liquidez de al menos 10 días, luego los subconjuntos con al menos 20, 40, 60 y 120 días, cada uno dentro del anterior; los subconjuntos posteriores al primero entran al déficit esperado con los pesos raíz de 1, 2, 2 y 6 para un horizonte base de 10 días')}>
      {boxes.map((b) => (
        <g key={b.j}>
          <rect className={b.j === 1 ? 'dg-box' : 'dg-box accent'} x={b.x} y={b.y} width={b.w} height={b.h} rx={8} />
          <text className="dg-box-title" x={b.x + 10} y={b.y + 17}>
            {b.j === 1 ? t('P: every factor, LH at least 10 days', 'P: todo factor, LH de al menos 10 días') : `Q${b.j}: LH ≥ ${b.lh}${b.w >= 200 ? ` ${t('days', 'días')}` : ''}`}
          </text>
          <text className="dg-box-sub" x={b.x + 10} y={b.y + 33}>
            {b.w1 === null ? 'ES_T(P)' : `ES_T(P, ${b.j}) × ${b.w1 === 1 ? '1' : `√${formatNumber(b.w1, lang)}`}`}
          </text>
        </g>
      ))}
    </svg>
  );
}

/** The SA-CCR multiplier of CRE52.23 against (V - C) / AddOn, with the 5 percent floor and the point of CRE99 netting set 2. */
function MultiplierFigure() {
  const lang = useShellLang();
  const t = useT();
  const floor = 0.05;
  const m = (x: number) => Math.min(1, floor + (1 - floor) * Math.exp(x / (2 * (1 - floor))));
  const X0 = 56;
  const X1 = 456;
  const Y0 = 204;
  const Y1 = 30;
  const x = (u: number) => X0 + ((u + 4) / 5) * (X1 - X0);
  const y = (v: number) => Y0 - v * (Y0 - Y1);
  const pts = Array.from({ length: 101 }, (_, i) => -4 + (i * 5) / 100);
  const d = pts.map((u, i) => `${i ? 'L' : 'M'}${r1(x(u))} ${r1(y(m(u)))}`).join(' ');
  const ex = -20 / 282;
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${FW} ${FH}`} role="img" aria-label={t('The SA-CCR multiplier against the ratio of the net value minus collateral to the add-on: it equals 1 from a ratio of 0 upward, falls as the position becomes more over-collateralised and tends to the floor of 5 percent; the point of CRE99 netting set 2 is at a ratio of minus 20 over 282 and a multiplier of 0.965', 'El multiplicador de SA-CCR contra la razón del valor neto menos las garantías sobre el recargo: vale 1 desde una razón de 0 hacia arriba, cae a medida que la posición queda más sobrecolateralizada y tiende al piso de 5 por ciento; el punto del conjunto 2 de CRE99 está en una razón de menos 20 sobre 282 y un multiplicador de 0,965')}>
      <line className="dg-axis" x1={X0} y1={Y0} x2={X1} y2={Y0} />
      <line className="dg-axis" x1={X0} y1={Y0} x2={X0} y2={Y1} />
      {[-4, -3, -2, -1, 0, 1].map((u) => (
        <text key={u} className="dg-tick" x={r1(x(u))} y={Y0 + 16} textAnchor="middle">{formatNumber(u, lang)}</text>
      ))}
      {[0, 0.5, 1].map((v) => (
        <text key={v} className="dg-tick" x={X0 - 6} y={r1(y(v) + 4)} textAnchor="end">{formatNumber(v, lang)}</text>
      ))}
      <line className="dg-asymptote" x1={X0} y1={r1(y(floor))} x2={X1} y2={r1(y(floor))} />
      <text className="dg-axis-label" x={X1} y={r1(y(floor) - 6)} textAnchor="end">{t('floor 5 %', 'piso de 5 %')}</text>
      <path className="dg-curve" d={d} />
      <circle className="dg-node" cx={r1(x(ex))} cy={r1(y(m(ex)))} r={5} />
      <text className="dg-axis-label" x={r1(x(ex) - 10)} y={r1(y(m(ex)) + 24)} textAnchor="end">{t('CRE99 set 2: 0.965', 'CRE99 conjunto 2: 0,965')}</text>
      <text className="dg-axis-label" x={(X0 + X1) / 2} y={Y0 + 36} textAnchor="middle">{t('(V − C) / aggregate add-on', '(V − C) / recargo agregado')}</text>
      <text className="dg-axis-label" x={14} y={(Y0 + Y1) / 2} textAnchor="middle" transform={`rotate(-90 14 ${(Y0 + Y1) / 2})`}>{t('Multiplier', 'Multiplicador')}</text>
      <text className="dg-note" x={FW - 8} y={18} textAnchor="end">{t('CRE52.23, from the formula', 'CRE52.23, desde la fórmula')}</text>
    </svg>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// the five parts

export function CreditPart({ doc, reason }: DocProps) {
  return (
    <>
      <P
        en={<>In the standardised approach a bank does not model the probability of default of an exposure: the Basel framework assigns a risk weight from a table, and the risk-weighted amount is the exposure, after its credit conversion factor and any adjustment, times that weight. Contraste carries the tables of CRE20 as data with their paragraph, in the chapter version in force since 2023-01-01 (published 2025-06-10; a further version scheduled for 2028-01-01 is not compared) <Cite id="regcre20" />. A validator needs them for two reasons: the output of an internal model is read against the standardised one, which is what the output floor of the next part does, and a model whose purpose is to replace a table weight has to be shown to land where the table does, or to say why it does not.</>}
        es={<>En el enfoque estandarizado el banco no modela la probabilidad de incumplimiento de una exposición: el marco de Basilea asigna un ponderador de riesgo desde una tabla, y el monto ponderado por riesgo es la exposición, tras su factor de conversión de crédito y cualquier ajuste, por ese ponderador. Contraste lleva las tablas de CRE20 como datos con su párrafo, en la versión del capítulo vigente desde 2023-01-01 (publicada el 2025-06-10; otra versión prevista para el 2028-01-01 no se compara) <Cite id="regcre20" />. Un validador las necesita por dos razones: el resultado de un modelo interno se lee frente al estandarizado, que es lo que hace el piso de salida de la parte siguiente, y un modelo cuyo propósito es reemplazar el ponderador de una tabla debe mostrar que cae donde cae la tabla, o explicar por qué no.</>}
      />
      <P
        en={<>For the jurisdictions that allow external ratings (ECRA) sovereigns and central banks weigh 0, 20, 50, 100 and 150 percent from AAA to AA- down to below B-, and 100 percent unrated (<Ref>CRE20.7</Ref> Table 1); where only an export credit agency score exists the weights run 0, 0, 20, 50, 100, 100, 100 and 150 percent for the scores 0 to 7 (<Ref>CRE20.9</Ref> Table 2). Banks weigh 20, 30, 50, 100 and 150 percent by rating, or 20, 20, 20, 50 and 150 percent for short-term exposures (<Ref>CRE20.18</Ref> Table 6), and an unrated bank falls to the standardised credit risk assessment (SCRA): grade A 40 percent (20 short-term), grade B 75 percent (50) and grade C 150 percent (<Ref>CRE20.21</Ref> Table 7). Corporates weigh 20, 50, 75, 100 and 150 percent by rating and 100 percent unrated (<Ref>CRE20.43</Ref> Table 10); where ratings are not allowed an investment-grade corporate weighs 65 percent (<Ref>CRE20.44</Ref> and <Ref>CRE20.46</Ref>), an unrated small or medium enterprise 85 percent and a regulatory retail one 75 percent (<Ref>CRE20.47</Ref>).</>}
        es={<>Para las jurisdicciones que permiten calificaciones externas (ECRA), los soberanos y bancos centrales ponderan 0, 20, 50, 100 y 150 por ciento desde AAA a AA- hasta bajo B-, y 100 por ciento sin calificación (<Ref>CRE20.7</Ref> Tabla 1); donde solo existe un puntaje de agencia de crédito a la exportación, los ponderadores son 0, 0, 20, 50, 100, 100, 100 y 150 por ciento para los puntajes de 0 a 7 (<Ref>CRE20.9</Ref> Tabla 2). Los bancos ponderan 20, 30, 50, 100 y 150 por ciento según su calificación, o 20, 20, 20, 50 y 150 por ciento si la exposición es de corto plazo (<Ref>CRE20.18</Ref> Tabla 6), y un banco sin calificación pasa a la evaluación estandarizada del riesgo de crédito (SCRA): grado A 40 por ciento (20 de corto plazo), grado B 75 por ciento (50) y grado C 150 por ciento (<Ref>CRE20.21</Ref> Tabla 7). Las empresas ponderan 20, 50, 75, 100 y 150 por ciento según su calificación y 100 por ciento sin calificación (<Ref>CRE20.43</Ref> Tabla 10); donde no se permiten calificaciones, una empresa con grado de inversión pondera 65 por ciento (<Ref>CRE20.44</Ref> y <Ref>CRE20.46</Ref>), una pyme sin calificación 85 por ciento y una pyme minorista regulatoria 75 por ciento (<Ref>CRE20.47</Ref>).</>}
      />
      <P
        en={<>Retail exposures weigh 75 percent as regulatory retail, 45 percent for transactors and 100 percent for the rest (<Ref>CRE20.68</Ref>). Equity weighs 250 percent, speculative unlisted equity 400 percent and equity in legislated programmes 100 percent up to 10 percent of Total capital, and subordinated debt and non-equity capital instruments weigh 150 percent (<Ref>CRE20.57</Ref> to <Ref>CRE20.60</Ref>). A defaulted exposure, 90 days past due or unlikely to pay, weighs 150 percent on its unsecured portion when the specific provisions are below 20 percent of the outstanding amount and 100 percent from 20 percent, and defaulted residential real estate that does not depend on cash flows weighs 100 percent (<Ref>CRE20.104</Ref> to <Ref>CRE20.107</Ref>). None of these needs a model; each needs the right key, and a validator&apos;s first check of a standardised calculation is that every exposure sits in the right row.</>}
        es={<>Las exposiciones minoristas ponderan 75 por ciento como minorista regulatorio, 45 por ciento para los transactores y 100 por ciento el resto (<Ref>CRE20.68</Ref>). Las acciones ponderan 250 por ciento, las acciones especulativas no listadas 400 por ciento y las de programas legislados 100 por ciento hasta 10 por ciento del capital total, y la deuda subordinada y los instrumentos de capital que no son acciones ponderan 150 por ciento (<Ref>CRE20.57</Ref> a <Ref>CRE20.60</Ref>). Una exposición en incumplimiento, con 90 días de mora o improbable pago, pondera 150 por ciento en su parte sin garantía cuando las provisiones específicas son menos de 20 por ciento del monto pendiente y 100 por ciento desde 20 por ciento, y un inmueble residencial en incumplimiento que no depende de flujos de caja pondera 100 por ciento (<Ref>CRE20.104</Ref> a <Ref>CRE20.107</Ref>). Ninguna necesita un modelo; todas necesitan la clave correcta, y la primera comprobación de un validador en un cálculo estandarizado es que cada exposición esté en la fila que corresponde.</>}
      />
      <Equation
        tex={String.raw`\mathrm{RWA} = E\cdot\mathrm{CCF}\cdot RW, \qquad RW^{\mathrm{adj}} = \min\bigl(1.5\,RW,\ 150\%\bigr)`}
        caption={<T en={<>The risk-weighted amount of one exposure and the currency-mismatch adjustment (dossier 01, C; <Ref>CRE20.92</Ref> and <Ref>CRE20.94</Ref> to <Ref>CRE20.101</Ref>): E the exposure, CCF the credit conversion factor (1 for an on-balance-sheet item, 0.1 to 1 for an off-balance-sheet one), RW the weight of the table by class, rating or loan to value, and RW<sup>adj</sup> the weight of an unhedged retail or residential exposure to an individual whose currency differs from that of the income, 1.5 times the weight and at most 150 percent. The calculator below returns RW with its table, paragraph and in-force date and then does this arithmetic per 100 of exposure.</>} es={<>El monto ponderado por riesgo de una exposición y el ajuste por descalce de moneda (dossier 01, C; <Ref>CRE20.92</Ref> y <Ref>CRE20.94</Ref> a <Ref>CRE20.101</Ref>): E la exposición, CCF el factor de conversión de crédito (1 para una partida de balance, de 0,1 a 1 para una fuera de balance), RW el ponderador de la tabla según clase, calificación o relación préstamo-valor, y RW<sup>adj</sup> el ponderador de una exposición minorista o residencial a una persona natural, sin cobertura, cuya moneda difiere de la de sus ingresos, 1,5 veces el ponderador y a lo más 150 por ciento. La calculadora de abajo devuelve RW con su tabla, párrafo y fecha de vigencia y luego hace esta aritmética por cada 100 de exposición.</>} />}
      />
      <P
        en={<>Real estate is where the lookup becomes a step function. A residential whole loan whose repayment does not depend on the property&apos;s cash flows weighs 20, 25, 30, 40, 50 and 70 percent as the loan to value rises through 50, 60, 80, 90 and 100 percent (<Ref>CRE20.82</Ref> Table 11), with a loan-splitting alternative that weighs 20 percent up to 55 percent of the property value (<Ref>CRE20.83</Ref>); when repayment does depend on them the weights are 30, 35, 45, 60, 75 and 105 percent on the same bands (<Ref>CRE20.84</Ref> Table 12). Commercial real estate takes the lower of 60 percent and the counterparty&apos;s weight up to a loan to value of 60 percent, and the counterparty&apos;s weight above it (<Ref>CRE20.85</Ref> Table 13), or 70, 90 and 110 percent up to 60, up to 80 and above 80 percent when it depends on cash flows (<Ref>CRE20.87</Ref> Table 14). The conversion factors of the off-balance-sheet items are 100 percent for direct credit substitutes, repos, securities lending and forward purchases, 50 percent for note issuance facilities and transaction-related contingents, 40 percent for commitments, 20 percent for short-term self-liquidating trade letters of credit and 10 percent when unconditionally cancellable (<Ref>CRE20.94</Ref> to <Ref>CRE20.101</Ref>).</>}
        es={<>Los inmuebles son donde la consulta se vuelve una función escalonada. Un préstamo hipotecario residencial cuyo pago no depende de los flujos de caja de la propiedad pondera 20, 25, 30, 40, 50 y 70 por ciento a medida que la relación préstamo-valor pasa por 50, 60, 80, 90 y 100 por ciento (<Ref>CRE20.82</Ref> Tabla 11), con una alternativa de división del préstamo que pondera 20 por ciento hasta 55 por ciento del valor de la propiedad (<Ref>CRE20.83</Ref>); cuando el pago sí depende de ellos, los ponderadores son 30, 35, 45, 60, 75 y 105 por ciento en los mismos tramos (<Ref>CRE20.84</Ref> Tabla 12). Los inmuebles comerciales toman el menor entre 60 por ciento y el ponderador de la contraparte hasta una relación préstamo-valor de 60 por ciento, y el ponderador de la contraparte sobre ella (<Ref>CRE20.85</Ref> Tabla 13), o 70, 90 y 110 por ciento hasta 60, hasta 80 y sobre 80 por ciento cuando dependen de flujos de caja (<Ref>CRE20.87</Ref> Tabla 14). Los factores de conversión de las partidas fuera de balance son 100 por ciento para los sustitutos directos de crédito, las recompras, el préstamo de valores y las compras a plazo, 50 por ciento para las facilidades de emisión de pagarés y los contingentes ligados a transacciones, 40 por ciento para los compromisos, 20 por ciento para las cartas de crédito comerciales de corto plazo con autoliquidación y 10 por ciento cuando son cancelables incondicionalmente (<Ref>CRE20.94</Ref> a <Ref>CRE20.101</Ref>).</>}
      />
      <Equation
        tex={String.raw`RW(\mathrm{LTV}) = RW_b \ \text{ if } \ \mathrm{LTV}_{b-1} < \mathrm{LTV} \le \mathrm{LTV}_b, \qquad RW_{\mathrm{CRE}}(\mathrm{LTV}) = \begin{cases}\min\bigl(60\%,\ RW_{\mathrm{cp}}\bigr) & \mathrm{LTV} \le 60\% \\[2pt] RW_{\mathrm{cp}} & \mathrm{LTV} > 60\%\end{cases}`}
        caption={<T en={<>The step function of the real estate tables (dossier 01, C; <Ref>CRE20.82</Ref> to <Ref>CRE20.87</Ref>): b the LTV band, LTV<sub>b</sub> its upper edge and RW<sub>b</sub> its weight, so the upper edge of a band belongs to it and a loan to value above the last edge takes the last band; the second line is commercial real estate that does not depend on cash flows (Table 13), RW<sub>cp</sub> the weight of the counterparty. The calculator draws these steps from the cells of the document and marks the loan to value the reader sets; it computes no weight of its own.</>} es={<>La función escalonada de las tablas de inmuebles (dossier 01, C; <Ref>CRE20.82</Ref> a <Ref>CRE20.87</Ref>): b el tramo de LTV, LTV<sub>b</sub> su borde superior y RW<sub>b</sub> su ponderador, de modo que el borde superior de un tramo le pertenece y una relación préstamo-valor sobre el último borde toma el último tramo; la segunda línea es el inmueble comercial que no depende de flujos de caja (Tabla 13), RW<sub>cp</sub> el ponderador de la contraparte. La calculadora dibuja estos escalones desde las celdas del documento y marca la relación préstamo-valor que fija el lector; no calcula ningún ponderador propio.</>} />}
      />
      <Figure caption={<T en="Tables 11 and 12 of CRE20 side by side: the residential weights by loan-to-value band, with and without dependence on the property's cash flows, as published. The bars are the published weights and not a result of any bank." es="Las Tablas 11 y 12 de CRE20 lado a lado: los ponderadores residenciales por tramo de relación préstamo-valor, con y sin dependencia de los flujos de caja de la propiedad, como se publican. Las barras son los ponderadores publicados y no un resultado de ningún banco." />}>
        <CreditFigure />
      </Figure>
      <FixtureNote doc={doc} />
      <Cre20Card doc={doc} reason={reason} />
    </>
  );
}

export function FloorPart({ doc, reason }: DocProps) {
  return (
    <>
      <P
        en={<>The output floor limits how far a bank&apos;s own models can lower its capital below what the standardised approaches would require. The total risk-weighted assets are the larger of the assets the bank computes with its approved approaches and a fraction f of the assets computed with the standardised approaches alone (<Ref>RBC20.4</Ref>) <Cite id="regrbc20" />. The minimums it applies to are 4.5 percent of the RWA for Common Equity Tier 1, 6 percent for Tier 1 and 8 percent for Total capital, plus the 2.5 percent conservation buffer (<Ref>RBC20.1</Ref>). A floor that binds is the clearest sign that a bank&apos;s internal models and the standardised approaches disagree about its portfolio, and a validator reads the gap as a question about the models, not as a capital detail.</>}
        es={<>El piso de salida limita cuánto pueden bajar los modelos propios de un banco su capital por debajo de lo que exigirían los enfoques estandarizados. Los activos ponderados por riesgo totales son el mayor entre los activos que el banco calcula con sus enfoques aprobados y una fracción f de los activos calculados solo con los enfoques estandarizados (<Ref>RBC20.4</Ref>) <Cite id="regrbc20" />. Los mínimos a los que se aplica son 4,5 por ciento de los RWA para el capital común de nivel 1, 6 por ciento para el nivel 1 y 8 por ciento para el capital total, más el colchón de conservación de 2,5 por ciento (<Ref>RBC20.1</Ref>). Un piso vinculante es la señal más clara de que los modelos internos del banco y los enfoques estandarizados discrepan sobre su cartera, y el validador lee la brecha como una pregunta sobre los modelos, no como un detalle de capital.</>}
      />
      <P
        en={<>The floor base takes only the standardised approaches (<Ref>RBC20.11</Ref>); the internal ratings-based approaches, the securitisation internal ratings-based approach, the internal models approach for market risk, the VaR models approach to counterparty credit risk and the internal model method are excluded from it (<Ref>RBC20.12</Ref>). The factor is phased in by year: 50 percent from 2023-01-01, 55 percent from 2024, 60 percent from 2025, 65 percent from 2026, 70 percent from 2027 and 72.5 percent from 2028 (<Ref>RBC90.1</Ref> Table 1) <Cite id="regrbc90" />. During the phase-in a jurisdiction may cap the increase in RWA that the floor causes at 25 percent of the pre-floor RWA (<Ref>RBC90.2</Ref>), an option the calculator below offers as a switch.</>}
        es={<>La base del piso toma solo los enfoques estandarizados (<Ref>RBC20.11</Ref>); quedan fuera de ella los enfoques basados en calificaciones internas, el enfoque de calificaciones internas para titulizaciones, el enfoque de modelos internos para riesgo de mercado, el enfoque de modelos VaR para el riesgo de crédito de contraparte y el método de modelos internos (<Ref>RBC20.12</Ref>). El factor se implementa por año: 50 por ciento desde 2023-01-01, 55 por ciento desde 2024, 60 por ciento desde 2025, 65 por ciento desde 2026, 70 por ciento desde 2027 y 72,5 por ciento desde 2028 (<Ref>RBC90.1</Ref> Tabla 1) <Cite id="regrbc90" />. Durante la implementación una jurisdicción puede limitar el aumento de RWA que causa el piso a 25 por ciento de los RWA previos al piso (<Ref>RBC90.2</Ref>), una opción que la calculadora de abajo ofrece como interruptor.</>}
      />
      <Equation
        tex={String.raw`\mathrm{RWA} = \max\bigl(\mathrm{RWA}_{\mathrm{nominated}},\ f_t\cdot\mathrm{RWA}_{\mathrm{SA\text{-}only}}\bigr), \qquad f_{2023},\dots,f_{2028} = 50,\ 55,\ 60,\ 65,\ 70,\ 72.5\ \%`}
        caption={<T en={<>The output floor and its phase-in (dossier 01, C.1; <Ref>RBC20.4</Ref> and <Ref>RBC90.1</Ref>): RWA_nominated the assets computed with the approaches the bank has approved, RWA<sub>SA</sub>-only those computed with the standardised approaches alone, and f<sub>t</sub> the factor of year t. The result is never below the nominated assets. The factor is the BCBS schedule; the dates a jurisdiction applies differ (section L of the dossier).</>} es={<>El piso de salida y su implementación (dossier 01, C.1; <Ref>RBC20.4</Ref> y <Ref>RBC90.1</Ref>): RWA_nominated los activos calculados con los enfoques que el banco tiene aprobados, RWA<sub>SA</sub>-only los calculados solo con los enfoques estandarizados, y f<sub>t</sub> el factor del año t. El resultado nunca queda bajo los activos nominados. El factor es el calendario del BCBS; las fechas que aplica cada jurisdicción difieren (sección L del dossier).</>} />}
      />
      <P
        en={<>The worked example of <Ref>RBC20.13</Ref> has a bank whose own approaches give 76 and whose standardised approaches give 140: at the fully phased-in factor of 72.5 percent the floor base is 101.5, above 76, so the floor binds and the result is 101.5; with the optional cap the increase is limited to 25 percent of 76, which is 19, and the result is 95. Contraste reproduces both values exactly and holds the live calculator to them. Two limits are stated. The calculator carries the BCBS schedule only, because the document carries only that one; the European Union applies 50 percent in 2025 and 72.5 percent from 2030 under the amended Article 465(1) of Regulation (EU) 2024/1623, the United Kingdom&apos;s schedule is reported in search summaries that were not re-read, and no United States rule is final. And the factor multiplies standardised assets that the reader types in: a bank&apos;s full standardised calculation is the sum of the tables of the previous part over its book.</>}
        es={<>El ejemplo resuelto de <Ref>RBC20.13</Ref> tiene un banco cuyos enfoques propios dan 76 y cuyos enfoques estandarizados dan 140: con el factor totalmente implementado de 72,5 por ciento la base del piso es 101,5, sobre 76, así que el piso es vinculante y el resultado es 101,5; con el tope opcional el aumento se limita a 25 por ciento de 76, que es 19, y el resultado es 95. Contraste reproduce ambos valores exactamente y sujeta la calculadora en vivo a ellos. Se declaran dos límites. La calculadora lleva solo el calendario del BCBS, porque el documento lleva solo ese; la Unión Europea aplica 50 por ciento en 2025 y 72,5 por ciento desde 2030 según el artículo 465(1) modificado del Reglamento (UE) 2024/1623, el calendario del Reino Unido figura en resúmenes de búsqueda que no se volvieron a leer, y ninguna norma de Estados Unidos es definitiva. Y el factor multiplica activos estandarizados que escribe el lector: el cálculo estandarizado completo de un banco es la suma de las tablas de la parte anterior sobre su cartera.</>}
      />
      <P
        en={<>How a validator reads the floor follows from that arithmetic. The ratio of the nominated assets to the standardised ones is the first diagnostic: in the example the bank&apos;s own approaches give 76 of a standardised 140, 54 percent (recomputed here), against a floor of 72.5 percent, so the models would lower the requirement by far more than the framework lets them. The factor also decides whether the floor bites at all: at the 50 percent of 2023 the floor base is 0.5 × 140 = 70, below the nominated 76, and the floor does not bind, while from 2024, at 55 percent, it does (77 against 76). That is why the phase-in year is a control of the calculator and not a footnote. The example is written in index points because the framework prints it without a currency; a bank&apos;s own figures are in its reporting currency and the factor does not depend on the unit.</>}
        es={<>La lectura del piso por un validador se sigue de esa aritmética. La razón de los activos nominados a los estandarizados es el primer diagnóstico: en el ejemplo los enfoques propios del banco dan 76 de unos 140 estandarizados, 54 por ciento (recalculado aquí), frente a un piso de 72,5 por ciento, de modo que los modelos bajarían el requerimiento mucho más de lo que el marco permite. El factor decide además si el piso muerde: con el 50 por ciento de 2023 la base del piso es 0,5 × 140 = 70, bajo los 76 nominados, y el piso no es vinculante, mientras que desde 2024, con 55 por ciento, sí lo es (77 contra 76). Por eso el año de implementación es un control de la calculadora y no una nota al pie. El ejemplo está escrito en puntos índice porque el marco lo imprime sin moneda; las cifras de un banco están en su moneda de reporte y el factor no depende de la unidad.</>}
      />
      <Equation
        tex={String.raw`\mathrm{RWA}^{\mathrm{cap}} = \min\bigl(\mathrm{RWA},\ (1 + 25\%)\,\mathrm{RWA}_{\mathrm{nominated}}\bigr), \qquad \max(76,\ 0.725\times 140) = 101.5, \quad \min(101.5,\ 1.25\times 76) = 95`}
        caption={<T en={<>The optional cap of the transition and the worked example (dossier 01, C.1; <Ref>RBC90.2</Ref> and <Ref>RBC20.13</Ref>): RWA<sup>cap</sup> the assets after the floor and the cap, 25 percent the largest increase over the pre-floor assets that the cap allows. With the nominated 76 and the standardised 140 of the example the floor gives 101.5 and the cap 95.</>} es={<>El tope opcional de la transición y el ejemplo resuelto (dossier 01, C.1; <Ref>RBC90.2</Ref> y <Ref>RBC20.13</Ref>): RWA<sup>cap</sup> los activos tras el piso y el tope, 25 por ciento el mayor aumento sobre los activos previos al piso que permite el tope. Con los 76 nominados y los 140 estandarizados del ejemplo el piso da 101,5 y el tope 95.</>} />}
      />
      <Figure caption={<T en="The RBC20.13 example as bars in index points: the bank's own RWA of 76, the floor base of 72.5 percent of the standardised 140, which is 101.5, and the result with the optional cap on the increase, which is 95. The dashed line marks the pre-floor 76." es="El ejemplo de RBC20.13 como barras en puntos índice: los RWA propios del banco, 76, la base del piso de 72,5 por ciento de los 140 estandarizados, que es 101,5, y el resultado con el tope opcional del aumento, que es 95. La línea segmentada marca los 76 previos al piso." />}>
        <FloorFigure />
      </Figure>
      <FixtureNote doc={doc} />
      <FloorCard doc={doc} reason={reason} />
    </>
  );
}

export function SbmPart({ doc, reason }: DocProps) {
  return (
    <>
      <P
        en={<>The standardised approach to market risk adds three charges: the sensitivities-based method, the default risk charge and the residual risk add-on (<Ref>MAR21.1</Ref>) <Cite id="regmar21" />. The sensitivities-based method works on seven risk classes: general interest rate risk (GIRR), credit spread risk for non-securitisations, for securitisations outside the correlation trading portfolio and for the correlation trading portfolio, equity, commodity and foreign exchange. The delta of GIRR is measured at ten tenors, 0.25, 0.5, 1, 2, 3, 5, 10, 15, 20 and 30 years (<Ref>MAR21.8</Ref>), as the change in value for a one basis point shift divided by 0.0001 (<Ref>MAR21.19</Ref>), and the equity delta as the change for a one percent move of the spot divided by 0.01 (<Ref>MAR21.21</Ref>). The sensitivity is per unit of the risk factor, not per basis point: a position worth 4,500 USD per basis point has a delta of 45 million USD per unit of rate.</>}
        es={<>El enfoque estandarizado de riesgo de mercado suma tres cargos: el método de sensibilidades, el cargo por riesgo de incumplimiento y el recargo por riesgo residual (<Ref>MAR21.1</Ref>) <Cite id="regmar21" />. El método de sensibilidades trabaja sobre siete clases de riesgo: riesgo general de tasa de interés (GIRR), riesgo de spread de crédito para no titulizaciones, para titulizaciones fuera de la cartera de negociación de correlación y para esa cartera, acciones, materias primas y tipo de cambio. El delta de GIRR se mide en diez plazos, 0,25, 0,5, 1, 2, 3, 5, 10, 15, 20 y 30 años (<Ref>MAR21.8</Ref>), como el cambio de valor ante un desplazamiento de un punto base dividido por 0,0001 (<Ref>MAR21.19</Ref>), y el delta de acciones como el cambio ante un movimiento de uno por ciento del precio spot dividido por 0,01 (<Ref>MAR21.21</Ref>). La sensibilidad es por unidad del factor de riesgo, no por punto base: una posición que vale 4.500 USD por punto base tiene un delta de 45 millones de USD por unidad de tasa.</>}
      />
      <Equation
        tex={String.raw`WS_k = RW_k\,s_k, \qquad K_b = \sqrt{\max\Bigl(0,\ \sum_k WS_k^2 + \sum_k\sum_{l\ne k}\rho_{kl}\,WS_k\,WS_l\Bigr)}`}
        caption={<T en={<>The within-bucket aggregation of delta and vega (dossier 01, D.2; <Ref>MAR21.4</Ref>): s<sub>k</sub> the sensitivity of risk factor k, RW<sub>k</sub> its risk weight, WS<sub>k</sub> the weighted sensitivity, ρ<sub>kl</sub> the correlation of factors k and l in the bucket and K<sub>b</sub> the bucket charge. One factor gives |WS|; perfectly correlated factors give |sum of WS|; the radicand can be negative, which the maximum with 0 turns into a zero charge.</>} es={<>La agregación dentro del bucket de delta y vega (dossier 01, D.2; <Ref>MAR21.4</Ref>): s<sub>k</sub> la sensibilidad del factor de riesgo k, RW<sub>k</sub> su ponderador de riesgo, WS<sub>k</sub> la sensibilidad ponderada, ρ<sub>kl</sub> la correlación de los factores k y l del bucket y K<sub>b</sub> el cargo del bucket. Un factor da |WS|; factores perfectamente correlacionados dan |suma de WS|; el radicando puede ser negativo, lo que el máximo con 0 vuelve un cargo nulo.</>} />}
      />
      <P
        en={<>The buckets then aggregate with the correlation gamma between buckets, on the signed sum S<sub>b</sub> of the weighted sensitivities of each bucket; if the sum under the root is negative, S<sub>b</sub> is replaced by max[min(sum of WS, K<sub>b</sub>), -K<sub>b</sub>] and the aggregation is redone (<Ref>MAR21.4</Ref>(5)(b)). Because the aggregation depends on the correlations assumed, the framework computes it three times: with the prescribed correlations (the medium scenario), with a high scenario in which every correlation is min(1.25 ρ, 100 percent) and with a low scenario in which every correlation is max(2 ρ - 100 percent, 75 percent of ρ), the same for gamma (<Ref>MAR21.6</Ref>), and the capital charge is the maximum of the three (<Ref>MAR21.7</Ref>). Curvature has its own rule (<Ref>MAR21.5</Ref>): the upward and downward curvature risk positions CVR+ and CVR-, the larger of the two bucket charges, and an indicator that sets to zero the cross term of two negative positions. The calculator below aggregates delta-type weighted sensitivities, which is what a swap book has.</>}
        es={<>Luego los buckets se agregan con la correlación gamma entre buckets, sobre la suma con signo S<sub>b</sub> de las sensibilidades ponderadas de cada bucket; si la suma bajo la raíz es negativa, S<sub>b</sub> se reemplaza por max[min(suma de WS, K<sub>b</sub>), -K<sub>b</sub>] y la agregación se rehace (<Ref>MAR21.4</Ref>(5)(b)). Como la agregación depende de las correlaciones supuestas, el marco la calcula tres veces: con las correlaciones prescritas (el escenario medio), con un escenario alto en que toda correlación es min(1,25 ρ, 100 por ciento) y con un escenario bajo en que toda correlación es max(2 ρ - 100 por ciento, 75 por ciento de ρ), igual para gamma (<Ref>MAR21.6</Ref>), y el cargo de capital es el máximo de los tres (<Ref>MAR21.7</Ref>). La curvatura tiene su propia regla (<Ref>MAR21.5</Ref>): las posiciones de riesgo de curvatura al alza y a la baja CVR+ y CVR-, el mayor de los dos cargos del bucket y un indicador que anula el término cruzado de dos posiciones negativas. La calculadora de abajo agrega sensibilidades ponderadas de tipo delta, que es lo que tiene una cartera de swaps.</>}
      />
      <Equation
        tex={String.raw`\mathrm{SBM}_{\mathrm{sc}} = \sqrt{\sum_b K_b^2 + \sum_b\sum_{c\ne b}\gamma_{bc}\,S_b\,S_c}, \qquad S_b = \sum_{k\in b} WS_k \ \to\ \max\Bigl[\min\Bigl(\sum_{k\in b} WS_k,\ K_b\Bigr),\ -K_b\Bigr]\ \text{if the radicand} < 0`}
        caption={<T en={<>The aggregation across buckets and its fallback (dossier 01, D.2; <Ref>MAR21.4</Ref>(5)(b)): b and c the buckets, γ<sub>bc</sub> their correlation, S<sub>b</sub> the signed sum of the weighted sensitivities of bucket b, which the arrow replaces by the sum limited to the interval from -K<sub>b</sub> to K<sub>b</sub> when the radicand is negative, and SBM<sub>sc</sub> the charge of one correlation scenario. After the replacement the radicand can still be negative; the charge is then zero.</>} es={<>La agregación entre buckets y su recurso (dossier 01, D.2; <Ref>MAR21.4</Ref>(5)(b)): b y c los buckets, γ<sub>bc</sub> su correlación, S<sub>b</sub> la suma con signo de las sensibilidades ponderadas del bucket b, que la flecha reemplaza por la suma limitada al intervalo de -K<sub>b</sub> a K<sub>b</sub> cuando el radicando es negativo, y SBM<sub>sc</sub> el cargo de un escenario de correlación. Tras el reemplazo el radicando aún puede ser negativo; el cargo es entonces cero.</>} />}
      />
      <Equation
        tex={String.raw`\rho^{\mathrm{high}} = \min(1.25\,\rho,\ 1), \quad \rho^{\mathrm{low}} = \max(2\rho - 1,\ 0.75\,\rho), \qquad \mathrm{SBM} = \max\bigl(\mathrm{SBM}^{\mathrm{low}},\ \mathrm{SBM}^{\mathrm{medium}},\ \mathrm{SBM}^{\mathrm{high}}\bigr)`}
        caption={<T en={<>The three correlation scenarios and the capital charge (dossier 01, D.2; <Ref>MAR21.6</Ref> and <Ref>MAR21.7</Ref>): ρ any prescribed correlation of the medium scenario and gamma likewise, so ρ of 0.5 gives 0.375, 0.5 and 0.625. The low scenario can give the largest charge when negative sensitivities offset, so the maximum is taken over all three and never assumed to be the high one.</>} es={<>Los tres escenarios de correlación y el cargo de capital (dossier 01, D.2; <Ref>MAR21.6</Ref> y <Ref>MAR21.7</Ref>): ρ cualquier correlación prescrita del escenario medio y gamma igual, de modo que ρ de 0,5 da 0,375, 0,5 y 0,625. El escenario bajo puede dar el mayor cargo cuando sensibilidades negativas se compensan, así que el máximo se toma sobre los tres y nunca se supone que sea el alto.</>} />}
      />
      <P
        en={<>The GIRR parameters are transcribed from the framework page in force since 2023-01-01 (addendum R7). The delta risk weights of <Ref>MAR21.42</Ref> Table 1 are 1.7, 1.7, 1.6, 1.3, 1.2, 1.1, 1.1, 1.1, 1.1 and 1.1 percent for the ten tenors; for a currency the Basel Committee specifies (EUR, USD, GBP, AUD, JPY, SEK, CAD and the bank&apos;s domestic currency) a bank may at its discretion divide them by the square root of 2 (<Ref>MAR21.44</Ref>), which gives 1.202, 1.202, 1.131, 0.919, 0.849 and 0.778 percent for the tenors of 0.25 to 5 years and longer, recomputed here and shown beside the undivided weights. The correlation of the same tenor on different curves is 99.90 percent (<Ref>MAR21.45</Ref>), the correlations of different tenors on one curve are the matrix of <Ref>MAR21.46</Ref> Table 2, from 100 percent down to 40 percent (0.5 against 5 years is 76.3 percent, 2 against 3 years 98.5 percent, 0.25 against 30 years 40 percent), and the gamma between currencies is 50 percent (<Ref>MAR21.50</Ref>). The curvature shock is the highest delta weight applied to every tenor, 1.7 percent (<Ref>MAR21.99</Ref>); the division by the square root of 2 names the delta weights, so Contraste uses the undivided shock and keeps the divided 1.202 percent as a labelled reading.</>}
        es={<>Los parámetros de GIRR se transcriben de la página del marco vigente desde 2023-01-01 (anexo R7). Los ponderadores de delta de <Ref>MAR21.42</Ref> Tabla 1 son 1,7, 1,7, 1,6, 1,3, 1,2, 1,1, 1,1, 1,1, 1,1 y 1,1 por ciento para los diez plazos; para una moneda que el Comité de Basilea especifica (EUR, USD, GBP, AUD, JPY, SEK, CAD y la moneda local del banco) el banco puede, a su discreción, dividirlos por la raíz cuadrada de 2 (<Ref>MAR21.44</Ref>), lo que da 1,202, 1,202, 1,131, 0,919, 0,849 y 0,778 por ciento para los plazos de 0,25 a 5 años y más largos, recalculados aquí y mostrados junto a los ponderadores sin dividir. La correlación del mismo plazo en curvas distintas es 99,90 por ciento (<Ref>MAR21.45</Ref>), las correlaciones de plazos distintos en una curva son la matriz de <Ref>MAR21.46</Ref> Tabla 2, de 100 por ciento hasta 40 por ciento (0,5 contra 5 años es 76,3 por ciento, 2 contra 3 años 98,5 por ciento, 0,25 contra 30 años 40 por ciento), y la gamma entre monedas es 50 por ciento (<Ref>MAR21.50</Ref>). El choque de curvatura es el mayor ponderador de delta aplicado a todos los plazos, 1,7 por ciento (<Ref>MAR21.99</Ref>); la división por la raíz de 2 nombra los ponderadores de delta, así que Contraste usa el choque sin dividir y deja el 1,202 por ciento dividido como una lectura etiquetada.</>}
      />
      <P
        en={<>The framework publishes no numerical example of the aggregation, so the acceptance tests of the calculator are invariants. The low scenario uses max(2 ρ - 1, 0.75 ρ), the result is the maximum over the three scenarios, one factor gives its absolute weighted sensitivity and perfectly correlated factors give the absolute sum. The document holds two aggregation cases built on them: one with several factors in each of two buckets, and one built to exercise the fallback, two buckets of opposite sign with a gamma of 0.8, where the radicand is negative under the medium and high scenarios and the plain path applies under the low one. Vega follows the same aggregation with its own parameters, a liquidity horizon of 60 days and a risk weight of 100 percent for GIRR (<Ref>MAR21.92</Ref> Table 13) and a correlation that is the product of an option-maturity and an underlying-maturity term with a parameter of 1 percent (<Ref>MAR21.93</Ref>); a swap book has no vega, so the calculator does not draw it, and the risk-weight formula of its footnote is not transcribed. For a book in one currency there is a single GIRR bucket and the cross-bucket step does not bind.</>}
        es={<>El marco no publica un ejemplo numérico de la agregación, así que las pruebas de aceptación de la calculadora son invariantes. El escenario bajo usa max(2 ρ - 1, 0,75 ρ), el resultado es el máximo de los tres escenarios, un factor da el valor absoluto de su sensibilidad ponderada y los factores perfectamente correlacionados dan el valor absoluto de la suma. El documento guarda dos casos de agregación construidos sobre ellas: uno con varios factores en cada uno de dos buckets, y otro construido para ejercitar el recurso, dos buckets de signo opuesto con una gamma de 0,8, donde el radicando es negativo bajo los escenarios medio y alto y bajo el escenario bajo se aplica la vía simple. El vega sigue la misma agregación con sus propios parámetros, un horizonte de liquidez de 60 días y un ponderador de 100 por ciento para GIRR (<Ref>MAR21.92</Ref> Tabla 13) y una correlación que es el producto de un término de vencimiento de la opción y otro del vencimiento del subyacente con un parámetro de 1 por ciento (<Ref>MAR21.93</Ref>); una cartera de swaps no tiene vega, así que la calculadora no lo dibuja, y la fórmula del ponderador de su nota al pie no está transcrita. Para una cartera en una sola moneda hay un único bucket de GIRR y el paso entre buckets no es vinculante.</>}
      />
      <Figure caption={<T en="The aggregation of MAR21.4 as a tree: the weighted sensitivities of each bucket aggregate with the within-bucket correlation rho into the bucket charge Kb, the bucket charges aggregate across buckets with gamma and the signed sums Sb into the charge of one scenario, and the capital charge is the maximum over the low, medium and high correlation scenarios. A schematic with no values." es="La agregación de MAR21.4 como un árbol: las sensibilidades ponderadas de cada bucket se agregan con la correlación interna rho en el cargo del bucket Kb, los cargos de los buckets se agregan entre buckets con gamma y las sumas con signo Sb en el cargo de un escenario, y el cargo de capital es el máximo entre los escenarios de correlación baja, media y alta. Un esquema sin valores." />}>
        <SbmFigure />
      </Figure>
      <FixtureNote doc={doc} />
      <SbmCard doc={doc} reason={reason} />
    </>
  );
}

export function CascadePart({ doc, reason }: DocProps) {
  return (
    <>
      <P
        en={<>Under the internal models approach the market risk capital rests on the expected shortfall at the 97.5th percentile, one-tailed, computed daily for the bank and for each desk (<Ref>MAR33.2</Ref> to <Ref>MAR33.3</Ref>) <Cite id="regmar33" />. The base horizon is T = 10 days, with no scaling up from a shorter one (<Ref>MAR33.4</Ref>), and a risk factor that cannot be liquidated in 10 days needs a longer horizon. The framework fixes five liquidity horizons, 10, 20, 40, 60 and 120 days (<Ref>MAR33.4</Ref> Table 1), and assigns each risk factor class to one (<Ref>MAR33.12</Ref> Table 2): interest rates of the specified currencies and the large-cap equity price and the specified currency pairs sit at 10 days, other interest rates, sovereign investment-grade spreads, the small-cap equity price, other currency pairs, energy and carbon and metals at 20, and credit spread volatility at 120.</>}
        es={<>En el enfoque de modelos internos, el capital por riesgo de mercado descansa en el déficit esperado al percentil 97,5, de una cola, calculado a diario para el banco y para cada mesa (<Ref>MAR33.2</Ref> a <Ref>MAR33.3</Ref>) <Cite id="regmar33" />. El horizonte base es T = 10 días, sin escalar desde uno más corto (<Ref>MAR33.4</Ref>), y un factor de riesgo que no se puede liquidar en 10 días necesita un horizonte más largo. El marco fija cinco horizontes de liquidez, 10, 20, 40, 60 y 120 días (<Ref>MAR33.4</Ref> Tabla 1), y asigna cada clase de factor de riesgo a uno (<Ref>MAR33.12</Ref> Tabla 2): las tasas de interés de las monedas especificadas, el precio de acciones de gran capitalización y los pares de monedas especificados están en 10 días; otras tasas, los spreads soberanos con grado de inversión, el precio de acciones de pequeña capitalización, otros pares de monedas, energía y carbono y metales en 20, y la volatilidad de los spreads de crédito en 120.</>}
      />
      <Equation
        tex={String.raw`ES = \sqrt{\bigl(ES_T(P)\bigr)^2 + \sum_{j\ge 2}\Bigl(ES_T(P,j)\sqrt{\tfrac{LH_j - LH_{j-1}}{T}}\Bigr)^2}`}
        caption={<T en={<>The liquidity-adjusted expected shortfall (dossier 01, D.3; <Ref>MAR33.4</Ref>): ES<sub>T</sub>(P) the T-day ES with every risk factor shocked, ES<sub>T</sub>(P, j) the T-day ES shocking only the risk factors whose liquidity horizon is at least LH<sub>j</sub>, with the others held constant, LH<sub>j</sub> the horizons of Table 1 and T the 10-day base horizon. The weights are the square roots of (LH<sub>j</sub> - LH_(j-1)) / T: 1, the root of 2, the root of 2 and the root of 6 for the horizons 20, 40, 60 and 120.</>} es={<>El déficit esperado ajustado por liquidez (dossier 01, D.3; <Ref>MAR33.4</Ref>): ES<sub>T</sub>(P) el ES a T días con todos los factores de riesgo sometidos a choque, ES<sub>T</sub>(P, j) el ES a T días con choque solo a los factores cuyo horizonte de liquidez es al menos LH<sub>j</sub>, con los demás constantes, LH<sub>j</sub> los horizontes de la Tabla 1 y T el horizonte base de 10 días. Los pesos son las raíces de (LH<sub>j</sub> - LH_(j-1)) / T: 1, la raíz de 2, la raíz de 2 y la raíz de 6 para los horizontes 20, 40, 60 y 120.</>} />}
      />
      <P
        en={<>The cascade is a nesting. The first subset holds every risk factor; each later subset keeps only the factors whose horizon reaches its own, so the sets shrink as the horizons grow, and the shocks of the factors that were dropped are held constant. Each added term therefore measures the extra loss of the less liquid factors alone, scaled to the time they take to unwind. Two properties are exact and are the acceptance tests of the calculator: if every factor has a horizon of 10 days the cascade returns ES<sub>T</sub>(P) itself, and the result is never below ES<sub>T</sub>(P) and never falls when any ES<sub>T</sub>(P, j) rises. The document holds both as invariant cases, the first with ES<sub>T</sub>(P) = 10 and the second with ES<sub>T</sub>(P) = 10 and ES<sub>T</sub>(P, 2) = 6, which gives the square root of 100 + 36, 11.66.</>}
        es={<>La cascada es un anidamiento. El primer subconjunto contiene todos los factores de riesgo; cada subconjunto posterior conserva solo los factores cuyo horizonte alcanza el propio, de modo que los conjuntos se achican al crecer los horizontes, y los choques de los factores que se dejaron caer se mantienen constantes. Cada término agregado mide así la pérdida adicional de los factores menos líquidos por sí solos, escalada al tiempo que tardan en deshacerse. Dos propiedades son exactas y son las pruebas de aceptación de la calculadora: si todo factor tiene un horizonte de 10 días la cascada devuelve el propio ES<sub>T</sub>(P), y el resultado nunca queda bajo ES<sub>T</sub>(P) ni baja cuando sube cualquier ES<sub>T</sub>(P, j). El documento guarda ambas como casos invariantes, la primera con ES<sub>T</sub>(P) = 10 y la segunda con ES<sub>T</sub>(P) = 10 y ES<sub>T</sub>(P, 2) = 6, que da la raíz de 100 + 36, 11,66.</>}
      />
      <P
        en={<>Around the cascade sit the rest of the capital calculation, which the calculator does not run. The stressed calibration scales the ES of the current period on the reduced set of risk factors by the ratio of the full to the reduced set measured on the current period, floored at 1 (<Ref>MAR33.6</Ref>), the reduced set having to explain at least 75 percent of the full ES; the internal models capital charge IMCC is a weighted mean of the all-risk-class ES and the sum over the five broad risk classes with the weight 0.5 (<Ref>MAR33.15</Ref>). Each of those ES is itself a cascade, so an error in a liquidity horizon travels through the stress scaling into the capital.</>}
        es={<>Alrededor de la cascada está el resto del cálculo de capital, que la calculadora no ejecuta. La calibración bajo estrés escala el ES del periodo actual sobre el conjunto reducido de factores de riesgo por la razón del conjunto completo al reducido medida en el periodo actual, con piso en 1 (<Ref>MAR33.6</Ref>), debiendo el conjunto reducido explicar al menos 75 por ciento del ES completo; el cargo de capital de modelos internos IMCC es un promedio ponderado del ES de todas las clases de riesgo y la suma sobre las cinco clases amplias con peso 0,5 (<Ref>MAR33.15</Ref>). Cada uno de esos ES es en sí una cascada, de modo que un error en un horizonte de liquidez viaja por el escalamiento de estrés hasta el capital.</>}
      />
      <P
        en={<>Non-modellable risk factors add a stress scenario charge, at least as prudent as the ES calibration, with a liquidity horizon of at least 20 days and an aggregation in which the idiosyncratic terms have correlation 0 and the others 0.6 (<Ref>MAR33.16</Ref> and <Ref>MAR33.17</Ref>); the default risk model uses two systematic factors, a one-year horizon at 99.9 percent and a probability of default floor of 0.03 percent (<Ref>MAR33.20</Ref> to <Ref>MAR33.24</Ref>); and the capital is the larger of the previous day&apos;s IMCC plus SES and a multiplier m<sub>c</sub> times the 60-day average IMCC plus the average SES, with m<sub>c</sub> equal to 1.5 plus a backtesting add-on of 0 to 0.5 (<Ref>MAR33.41</Ref> to <Ref>MAR33.45</Ref>). The default risk charge at 99.9 percent over one year cannot be backtested directly (<Ref>MAR33.34</Ref>), which is why a validator relies on stress tests, sensitivity analyses and benchmarks for it.</>}
        es={<>Los factores de riesgo no modelables agregan un cargo de escenario de estrés, al menos tan prudente como la calibración del ES, con un horizonte de liquidez de al menos 20 días y una agregación en que los términos idiosincráticos tienen correlación 0 y los demás 0,6 (<Ref>MAR33.16</Ref> y <Ref>MAR33.17</Ref>); el modelo de riesgo de incumplimiento usa dos factores sistemáticos, un horizonte de un año al 99,9 por ciento y un piso de probabilidad de incumplimiento de 0,03 por ciento (<Ref>MAR33.20</Ref> a <Ref>MAR33.24</Ref>); y el capital es el mayor entre el IMCC más el SES del día anterior y un multiplicador m<sub>c</sub> por el IMCC promedio de 60 días más el SES promedio, con m<sub>c</sub> igual a 1,5 más un recargo de backtesting de 0 a 0,5 (<Ref>MAR33.41</Ref> a <Ref>MAR33.45</Ref>). El cargo por riesgo de incumplimiento al 99,9 por ciento a un año no puede someterse a backtesting directo (<Ref>MAR33.34</Ref>), por lo que el validador se apoya para él en pruebas de estrés, análisis de sensibilidad y comparaciones con referencias.</>}
      />
      <Equation
        tex={String.raw`ES = ES_{R,S}\,\frac{ES_{F,C}}{ES_{R,C}}\ \ (\text{ratio}\ \ge 1), \qquad \mathrm{IMCC} = \rho\,\mathrm{IMCC}(C) + (1-\rho)\sum_{i=1}^{B}\mathrm{IMCC}(C_i), \quad \rho = 0.5`}
        caption={<T en={<>The stressed calibration and the internal models capital charge (dossier 01, D.3; <Ref>MAR33.6</Ref> and <Ref>MAR33.15</Ref>): ES<sub>R</sub>,S the ES on the reduced set of risk factors over the stress period, ES<sub>F</sub>,C and ES<sub>R</sub>,C the ES on the full and the reduced sets over the current period, IMCC(C) the same scaling for all risk classes together, IMCC(C<sub>i</sub>) for broad risk class i of B = 5, and ρ = 0.5 the weight between them. Each ES is itself the cascade of the equation above.</>} es={<>La calibración bajo estrés y el cargo de capital de modelos internos (dossier 01, D.3; <Ref>MAR33.6</Ref> y <Ref>MAR33.15</Ref>): ES<sub>R</sub>,S el ES del conjunto reducido de factores de riesgo en el periodo de estrés, ES<sub>F</sub>,C y ES<sub>R</sub>,C el ES de los conjuntos completo y reducido en el periodo actual, IMCC(C) la misma escala para todas las clases de riesgo juntas, IMCC(C<sub>i</sub>) para la clase amplia i de B = 5, y ρ = 0,5 el peso entre ellos. Cada ES es en sí la cascada de la ecuación anterior.</>} />}
      />
      <Figure caption={<T en="The nested subsets of the cascade: every risk factor in the outer box, then the factors with a liquidity horizon of at least 20, 40, 60 and 120 days, each subset inside the one before, with the term it adds to the square root: ES_T(P, j) times the square root of (LH_j - LH_{j-1}) / 10, which is 1, the root of 2, the root of 2 and the root of 6. A schematic with no values." es="Los subconjuntos anidados de la cascada: todo factor de riesgo en la caja exterior, luego los factores con horizonte de liquidez de al menos 20, 40, 60 y 120 días, cada subconjunto dentro del anterior, con el término que agrega a la raíz cuadrada: ES_T(P, j) por la raíz de (LH_j - LH_{j-1}) / 10, que es 1, la raíz de 2, la raíz de 2 y la raíz de 6. Un esquema sin valores." />}>
        <CascadeFigure />
      </Figure>
      <FixtureNote doc={doc} />
      <CascadeCard doc={doc} reason={reason} />
    </>
  );
}

export function CcrPart({ doc, reason }: DocProps) {
  return (
    <>
      <P
        en={<>The standardised approach for counterparty credit risk, SA-CCR, sets the exposure at default of a netting set as 1.4 times the sum of the replacement cost and the potential future exposure (<Ref>CRE52.1</Ref>) <Cite id="regcre52" />. The replacement cost is max(V - C, 0) for an unmargined netting set (<Ref>CRE52.10</Ref>) and max(V - C, TH + MTA - NICA, 0) for a margined one (<Ref>CRE52.18</Ref>), with V the value, C the collateral, TH the threshold, MTA the minimum transfer amount and NICA the net independent collateral amount. The potential future exposure is a multiplier times the aggregate add-on (<Ref>CRE52.20</Ref>); the multiplier is 1 when V - C is not negative and falls toward a floor of 5 percent as the position becomes over-collateralised (<Ref>CRE52.23</Ref>), and the aggregate add-on sums the five asset classes: interest rate, foreign exchange, credit, equity and commodity (<Ref>CRE52.24</Ref> to <Ref>CRE52.25</Ref>).</>}
        es={<>El enfoque estandarizado para el riesgo de crédito de contraparte, SA-CCR, fija la exposición en incumplimiento de un conjunto de neteo como 1,4 veces la suma del costo de reposición y la exposición potencial futura (<Ref>CRE52.1</Ref>) <Cite id="regcre52" />. El costo de reposición es max(V - C, 0) para un conjunto sin margen (<Ref>CRE52.10</Ref>) y max(V - C, TH + MTA - NICA, 0) para uno con margen (<Ref>CRE52.18</Ref>), con V el valor, C la garantía, TH el umbral, MTA el monto mínimo de transferencia y NICA el monto neto de garantía independiente. La exposición potencial futura es un multiplicador por el recargo agregado (<Ref>CRE52.20</Ref>); el multiplicador vale 1 cuando V - C no es negativo y cae hacia un piso de 5 por ciento a medida que la posición queda sobrecolateralizada (<Ref>CRE52.23</Ref>), y el recargo agregado suma las cinco clases de activo: tasa de interés, tipo de cambio, crédito, acciones y materias primas (<Ref>CRE52.24</Ref> a <Ref>CRE52.25</Ref>).</>}
      />
      <Equation
        tex={String.raw`\mathrm{EAD} = 1.4\,(\mathrm{RC} + \mathrm{PFE}), \quad \mathrm{PFE} = m\cdot\mathrm{AddOn}^{\mathrm{agg}}, \quad m = \min\Bigl\{1,\ F + (1-F)\exp\Bigl(\tfrac{V-C}{2(1-F)\,\mathrm{AddOn}^{\mathrm{agg}}}\Bigr)\Bigr\},\ F = 5\%`}
        caption={<T en={<>The SA-CCR exposure at default and its multiplier (dossier 01, E.2; <Ref>CRE52.1</Ref>, <Ref>CRE52.20</Ref> and <Ref>CRE52.23</Ref>): RC the replacement cost, PFE the potential future exposure, m the multiplier, F its floor of 5 percent, V - C the value net of collateral and AddOn^agg the aggregate add-on. For the second CRE99 netting set V - C is -20 and the add-on 282, so m = 0.05 + 0.95 exp(-20 / (2 × 0.95 × 282)) = 0.965.</>} es={<>La exposición en incumplimiento de SA-CCR y su multiplicador (dossier 01, E.2; <Ref>CRE52.1</Ref>, <Ref>CRE52.20</Ref> y <Ref>CRE52.23</Ref>): RC el costo de reposición, PFE la exposición potencial futura, m el multiplicador, F su piso de 5 por ciento, V - C el valor neto de garantías y AddOn^agg el recargo agregado. Para el segundo conjunto de CRE99, V - C es -20 y el recargo 282, así que m = 0,05 + 0,95 exp(-20 / (2 × 0,95 × 282)) = 0,965.</>} />}
      />
      <P
        en={<>The add-on of each asset class is built from the trades. Each trade has a supervisory duration SD = (exp(-0.05 S) - exp(-0.05 E)) / 0.05 from its start S to its end E in years (<Ref>CRE52.34</Ref>), a supervisory delta that is plus or minus 1 for a linear trade, the normal distribution of (ln(P/K) + 0.5 σ² T) / (σ √T) with the sign of a bought or sold call or put for an option, and 15 / ((1 + 14 A)(1 + 14 D)) for a tranche (<Ref>CRE52.38</Ref> to <Ref>CRE52.41</Ref>), and a maturity factor, the square root of min(M, 1) when unmargined and 1.5 times the square root of the margin period of risk over one year when margined, with a floor of 10 business days for daily-margined non-cleared netting sets (<Ref>CRE52.48</Ref> to <Ref>CRE52.52</Ref>). Interest rate trades fall into maturity buckets of under one year, one to five years and over five years and offset by a formula; foreign exchange nets per currency pair; credit and equity aggregate a systematic and an idiosyncratic part; commodities aggregate per hedging set (<Ref>CRE52.57</Ref> to <Ref>CRE52.70</Ref>). The supervisory factors, correlations and volatilities are the table of <Ref>CRE52.72</Ref>, shown below with its paragraph and date.</>}
        es={<>El recargo de cada clase de activo se construye desde las operaciones. Cada operación tiene una duración supervisora SD = (exp(-0,05 S) - exp(-0,05 E)) / 0,05 desde su inicio S hasta su término E en años (<Ref>CRE52.34</Ref>), un delta supervisor que es más o menos 1 para una operación lineal, la distribución normal de (ln(P/K) + 0,5 σ² T) / (σ √T) con el signo de una compra o venta de opción de compra o de venta para una opción, y 15 / ((1 + 14 A)(1 + 14 D)) para un tramo (<Ref>CRE52.38</Ref> a <Ref>CRE52.41</Ref>), y un factor de vencimiento, la raíz de min(M, 1) sin margen y 1,5 veces la raíz del periodo de margen en riesgo sobre un año con margen, con un piso de 10 días hábiles para conjuntos con margen diario no compensados centralmente (<Ref>CRE52.48</Ref> a <Ref>CRE52.52</Ref>). Las operaciones de tasa de interés caen en tramos de vencimiento de menos de un año, de uno a cinco años y de más de cinco años y se compensan por una fórmula; el tipo de cambio se netea por par de monedas; crédito y acciones agregan una parte sistemática y una idiosincrática; las materias primas agregan por conjunto de cobertura (<Ref>CRE52.57</Ref> a <Ref>CRE52.70</Ref>). Los factores supervisores, correlaciones y volatilidades son la tabla de <Ref>CRE52.72</Ref>, mostrada abajo con su párrafo y fecha.</>}
      />
      <Equation
        tex={String.raw`EN_{HS} = \Bigl[(D^{B1})^2 + (D^{B2})^2 + (D^{B3})^2 + 1.4\,D^{B1}D^{B2} + 1.4\,D^{B2}D^{B3} + 0.6\,D^{B1}D^{B3}\Bigr]^{1/2}, \qquad \mathrm{AddOn} = \Bigl[\bigl(\textstyle\sum_e \rho_e\,\mathrm{AddOn}_e\bigr)^2 + \sum_e (1-\rho_e^2)\,\mathrm{AddOn}_e^2\Bigr]^{1/2}`}
        caption={<T en={<>The interest rate offset and the credit, equity and commodity aggregation (dossier 01, E.2; <Ref>CRE52.57</Ref>, <Ref>CRE52.61</Ref>, <Ref>CRE52.66</Ref> and <Ref>CRE52.70</Ref>): D<sup>B1</sup>, D<sup>B2</sup> and D<sup>B3</sup> the effective notionals of the three maturity buckets of a hedging set, EN<sub>HS</sub> the effective notional with offset (the sum of the absolute values is the alternative without offset), AddOn<sub>e</sub> the add-on of entity or hedging set e and ρ<sub>e</sub> its correlation from the table, the systematic part first and the idiosyncratic part second.</>} es={<>La compensación de tasa de interés y la agregación de crédito, acciones y materias primas (dossier 01, E.2; <Ref>CRE52.57</Ref>, <Ref>CRE52.61</Ref>, <Ref>CRE52.66</Ref> y <Ref>CRE52.70</Ref>): D<sup>B1</sup>, D<sup>B2</sup> y D<sup>B3</sup> los nocionales efectivos de los tres tramos de vencimiento de un conjunto de cobertura, EN<sub>HS</sub> el nocional efectivo con compensación (la suma de los valores absolutos es la alternativa sin compensación), AddOn<sub>e</sub> el recargo de la entidad o conjunto de cobertura e y ρ<sub>e</sub> su correlación de la tabla, primero la parte sistemática y después la idiosincrática.</>} />}
      />
      <P
        en={<>The basic approach to credit valuation adjustment risk, BA-CVA, prices the counterparty credit spread risk that SA-CCR ignores. A bank with aggregate non-centrally cleared derivatives of at most EUR 100 billion in notional may set the CVA capital equal to its counterparty credit risk capital (<Ref>MAR50.9</Ref>) <Cite id="regmar50" />. Otherwise the reduced version has the capital DS times K_reduced, with DS = 0.65, a correlation ρ of 50 percent, the discount factor (1 - exp(-0.05 M)) / (0.05 M) and the alpha of 1.4, and the counterparty risk weights of <Ref>MAR50.16</Ref> Table 1 by sector and credit quality, shown below (<Ref>MAR50.14</Ref> to <Ref>MAR50.16</Ref>). The full version blends K_reduced with a hedged capital, K_full = beta K_reduced + (1 - beta) K_hedged with beta = 0.25, and recognises only single-name CDS, single-name contingent CDS and index CDS as hedges (<Ref>MAR50.18</Ref> and <Ref>MAR50.20</Ref> to <Ref>MAR50.25</Ref>). No official numerical example of BA-CVA was found, so its tests rest on invariants: with ρ = 1 the reduced capital is the sum of the counterparty terms, and hedges never take K_full below beta K_reduced.</>}
        es={<>El enfoque básico del riesgo de ajuste de valoración del crédito, BA-CVA, pone precio al riesgo de spread de crédito de la contraparte que SA-CCR ignora. Un banco con derivados no compensados centralmente de a lo más EUR 100.000 millones en nocional agregado puede fijar el capital por CVA igual a su capital por riesgo de crédito de contraparte (<Ref>MAR50.9</Ref>) <Cite id="regmar50" />. En otro caso la versión reducida tiene el capital DS por K_reduced, con DS = 0,65, una correlación ρ de 50 por ciento, el factor de descuento (1 - exp(-0,05 M)) / (0,05 M) y el alfa de 1,4, y los ponderadores de riesgo de contraparte de <Ref>MAR50.16</Ref> Tabla 1 por sector y calidad crediticia, mostrados abajo (<Ref>MAR50.14</Ref> a <Ref>MAR50.16</Ref>). La versión completa mezcla K_reduced con un capital con coberturas, K_full = beta K_reduced + (1 - beta) K_hedged con beta = 0,25, y reconoce como coberturas solo los CDS de nombre único, los CDS contingentes de nombre único y los CDS de índice (<Ref>MAR50.18</Ref> y <Ref>MAR50.20</Ref> a <Ref>MAR50.25</Ref>). No se encontró un ejemplo numérico oficial de BA-CVA, así que sus pruebas se apoyan en invariantes: con ρ = 1 el capital reducido es la suma de los términos de las contrapartes, y las coberturas nunca llevan K_full bajo beta K_reduced.</>}
      />
      <Equation
        tex={String.raw`K_{\mathrm{reduced}} = \sqrt{\Bigl(\rho\sum_c \mathrm{SCVA}_c\Bigr)^2 + (1-\rho^2)\sum_c \mathrm{SCVA}_c^2}, \quad \mathrm{SCVA}_c = \tfrac{1}{\alpha}\,RW_c\sum_{NS} M_{NS}\,\mathrm{EAD}_{NS}\,DF_{NS}, \quad K_{\mathrm{full}} = \beta K_{\mathrm{reduced}} + (1-\beta)K_{\mathrm{hedged}}`}
        caption={<T en={<>The BA-CVA capital bases (dossier 01, E.1; <Ref>MAR50.14</Ref> to <Ref>MAR50.16</Ref> and <Ref>MAR50.20</Ref>): SCVA<sub>c</sub> the stand-alone CVA of counterparty c, RW<sub>c</sub> its risk weight from the table, M<sub>NS</sub>, EAD<sub>NS</sub> and DF<sub>NS</sub> the effective maturity, the exposure at default and the discount factor of netting set NS, ρ = 50 percent the correlation, alpha = 1.4, beta = 0.25 and K_hedged the capital after the eligible hedges. The capital is 0.65 times K_reduced or K_full.</>} es={<>Las bases de capital de BA-CVA (dossier 01, E.1; <Ref>MAR50.14</Ref> a <Ref>MAR50.16</Ref> y <Ref>MAR50.20</Ref>): SCVA<sub>c</sub> el CVA individual de la contraparte c, RW<sub>c</sub> su ponderador de riesgo de la tabla, M<sub>NS</sub>, EAD<sub>NS</sub> y DF<sub>NS</sub> el vencimiento efectivo, la exposición en incumplimiento y el factor de descuento del conjunto de neteo NS, ρ = 50 por ciento la correlación, alfa = 1,4, beta = 0,25 y K_hedged el capital tras las coberturas elegibles. El capital es 0,65 veces K_reduced o K_full.</>} />}
      />
      <P
        en={<>The framework gives five worked examples that Contraste reproduces (<Ref>CRE99.20</Ref> to <Ref>CRE99.97</Ref>, in thousands of USD) <Cite id="regcre99" />. The first netting set, interest rate swaps and a swaption without margin, has a replacement cost of 60, effective notionals of 59,270 for USD and 10,083 for EUR, an interest rate add-on of 296.35 + 50.415 = 347, a swaption delta of -0.2694 and an exposure at default of 1.4 × (60 + 1 × 347) = 569. The second, credit derivatives, has no replacement cost, an add-on of the square root of (2,253 + 77,344) = 282, a multiplier of 0.965 and an exposure of 381. The third, commodity forwards and swaps, has a replacement cost of 20, add-ons of 2,041 for energy and 1,800 for metals, 3,841 in all, and 5,406. The fourth joins the first two: replacement cost 40, add-on 347 + 282 = 629 and 936. The fifth is margined, interest rate and commodity: a replacement cost of max(80 - 200, 0 + 5 - 150, 0) = 0, a maturity factor of 1.5 √(14/250), add-ons of 123 and 1,278, 1,401 in all, a multiplier of 0.958 and 1,879. The acceptance gate is exact: from the trade inputs, transcribed from the page with their paragraphs, every printed intermediate recomputes and each exposure rounds to its published integer.</>}
        es={<>El marco da cinco ejemplos resueltos que Contraste reproduce (<Ref>CRE99.20</Ref> a <Ref>CRE99.97</Ref>, en miles de USD) <Cite id="regcre99" />. El primer conjunto de neteo, swaps de tasa de interés y una swaption sin margen, tiene un costo de reposición de 60, nocionales efectivos de 59.270 para USD y 10.083 para EUR, un recargo de tasa de interés de 296,35 + 50,415 = 347, un delta de la swaption de -0,2694 y una exposición en incumplimiento de 1,4 × (60 + 1 × 347) = 569. El segundo, derivados de crédito, no tiene costo de reposición, tiene un recargo de la raíz de (2.253 + 77.344) = 282, un multiplicador de 0,965 y una exposición de 381. El tercero, forwards y swaps de materias primas, tiene un costo de reposición de 20, recargos de 2.041 para energía y 1.800 para metales, 3.841 en total, y 5.406. El cuarto reúne los dos primeros: costo de reposición 40, recargo 347 + 282 = 629 y 936. El quinto tiene margen, tasa de interés y materias primas: un costo de reposición de max(80 - 200, 0 + 5 - 150, 0) = 0, un factor de vencimiento de 1,5 √(14/250), recargos de 123 y 1.278, 1.401 en total, un multiplicador de 0,958 y 1.879. La puerta de aceptación es exacta: desde los datos de las operaciones, transcritos de la página con sus párrafos, cada intermedio impreso se recalcula y cada exposición se redondea a su entero publicado.</>}
      />
      <Figure caption={<T en="The SA-CCR multiplier of CRE52.23 against (V - C) divided by the aggregate add-on, drawn from the formula: 1 from zero upward, falling as the position becomes over-collateralised toward the 5 percent floor. The point is the second CRE99 netting set, with V - C of -20 and an add-on of 282, whose multiplier is 0.965." es="El multiplicador de SA-CCR de CRE52.23 contra (V - C) dividido por el recargo agregado, dibujado desde la fórmula: 1 desde cero hacia arriba, cayendo a medida que la posición queda sobrecolateralizada hacia el piso de 5 por ciento. El punto es el segundo conjunto de CRE99, con V - C de -20 y un recargo de 282, cuyo multiplicador es 0,965." />}>
        <MultiplierFigure />
      </Figure>
      <FixtureNote doc={doc} />
      <ParameterCard doc={doc} reason={reason} id="cre52-72-table-2" />
      <ParameterCard doc={doc} reason={reason} id="mar50-16-table-1" />
      <WorkedExamplesCard doc={doc} reason={reason} />
    </>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// the section

export function RegulationBody({ doc, reason }: DocProps) {
  const t = useT();
  const props = { doc, reason };
  return (
    <DocSection
      area="method"
      kind="classical"
      title={{ en: 'The regulation map: Basel calculators and their parameters', es: 'El mapa regulatorio: calculadoras de Basilea y sus parámetros' }}
      refs={['regcre20', 'regrbc20', 'regrbc90', 'regmar21', 'regmar33', 'regcre52', 'regcre99', 'regmar50']}
    >
      <SubTabs
        ariaLabel={t('Parts of the topic', 'Partes del tema')}
        tabs={[
          { id: 'credit', label: t('Credit risk weights (CRE20)', 'Ponderadores de crédito (CRE20)'), content: <CreditPart {...props} /> },
          { id: 'floor', label: t('The output floor', 'El piso de salida'), content: <FloorPart {...props} /> },
          { id: 'sbm', label: t('FRTB sensitivities (MAR21)', 'Sensibilidades FRTB (MAR21)'), content: <SbmPart {...props} /> },
          { id: 'cascade', label: t('Liquidity horizons (MAR33)', 'Horizontes de liquidez (MAR33)'), content: <CascadePart {...props} /> },
          { id: 'ccr', label: t('SA-CCR and BA-CVA', 'SA-CCR y BA-CVA'), content: <CcrPart {...props} /> },
        ]}
      />
      <Callout variant="honest" title={t('What is exact, what is a choice and what these calculators are not', 'Qué es exacto, qué es una decisión y qué no son estas calculadoras')}>
        <T
          en={<>The tables, factors, horizons and formulas on this tab are published values of the Basel Framework in the chapter versions in force since 2023-01-01, transcribed with their paragraph and checked by the live ports against the regulatory-calculators document within 1e-9 relative: the five CRE99 SA-CCR examples round exactly to their published exposures at default of 569, 381, 5,406, 936 and 1,879, and the <Ref>RBC20.13</Ref> example gives 101.5 and, with the optional cap, 95. They reproduce published formulas and nothing more. They do not claim regulatory approval, compliance or equivalence to any bank&apos;s approved model, and a result of a calculator is not a bank&apos;s capital requirement. Three choices are named: the output-floor factor is the BCBS schedule and not any jurisdiction&apos;s; the weights of the GIRR delta may be divided by the square root of 2 for a specified currency at the bank&apos;s discretion, and the curvature shock stays undivided; and the correlation of the GIRR matrix is the published table, whose footnote formula is reconstructed and agrees with all 100 entries. Several items stay unverified: the text of the FAQ of 2026-03-23 on flooring credit spread curvature factors, any numerical BA-CVA example, the row of commodity volatility of the liquidity horizons, and the entry into force of the 2026 European relief for the FRTB. The dates on which the European Union, the United Kingdom and the United States apply the framework are not stated here as adopted.</>}
          es={<>Las tablas, factores, horizontes y fórmulas de esta pestaña son valores publicados del Marco de Basilea en las versiones de los capítulos vigentes desde 2023-01-01, transcritos con su párrafo y verificados por los puertos en vivo contra el documento de calculadoras regulatorias dentro de 1e-9 relativo: los cinco ejemplos de SA-CCR de CRE99 se redondean exactamente a sus exposiciones en incumplimiento publicadas de 569, 381, 5.406, 936 y 1.879, y el ejemplo de <Ref>RBC20.13</Ref> da 101,5 y, con el tope opcional, 95. Reproducen fórmulas publicadas y nada más. No afirman aprobación regulatoria, cumplimiento ni equivalencia con el modelo aprobado de ningún banco, y el resultado de una calculadora no es el requerimiento de capital de un banco. Se nombran tres decisiones: el factor del piso de salida es el calendario del BCBS y no el de ninguna jurisdicción; los ponderadores de delta de GIRR pueden dividirse por la raíz de 2 para una moneda especificada a discreción del banco, y el choque de curvatura se deja sin dividir; y la correlación de la matriz de GIRR es la tabla publicada, cuya fórmula de nota al pie se reconstruye y coincide con las 100 entradas. Varios puntos quedan sin verificar: el texto de las preguntas frecuentes del 2026-03-23 sobre acotar en cero los factores de curvatura de spread de crédito, cualquier ejemplo numérico de BA-CVA, la fila de volatilidad de materias primas de los horizontes de liquidez y la entrada en vigor del alivio europeo de 2026 para el FRTB. Las fechas en que la Unión Europea, el Reino Unido y Estados Unidos aplican el marco no se dan aquí como adoptadas.</>}
        />
      </Callout>
    </DocSection>
  );
}

function Body() {
  const loaded = useArtifact<RegulatoryDoc>(() => loadRegulatory(), [], { unavailable: true });
  if (loaded.state === 'loading') return <RegulationBody doc={undefined} />;
  if (loaded.state === 'ready') return <RegulationBody doc={loaded.data} />;
  return <RegulationBody doc={null} reason={loaded.state === 'unavailable' ? loaded.reason : NOT_PUBLISHED} />;
}

export const methodologySection: MethodologySection = {
  id: 'regulation',
  group: 'capital',
  order: 230,
  title: { en: 'Regulation map (Basel calculators)', es: 'Mapa regulatorio (calculadoras de Basilea)' },
  Body,
};
