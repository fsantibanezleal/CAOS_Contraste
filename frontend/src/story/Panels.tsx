// The docked panel of each step: V2 (the selected family opened by the three elements of SR 11-7) beside the flow, and the
// readouts and model lists beside V3 to V6. A panel item and its scene object share one selection (useLinkedView): choosing a
// model or a family here highlights it in the drawing and back, with the same accent outline. Every number is read from the
// documents through model.ts; a value the document does not hold is shown as missing with its reason.
import { formatNumber, useLinkedView, useShellLang } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { evidenceText } from '../workbench/names';
import { entryText } from '../workbench/names';
import { WINDOW_TEXT, reasonText, testName, text as winText } from '../workbench/c11/selection';
import { ECB_F_OF, SEVERITY_NAME, severityText } from '../workbench/governance/model';
import { dayLabel, int, pct } from './chart';
import { crisisReadout } from './CrisisView';
import {
  ELEMENTS, SEVERITIES, findingsOfFamily, groupByElement, zoneOf, type Decision, type Flow, type ModelPath, type Recalibrated, type WindowModel,
} from './model';
import { MANUSCRIPT_LINK, MANUSCRIPT_URL, TESTS_TOO_EASY, UPPER_BOUND, VERDICT_LABEL } from '../workbench/c11/caveat';
import { zoneAdjective, zoneBi, zoneRange, type Lang } from './text';
import type { GovFindings } from '../workbench/governance/model';

const BASEL_URL = 'https://www.bis.org/publ/bcbs22.htm';
const MAR_URL = 'https://www.bis.org/basel_framework/chapter/MAR/32.htm';

export const WINDOW_IDS = Object.keys(WINDOW_TEXT);

function useT() {
  const lang = useShellLang() as Lang;
  return { lang, t: (en: string, es: string) => (lang === 'es' ? es : en) };
}

/** The window selector every panel carries: the story works for each window of the market case. */
export function WindowPicker({ value, onChange }: { value: string; onChange: (id: string) => void }) {
  const { lang, t } = useT();
  return (
    <label className="story-window">
      <span>{t('Market window', 'Ventana de mercado')}</span>
      <select value={value} onChange={(e) => onChange(e.currentTarget.value)} aria-label={t('Choose the market window of the story', 'Elegir la ventana de mercado del recorrido')}>
        {WINDOW_IDS.map((id) => (
          <option key={id} value={id}>
            {winText(WINDOW_TEXT, id)[lang]}
          </option>
        ))}
      </select>
    </label>
  );
}

/** A selectable object of the panel, linked to the same object of the scene. */
export function LinkedButton({ id, selected, onPick, children, title }: { id: string; selected: boolean; onPick: () => void; children: ReactNode; title?: string }) {
  const select = useLinkedView((s) => s.select);
  return (
    <button type="button" className="story-item" title={title} aria-pressed={selected} data-linked-id={id} data-linked-view="panel" data-linked-selected={selected ? 'true' : 'false'} onClick={() => { select(id, 'panel'); onPick(); }}>
      {children}
    </button>
  );
}

const ZONE_CLASS = { green: 'ok', amber: 'warn', red: 'bad' } as const;

/** The models of the window, each with its exceptions and the zone it ends in. */
export function ModelList({ w, selected, onPick, only }: { w: WindowModel; selected: string; onPick: (id: string) => void; only?: readonly string[] }) {
  const { lang, t } = useT();
  const models = only ? w.models.filter((m) => only.includes(m.id)) : w.models;
  return (
    <ul className="story-models" aria-label={t('Models of the ladder', 'Modelos de la escalera')}>
      {models.map((m) => {
        const zone = m.light ? m.light.zone : null;
        return (
          <li key={m.id}>
            <LinkedButton id={`model:${m.id}`} selected={m.id === selected} onPick={() => onPick(m.id)}>
              <span className="story-item-name">{m.label[lang]}</span>
              <span className="story-item-n">{int(m.exceedances.length, lang)}</span>
              <span className={`story-zone ${zone ? ZONE_CLASS[zone] : ''}`}>{zone ? zoneBi(zone)[lang] : t('n/e', 'n/e')}</span>
            </LinkedButton>
          </li>
        );
      })}
    </ul>
  );
}

const Source = ({ children }: { children: ReactNode }) => <small className="story-source">{children}</small>;

// --- step 1: V2, the family opened by the three elements of SR 11-7 -----------------------------------------------------

export function InventoryPanel({ flow, fin, selected, finding, onPick, onFinding }: { flow: Flow; fin: GovFindings; selected: string; finding: string | null; onPick: (id: string) => void; onFinding: (key: string | null) => void }) {
  const { lang, t } = useT();
  const family = flow.families.find((f) => `family:${f.id}` === selected) ?? flow.families[0]!;
  const rows = findingsOfFamily(flow, fin, family.id);
  const groups = groupByElement(rows);
  return (
    <section className="story-evidence" data-panel="inventory">
      <div role="group" className="story-chips" aria-label={t('Model families', 'Familias de modelos')}>
        {flow.families.map((f) => (
          <LinkedButton key={f.id} id={`family:${f.id}`} selected={f.id === family.id} onPick={() => onPick(`family:${f.id}`)}>
            <span className="story-item-name">{f.short[lang]}</span>
            <span className="story-item-n">{int(f.total, lang)}</span>
          </LinkedButton>
        ))}
      </div>
      <h2>{family.label[lang]}</h2>
      <p>
        <strong>{int(family.entries.length, lang)}</strong> {family.entries.length === 1 ? t('inventory entry', 'entrada del inventario') : t('inventory entries', 'entradas del inventario')} · <strong>{int(family.total, lang)}</strong> {family.total === 1 ? t('finding', 'hallazgo') : t('findings', 'hallazgos')}
        {' · '}
        {SEVERITIES.map((s) => `${s} ${int(family.sev[s], lang)}`).join(' · ')}
      </p>
      <ul className="story-entries">
        {family.entries.slice(0, 6).map((k) => (
          <li key={k}>{entryText(k)[lang]}</li>
        ))}
        {family.entries.length > 6 && <li>{t(`and ${int(family.entries.length - 6, lang)} more`, `y ${int(family.entries.length - 6, lang)} más`)}</li>}
      </ul>
      {ELEMENTS.map((el) => (
        <div key={el.id} className="story-element" data-element={el.id}>
          <h3>
            {el.label[lang]} <span className="story-item-n">{int(groups[el.id].length, lang)}</span>
          </h3>
          <ul>
            {groups[el.id].slice(0, 3).map((r) => (
              <li key={r.key}>
                <button type="button" className="story-finding" aria-pressed={finding === r.key} onClick={() => onFinding(finding === r.key ? null : r.key)}>
                  <span className="story-sev" data-severity={r.severity}>
                    {severityText(r.severity, ECB_F_OF[r.severity], lang)}
                  </span>
                  <span>{r.title[lang]}</span>
                </button>
                <small>{r.evidence.slice(0, 2).map((e) => evidenceText(e, { caseId: r.case_id }, lang)).join(' · ')}</small>
              </li>
            ))}
            {groups[el.id].length > 3 && <li className="story-more">{t(`and ${int(groups[el.id].length - 3, lang)} more`, `y ${int(groups[el.id].length - 3, lang)} más`)}</li>}
          </ul>
        </div>
      ))}
      <Source>
        {t('Source: the model inventory and the register of findings. The flow and the elements are a stated convention of Contraste; the severity is shown beside its ECB F equivalent.', 'Fuente: el inventario de modelos y el registro de hallazgos. El flujo y los elementos son una convención declarada de Contraste; la severidad se muestra junto a su equivalente en la escala F del BCE.')}{' '}
        {SEVERITIES.map((s) => `${s} ${SEVERITY_NAME[s][lang]}`).join(', ')}.
      </Source>
    </section>
  );
}

// --- steps 2 to 5 -------------------------------------------------------------------------------------------------------------

export function LightPanel({ w, m, cursor, selected, onPick }: { w: WindowModel; m: ModelPath; cursor: number; selected: string; onPick: (id: string) => void }) {
  const { lang, t } = useT();
  const here = m.trailing[cursor] ?? 0;
  const zone = zoneOf(here, w.cuts);
  return (
    <section className="story-evidence" data-panel="light">
      <h2>{m.label[lang]}</h2>
      <p aria-live="polite" data-light-readout="">
        {t('On', 'El')} <strong>{dayLabel(w.dates[cursor], lang)}</strong>: <strong>{int(here, lang)}</strong> {t('exceptions in the trailing 250 days,', 'excepciones en los 250 días previos,')} <strong>{t(`${zoneAdjective(zone, lang)} zone`, `zona ${zoneAdjective(zone, lang)}`)}</strong>.
      </p>
      {m.light ? (
        <p>
          {t('Over the complete windows the model peaks at', 'En las ventanas completas el modelo llega a un máximo de')} <strong>{int(m.light.max, lang)}</strong> {t('and ends at', 'y termina en')} <strong>{int(m.light.final, lang)}</strong> ({t(`${zoneAdjective(m.light.zone, lang)} zone`, `zona ${zoneAdjective(m.light.zone, lang)}`)}): {int(m.light.green, lang)} {t('days green', 'días verde')}, {int(m.light.amber, lang)} {t('amber', 'ámbar')}, {int(m.light.red, lang)} {t('red', 'rojo')}.
        </p>
      ) : (
        <p data-state="unavailable">{reasonText(w.notEvaluatedReason ?? 'not evaluated', lang)}</p>
      )}
      <ModelList w={w} selected={selected} onPick={onPick} />
      <Source>
        {t('Zones of the Basel table:', 'Zonas de la tabla de Basilea:')} {zoneBi('green')[lang].toLowerCase()} {zoneRange('green', w.cuts, lang)}, {zoneBi('amber')[lang].toLowerCase()} ({t('the Basel yellow', 'el amarillo de Basilea')}) {zoneRange('amber', w.cuts, lang)}, {zoneBi('red')[lang].toLowerCase()} {zoneRange('red', w.cuts, lang)}. {t('Source: BCBS (1996),', 'Fuente: BCBS (1996),')}{' '}
        <a href={BASEL_URL} target="_blank" rel="noreferrer">
          {t('Supervisory framework for the use of backtesting', 'Supervisory framework for the use of backtesting')}
        </a>
        ; <a href={MAR_URL} target="_blank" rel="noreferrer">MAR32.9</a>. {t('Exceptions are the days the document lists.', 'Las excepciones son los días que lista el documento.')}
      </Source>
    </section>
  );
}

export function CrisisPanel({ w, m, cursor, selected, onPick }: { w: WindowModel; m: ModelPath; cursor: number; selected: string; onPick: (id: string) => void }) {
  const { lang, t } = useT();
  const r = crisisReadout(w, m.id, cursor);
  return (
    <section className="story-evidence" data-panel="crisis">
      <h2>{m.label[lang]}</h2>
      <p>
        <strong>{int(m.exceedances.length, lang)}</strong> {t('breaches of the 1% VaR in', 'excedencias del VaR de 1 % en')} <strong>{int(m.n, lang)}</strong> {t('days; the VaR expects', 'días; el VaR espera')} <strong>{formatNumber(m.expected, lang, { decimals: 2 })}</strong>.
      </p>
      <p aria-live="polite" data-crisis-readout="">
        <strong>{dayLabel(r.date, lang)}</strong> · VaR <strong>{pct(r.var, lang)}</strong> · ES <strong>{r.es == null ? formatNumber(null, lang) : pct(r.es, lang)}</strong>
        {r.loss != null && (
          <>
            {' '}· {t('loss', 'pérdida')} <strong>{pct(r.loss, lang)}</strong>
          </>
        )}{' '}
        · {r.exceeded ? t('VaR exceeded that day', 'el VaR se excedió ese día') : t('VaR held', 'el VaR se sostuvo')} · {int(r.trailing, lang)} {t('exceptions in 250 days', 'excepciones en 250 días')} ({t(`${zoneAdjective(r.zone, lang)} zone`, `zona ${zoneAdjective(r.zone, lang)}`)}).
      </p>
      {w.loss === null && w.lossReason && <p className="story-note" data-state="unavailable">{reasonText(w.lossReason, lang)}</p>}
      <ModelList w={w} selected={selected} onPick={onPick} />
      <Source>{t('Source: the window document of the market case. The band is the lowest and the highest VaR of the ladder each day; every VaR and ES is a positive loss, a decimal of the portfolio value.', 'Fuente: el documento de ventana del caso de mercado. La banda es el VaR más bajo y el más alto de la escalera cada día; todo VaR y toda ES es una pérdida positiva, un decimal del valor de la cartera.')}</Source>
    </section>
  );
}

export function RecalibrationPanel({ w, raw, rec, wrapped, selected, onPick, verdict, usingFallback }: { w: WindowModel; raw: ModelPath; rec: Recalibrated; wrapped: readonly string[]; selected: string; onPick: (id: string) => void; verdict: string | null; usingFallback: boolean }) {
  const { lang, t } = useT();
  const kupiec = (p: number | null) => (p == null ? formatNumber(null, lang) : formatNumber(p, lang, { decimals: 3 }));
  return (
    <section className="story-evidence" data-panel="recalibration">
      <h2>{rec.label[lang]}</h2>
      {usingFallback && <p className="story-note">{t('The recalibration is defined for three models; the selected model is not one of them, so the first of the three is shown.', 'La recalibración está definida para tres modelos; el modelo seleccionado no es uno de ellos, así que se muestra el primero de los tres.')}</p>}
      <table className="story-table" data-recalibration-table="">
        <thead>
          <tr>
            <th />
            <th>{t('Without', 'Sin')}</th>
            <th>{t('With', 'Con')}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>{t('Breaches', 'Excedencias')}</th>
            <td>{int(rec.rawExceptions, lang)}</td>
            <td>{int(rec.wrappedExceptions, lang)}</td>
          </tr>
          <tr>
            <th>{t('Expected', 'Esperadas')}</th>
            <td colSpan={2}>{formatNumber(rec.expected, lang, { decimals: 2 })}</td>
          </tr>
          <tr>
            <th>{t('Kupiec p-value', 'Valor p de Kupiec')}</th>
            <td>{kupiec(rec.rawKupiec)}</td>
            <td data-upper-bound="">{kupiec(rec.wrappedKupiec)} <small>({UPPER_BOUND[lang]})</small></td>
          </tr>
          <tr>
            <th>{t('Final zone', 'Zona final')}</th>
            <td>{raw.light ? zoneBi(raw.light.zone)[lang] : formatNumber(null, lang)}</td>
            <td data-upper-bound="">{rec.tally ? zoneBi(zoneOf(rec.tally.final, w.cuts))[lang] : formatNumber(null, lang)} <small>({UPPER_BOUND[lang]})</small></td>
          </tr>
        </tbody>
      </table>
      <p className="story-note" data-recalibration-caveat="">{TESTS_TOO_EASY[lang]}</p>
      <ModelList w={w} selected={selected} onPick={onPick} only={wrapped} />
      {verdict && (
        <p data-hypothesis="">
          {VERDICT_LABEL[lang]} {verdict}
        </p>
      )}
      <p className="story-note">
        <a href={MANUSCRIPT_URL} target="_blank" rel="noreferrer">
          {MANUSCRIPT_LINK[lang]}
        </a>
      </p>
      <Source>
        {t(`Source: the conformal block of the window document. The working tail level moves by ${formatNumber(rec.gamma, lang, { decimals: 3 })} times the target minus the hit after each day; the model is asked for its VaR at that level.`, `Fuente: el bloque conforme del documento de ventana. El nivel de cola de trabajo se mueve en ${formatNumber(rec.gamma, lang, { decimals: 3 })} veces el objetivo menos la excedencia después de cada día; al modelo se le pide su VaR en ese nivel.`)}
      </Source>
    </section>
  );
}

export function DecisionPanel({ w, d, selected, onPick, reason }: { w: WindowModel; d: Decision; selected: string; onPick: (id: string) => void; reason: string | null }) {
  const { lang, t } = useT();
  const row = d.rows.find((q) => q.id === selected) ?? d.rows[0]!;
  const m = w.models.find((q) => q.id === row.id)!;
  const champ = d.rows.find((q) => q.id === d.champion);
  return (
    <section className="story-evidence" data-panel="decision">
      <h2>{row.label[lang]}</h2>
      <p>
        <strong>{int(row.exceptions, lang)}</strong> {t('exceptions in', 'excepciones en')} {int(row.n, lang)} {t('days', 'días')}: {t('rate', 'tasa')} <strong>{pct(row.rate, lang)}</strong> ({pct(row.lo, lang)} {t('to', 'a')} {pct(row.hi, lang)}).{' '}
        {row.esP == null ? t('No expected-shortfall back-test.', 'Sin prueba retrospectiva de la pérdida esperada.') : <>{t('Expected-shortfall back-test p-value', 'Valor p de la prueba retrospectiva de la pérdida esperada')} <strong>{formatNumber(row.esP, lang, { decimals: 3 })}</strong>.</>}
      </p>
      <p data-gates="">
        {row.eligible ? t('Passes every gate.', 'Pasa todas las compuertas.') : <>{t('Fails', 'Falla')} {m.failedGates.map((g) => testName(g)[lang]).join(', ')}.</>}{' '}
        {row.setState == null
          ? ''
          : row.setState === 'in'
            ? t('Kept by the model confidence set.', 'Retenido por el conjunto de confianza de modelos.')
            : row.setState === 'out'
              ? t('Left out by the model confidence set.', 'Excluido por el conjunto de confianza de modelos.')
              : t('Not ranked by the model confidence set: the model forecasts no expected shortfall, so the comparison never included it.', 'Sin ranking en el conjunto de confianza de modelos: el modelo no pronostica pérdida esperada, así que la comparación nunca lo incluyó.')}
      </p>
      <p data-champion="">
        {champ ? <>{t('Champion', 'Campeón')}: <strong>{champ.label[lang]}</strong>.</> : <>{t('No champion', 'Sin campeón')}: {reasonText(reason ?? '', lang)}</>}
      </p>
      <ModelList w={w} selected={selected} onPick={onPick} />
      <Source>
        {t('Source: eligibility gates, model confidence set and expected-shortfall back-test of the window document; the interval is the Wilson score interval of the exception count.', 'Fuente: compuertas de elegibilidad, conjunto de confianza de modelos y prueba retrospectiva de la pérdida esperada del documento de ventana; el intervalo es el de puntaje de Wilson del conteo de excepciones.')}{' '}
        {d.confidence != null && t(`Confidence ${pct(d.confidence, lang, 0)}.`, `Confianza ${pct(d.confidence, lang, 0)}.`)}
      </Source>
    </section>
  );
}

/** The state of a step whose artifact does not load: the product's unavailable state, with the reason. */
export function Unavailable({ title, reason, retry }: { title: string; reason: string; retry?: ReactNode }) {
  return (
    <section className="story-state" data-state="unavailable">
      <h2>{title}</h2>
      <p>{reason}</p>
      {retry}
    </section>
  );
}
