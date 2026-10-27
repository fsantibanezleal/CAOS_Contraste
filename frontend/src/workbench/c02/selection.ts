// The selection the C02 views share, and the readings of a horizon document every view needs. Nothing here computes a
// statistic: the ROC and CAP points, the AUC with its DeLong interval, the reliability bins, the overfit gap, the
// transfer cells, the term structure and the ECL effect are the bake's; the helpers find, name and map. The files carry
// no date and no firm identifier, so no helper claims an out-of-time reading; the transfer and the term structure are
// labelled exploratory wherever they are shown.
import type { Bi } from '../c03/U6Shared';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import { shortName } from '../model';
import { segmentName } from '../names';
import type { NamedParam } from '../c20/U14Common';

export type C02Outputs = components['schemas']['c02Outputs'];
export type C02Fit = components['schemas']['c02Fit'];
export type C02Rung = components['schemas']['c02Rung'];
export type C02Challenger = components['schemas']['c02Challenger'];

export interface C02Sel {
  data: CaseData;
  /** The rung in focus (its model id): the ROC, the reliability diagram and the transfer map draw it. */
  rung: string;
  /** The challenger compared with the champion in the Rungs view (its model id). */
  challenger: string;
}

/** The outputs of the selected variant, or null when it is not a horizon document. */
export function outputsOf(sel: Pick<C02Sel, 'data'> | null): C02Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'horizon' ? (out as C02Outputs) : null;
}

/** The fit of the C02 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C02Sel, 'data'> | null): C02Fit | null {
  return (sel?.data.models as unknown as { fit?: C02Fit } | undefined)?.fit ?? null;
}

export function rungOf(o: C02Outputs | null, id: string): C02Rung | null {
  return o?.rungs.find((r) => r.model_id === id) ?? null;
}

/** The rung in focus of a selection, or the first rung when the document does not carry it. */
/** A model's id without the prefix of the file it was fitted on: "h1-P2a-l1" and "pooled-P2a-l1" are the model "P2a-l1", the
 * key the transfer cells use and the one that joins a model across the six files (the rung code alone does not: P4 names
 * LightGBM and XGBoost). */
export const bareModel = (id: string): string => id.replace(/^(?:h\d+|pooled)-/, '');

export function rungFor(sel: C02Sel | null): C02Rung | null {
  const o = outputsOf(sel);
  return rungOf(o, sel?.rung ?? '') ?? o?.rungs[0] ?? null;
}

/** The comparison of the challenger in focus with the champion, or the first one the document carries. */
export function challengerFor(sel: C02Sel | null): C02Challenger | null {
  const o = outputsOf(sel);
  return o?.challenger.find((c) => c.challenger === sel?.challenger) ?? o?.challenger[0] ?? null;
}

/** The name of a rung of the variant: its short title, else its id. */
export function rungName(sel: Pick<C02Sel, 'data'> | null, id: string): Bi {
  const m = sel?.data.variant.model.find((x) => x.id === id);
  const t = shortName(m, id);
  return typeof t === 'string' ? { en: t, es: t } : t;
}

/** The name of a ladder rung in the Context, from the loaded file's own model where the file carries it: the single-variable rung's
 * input differs by file (U16-R4 c03 NB2: the 1-year file's "Attr39" on every variant) and is named as the codebook names it
 * ("Single variable: profit on sales / sales (Attr39)", NB1), a `_missing` column as its missing-value indicator. */
export function ladderLabel(sel: Pick<C02Sel, 'data'> | null, label: Bi): Bi {
  const own = /^Single variable \(/.test(label.en) ? sel?.data.variant.model.find((m) => bareModel(m.id) === 'P0-single')?.title : undefined;
  const title = (own as Bi | undefined) ?? label;
  const col = /^Single variable \(([^()]+)\)$/.exec(title.en)?.[1];
  if (!col) return title;
  const name = segmentName(`characteristic:${col}`, { caseId: 'C02' });
  return name ? { en: `Single variable: ${name.en}`, es: `Una variable: ${name.es}` } : title;
}

/** The selection a variant opens on: the challenger of the first comparison (else the last rung) in focus. */
export function defaultSel(data: CaseData | null): C02Sel | null {
  if (!data || data.manifest.case_id !== 'C02') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const last = o.rungs[o.rungs.length - 1]?.model_id ?? '';
  const challenger = o.challenger[0]?.challenger ?? last;
  return { data, rung: challenger, challenger };
}

export const HORIZON_TEXT = (years: number | null): Bi =>
  years === null ? { en: 'Pooled', es: 'Agrupado' } : { en: `${years}-year horizon`, es: years === 1 ? 'Horizonte de 1 año' : `Horizonte de ${years} años` };

/** An interval's two ends as a range a reader cannot misread beside a negative bound ("-0,0221 a -0,0118", never "-0,0221 - -0,0118"). */
export function span(lo: string, hi: string, lang: 'en' | 'es'): string {
  return `${lo} ${lang === 'es' ? 'a' : 'to'} ${hi}`;
}

/** A document text in the language: a bilingual text (c02-outputs 3.0.0, c02-models 2.0.0) or the English string a document baked
 * before carries until it is re-baked (the named parameter's unit and basis, the ladder's engine; U16-R3 c03 B2 and B3). */
export function textIn(t: string | Bi | null | undefined, lang: 'en' | 'es'): string {
  if (t === null || t === undefined) return '';
  return typeof t === 'string' ? t : t[lang];
}

/** The named parameters of a C02 document with the unit and the basis in the language, as the shared table prints them. */
export function paramsIn(params: unknown, lang: 'en' | 'es'): NamedParam[] {
  return (params as Array<Omit<NamedParam, 'unit' | 'basis'> & { unit: string | Bi; basis: string | Bi }>).map((p) => ({
    ...p,
    unit: textIn(p.unit, lang),
    basis: textIn(p.basis, lang),
  }));
}

/** A value of three decimals that rounds to zero prints as 0, never "-0.000" (the pooled scorecard's gap is -0.000002; R3 c03 m5). */
export const noNegZero = (v: number, decimals = 3): number => (Math.round(Math.abs(v) * 10 ** decimals) === 0 ? 0 : v);
