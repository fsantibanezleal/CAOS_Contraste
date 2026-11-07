// The guided story (ADR-0082 rule 3, SHOW-1): five steps over the same artifacts as the App, /story/<step>, each a finding with
// its number read from the documents. 1 Inventory (the flow of the bank, with the findings of each model family and the
// family opened by SR 11-7), 2 Back-test (the Basel traffic light), 3 Crisis (the losses and the VaR through the window), 4
// Recalibrate (the conformal recalibration against the raw VaR, coupled to the light), 5 Decide (the ladder on one axis). One stage
// and one docked panel per step on the shell's StoryFrame, three anchored callouts per stage, the scene and the panel one linked
// selection, one day cursor shared by the light, the crisis and the recalibration. The exit lands on the App (`from`).
import { SceneCallouts, StoryFrame, useLinkedView, useShellLang, useStageSize, type SceneCalloutDef, type StoryStep } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useGovernanceDocs, useWindowDocs } from '../story/data';
import { CrisisView, crisisGeometry } from '../story/CrisisView';
import { DecisionView, decisionGeometry } from '../story/DecisionView';
import { FlowView, flowGeometry, type MarketInfo } from '../story/FlowView';
import { CrisisPanel, DecisionPanel, InventoryPanel, LightPanel, RecalibrationPanel, Unavailable, WINDOW_IDS, WindowPicker } from '../story/Panels';
import { RecalibrationView, recalibrationGeometry } from '../story/RecalibrationView';
import { TrafficLightView, lightGeometry } from '../story/TrafficLightView';
import { int, pct, type Size } from '../story/chart';
import {
  CASE_FLOW, DEFAULT_MODEL, DEFAULT_WINDOW, clampCursor, decision, defaultCursor, recalibration, windowModel, wrappedModels, zoneOf, type Decision, type Flow, type ModelPath, type Zone,
} from '../story/model';
import {
  STEP_IDS, VERBS, headName, headlineBacktest, headlineCrisis, headlineDecision, headlineInventory, headlineRecalibration, missingNumber, sublineTally, zoneBi, type Lang, type StepId,
} from '../story/text';
import { WINDOW_TEXT, outputsOf } from '../workbench/c11/selection';
import './story.css';

type Bi = { en: string; es: string };
const bi = (en: string, es: string): Bi => ({ en, es });
/** The ids of the windows a document sentence names, in the window's own name. */
const windowWords = (sentence: string, lang: Lang): string => sentence.replace(/(equity-2007-09|equity-2020|rates-2022|fx-2008|mixed-2023|calm-2004-06)/g, (id) => WINDOW_TEXT[id]?.[lang] ?? id);
const BAND = (width: number) => (width < 760 ? 130 : 86);
const clamp01 = (v: number, lo = 0.04, hi = 0.96) => Math.max(lo, Math.min(hi, v));
const stateOfZone = (z: Zone): SceneCalloutDef['state'] => (z === 'red' ? 'alarm' : z === 'amber' ? 'warning' : 'normal');

/** One stage: it measures its box, hands the drawing the part below the callout band and the callouts their anchors in the box. */
function StageBox({ build }: { build: (draw: Size, at: (px: number, py: number) => { x: number; y: number }) => { callouts: SceneCalloutDef[]; drawing: ReactNode } }) {
  const [ref, size] = useStageSize();
  const band = BAND(size.width || 1000);
  const draw: Size = { width: size.width, height: Math.max(0, size.height - band) };
  const ready = draw.width > 120 && draw.height > 160;
  const box = ready ? draw : { width: 900, height: 480 };
  const total = ready ? size.height : box.height + band;
  const at = (px: number, py: number) => ({ x: clamp01(px / box.width), y: clamp01((band + py) / total, Math.min(0.9, (band + 18) / total), 0.97) });
  const built = build(box, at);
  return (
    <div ref={ref} className="story-stage-box" style={{ ['--story-band' as string]: `${band}px` }}>
      <SceneCallouts items={built.callouts} placement="header" className="story-callouts" />
      <div className="story-drawing">{ready ? built.drawing : null}</div>
    </div>
  );
}

const callout = (id: string, eyebrow: Bi, value: string, unit: Bi, state: SceneCalloutDef['state'], anchor: { x: number; y: number }, source: Bi, trend?: SceneCalloutDef['trend']): SceneCalloutDef => ({ id, eyebrow, value, unit, state, anchor, source, ...(trend ? { trend } : {}) });

export function Story() {
  const lang = useShellLang() as Lang;
  const { step = 'inventory' } = useParams();
  const [query] = useSearchParams();
  const navigate = useNavigate();
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const cursorStore = useLinkedView((s) => s.cursor);
  const scrub = useLinkedView((s) => s.scrub);
  const select = useLinkedView((s) => s.select);
  const findingKey = useLinkedView((s) => s.seriesId);
  const showSeries = useLinkedView((s) => s.showSeries);

  const windowId = WINDOW_IDS.includes(query.get('window') ?? '') ? query.get('window')! : DEFAULT_WINDOW;
  const [modelId, setModelId] = useState(query.get('model') ?? DEFAULT_MODEL);
  const [familyId, setFamilyId] = useState('family:market');
  const gov = useGovernanceDocs();
  const win = useWindowDocs(windowId);
  const w = useMemo(() => (win.state === 'ready' ? windowModel(win.data) : null), [win]);
  const o = win.state === 'ready' ? outputsOf({ data: win.data }) : null;
  const chosen: ModelPath | undefined = w ? (w.models.find((m) => m.id === modelId) ?? w.models.find((m) => m.id === DEFAULT_MODEL) ?? w.models[0]) : undefined;
  const cursor = w ? clampCursor(cursorStore, w.n, defaultCursor(chosen, w.n)) : 0;
  const dec: Decision | null = useMemo(() => (win.state === 'ready' && w ? decision(win.data, w) : null), [win, w]);
  const wrapped = wrappedModels(o);
  const recId = wrapped.includes(chosen?.id ?? '') ? chosen!.id : (wrapped[0] ?? '');
  const rec = useMemo(() => (win.state === 'ready' && recId ? recalibration(win.data, recId) : null), [win, recId]);
  const rawOfRec = w?.models.find((m) => m.id === recId);

  const from = query.get('from');
  const safeFrom = from && from.startsWith('/app') && !from.startsWith('//') && !from.includes('\\') ? from : null;
  const fallback = '/app?case=C11';
  const params = new URLSearchParams({ window: windowId, model: chosen?.id ?? modelId });
  if (safeFrom) params.set('from', safeFrom);

  // the linked selection of the store follows the subject of the step, so the scene and the panel read one object
  const active = (STEP_IDS as readonly string[]).includes(step) ? (step as StepId) : 'inventory';
  useEffect(() => {
    select(active === 'inventory' ? familyId : `model:${chosen?.id ?? modelId}`, 'external');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);
  const pickModel = (id: string) => setModelId(id);
  const pickFamily = (id: string) => setFamilyId(id);
  const changeWindow = (id: string) => {
    scrub(null);
    const p = new URLSearchParams(params);
    p.set('window', id);
    navigate(`/story/${active}?${p.toString()}`, { replace: true });
  };
  const picker = <WindowPicker value={windowId} onChange={changeWindow} />;
  const panelOf = (body: ReactNode) => (
    <div className="story-panel-body">
      {picker}
      {body}
    </div>
  );
  const govState = (): ReactNode | null =>
    gov.state === 'ready'
      ? null
      : gov.state === 'unavailable'
        ? <Unavailable title={t('The inventory is not available', 'El inventario no está disponible')} reason={gov.reason[lang]} />
        : gov.state === 'error'
          ? <Unavailable title={t('The inventory did not load', 'El inventario no cargó')} reason={gov.error} />
          : <p className="caos-pending" data-state="loading">{t('Loading the inventory and the findings', 'Cargando el inventario y los hallazgos')}</p>;
  const winState = (): ReactNode | null =>
    win.state === 'ready' && w && chosen
      ? null
      : win.state === 'unavailable'
        ? <Unavailable title={t('This market window is not available', 'Esta ventana de mercado no está disponible')} reason={win.reason[lang]} />
        : win.state === 'error'
          ? <Unavailable title={t('This market window did not load', 'Esta ventana de mercado no cargó')} reason={win.error} />
          : <p className="caos-pending" data-state="loading">{t('Loading the market window', 'Cargando la ventana de mercado')}</p>;

  // --- step 1: the flow -----------------------------------------------------------------------------------------------------
  const flow: Flow | null = gov.state === 'ready' ? gov.data.flow : null;
  const fin = gov.state === 'ready' ? gov.data.fin : null;
  const finding = fin?.rows.find((r) => r.key === findingKey) ?? null;
  const market: MarketInfo | null = w && chosen ? { label: chosen.label, zone: w.evaluated ? zoneOf(chosen.trailing[cursor] ?? 0, w.cuts) : null, exceptions: chosen.trailing[cursor] ?? 0, day: cursor } : null;

  const inventoryStage = (() => {
    const bad = govState();
    if (bad || !flow || !fin) return <div className="story-state-box">{bad}</div>;
    return (
      <StageBox
        build={(draw, at) => {
          const { boxes } = flowGeometry(draw, flow);
          const boxOf = (id: string) => boxes.find((b) => b.id === id)!;
          const top = [...flow.families].sort((a, b) => b.total - a.total)[0]!;
          const s1 = [...flow.families].sort((a, b) => b.sev.S1 - a.sev.S1)[0]!;
          const sel = flow.families.find((f) => `family:${f.id}` === familyId) ?? flow.families[0]!;
          const right = (id: string) => { const b = boxOf(id); return at(b.x + b.w, b.y + b.h / 2); };
          const src = bi('Register of findings', 'Registro de hallazgos');
          return {
            callouts: [
              callout('findings', bi('REGISTER', 'REGISTRO'), int(flow.total, lang), bi('findings', 'hallazgos'), 'warning', right(`family:${top.id}`), bi('Register of findings', 'Registro de hallazgos')),
              callout('critical', bi('CRITICAL', 'CRÍTICOS'), int(flow.sev.S1, lang), bi('S1 findings', 'hallazgos S1'), flow.sev.S1 > 0 ? 'alarm' : 'normal', right(`family:${s1.id}`), bi('Register of findings', 'Registro de hallazgos')),
              callout('selected', bi('FAMILY', 'FAMILIA'), int(sel.total, lang), bi(`findings, ${sel.short.en}`, `hallazgos, ${sel.short.es}`), 'selected', right(`family:${sel.id}`), src),
            ],
            drawing: (
              <FlowView
                size={draw}
                flow={flow}
                selected={familyId}
                entryExposure={finding ? `exposure:${CASE_FLOW[finding.case_id]?.exposure ?? 'none'}` : null}
                market={market}
                dates={w?.dates ?? null}
                cursor={cursor}
                onSelect={pickFamily}
              />
            ),
          };
        }}
      />
    );
  })();
  const inventoryPanel = (() => {
    const bad = govState();
    return panelOf(bad ?? (flow && fin ? <InventoryPanel flow={flow} fin={fin} selected={familyId} finding={finding?.key ?? null} onPick={pickFamily} onFinding={(k) => showSeries(k)} /> : null));
  })();

  // --- step 2: the Basel light ----------------------------------------------------------------------------------------------
  const lightStage = (() => {
    const bad = winState();
    if (bad || !w || !chosen) return <div className="story-state-box">{bad}</div>;
    return (
      <StageBox
        build={(draw, at) => {
          const g = lightGeometry(draw, w);
          const src = bi('Window document', 'Documento de ventana');
          const finalCount = chosen.trailing.at(-1) ?? 0;
          const peakDay = defaultCursor(chosen, w.n);
          const peak = chosen.trailing[peakDay] ?? 0;
          const zoneEnd = zoneOf(finalCount, w.cuts);
          const zonePeak = zoneOf(peak, w.cuts);
          const here = chosen.trailing[cursor] ?? 0;
          return {
            callouts: [
              callout('final', bi('FINAL', 'FINAL'), int(finalCount, lang), bi('exceptions', 'excepciones'), w.evaluated ? stateOfZone(zoneEnd) : 'inactive', at(g.x(w.n - 1), g.y(finalCount)), src),
              callout('peak', bi('PEAK', 'MÁXIMO'), int(peak, lang), bi('exceptions', 'excepciones'), w.evaluated ? stateOfZone(zonePeak) : 'inactive', at(g.x(peakDay), g.y(peak)), src, 'up'),
              callout('day', bi('DAY', 'DÍA'), int(here, lang), bi('exceptions', 'excepciones'), 'selected', at(g.x(cursor), g.y(here)), bi('Window document', 'Documento de ventana')),
            ],
            drawing: <TrafficLightView size={draw} w={w} selected={chosen.id} cursor={cursor} onSelect={pickModel} onCursor={() => undefined} />,
          };
        }}
      />
    );
  })();
  const lightPanel = (() => {
    const bad = winState();
    return panelOf(bad ?? (w && chosen ? <LightPanel w={w} m={chosen} cursor={cursor} selected={chosen.id} onPick={pickModel} /> : null));
  })();

  // --- step 3: the crisis ---------------------------------------------------------------------------------------------------
  const crisisStage = (() => {
    const bad = winState();
    if (bad || !w || !chosen) return <div className="story-state-box">{bad}</div>;
    return (
      <StageBox
        build={(draw, at) => {
          const g = crisisGeometry(draw, w, chosen.id);
          const last = chosen.exceedances.at(-1) ?? 0;
          const src = bi('Window document', 'Documento de ventana');
          const ratio = chosen.expected ? chosen.exceedances.length / chosen.expected : 0;
          const hiHere = g.env.hi[cursor] ?? 0;
          const loHere = g.env.lo[cursor] ?? 0;
          return {
            callouts: [
              callout('breaches', bi('BREACHES', 'EXCEDEN.'), int(chosen.exceedances.length, lang), bi(`of ${int(chosen.n, lang)} days`, `de ${int(chosen.n, lang)} días`), ratio > 2 ? 'alarm' : ratio > 1 ? 'warning' : 'normal', at(g.x(last), g.y(chosen.var[last] ?? 0)), src, ratio > 1 ? 'up' : 'flat'),
              callout('var', bi('VAR', 'VAR'), pct(chosen.var[cursor], lang), bi('of value', 'del valor'), 'selected', at(g.x(cursor), g.y(chosen.var[cursor] ?? 0)), bi('Window document', 'Documento de ventana')),
              callout('range', bi('RANGE', 'RANGO'), pct(hiHere - loHere, lang), bi('of value', 'del valor'), 'inactive', at(g.x(cursor), g.y(Math.min(hiHere, g.top))), bi('Window document', 'Documento de ventana')),
            ],
            drawing: <CrisisView size={draw} w={w} modelId={chosen.id} cursor={cursor} onCursor={() => undefined} />,
          };
        }}
      />
    );
  })();
  const crisisPanel = (() => {
    const bad = winState();
    return panelOf(bad ?? (w && chosen ? <CrisisPanel w={w} m={chosen} cursor={cursor} selected={chosen.id} onPick={pickModel} /> : null));
  })();

  // --- step 4: the recalibration --------------------------------------------------------------------------------------------
  const recalibrateStage = (() => {
    const bad = winState();
    if (bad || !w || !chosen) return <div className="story-state-box">{bad}</div>;
    if (!rec || !rawOfRec) {
      return <div className="story-state-box"><Unavailable title={t('No recalibration in this window', 'Sin recalibración en esta ventana')} reason={t('The window document carries no conformal recalibration block for this level.', 'El documento de ventana no trae un bloque de recalibración conforme para este nivel.')} /></div>;
    }
    return (
      <StageBox
        build={(draw, at) => {
          const g = recalibrationGeometry(draw, w, rawOfRec, rec);
          const src = bi('Window document', 'Documento de ventana');
          const lastRaw = rawOfRec.exceedances.at(-1) ?? 0;
          const lastRec = rec.exceedances.at(-1) ?? 0;
          const here = rec.trailing[cursor] ?? 0;
          const zone = zoneOf(here, w.cuts);
          return {
            callouts: [
              callout('without', bi('RAW VAR', 'VAR SIN'), int(rec.rawExceptions, lang), bi('breaches', 'excedencias'), 'warning', at(g.x(lastRaw), g.y1(rawOfRec.var[lastRaw] ?? 0)), src),
              callout('with', bi('RECAL.', 'VAR CON'), int(rec.wrappedExceptions, lang), bi('breaches', 'excedencias'), rec.wrappedExceptions <= rec.rawExceptions ? 'normal' : 'warning', at(g.x(lastRec), g.y1(rec.var[lastRec] ?? 0)), src, rec.wrappedExceptions < rec.rawExceptions ? 'down' : 'flat'),
              callout('zone', bi('DAY', 'DÍA'), int(here, lang), bi(`exceptions, ${zoneBi(zone).en.toLowerCase()}`, `excepciones, ${zoneBi(zone).es.toLowerCase()}`), w.evaluated ? stateOfZone(zone) : 'inactive', at(g.x(cursor), g.y2(here)), bi('Window document', 'Documento de ventana')),
            ],
            drawing: <RecalibrationView size={draw} w={w} raw={rawOfRec} rec={rec} cursor={cursor} onCursor={() => undefined} />,
          };
        }}
      />
    );
  })();
  const recalibratePanel = (() => {
    const bad = winState();
    if (bad) return panelOf(bad);
    if (!w || !rec || !rawOfRec) return panelOf(<Unavailable title={t('No recalibration in this window', 'Sin recalibración en esta ventana')} reason={t('The window document carries no conformal recalibration block for this level.', 'El documento de ventana no trae un bloque de recalibración conforme para este nivel.')} />);
    const h = o?.conformal?.hypothesis;
    const verdict = h ? windowWords(h.verdict[lang], lang) : null;
    return panelOf(<RecalibrationPanel w={w} raw={rawOfRec} rec={rec} wrapped={wrapped} selected={recId} onPick={pickModel} verdict={verdict} usingFallback={recId !== (chosen?.id ?? '')} />);
  })();

  // --- step 5: the decision -------------------------------------------------------------------------------------------------
  const decideStage = (() => {
    const bad = winState();
    if (bad || !w || !chosen || !dec) return <div className="story-state-box">{bad}</div>;
    return (
      <StageBox
        build={(draw, at) => {
          const g = decisionGeometry(draw, dec, 0.01);
          const src = bi('Window document', 'Documento de ventana');
          const champIdx = g.rows.findIndex((q) => q.id === dec.champion);
          const selIdx = Math.max(0, g.rows.findIndex((q) => q.id === chosen.id));
          const rowAt = champIdx >= 0 ? champIdx : selIdx;
          const firstPass = g.rows.findIndex((q) => q.eligible);
          const firstSet = g.rows.findIndex((q) => q.inSet);
          const champ = dec.rows.find((q) => q.id === dec.champion);
          return {
            callouts: [
              callout('champion', bi('CHAMPION', 'CAMPEÓN'), champ ? headName(champ.label)[lang] : '0', bi(champ ? 'chosen' : 'models chosen', champ ? 'elegido' : 'modelos elegidos'), champ ? 'selected' : 'inactive', at(g.l + 8, g.rowY(rowAt)), src),
              callout('gates', bi('GATES', 'PASAN'), int(dec.eligible, lang), bi(`of ${int(dec.total, lang)} models`, `de ${int(dec.total, lang)} modelos`), dec.eligible === 0 ? 'alarm' : 'normal', at(g.r + 30, g.rowY(Math.max(0, firstPass))), src),
              callout('set', bi('IN SET', 'CONJUNTO'), dec.setSize == null ? '0' : int(dec.setSize, lang), bi(dec.setSize == null ? 'no set in this window' : 'models kept', dec.setSize == null ? 'sin conjunto en esta ventana' : 'modelos retenidos'), dec.setSize == null ? 'inactive' : 'normal', at(g.r + 30 + (g.narrow ? 0 : 66), g.rowY(Math.max(0, firstSet))), src),
            ],
            drawing: <DecisionView size={{ width: draw.width, height: draw.height }} d={dec} alpha={0.01} selected={chosen.id} onSelect={pickModel} />,
          };
        }}
      />
    );
  })();
  const decidePanel = (() => {
    const bad = winState();
    return panelOf(bad ?? (w && chosen && dec ? <DecisionPanel w={w} d={dec} selected={chosen.id} onPick={pickModel} reason={dec.championReason} /> : null));
  })();

  // --- the steps ------------------------------------------------------------------------------------------------------------
  const missing = (b: Bi): Bi => bi(`${b.en}: ${missingNumber.en}`, `${b.es}: ${missingNumber.es}`);
  const finalOf = chosen?.light ?? null;
  const heads: Record<StepId, Bi> = {
    inventory: flow ? headlineInventory(flow.entries, flow.sev.S1, flow.sev.S2) : missing(VERBS.inventory),
    backtest: chosen && w ? headlineBacktest(chosen.label, finalOf ? finalOf.final : null, finalOf ? finalOf.zone : null, chosen.exceedances.length, w.n) : missing(VERBS.backtest),
    crisis: chosen ? headlineCrisis(chosen.label, chosen.exceedances.length, chosen.n) : missing(VERBS.crisis),
    recalibrate: rec ? headlineRecalibration(rec.rawExceptions, rec.wrappedExceptions) : missing(VERBS.recalibrate),
    decide: dec ? headlineDecision(dec) : missing(VERBS.decide),
  };
  const lines: Record<StepId, Bi> = {
    inventory: bi('Each model family sits between what it is exposed to and what it sets; the bar under a family is its findings by severity.', 'Cada familia de modelos está entre aquello a lo que se expone y lo que fija; la barra bajo una familia son sus hallazgos por severidad.'),
    backtest: chosen && w ? bi(sublineTally(chosen.computed, w.n, 'en'), sublineTally(chosen.computed, w.n, 'es')) : bi('The exceptions of each model against the three zones of the Basel table.', 'Las excepciones de cada modelo frente a las tres zonas de la tabla de Basilea.'),
    crisis: bi('The VaR and the ES of the selected model through the window, the range the ladder spans, and the days the VaR was exceeded.', 'El VaR y la ES del modelo seleccionado en la ventana, el rango que abarca la escalera y los días en que se excedió el VaR.'),
    recalibrate: bi(`${rec ? rec.label.en : 'The model'} with the adaptive conformal recalibration, against its own raw VaR on the same days.`, `${rec ? rec.label.es : 'El modelo'} con la recalibración conforme adaptativa, frente a su propio VaR sin tratar en los mismos días.`),
    decide: bi('The models on one axis with the interval of their exception rate, the gates they fail and the set the comparison keeps.', 'Los modelos en un eje, con el intervalo de su tasa de excepciones, las compuertas que fallan y el conjunto que retiene la comparación.'),
  };
  const stages: Record<StepId, ReactNode> = { inventory: inventoryStage, backtest: lightStage, crisis: crisisStage, recalibrate: recalibrateStage, decide: decideStage };
  const panels: Record<StepId, ReactNode> = { inventory: inventoryPanel, backtest: lightPanel, crisis: crisisPanel, recalibrate: recalibratePanel, decide: decidePanel };
  const steps: StoryStep[] = STEP_IDS.map((id, i) => ({
    id,
    number: i + 1,
    verb: VERBS[id],
    headline: heads[id],
    summary: lines[id],
    href: `/story/${id}?${params.toString()}`,
    accent: ((i % 5) + 1) as StoryStep['accent'],
    stage: stages[id],
    panel: panels[id],
  }));
  return <StoryFrame className="contraste-story" steps={steps} activeId={active} mobileStageMinHeight={620} autoAdvanceMs={7000} onStepChange={(next) => navigate(`/story/${next}?${params.toString()}`)} onExit={() => navigate(safeFrom ?? fallback)} />;
}

