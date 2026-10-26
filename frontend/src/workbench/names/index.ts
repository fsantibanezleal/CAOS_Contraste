// The names of every id a reader can meet in a finding's evidence or a tests table: tests, models, segments, design limits,
// outputs blocks, rate configurations and contract rules (U16-R2b, the ruling of 2026-10-24: a raw id shown where the product
// has a name is a blocker). The views of a case keep their own words where they have them; the Findings card of every case, the
// governance views and every fallback read these, so no view prints an id. The names gate (names.test.ts) walks every committed
// document and fails on any key these do not name.
import type { Bi as BiText } from '../c03/U6Shared';
import { HORIZON_LONG, SUBJECT_TEXT } from '../c12/selection';
import { DESIGN_TEXT, ESTIMATOR_TEXT, TREATMENT_TEXT } from '../c09/selection';
import { ESTIMATOR_TEXT as C10_ESTIMATOR_TEXT } from '../c10/selection';
import { LOAN_TEXT } from '../c18/selection';
import { SHOCK_TEXT } from '../c20/selection';
import { FIELD_TEXT, GROUP_TEXT } from '../c21/selection';
import { DESIGN_LIMITS, OUTPUT_BLOCKS } from './design';
import MODELS from './models.gen.json';
import { TEST_NAMES } from './tests';

export { DESIGN_LIMITS, OUTPUT_BLOCKS, TEST_NAMES };

type Lang = 'en' | 'es';
const bi = (en: string, es: string): BiText => ({ en, es });
const join = (parts: Array<BiText | null | undefined>, sep = ', '): BiText => {
  const xs = parts.filter((p): p is BiText => !!p);
  return bi(xs.map((p) => p.en).join(sep), xs.map((p) => p.es).join(sep));
};
const num = (s: string, lang: Lang): string => (lang === 'es' ? s.replace('.', ',') : s);
const GEN = MODELS as {
  models: Record<string, Record<string, BiText>>;
  rates: Record<string, Record<string, BiText>>;
  variants: Record<string, Record<string, BiText>>;
  sources: Record<string, string>;
};

/** A variant's title in its case manifest (for the views that load no manifest: the governance report). */
export const variantName = (caseId: string, variantId: string): BiText | null => GEN.variants[caseId]?.[variantId] ?? null;

/** A source by its published name (the manifests' `source_details`), the same in both languages; null for an unknown id. */
export const sourceName = (id: string): string | null => GEN.sources[id] ?? null;

/** The fits of the governance inventory that are not a variant of their case (an inventory entry is one fit: the models
 * document `models-<fit>.json`; data-pipeline/pipeline/governance/inputs.json). C06 and C08 fit one ladder per variant and take
 * the variant's name. */
const FIT_NAME: Record<string, BiText> = {
  'C01/german': bi('German Credit fit', 'Ajuste German Credit'),
  'C01/taiwan': bi('Taiwan fit', 'Ajuste Taiwán'),
  'C01/taiwan-small': bi('Taiwan small-sample fit', 'Ajuste Taiwán de muestra pequeña'),
  'C02/polish-horizons': bi('Polish horizons fit', 'Ajuste de los horizontes polacos'),
  'C03/sba-7a': bi('SBA 7(a) fit', 'Ajuste SBA 7(a)'),
  'C04/transitions': bi('Rating transitions', 'Transiciones de calificación'),
  'C05/ldp': bi('Low-default portfolios', 'Carteras de bajo incumplimiento'),
  'C05/sp2009': bi('S&P 2009 fit', 'Ajuste S&P 2009'),
  'C07/banco-andino': bi('Banco Andino', 'Banco Andino'),
  'C09/generator': bi('Generator', 'Generador'),
  'C10/c10': bi('Portfolio model ladder', 'Escalera de modelos de cartera'),
  'C11/ladder': bi('VaR and ES ladder', 'Escalera de VaR y ES'),
  'C12/hw1f-treasury-2000-2025': bi('Hull-White, Treasury 2000 to 2025', 'Hull-White, Tesoro 2000 a 2025'),
  'C13/generator': bi('Generator', 'Generador'),
  'C14/svb-2021-2022': bi('SVB, 2021 to 2022', 'SVB, 2021 a 2022'),
  'C15/banco-andino-2026-09': bi('Banco Andino, September 2026', 'Banco Andino, septiembre de 2026'),
  'C16/svb-liquidity': bi('SVB liquidity', 'Liquidez de SVB'),
  'C17/generator': bi('Generator', 'Generador'),
  'C18/banco-andino': bi('Banco Andino', 'Banco Andino'),
  'C20/c20-ladder': bi('ML model ladder', 'Escalera de modelos de ML'),
  'C21/hmda-de-2018-2023': bi('HMDA Delaware, 2018 to 2023', 'HMDA Delaware, 2018 a 2023'),
  'C22/generators': bi('Generators', 'Generadores'),
};

/** An inventory entry (`C02/polish-horizons`) or a variant key (`C05/ldp-sim-0`) in words: its case and its fit or variant;
 * null for a key with no name. */
export function entryName(key: string): BiText | null {
  const i = key.indexOf('/');
  if (i < 0) return null;
  const caseId = key.slice(0, i);
  const name = FIT_NAME[key] ?? variantName(caseId, key.slice(i + 1));
  return name ? bi(`${caseId}, ${name.en}`, `${caseId}, ${name.es}`) : null;
}

/** An entry key in words, or as written when it has no name. */
export const entryText = (key: string): BiText => entryName(key) ?? bi(key, key);

/** A test row's model and segment in words ("P1 Scorecard, portfolio"), each part named or, failing that, left out. */
export function rowWhere(caseId: string, modelId: string | null | undefined, segment: string | null | undefined, models?: NameContext['models']): BiText | null {
  const ctx = { caseId, models };
  const parts = [modelId ? modelName(modelId, ctx) : null, segment ? segmentName(segment, ctx) : null].filter((p): p is BiText => !!p);
  return parts.length ? bi(parts.map((p) => p.en).join(', '), parts.map((p) => p.es).join(', ')) : null;
}

/** A test's name. A repeated test of a rate key (`market.dynamic_quantile_test#2`) adds its number; an id no map holds is null. */
export function testName(id: string): BiText | null {
  const m = /^(.*)#(\d+)$/.exec(id);
  const base = TEST_NAMES[m ? m[1] : id];
  if (!base) return null;
  return m ? bi(`${base.en} (${Number(m[2]) + 1})`, `${base.es} (${Number(m[2]) + 1})`) : base;
}

/** A test's name, else the id: for a view that must print something; the names gate keeps this fallback unused. */
export const testText = (id: string): BiText => testName(id) ?? bi(id, id);

/** What the names of a case read: its id and, when the view loaded it, the document's own model list. */
export interface NameContext {
  caseId: string;
  models?: ReadonlyArray<{ id: string; title?: BiText; short_title?: BiText }>;
}

/** C09's composed CCF ids (`ccf-<design>-<treatment>[-<estimator>]`, the bake's ead_models and fits) in C09's own words. */
function c09Model(id: string): BiText | null {
  const m = /^ccf-(fixed-horizon|cohort|variable-horizon)-(none|censor|floor-cap|bounded-scale)(?:-(mean|pooled))?$/.exec(id);
  if (!m) return null;
  const parts: BiText[] = [DESIGN_TEXT[m[1]], TREATMENT_TEXT[m[2]], ...(m[3] ? [ESTIMATOR_TEXT[m[3]]] : [])];
  const low = (lang: Lang) => parts.map((p) => p[lang].toLowerCase()).join(', ');
  return bi(`CCF, ${low('en')}`, `CCF, ${low('es')}`);
}

/** A model's name: the document's short title (or title), else the committed documents' table, else the case's composed form. */
export function modelName(id: string, ctx: NameContext): BiText | null {
  const own = ctx.models?.find((m) => m.id === id);
  const fromDoc = own?.short_title && own.short_title.en !== id ? own.short_title : own?.title;
  if (fromDoc && fromDoc.en !== id) return fromDoc;
  const table = GEN.models[ctx.caseId]?.[id];
  if (table) return table;
  if (ctx.caseId === 'C09') return c09Model(id);
  // C18's satellite of one loan class (c18/satellites: `c18-satellite-<loan>`), in C18's words for the class
  const sat = ctx.caseId === 'C18' ? /^c18-satellite-(.+)$/.exec(id) : null;
  if (sat && LOAN_TEXT[sat[1]]) return bi(`Satellite of ${LOAN_TEXT[sat[1]].en.toLowerCase()}`, `Satélite de ${LOAN_TEXT[sat[1]].es.toLowerCase()}`);
  return null;
}

const SEGMENT_FIXED: Record<string, BiText> = {
  portfolio: bi('portfolio', 'cartera'),
  all: bi('whole book', 'toda la cartera'),
  annual: bi('the annual cohorts', 'las cohortes anuales'),
  semesters: bi('the semesters', 'los semestres'),
  holdout: bi('holdout', 'muestra reservada'),
  screen: bi('the leakage screen', 'el filtro de fuga'),
  'train-vs-holdout': bi('training against holdout', 'entrenamiento contra muestra reservada'),
  'shap-vs-ale-range': bi('SHAP against the ALE range', 'SHAP contra el rango de ALE'),
  'window:pooled': bi('the windows pooled', 'las ventanas agrupadas'),
  age: bi('age', 'edad'),
  sex: bi('sex', 'sexo'),
  marital_status: bi('marital status', 'estado civil'),
  'minimum-transfer-amount-0': bi('minimum transfer amount 0', 'monto mínimo de transferencia 0'),
};

/** C20's Fed portfolios and the fields of their loans (the Federal Reserve's hypothetical portfolios, c20/v_shift.py). */
const FED_PORTFOLIO: Record<string, BiText> = {
  typical: bi('typical', 'típica'),
  'lower-risk': bi('lower-risk', 'de menor riesgo'),
  'higher-risk': bi('higher-risk', 'de mayor riesgo'),
};
const FED_FIELD: Record<string, BiText> = {
  committed_exposure_amt: bi('committed exposure', 'exposición comprometida'),
  utilized_exposure_amt: bi('utilised exposure', 'exposición utilizada'),
  interest_rate: bi('interest rate', 'tasa de interés'),
  term: bi('term', 'plazo'),
  orig_year: bi('origination year', 'año de originación'),
  rating: bi('rating', 'calificación'),
  facility_type_cat: bi('facility type', 'tipo de facilidad'),
  lien_position_cat: bi('lien position', 'posición del gravamen'),
  domestic_flag: bi('domestic borrower', 'deudor doméstico'),
  naics_two_digit_cat: bi('industry (two-digit NAICS)', 'industria (NAICS a dos dígitos)'),
  interest_rate_variability: bi('interest rate variability', 'variabilidad de la tasa de interés'),
  guarantor_flag: bi('guarantor', 'garante'),
};

/** The inputs of the UCI German credit file (C01's German twin, C20's SGCD) by name (data-pipeline/pipeline/cases/c01_features.py). */
const GERMAN_FIELD: Record<string, BiText> = {
  checking_status: bi('Status of the existing checking account', 'Estado de la cuenta corriente'),
  duration_months: bi('Duration', 'Plazo'),
  credit_history: bi('Credit history', 'Historial de crédito'),
  purpose: bi('Purpose', 'Propósito'),
  credit_amount: bi('Credit amount', 'Monto del crédito'),
  savings: bi('Savings account and bonds', 'Cuenta de ahorro y bonos'),
  employment_since: bi('Present employment since', 'Antigüedad en el empleo actual'),
  installment_rate: bi('Instalment rate in percent of disposable income', 'Cuota como porcentaje del ingreso disponible'),
  other_debtors: bi('Other debtors and guarantors', 'Otros deudores y avales'),
  residence_since: bi('Present residence since', 'Antigüedad en la residencia actual'),
  property: bi('Property', 'Bienes'),
  other_installment_plans: bi('Other instalment plans', 'Otros planes de cuotas'),
  housing: bi('Housing', 'Vivienda'),
  existing_credits: bi('Number of existing credits at this bank', 'Créditos vigentes en este banco'),
  job: bi('Job', 'Empleo'),
  people_liable: bi('People liable to provide maintenance for', 'Personas a cargo'),
  telephone: bi('Telephone', 'Teléfono'),
};

/** The model inputs C03 derives from the SBA 7(a) loan file by name (data-pipeline/pipeline/cases/c03/panel.py FEATURES). */
const SBA_FIELD: Record<string, BiText> = {
  log10_amount: bi('Log10 of the gross approved amount', 'Log10 del monto bruto aprobado'),
  guarantee_share: bi('Share guaranteed by the SBA', 'Proporción garantizada por la SBA'),
  term_months: bi('Term in months', 'Plazo en meses'),
  sector: bi('Sector', 'Sector'),
  revolver: bi('Revolving line', 'Línea rotativa'),
  '(intercept)': bi('Intercept', 'Intercepto'),
  // C20's planted leak (c20/v_leak.py LEAK): the default flag plus noise, dated one month after the observation date
  future_status_code: bi('future status code (the planted leak)', 'código de estado futuro (la fuga sembrada)'),
};

/** An input of a data file by name: a column of the German file, a field of the Fed portfolios or an input C03 derives from the
 * SBA file; null for any other (a column whose published name is its name, such as the Taiwan file's LIMIT_BAL, prints as
 * written). */
export const inputName = (col: string): BiText | null => GERMAN_FIELD[col] ?? FED_FIELD[col] ?? SBA_FIELD[col] ?? null;

/** A rule over inputs (`log10_amount <= 5.00043 and sector > 0.0554929`) with each named input in words; an input whose
 * published name is its name stays as written. */
export function ruleNames(rule: string, lang: 'en' | 'es'): string {
  return rule.replace(/[A-Za-z_][A-Za-z0-9_]*/g, (w) => {
    const n = inputName(w);
    return n ? n[lang] : w;
  });
}

/** C20's Fed shift (`fed-higher-risk-x0.25`): the Fed's higher-risk portfolio drift at a multiple (c20/v_shift.py). */
const fedShift = (k: string): BiText => bi(`the Fed higher-risk drift times ${num(k, 'en')}`, `la deriva de mayor riesgo de la Fed por ${num(k, 'es')}`);

/** A segment of a test row or an evidence key in words; null when no form of the case matches (the gate fails on it). */
export function segmentName(seg: string, ctx: Pick<NameContext, 'caseId'>): BiText | null {
  if (SEGMENT_FIXED[seg]) return SEGMENT_FIXED[seg];
  let m: RegExpExecArray | null;
  // the input of a CSI row, as its data file names the column (C02: the UCI file's Attr27; a `_missing` column is its missing-value
  // indicator); a dataset's column name is the name it publishes
  if ((m = /^characteristic:(.+?)(_missing)?$/.exec(seg))) {
    // a column the product names (the German file's checking_status) in words; a published column name (Attr27) as written
    const n = inputName(m[1]);
    const en = n ? n.en : `input ${m[1]}`;
    const es = n ? n.es : `entrada ${m[1]}`;
    return m[2] ? bi(`${en}, missing-value indicator`, `${es}, indicador de valor faltante`) : bi(en, es);
  }
  switch (ctx.caseId) {
    case 'C04':
      if (/^\d{4}$/.test(seg)) return bi(`cohort ${seg}`, `cohorte ${seg}`);
      break;
    case 'C05':
      if (/^(AAA|AA|A|BBB|BB|B|CCC-C|C)$/.test(seg)) return bi(`grade ${seg}`, `grado ${seg}`);
      break;
    case 'C08':
      if ((m = /^cohort-(\d{4})-(\d{2})$/.exec(seg))) {
        const end = `${m[1].slice(0, 2)}${m[2]}`;
        return bi(`the ${m[1]} to ${end} cohort`, `la cohorte ${m[1]} a ${end}`);
      }
      break;
    case 'C10':
      if ((m = /^lhp-like-([\d.]+)$/.exec(seg))) return bi(`the LHP anchor at ${num(m[1], 'en')}%`, `el ancla LHP al ${num(m[1], 'es')} %`);
      if ((m = /^rho=([\d.]+)\/(maximum-likelihood|moments)$/.exec(seg))) {
        const e = C10_ESTIMATOR_TEXT[m[2]];
        return bi(`known correlation ${num(m[1], 'en')}, ${e.en.toLowerCase()}`, `correlación conocida ${num(m[1], 'es')}, ${e.es.toLowerCase()}`);
      }
      break;
    case 'C12':
      if ((m = /^(book|risk factor|risk-factor)-([0-9a-z]+?)(?:-q(\d+))?$/.exec(seg)) && HORIZON_LONG[m[2]]) {
        const s = SUBJECT_TEXT[m[1] === 'book' ? 'book' : 'risk-factor'];
        const subject = bi(s.en.charAt(0).toLowerCase() + s.en.slice(1), s.es.charAt(0).toLowerCase() + s.es.slice(1));
        return join([subject, HORIZON_LONG[m[2]], m[3] ? bi(`quantile ${m[3]} %`, `cuantil ${m[3]} %`) : null]);
      }
      break;
    case 'C17':
      // the cell of the capital-stability grid: the years of history and the collection threshold (c17/documents.py cell_id)
      if ((m = /^y(\d+)-h(\d+)$/.exec(seg))) {
        const t = Number(m[2]);
        return bi(`${m[1]} years of losses, threshold ${t.toLocaleString('en-US')}`, `${m[1]} años de pérdidas, umbral ${t.toLocaleString('es-CL')}`);
      }
      break;
    case 'C20':
      if ((m = /^(\d+)-bootstrap-refits$/.exec(seg))) return bi(`${m[1]} bootstrap refits`, `${m[1]} reajustes bootstrap`);
      if ((m = /^(\d+)-seeds$/.exec(seg))) return bi(`${m[1]} retraining seeds`, `${m[1]} semillas de reentrenamiento`);
      if (seg === 'window:baseline') return bi('the baseline window', 'la ventana base');
      // the weak-spot slices of one input (c20/v_perturb.py: the input as the UCI Taiwan file names its column)
      if ((m = /^slices-of-(.+)$/.exec(seg))) return bi(`slices of ${m[1]}`, `segmentos de ${m[1]}`);
      if ((m = /^(shipped|applied):(numeric-noise)$/.exec(seg))) {
        return join([SHOCK_TEXT[m[2]], m[1] === 'shipped' ? bi('as shipped', 'como se entregan') : bi('applied by Contraste', 'aplicado por Contraste')]);
      }
      if ((m = /^(?:(control-zeros-kept):)?preset-eps-([\d.]+)$/.exec(seg))) {
        const base = bi(`preset noise scale ${num(m[2], 'en')}`, `escala de ruido predefinida ${num(m[2], 'es')}`);
        return m[1] ? join([base, bi('control zeros kept', 'ceros de control conservados')]) : base;
      }
      if ((m = /^(shipped|applied):(F\d)$/.exec(seg)) && SHOCK_TEXT[m[2]]) {
        const how = m[1] === 'shipped' ? bi('as shipped', 'como se entregan') : bi('applied by Contraste', 'aplicado por Contraste');
        return join([SHOCK_TEXT[m[2]], how]);
      }
      if ((m = /^(?:window:)?fed-higher-risk-x([\d.]+)$/.exec(seg))) return fedShift(m[1]);
      // one field's drift from one Fed portfolio to another ("typical>higher-risk:interest_rate")
      if ((m = /^([a-z-]+)>([a-z-]+):([a-z_]+)$/.exec(seg)) && FED_PORTFOLIO[m[1]] && FED_PORTFOLIO[m[2]] && FED_FIELD[m[3]]) {
        const [a, b, f] = [FED_PORTFOLIO[m[1]], FED_PORTFOLIO[m[2]], FED_FIELD[m[3]]];
        return bi(`${f.en}, ${a.en} against ${b.en} portfolio`, `${f.es}, cartera ${a.es} frente a ${b.es}`);
      }
      break;
    case 'C21': {
      // field | contrast | measure (c21 FindingsEvidence): "applicant_age|25-34 vs 35-44|controlled"
      const [field, contrast, measure] = seg.split('|');
      const f = FIELD_TEXT[field];
      if (!f) break;
      const c = contrast === undefined ? null : bi(contrastBi(contrast, 'en'), contrastBi(contrast, 'es'));
      const how = measure === 'controlled' ? bi('controlled', 'controlado') : measure === 'rate_spread' ? bi('rate spread', 'diferencial de tasa') : null;
      if (measure !== undefined && !how) break;
      return join([f, c, how]);
    }
    default:
      break;
  }
  return null;
}

/** A conformal window of C20 by name ("fed-higher-risk-x0.25", "pooled", "baseline"); the id when no form matches. */
export const windowName = (w: string): BiText => segmentName(`window:${w}`, { caseId: 'C20' }) ?? segmentName(w, { caseId: 'C20' }) ?? bi(w, w);

/** A C21 contrast ("25-34 vs 35-44") with the groups in the language's words and "vs" as "frente a" in Spanish. */
function contrastBi(label: string, lang: Lang): string {
  const words = Object.entries(GROUP_TEXT).reduce((acc, [g, b]) => acc.replaceAll(g, b[lang]), label);
  return lang === 'es' ? words.replace(' vs ', ' frente a ') : words;
}

/** A measured rate of a `rate:<test>@<config>` key: the test, then its configuration (C22's scenario from its documents, collected by
 * scripts/gen-names.mjs; C04's from the key's tail). */
export function rateName(key: string, ctx: Pick<NameContext, 'caseId'>): BiText | null {
  const [test, tail = ''] = key.split('@');
  const t = testName(test);
  if (!t) return null;
  const detail = rateDetail(ctx.caseId, key, tail);
  return detail ? join([t, detail]) : null;
}

const RATE_TAIL: Record<string, BiText> = {
  null: bi('under the null (its size)', 'bajo la hipótesis nula (su tamaño)'),
  'form-chi2': bi('chi-square form, Markov chain', 'forma chi-cuadrado, cadena de Markov'),
  'form-lr': bi('likelihood ratio form, Markov chain', 'forma de razón de verosimilitud, cadena de Markov'),
};

function rateDetail(caseId: string, key: string, tail: string): BiText | null {
  const docs = GEN.rates[caseId]?.[key];
  if (docs) return docs;
  if (RATE_TAIL[tail]) return RATE_TAIL[tail];
  let m: RegExpExecArray | null;
  if ((m = /^k([\d.]+)$/.exec(tail))) return bi(`k = ${num(m[1], 'en')}`, `k = ${num(m[1], 'es')}`);
  if ((m = /^alpha([\d.]+)$/.exec(tail))) return bi(`alpha = ${num(m[1], 'en')}`, `alfa = ${num(m[1], 'es')}`);
  return null;
}

/** A contract rule a finding cites (`contract:<rule>`), from the rule's own text (data-pipeline/pipeline/cases/c01_features.py). */
export const CONTRACT_RULES: Record<string, BiText> = {
  'C01-EDU-CODE': bi('EDUCATION outside its documented codes (1 to 4)', 'EDUCATION fuera de sus códigos documentados (1 a 4)'),
  'C01-PAY-CODE': bi('a repayment status outside its documented codes (-1, 1 to 9)', 'un estado de pago fuera de sus códigos documentados (-1, 1 a 9)'),
};

/** What an evidence key names, in words, and its parts (the caller adds the row's result: p value and light). */
export interface EvidenceLabel {
  kind: 'test' | 'design' | 'block' | 'rate' | 'contract';
  text: BiText;
  testId?: string;
  modelId?: string;
  segment?: string;
}

/** The words of one evidence key, or null for a key no form names (the names gate fails on it). */
export function evidenceLabel(key: string, ctx: NameContext): EvidenceLabel | null {
  if (key.startsWith('design:')) {
    const id = key.slice(7);
    if (DESIGN_LIMITS[id]) return { kind: 'design', text: join([bi('Design limit', 'Límite de diseño'), DESIGN_LIMITS[id]], ': ') };
    if (OUTPUT_BLOCKS[id]) return { kind: 'block', text: join([bi('Computed in the bake from', 'Calculado previamente desde'), OUTPUT_BLOCKS[id]], ' ') };
    return null;
  }
  if (key.startsWith('contract:')) {
    const rule = CONTRACT_RULES[key.slice(9)];
    return rule ? { kind: 'contract', text: join([bi('Contract 1 rule', 'Regla del contrato 1'), rule], ': ') } : null;
  }
  if (key.startsWith('rate:')) {
    const text = rateName(key.slice(5), ctx);
    return text ? { kind: 'rate', text } : null;
  }
  const [testId, modelId, ...rest] = key.split('@');
  const t = testName(testId);
  if (!t) return null;
  const parts: BiText[] = [];
  if (modelId !== undefined) {
    const mn = modelName(modelId, ctx);
    if (!mn) return null;
    parts.push(mn);
  }
  const segment = rest.length ? rest.join('@') : undefined;
  if (segment !== undefined) {
    const sn = segmentName(segment, ctx);
    if (!sn) return null;
    parts.push(sn);
  }
  // the model and the segment in parentheses after the test; after a name that ends in its own parentheses, a comma
  const wrap = (name: string, rest: string) => (name.endsWith(')') ? `${name}, ${rest}` : `${name} (${rest})`);
  const text = parts.length ? bi(wrap(t.en, parts.map((p) => p.en).join(', ')), wrap(t.es, parts.map((p) => p.es).join(', '))) : t;
  return { kind: 'test', text, testId, modelId, segment };
}

/** The words of an evidence key in a language, else the key: for a renderer; the names gate keeps the fallback unused. */
export function evidenceText(key: string, ctx: NameContext, lang: Lang): string {
  const l = evidenceLabel(key, ctx);
  return l ? l.text[lang] : key;
}
