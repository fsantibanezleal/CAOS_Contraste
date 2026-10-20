// The C12 instrument (U9-W1): the counterparty credit risk of a synthetic USD swap book over the real Treasury curve. Four
// groups answer the validator's questions: how large is the exposure and its PFE over the life of the book, and how much
// netting, collateral, the margin period and initial margin remove (Exposure); what CVA it implies and how wrong-way risk
// moves it (CVA and wrong-way risk); how the regulatory measures compare with the modelled ones, with the SA-CCR and the
// BA-CVA live on the netting set (Regulatory capital); and would the simulated exposure distributions have held against
// the curves that were later realised (Back-test and tests). Each rail section has its control and a live read-out
// (ADR-0071 rule 6): a point of the time grid, a back-test horizon, a wrong-way point or a calibration case, the collateral
// held by the live SA-CCR, and the sector and rating class of the live BA-CVA. The workbench calls this hook on every
// case and uses it when the case is C12.
import { ChipGroup, Knob, SubTabs, formatNumber, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import { loadAllVariants, useArtifact, type CaseData } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { SECTORS } from './bacva';
import { C12ContextView, C12FindingsView, C12TestsView, C12VariantsView, CaseReadout, HorizonReadout, LiveCcrReadout, TimeReadout } from './C12Common';
import { CollateralView, NettingView, ProfileView, SensitivityView } from './ExposureViews';
import { CvaView, WwrView } from './CreditViews';
import { BaCvaView, ComparisonView, GirrView, SaCcrView } from './RegulatoryViews';
import { ExceedanceView, PitView } from './BacktestViews';
import {
  CASE_ORDER, CASE_TEXT, HORIZONS, HORIZON_LONG, HORIZON_SHORT, RATING_SHORT, RATING_TEXT, SECTOR_TEXT, SUBJECT_LONG, SUBJECT_TEXT, VARIANT_TEXT,
  collateralRange, committedCollateral, defaultSel, gridOf, isRating, isSector, outputsOf, text,
  type C12Outputs, type C12Sel, type CaseId, type HorizonId, type Peers, type Subject,
} from './selection';

export interface C12Instrument {
  sel: C12Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

/** The documents of every variant of the case, by `outputs.variant`, once the manifest's artifacts are loaded; null before, and for any other case. */
function usePeers(data: CaseData | null): Peers | null {
  const manifest = data && data.manifest.case_id === 'C12' ? data.manifest : null;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  return useMemo(() => {
    if (!manifest || all.state !== 'ready') return null;
    const peers: Peers = {};
    for (const v of all.data) {
      const out = v.outputs as unknown as { kind?: string; variant?: string };
      if (out.kind !== 'swap-exposure' || !out.variant) continue;
      const entry = manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === v.variant_id);
      peers[out.variant] = { variantId: v.variant_id, title: entry?.short_title ?? text(VARIANT_TEXT, out.variant), o: v.outputs as unknown as C12Outputs };
    }
    return peers;
  }, [manifest, all]);
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C12Instrument | null {
  const lang = useShellLang();
  const peers = usePeers(data);
  const base = useMemo(() => defaultSel(data, peers), [data, peers]);
  const [t, setT] = useState<number | null>(null);
  const [horizon, setHorizon] = useState<string | null>(null);
  const [subject, setSubject] = useState<string | null>(null);
  const [b, setB] = useState<string | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [collateral, setCollateral] = useState<number | null>(null);
  const [counterparty, setCounterparty] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setT(null);
    setHorizon(null);
    setSubject(null);
    setB(null);
    setCaseId(null);
    setCollateral(null);
    setCounterparty(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const grid = gridOf(o);
  const sweep = o?.wrong_way_risk?.sweep ?? null;
  const cp = counterparty !== null ? counterparty.split('|') : null;
  const sel: C12Sel | null = useMemo(() => {
    if (!base) return null;
    return {
      ...base,
      t: t !== null && t >= 0 && t < grid.length ? t : base.t,
      horizon: (horizon !== null && (HORIZONS as readonly string[]).includes(horizon) ? horizon : base.horizon) as HorizonId,
      subject: (subject === 'book' || subject === 'risk-factor' ? subject : base.subject) as Subject,
      b: b !== null && sweep && Number(b) >= 0 && Number(b) < sweep.length ? Number(b) : base.b,
      caseId: (caseId !== null && (CASE_ORDER as readonly string[]).includes(caseId) ? caseId : base.caseId) as CaseId,
      collateral,
      sector: cp && isSector(cp[0]) ? cp[0] : base.sector,
      rating: cp && isRating(cp[1]) ? cp[1] : base.rating,
    };
  }, [base, grid.length, sweep, t, horizon, subject, b, caseId, collateral, counterparty]);
  if (!sel || !data || !o) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((x) => ({ ...x, label: pick(x.label, lang) }))} />
  );
  const group = (id: string, label: BiText, content: ReactElement, lane: 'live' | 'replay' = 'replay') => ({ id, label, lane, provenance: prov, content });

  const nGrid = grid.length;
  const timeSection: RailSection = {
    id: 'time',
    label: { en: 'Time', es: 'Tiempo' },
    content: (
      <>
        <Knob
          id="c12-time"
          label={{ en: 'Point of the time grid', es: 'Punto de la grilla de tiempo' }}
          value={sel.t + 1}
          min={1}
          max={Math.max(nGrid, 2)}
          step={1}
          unit={{ en: `of ${nGrid}`, es: `de ${nGrid}` }}
          hint={{ en: 'The point of the time grid, from the first to the last, that the read-out and the marked line show.', es: 'El punto de la grilla de tiempo, del primero al último, que muestran la lectura y la línea marcada.' }}
          format={{ decimals: 0 }}
          disabled={nGrid < 2}
          onChange={(v) => setT(Math.min(nGrid - 1, Math.max(0, Math.round(v) - 1)))}
        />
        <TimeReadout sel={sel} />
      </>
    ),
  };
  const horizonSection: RailSection = {
    id: 'horizon',
    label: { en: 'Test', es: 'Prueba' },
    content: (
      <>
        <ChipGroup
          id="c12-horizon"
          label={{ en: 'Horizon', es: 'Horizonte' }}
          options={HORIZONS.map((h) => ({ id: h, label: text(HORIZON_SHORT, h), hint: text(HORIZON_LONG, h) }))}
          value={sel.horizon}
          onChange={setHorizon}
        />
        <ChipGroup
          id="c12-subject"
          label={{ en: 'Backtested', es: 'Evaluado' }}
          options={(['book', 'risk-factor'] as const).map((s) => ({ id: s, label: text(SUBJECT_TEXT, s), hint: text(SUBJECT_LONG, s) }))}
          value={sel.subject}
          onChange={setSubject}
        />
        <HorizonReadout sel={sel} />
      </>
    ),
  };
  const caseSection: RailSection = sweep
    ? {
        id: 'case',
        label: { en: 'Case', es: 'Caso' },
        content: (
          <>
            <ChipGroup
              id="c12-wwr-b"
              label={{ en: 'Parameter b, per USD million', es: 'Parámetro b, por millón de USD' }}
              options={sweep.map((p, i) => ({ id: String(i), label: { en: formatNumber(p.b, 'en', { digits: 4 }), es: formatNumber(p.b, 'es', { digits: 4 }) } }))}
              value={String(sel.b)}
              onChange={setB}
            />
            <CaseReadout sel={sel} />
          </>
        ),
      }
    : {
        id: 'case',
        label: { en: 'Case', es: 'Caso' },
        content: (
          <>
            <RailSelect
              id="c12-case"
              label={{ en: 'Calibration case', es: 'Caso de calibración' }}
              options={CASE_ORDER.map((id) => ({ id, label: text(CASE_TEXT, id) }))}
              value={sel.caseId}
              onChange={setCaseId}
            />
            <CaseReadout sel={sel} />
          </>
        ),
      };
  const range = collateralRange(o);
  const held = sel.collateral ?? committedCollateral(o);
  const liveSection: RailSection = {
    id: 'live',
    label: { en: 'Live', es: 'Vivo' },
    content: (
      <>
        <Knob
          id="c12-collateral"
          label={{ en: 'Collateral held, C', es: 'Colateral mantenido, C' }}
          value={Math.min(range.max, Math.max(range.min, Math.round(held / 1000)))}
          min={range.min}
          max={range.max}
          step={range.step}
          unit={{ en: 'thousand USD', es: 'miles de USD' }}
          hint={{ en: 'The net independent collateral amount of the live SA-CCR: the replacement cost is the value less this amount, and the multiplier falls as it grows.', es: 'El monto neto de colateral independiente del SA-CCR en vivo: el costo de reemplazo es el valor menos este monto, y el multiplicador baja cuando crece.' }}
          format={{ decimals: 0 }}
          onChange={(v) => setCollateral(v === Math.round(committedCollateral(o) / 1000) ? null : v * 1000)}
        />
        <RailSelect
          id="c12-counterparty"
          label={{ en: 'Counterparty of the BA-CVA', es: 'Contraparte del BA-CVA' }}
          options={SECTORS.flatMap((s) => (['investment-grade', 'high-yield-or-not-rated'] as const).map((r) => ({ id: `${s}|${r}`, label: { en: `${text(SECTOR_TEXT, s).en}, ${text(RATING_SHORT, r).en}`, es: `${text(SECTOR_TEXT, s).es}, ${text(RATING_SHORT, r).es}` }, hint: text(RATING_TEXT, r) })))}
          value={`${sel.sector}|${sel.rating}`}
          onChange={setCounterparty}
        />
        <LiveCcrReadout sel={sel} />
      </>
    ),
  };

  return {
    sel,
    rail: [timeSection, horizonSection, caseSection, liveSection],
    groups: [
      group(
        'exposure',
        { en: 'Exposure', es: 'Exposición' },
        tabs(
          [
            { id: 'profile', label: { en: 'EE, ENE and PFE', es: 'EE, ENE y PFE' }, content: <ProfileView sel={sel} /> },
            { id: 'collateral', label: { en: 'Collateral and margin', es: 'Colateral y margen' }, content: <CollateralView sel={sel} /> },
            { id: 'netting', label: { en: 'Netting benefit', es: 'Beneficio del neteo' }, content: <NettingView sel={sel} /> },
            { id: 'sensitivity', label: { en: 'Calibration', es: 'Calibración' }, content: <SensitivityView sel={sel} /> },
          ],
          { en: 'Views of the exposure', es: 'Vistas de la exposición' },
          'c12-exposure',
        ),
      ),
      group(
        'credit',
        { en: 'CVA and wrong-way risk', es: 'CVA y correlación adversa' },
        tabs(
          [
            { id: 'cva', label: { en: 'CVA build-up', es: 'Acumulación del CVA' }, content: <CvaView sel={sel} /> },
            { id: 'wwr', label: { en: 'Wrong-way risk', es: 'Correlación adversa' }, content: <WwrView sel={sel} /> },
          ],
          { en: 'Views of the CVA', es: 'Vistas del CVA' },
          'c12-credit',
        ),
      ),
      group(
        'regulatory',
        { en: 'Regulatory capital', es: 'Capital regulatorio' },
        tabs(
          [
            { id: 'comparison', label: { en: 'Against modelled', es: 'Contra modelado' }, content: <ComparisonView sel={sel} /> },
            { id: 'saccr', label: { en: 'SA-CCR, live', es: 'SA-CCR en vivo' }, content: <SaCcrView sel={sel} /> },
            { id: 'bacva', label: { en: 'BA-CVA, live', es: 'BA-CVA en vivo' }, content: <BaCvaView sel={sel} /> },
            { id: 'girr', label: { en: 'GIRR delta', es: 'GIRR delta' }, content: <GirrView sel={sel} /> },
          ],
          { en: 'Views of the regulatory capital', es: 'Vistas del capital regulatorio' },
          'c12-regulatory',
        ),
        'live',
      ),
      group(
        'backtest',
        { en: 'Back-test and tests', es: 'Backtest y pruebas' },
        tabs(
          [
            { id: 'pit', label: { en: 'PIT histogram', es: 'Histograma PIT' }, content: <PitView sel={sel} /> },
            { id: 'exceedances', label: { en: 'Exceedances', es: 'Excedencias' }, content: <ExceedanceView sel={sel} /> },
            { id: 'tests', label: { en: 'Tests', es: 'Pruebas' }, content: <C12TestsView sel={sel} /> },
            { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, content: <C12FindingsView sel={sel} /> },
          ],
          { en: 'Views of the back-test and the tests', es: 'Vistas del backtest y las pruebas' },
          'c12-backtest',
        ),
      ),
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C12VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C12ContextView sel={sel} /> },
    controls: { t: sel.t, horizon: sel.horizon, subject: sel.subject, [sweep ? 'b' : 'case']: sweep ? sel.b : sel.caseId, collateral: held, counterparty: `${sel.sector}|${sel.rating}` },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC12Instrument = useInstrument;
