// The words of the story, in both languages. A headline states a finding with its number, at most 12 words (ADR-0082 rule 3);
// every number arrives as an argument read from an artifact, never written here. Spanish follows the product's rules
// (scripts/check_spanish.py): accents, the rulings on terms, decimals with a comma through formatNumber.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { ZONE_TEXT } from '../workbench/c11/selection';
import { bi, type Bi, type Decision, type Tally, type Zone } from './model';

export type Lang = 'en' | 'es';
const n0 = (v: number, lang: Lang) => formatNumber(v, lang, { decimals: 0 });

export const STEP_IDS = ['inventory', 'backtest', 'crisis', 'recalibrate', 'decide'] as const;
export type StepId = (typeof STEP_IDS)[number];

export const VERBS: Record<StepId, Bi> = {
  inventory: bi('Take inventory', 'Hacer el inventario'),
  backtest: bi('Back-test', 'Contrastar'),
  crisis: bi('Read the crisis', 'Leer la crisis'),
  recalibrate: bi('Recalibrate', 'Recalibrar'),
  decide: bi('Decide', 'Decidir'),
};

export const zoneBi = (z: Zone | 'not_evaluated'): Bi => ZONE_TEXT[z] ?? bi(z, z);

/** The words of the three zones and the exceptions each holds, from the cuts of the Basel table. */
export function zoneRange(z: Zone, cuts: { amberStart: number; redStart: number }, lang: Lang): string {
  const to = lang === 'es' ? 'a' : 'to';
  if (z === 'green') return `0 ${to} ${cuts.amberStart - 1}`;
  if (z === 'amber') return `${cuts.amberStart} ${to} ${cuts.redStart - 1}`;
  return lang === 'es' ? `${cuts.redStart} o más` : `${cuts.redStart} or more`;
}

export const missingNumber: Bi = bi('number not available', 'número no disponible');

export function headlineInventory(models: number, s1: number, s2: number): Bi {
  return bi(
    `${models} models carry ${s1} critical and ${s2} significant findings`,
    `${models} modelos acumulan ${s1} hallazgos críticos y ${s2} significativos`,
  );
}

/** A model's name short enough for a headline: the title up to ' with ' / ' con ', up to a parenthesis, and up to a comma that
 * leaves two words and keeps no number (so "Historical simulation, 250 days" stays whole). */
export function headName(label: Bi): Bi {
  const cut = (v: string): string => {
    let out = v.split(/ with | con /)[0]!;
    out = out.split(' (')[0]!;
    const comma = out.indexOf(',');
    if (comma > 0 && out.slice(0, comma).trim().split(/\s+/).length >= 2 && !/\d/.test(out.slice(comma))) out = out.slice(0, comma);
    return out.trim();
  };
  return bi(cut(label.en), cut(label.es));
}

export function headlineBacktest(label: Bi, final: number | null, zone: Zone | null, exceptions: number, days: number): Bi {
  const name = headName(label);
  if (final == null || zone == null) {
    return bi(`${name.en}: ${exceptions} exceptions in ${days} days`, `${name.es}: ${exceptions} excepciones en ${days} días`);
  }
  const z = zoneBi(zone);
  return bi(`${name.en}: ${final} exceptions, ${z.en.toLowerCase()} zone`, `${name.es}: ${final} excepciones, zona ${z.es.toLowerCase()}`);
}

export function headlineCrisis(label: Bi, exceptions: number, days: number): Bi {
  const name = headName(label);
  return bi(`${name.en}: ${exceptions} VaR breaches in ${days} days`, `${name.es}: ${exceptions} excedencias del VaR en ${days} días`);
}

export function headlineRecalibration(raw: number, wrapped: number): Bi {
  if (wrapped < raw) return bi(`Recalibration cuts breaches from ${raw} to ${wrapped}`, `La recalibración baja las excedencias de ${raw} a ${wrapped}`);
  if (wrapped > raw) return bi(`Recalibration raises breaches from ${raw} to ${wrapped}`, `La recalibración sube las excedencias de ${raw} a ${wrapped}`);
  return bi(`Recalibration leaves breaches at ${raw}`, `La recalibración deja las excedencias en ${raw}`);
}

export function headlineDecision(d: Pick<Decision, 'eligible' | 'total' | 'setSize'>): Bi {
  if (d.setSize == null) {
    return bi(`The gates pass ${d.eligible} of ${d.total} models`, `Las compuertas aprueban ${d.eligible} de ${d.total} modelos`);
  }
  return bi(
    `Gates pass ${d.eligible} of ${d.total} models; the confidence set keeps ${d.setSize}`,
    `Pasan las compuertas ${d.eligible} de ${d.total} modelos; el conjunto retiene ${d.setSize}`,
  );
}

export const words = (b: Bi, lang: Lang): number => b[lang].split(/\s+/).filter(Boolean).length;

export function sublineTally(t: Tally | null, days: number, lang: Lang): string {
  if (!t) {
    return lang === 'es'
      ? `La ventana tiene ${n0(days, lang)} días y el semáforo de Basilea necesita 250: aquí se cuentan las excepciones acumuladas.`
      : `The window has ${n0(days, lang)} days and the Basel light needs 250: the exceptions so far are counted here.`;
  }
  return lang === 'es'
    ? `Excepciones en los 250 días previos, de ${n0(t.windows, lang)} ventanas completas: ${n0(t.green, lang)} verdes, ${n0(t.amber, lang)} ámbar, ${n0(t.red, lang)} rojas.`
    : `Exceptions in the trailing 250 days over ${n0(t.windows, lang)} complete windows: ${n0(t.green, lang)} green, ${n0(t.amber, lang)} amber, ${n0(t.red, lang)} red.`;
}
