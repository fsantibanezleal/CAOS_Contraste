// C22's sections of the cross-case pages: Experiments (the eight families and the size of every test) and Benchmark
// (which test sees which defect at equal size, and the published simulations reproduced). Every number is read from
// the committed artifacts at load time; the verdicts are computed from them, never typed in.
import { PlotCard, Verdict, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../api/artifacts';
import type { C22Simulation, CaseManifest, Text, VariantArtifact } from '../lib/contract.types';
import { WithQuotes, useT } from '../content/bi';
import { curves, isC22, rateOf, type C22Variant } from '../workbench/c22/selection';

const pct = (lang: 'en' | 'es', v: number | null | undefined, decimals = 1) => formatNumber(v, lang, { percent: true, decimals });
const AT5 = 'p<0.05';
const AT1 = 'p<0.01';
/** the power a test is said to reach a defect with */
const POWER = 0.8;

function useFamilies(manifest: CaseManifest) {
  const all = useArtifact<VariantArtifact[]>((s) => loadAllVariants(manifest, s), [manifest.case_id]);
  const families = all.state === 'ready' ? (all.data as VariantArtifact<unknown>[]).filter(isC22) : null;
  return families;
}

function rateCell(s: C22Simulation, rule: string, lang: 'en' | 'es') {
  const r = rateOf(s, rule);
  return r.rate === null ? '-' : `${pct(lang, r.rate)} (${pct(lang, r.se, 2)})`;
}

/** A test's size holds when its exact probability is at most the level, or, without one, its rate is under the bound. */
function holds(v: C22Variant, s: C22Simulation, rule: string, level: number) {
  const r = rateOf(s, rule);
  return r.exact !== null ? r.exact <= level + 1e-12 : (r.rate ?? 1) <= v.outputs.size_bounds[rule];
}

export function C22ExperimentsSection({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const families = useFamilies(manifest);
  if (!families) return <p className="caos-pending" data-state="loading">{t('Loading the families', 'Cargando las familias')}</p>;
  const titles = Object.fromEntries(manifest.artifacts.map((a) => [a.variant_id, a.title]));
  const nul = families.find((v) => v.outputs.ladder === null);
  const sizes = nul ? nul.outputs.simulations.filter((s) => s.key.endsWith('@null')) : [];
  return (
    <div data-state="ready">
      <table className="caos-table ct-wrap-head" data-table="families">
        <thead>
          <tr>
            <th className="caos-col-text">{t('Family', 'Familia')}</th>
            <th className="caos-col-text">{t('Generators', 'Generadores')}</th>
            <th className="caos-col-text">{t('Severity ladder', 'Escala de severidad')}</th>
            <th>{t('Simulations', 'Simulaciones')}</th>
            <th className="caos-col-text">{t('Findings', 'Hallazgos')}</th>
          </tr>
        </thead>
        <tbody>
          {families.map((v) => {
            const o = v.outputs;
            const names = [...new Set(Object.values(o.generators).map((g) => g.name))];
            return (
              <tr key={v.variant_id} data-family={v.variant_id}>
                <td className="caos-col-text">{pick(titles[v.variant_id] ?? { en: v.variant_id, es: v.variant_id }, lang)}</td>
                <td className="caos-col-text">{names.join(', ')}</td>
                <td className="caos-col-text">
                  {o.ladder ? `${pick(o.ladder.label, lang)}: ${o.ladder.values.map((x) => formatNumber(x, lang, { digits: 3 })).join('; ')}` : t('none: every test at its null', 'ninguna: cada prueba en su nula')}
                </td>
                <td>{formatNumber(o.simulations.length, lang)}</td>
                <td className="caos-col-text">{v.findings.map((f) => `${f.id} (${f.severity})`).join(', ')}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {nul && (
        <PlotCard title={{ en: 'C22, the size of every test with a p-value', es: 'C22, el tamaño de cada prueba con valor p' }} lane="replay" provenance="synthetic">
          <Verdict
            compact
            title={{ en: 'What the null family supports', es: 'Lo que respalda la familia nula' }}
            tone="accent"
            verdict={(() => {
              const bad = sizes.filter((s) => !holds(nul, s, AT5, 0.05) || !holds(nul, s, AT1, 0.01));
              const size = (s: C22Simulation, rule: string) => rateOf(s, rule).exact ?? rateOf(s, rule).rate;
              const names = (l: 'en' | 'es') => {
                const at = l === 'es' ? 'al' : 'at';
                return bad.map((s) => `${pick(s.label, l)} (${pct(l, size(s, AT5), 2)} ${at} 5%, ${pct(l, size(s, AT1), 2)} ${at} 1%)`).join('; ');
              };
              return {
                en: `${sizes.length - bad.length} of the ${sizes.length} tests hold their size at both levels on ${formatNumber(sizes[0]?.n_rep, 'en')} repetitions of data where their null holds at its boundary. ${bad.length ? `Not: ${names('en')}.` : ''}`,
                es: `${sizes.length - bad.length} de las ${sizes.length} pruebas mantienen su tamaño en ambos niveles en ${formatNumber(sizes[0]?.n_rep, 'es')} repeticiones de datos donde su nula se cumple en su frontera. ${bad.length ? `No: ${names('es')}.` : ''}`,
              };
            })()}
          />
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="sizes">
              <thead>
                <tr>
                  <th className="caos-col-text">{t('Test', 'Prueba')}</th>
                  <th className="caos-col-text">{t('Where its null holds', 'Dónde se cumple su nula')}</th>
                  <th>{t('Rate at 5% (SE)', 'Tasa al 5% (EE)')}</th>
                  <th>{t('Rate at 1% (SE)', 'Tasa al 1% (EE)')}</th>
                  <th>{t('Exact at 5%', 'Exacta al 5%')}</th>
                  <th>{t('Size', 'Tamaño')}</th>
                </tr>
              </thead>
              <tbody>
                {sizes.map((s) => {
                  const ok = holds(nul, s, AT5, 0.05) && holds(nul, s, AT1, 0.01);
                  return (
                    <tr key={s.key} data-sim={s.key} data-holds={ok ? 'yes' : 'no'}>
                      <td className="caos-col-text">{pick(s.label, lang)}</td>
                      <td className="caos-col-text">{pick(s.scenario, lang)}</td>
                      <td>{rateCell(s, AT5, lang)}</td>
                      <td>{rateCell(s, AT1, lang)}</td>
                      <td>{rateOf(s, AT5).exact === null ? '-' : pct(lang, rateOf(s, AT5).exact, 2)}</td>
                      <td>{ok ? t('holds', 'se mantiene') : t('exceeds', 'excede')}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </PlotCard>
      )}
    </div>
  );
}

interface Detection {
  family: string;
  familyTitle: Text;
  panel: Text;
  test: Text;
  axis: Text;
  null0: number | null;
  first80: number | null;
  top: number | null;
  topX: number;
}

/** Every curve of every defect family: its rate where the defect is absent, the first setting of the ladder at which it
 * reaches 80% at 5%, and its rate at the highest severity. */
function detections(families: C22Variant[], titles: Record<string, Text>): Detection[] {
  const out: Detection[] = [];
  for (const v of families) {
    if (!v.outputs.ladder) continue;
    // the power curves only: a size panel (the development AUC estimated, nothing changed) is not a defect
    for (const p of v.outputs.panels.filter((x) => x.measures === 'power')) {
      for (const g of curves(v, p.id)) {
        const xs = [...new Set(g.rows.map((s) => s.x))];
        if (xs.length < 2) continue;
        const rows = [...g.rows].sort((a, b) => a.x - b.x);
        const first = rows.find((s) => (rateOf(s, AT5).rate ?? 0) >= POWER);
        const top = rows[rows.length - 1];
        out.push({
          family: v.variant_id,
          familyTitle: titles[v.variant_id] ?? { en: v.variant_id, es: v.variant_id },
          panel: p.label,
          test: rows[0].label,
          axis: p.axis ?? v.outputs.ladder.label,
          null0: rateOf(rows[0], AT5).rate,
          first80: first ? first.x : null,
          top: rateOf(top, AT5).rate,
          topX: top.x,
        });
      }
    }
  }
  return out;
}

interface FalseAlarm {
  family: string;
  familyTitle: Text;
  panel: Text;
  test: Text;
  axis: Text;
  base: number | null;
  top: number | null;
  topX: number;
  bound: number;
}

/** The size panels of the defect families: the model is right and an assumption fails, so every rejection is a false
 * alarm; the rate where the assumption holds, and at the highest severity against the size bound. */
function falseAlarms(families: C22Variant[], titles: Record<string, Text>): FalseAlarm[] {
  const out: FalseAlarm[] = [];
  for (const v of families) {
    if (!v.outputs.ladder) continue;
    for (const p of v.outputs.panels.filter((x) => x.measures === 'size')) {
      for (const g of curves(v, p.id)) {
        const rows = [...g.rows].sort((a, b) => a.x - b.x);
        if (new Set(rows.map((s) => s.x)).size < 2) continue;
        const top = rows[rows.length - 1];
        out.push({
          family: v.variant_id,
          familyTitle: titles[v.variant_id] ?? { en: v.variant_id, es: v.variant_id },
          panel: p.label,
          test: rows[0].label,
          axis: p.axis ?? v.outputs.ladder.label,
          base: rateOf(rows[0], AT5).rate,
          top: rateOf(top, AT5).rate,
          topX: top.x,
          // the level plus 3.09 Monte Carlo SEs at this row's repetitions (the engine's size_bound)
          bound: 0.05 + 3.090232306167813 * Math.sqrt((0.05 * 0.95) / top.n_rep),
        });
      }
    }
  }
  return out;
}

export function C22BenchmarkSection({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const families = useFamilies(manifest);
  if (!families) return <p className="caos-pending" data-state="loading">{t('Loading the comparisons', 'Cargando las comparaciones')}</p>;
  const titles = Object.fromEntries(manifest.artifacts.map((a) => [a.variant_id, a.title])) as Record<string, Text>;
  const rows = detections(families, titles);
  const reach = rows.filter((r) => r.first80 !== null);
  const blind = rows.filter((r) => (r.top ?? 0) < 0.2);
  const golden = families.flatMap((v) => v.outputs.golden);
  const alarms = falseAlarms(families, titles);
  const exceeds = alarms.filter((a) => (a.top ?? 0) > a.bound);
  const list = (rs: Detection[], l: 'en' | 'es') => rs.map((r) => `${pick(r.test, l)} (${pick(r.familyTitle, l)}, ${pct(l, r.top)})`).join('; ');
  return (
    <div data-state="ready">
      <PlotCard title={{ en: 'C22, which test sees which defect', es: 'C22, qué prueba ve qué defecto' }} lane="replay" provenance="synthetic">
        <Verdict
          compact
          title={{ en: 'What the power curves support', es: 'Lo que respaldan las curvas de potencia' }}
          tone="accent"
          verdict={{
            en: `Of ${rows.length} curves of a test against a planted defect it should see, ${reach.length} reach ${pct('en', POWER, 0)} power at 5% within the family's ladder. ${blind.length} stay below 20% at the highest severity: ${list(blind, 'en')}. The ladders are Contraste's design choices; power on them is not the probability of finding a real bank's problem.`,
            es: `De ${rows.length} curvas de una prueba contra un defecto plantado que debería ver, ${reach.length} alcanzan ${pct('es', POWER, 0)} de potencia al 5% dentro de la escala de la familia. ${blind.length} quedan bajo 20% en la mayor severidad: ${list(blind, 'es')}. Las escalas son elecciones de diseño de Contraste; la potencia en ellas no es la probabilidad de encontrar el problema de un banco real.`,
          }}
        />
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="detections">
            <thead>
              <tr>
                <th className="caos-col-text">{t('Defect', 'Defecto')}</th>
                <th className="caos-col-text">{t('Test', 'Prueba')}</th>
                <th className="caos-col-text">{t('Setting', 'Ajuste')}</th>
                <th>{t('Rate without the defect', 'Tasa sin el defecto')}</th>
                <th>{t('80% power from', '80% de potencia desde')}</th>
                <th>{t('Rate at the highest severity', 'Tasa en la mayor severidad')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.family}|${r.panel.en}|${r.test.en}`} data-family={r.family}>
                  <td className="caos-col-text">{pick(r.familyTitle, lang)}</td>
                  <td className="caos-col-text">{pick(r.test, lang)}</td>
                  <td className="caos-col-text">{`${pick(r.panel, lang)}; ${pick(r.axis, lang)}`}</td>
                  <td>{pct(lang, r.null0)}</td>
                  <td>{r.first80 === null ? t('not within the ladder', 'no dentro de la escala') : formatNumber(r.first80, lang, { digits: 3 })}</td>
                  <td>{`${pct(lang, r.top)} (${formatNumber(r.topX, lang, { digits: 3 })})`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
      <PlotCard title={{ en: 'C22, false alarms when an assumption fails', es: 'C22, falsas alarmas cuando falla un supuesto' }} lane="replay" provenance="synthetic">
        <Verdict
          compact
          title={{ en: 'What the size curves support', es: 'Lo que respaldan las curvas de tamaño' }}
          tone={exceeds.length ? 'warn' : 'accent'}
          verdict={{
            en: `The model is right in every row below; only an assumption fails. ${exceeds.length} of ${alarms.length} curves exceed the size bound (the level plus 3.09 Monte Carlo SEs) at the highest severity: ${exceeds.map((a) => `${pick(a.test, 'en')} (${pick(a.familyTitle, 'en')}, ${pct('en', a.top)})`).join('; ')}.`,
            es: `El modelo es correcto en cada fila de abajo; solo falla un supuesto. ${exceeds.length} de ${alarms.length} curvas exceden la cota de tamaño (el nivel más 3,09 EE de Monte Carlo) en la mayor severidad: ${exceeds.map((a) => `${pick(a.test, 'es')} (${pick(a.familyTitle, 'es')}, ${pct('es', a.top)})`).join('; ')}.`,
          }}
        />
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="false-alarms">
            <thead>
              <tr>
                <th className="caos-col-text">{t('Assumption that fails', 'Supuesto que falla')}</th>
                <th className="caos-col-text">{t('Test', 'Prueba')}</th>
                <th className="caos-col-text">{t('Setting', 'Ajuste')}</th>
                <th>{t('Rate where it holds', 'Tasa donde se cumple')}</th>
                <th>{t('Rate at the highest severity', 'Tasa en la mayor severidad')}</th>
                <th>{t('Size', 'Tamaño')}</th>
              </tr>
            </thead>
            <tbody>
              {alarms.map((a) => (
                <tr key={`${a.family}|${a.panel.en}|${a.test.en}`} data-family={a.family} data-holds={(a.top ?? 0) > a.bound ? 'no' : 'yes'}>
                  <td className="caos-col-text">{pick(a.familyTitle, lang)}</td>
                  <td className="caos-col-text">{pick(a.test, lang)}</td>
                  <td className="caos-col-text">{`${pick(a.panel, lang)}; ${pick(a.axis, lang)}`}</td>
                  <td>{pct(lang, a.base)}</td>
                  <td>{`${pct(lang, a.top)} (${formatNumber(a.topX, lang, { digits: 3 })})`}</td>
                  <td>{(a.top ?? 0) > a.bound ? t('exceeds', 'excede') : t('holds', 'se mantiene')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
      <PlotCard title={{ en: 'C22, the published simulations reproduced', es: 'C22, las simulaciones publicadas reproducidas' }} lane="replay" provenance="published">
        <table className="caos-table ct-wrap-head" data-table="reproductions">
          <thead>
            <tr>
              <th className="caos-col-text">{t('Study', 'Estudio')}</th>
              <th>{t('Cells', 'Celdas')}</th>
              <th>{t('Agree within 3.29 combined SE', 'Concuerdan dentro de 3,29 EE combinados')}</th>
              <th className="caos-col-text">{t('Cells that do not', 'Celdas que no')}</th>
            </tr>
          </thead>
          <tbody>
            {golden.map((g) => (
              <tr key={g.study} data-study={g.study}>
                <td className="caos-col-text">{pick(g.title, lang)}</td>
                <td>{formatNumber(g.total, lang)}</td>
                <td>{formatNumber(g.agree, lang)}</td>
                <td className="caos-col-text">
                  {/* each cell as its paper names it (table, row, column: the paper's own labels), then published / measured */}
                  {g.cells.filter((c) => !c.agrees).length
                    ? g.cells
                        .filter((c) => !c.agrees)
                        .map((c, k) => (
                          <span key={`${c.table}-${c.row}-${c.column}`}>
                            {k > 0 ? '; ' : ''}
                            <span translate="no" lang="en">{`${c.table}, ${c.row}, ${c.column}`}</span>
                            {`: ${formatNumber(c.published, lang, { digits: 3 })} / ${formatNumber(c.measured, lang, { digits: 3 })}`}
                          </span>
                        ))
                    : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {golden.map((g) => (
          <p key={g.study} className="ct-note">
            <WithQuotes text={pick(g.note, lang)} />
          </p>
        ))}
      </PlotCard>
    </div>
  );
}
