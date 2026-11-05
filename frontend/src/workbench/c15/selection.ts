// The selection the C15 views share, and the readings of an annex1-variant document every view needs. Nothing here
// computes a statistic: the legs, the shocked EVE and NII, the offset, the indexation charge, the floors' effect and the
// prioritised-bank tests are the bake's; the helpers find, name and map. Where the rail chooses the offset on or off the
// helper picks the matching field of the pair (`with_offset` or `without_offset`) and takes the largest of the six, as
// Annex 1 defines the measure; it never rescales a number. The sign convention is the document's: a positive delta is a loss.
import type { Bi } from '../c03/U6Shared';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import { compactMoney, axisScale } from '../c06/format';

export type C15Outputs = components['schemas']['c15Outputs'];
export type C15Fit = components['schemas']['c15Fit'];
export type C15EveRow = components['schemas']['c15EveRow'];
export type C15NiiRow = components['schemas']['c15NiiRow'];
export type C15Pair = components['schemas']['c15Pair'];
export type C15Leg = components['schemas']['c15Leg'];

export type ShockId = C15EveRow['shock'];
export type LegId = 'CLP' | 'UR';
export type OffsetChoice = 'on' | 'off';

export interface C15Sel {
  data: CaseData;
  /** The prescribed shock in focus. */
  shock: ShockId;
  /** The leg of the banking book in focus (CLP, or the UF-indexed UR leg). */
  leg: LegId;
  /** Whether the 50 percent CLP and CLF offset is applied. */
  offset: OffsetChoice;
}

/** The outputs of the selected variant, or null when it is not an annex1-variant document. */
export function outputsOf(sel: Pick<C15Sel, 'data'> | null): C15Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'annex1-variant' ? (out as C15Outputs) : null;
}

/** The fit of the C15 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C15Sel, 'data'> | null): C15Fit | null {
  return (sel?.data.models as unknown as { fit?: C15Fit } | undefined)?.fit ?? null;
}

export const SHOCK_ORDER: readonly ShockId[] = ['parallel-up', 'parallel-down', 'steepener', 'flattener', 'short-up', 'short-down'];
export const SHOCK_TEXT: Record<string, Bi> = {
  'parallel-up': { en: 'Parallel up', es: 'Paralelo al alza' },
  'parallel-down': { en: 'Parallel down', es: 'Paralelo a la baja' },
  steepener: { en: 'Steepener', es: 'Empinamiento' },
  flattener: { en: 'Flattener', es: 'Aplanamiento' },
  'short-up': { en: 'Short rates up', es: 'Tasas cortas al alza' },
  'short-down': { en: 'Short rates down', es: 'Tasas cortas a la baja' },
};
export const LEG_TEXT: Record<string, Bi> = {
  CLP: { en: 'CLP leg', es: 'Tramo CLP' },
  UR: { en: 'UF (UR) leg', es: 'Tramo UF (UR)' },
};
export const LEG_SHORT: Record<string, Bi> = { CLP: { en: 'CLP', es: 'CLP' }, UR: { en: 'UF (UR)', es: 'UF (UR)' } };
export const OFFSET_TEXT: Record<string, Bi> = {
  on: { en: 'Offset on', es: 'Compensación activa' },
  off: { en: 'Offset off', es: 'Compensación inactiva' },
};
/** The chip text of the offset choice: the section and the group label already say "offset", so the two chips fit one row of the rail. */
export const OFFSET_SHORT: Record<string, Bi> = {
  on: { en: 'On', es: 'Activa' },
  off: { en: 'Off', es: 'Inactiva' },
};
export const OFFSET_LONG: Record<string, Bi> = {
  on: { en: 'Half of the CLP delta is offset against the CLF delta when their signs are opposite', es: 'Se compensa la mitad del delta CLP contra el delta CLF cuando sus signos son opuestos' },
  off: { en: 'No offset: the positive parts of the two legs add', es: 'Sin compensación: se suman las partes positivas de los dos tramos' },
};
export const ORIGIN_TEXT: Record<string, Bi> = {
  'srp31-table-2024': { en: 'Basel SRP31 Table 2 (2024)', es: 'Basilea SRP31 Tabla 2 (2024)' },
  'srp31-table-2016': { en: 'Basel d368 Annex 2 (2016)', es: 'Basilea d368 Anexo 2 (2016)' },
  'cmf-annex1': { en: 'CMF RAN 21-13 Annex 1', es: 'CMF RAN 21-13 Anexo 1' },
  'contraste-estimate': { en: 'Contraste estimate, not a regulatory parameter', es: 'Estimación de Contraste, no un parámetro regulatorio' },
};
export const BASKET_TEXT: Record<string, Bi> = {
  'canasta-1': { en: 'Basket 1 currencies', es: 'Monedas de la canasta 1' },
  'canasta-2': { en: 'Basket 2 currencies', es: 'Monedas de la canasta 2' },
  CLP: { en: 'CLP', es: 'CLP' },
  'UR-nii': { en: 'UR, delta NII', es: 'UR, delta NII' },
  'UR-eve': { en: 'UR, delta EVE', es: 'UR, delta EVE' },
};
export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

/** The money fields of the document are in the reporting currency; the document's scale says in what unit. */
export interface MoneyDoc {
  units: C15Outputs['units'];
  currency: string;
}
export const moneyDoc = (o: C15Outputs): MoneyDoc => ({ units: o.units, currency: o.reporting_currency });

export function scaleFactor(o: Pick<MoneyDoc, 'units'>): number {
  return o.units.money_scale === 'millions' ? 1e6 : o.units.money_scale === 'thousands' ? 1e3 : 1;
}
/** The unit text of a column of money in the document's scale: "CLP millions". */
export function scaleUnit(o: MoneyDoc): Bi {
  const word = o.units.money_scale === 'millions' ? { en: 'millions', es: 'millones' } : o.units.money_scale === 'thousands' ? { en: 'thousands', es: 'miles' } : null;
  return word ? { en: `${o.currency} ${word.en}`, es: `${word.es} de ${o.currency}` } : { en: o.currency, es: o.currency };
}
/** An amount in a narrow place (a read-out): scaled to units, then to bn or m with the unit that says so. */
export function amount(o: MoneyDoc, v: number | null | undefined, currency?: string) {
  return compactMoney(v === null || v === undefined ? null : v * scaleFactor(o), currency ?? o.currency);
}
/** The scale of a money axis: the divisor from the document's scale and the unit its title carries. */
export function axisOf(o: MoneyDoc, values: ReadonlyArray<number | null | undefined>) {
  const k = scaleFactor(o);
  const max = Math.max(0, ...values.map((v) => Math.abs(v ?? 0))) * k;
  const s = axisScale(max, o.currency);
  return { div: s.div / k, unit: s.unit };
}

/** The pair total the offset choice selects: the pair field `with_offset` or `without_offset`. */
export const pairTotal = (p: C15Pair, offset: OffsetChoice): number => (offset === 'on' ? p.with_offset : p.without_offset);

/** The measure of Annex 1 under an offset choice: the largest of the pair totals, never below zero (no loss is a zero). */
export function worst<T>(rows: readonly T[], pairOf: (r: T) => C15Pair, offset: OffsetChoice): number {
  return Math.max(0, ...rows.map((r) => pairTotal(pairOf(r), offset)));
}

export const eveRowOf = (o: C15Outputs | null, shock: string): C15EveRow | null => o?.eve.rows.find((r) => r.shock === shock) ?? null;
export const legOf = (o: C15Outputs | null, leg: string): C15Leg | null => o?.legs.find((l) => l.leg === leg) ?? null;

/** The offset state the document applies in its own measure: "off" when it says so, "on" for on and compared. */
export const documentOffset = (o: Pick<C15Outputs, 'offset_rule'>): OffsetChoice => (o.offset_rule.state === 'off' ? 'off' : 'on');

/** The selection a variant opens on: the first shock, the CLP leg and the offset state the document applies. */
export function defaultSel(data: CaseData | null): C15Sel | null {
  if (!data || data.manifest.case_id !== 'C15') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  return { data, shock: o.eve.rows[0]?.shock ?? 'parallel-up', leg: 'CLP', offset: documentOffset(o) };
}
