// The C08 instrument (U6-W): the loss given default of the defaults of one cohort on the SBA charge-off twin. The rail
// is split in four sections (ADR-0071 rule 6: Model, Endpoint, Cohort, Floor), each with its control and a live read-out;
// the groups are the validator's questions: Severity, Models (with the tests), Downturn and floors, and Findings,
// with the Variants and Context views. The workbench calls this hook on every case and uses it when the case is C08.
import { ChipGroup, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { C08ContextView, C08FindingsView, C08VariantsView, CohortReadout, EndpointReadout, FloorReadout, RungReadout } from './C08Common';
import { DownturnView, FloorsView } from './DownturnViews';
import { CalibrationView, EndpointsView, RealisedView, RungsView } from './ModelViews';
import { DistributionView, ProxyView } from './SeverityViews';
import { SEGMENT_SHORT, cohortIds, cohortLabel, defaultSel, fitOf, floorCellLabel, outputsOf, rungLabel, segmentLabel, type C08Sel } from './selection';

export interface C08Instrument {
  sel: C08Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C08Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [rung, setRung] = useState<string | null>(null);
  const [epsilon, setEpsilon] = useState<number | null>(null);
  const [cohort, setCohort] = useState<string | null>(null);
  const [segment, setSegment] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setRung(null);
    setEpsilon(null);
    setCohort(null);
    setSegment(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C08Sel | null = useMemo(() => {
    if (!base || !o) return null;
    return {
      ...base,
      rung: rung !== null && o.rung_comparison.some((r) => r.rung_id === rung) ? rung : base.rung,
      epsilon: epsilon !== null && o.endpoint_sensitivity.some((e) => e.epsilon === epsilon) ? epsilon : base.epsilon,
      cohort: cohort !== null && cohortIds(base).includes(cohort) ? cohort : base.cohort,
      segment: segment !== null && o.floors_bite.rows.some((r) => r.segment_id === segment) ? segment : base.segment,
    };
  }, [base, o, rung, epsilon, cohort, segment]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);
  const cells = fitOf(sel)?.floors.cells ?? [];
  const eps = (e: number) => (lang === 'es' ? String(e).replace('.', ',') : String(e));

  const modelSection: RailSection = {
    id: 'rung',
    label: { en: 'Model', es: 'Modelo' },
    content: (
      <>
        <RailSelect id="c08-rung" label={{ en: 'Model', es: 'Modelo' }} options={o.rung_comparison.map((r) => ({ id: r.rung_id, label: rungLabel(sel, r.rung_id) }))} value={sel.rung} onChange={setRung} />
        <RungReadout sel={sel} />
      </>
    ),
  };
  const endpointSection: RailSection = {
    id: 'endpoint',
    label: { en: 'Endpoint', es: 'Extremos' },
    content: (
      <>
        <ChipGroup
          id="c08-epsilon"
          label={{ en: 'Endpoint shift', es: 'Desplazamiento de extremos' }}
          options={o.endpoint_sensitivity.map((e) => ({
            id: String(e.epsilon),
            label: { en: String(e.epsilon), es: eps(e.epsilon) },
            hint: { en: `The beta regression moves an LGD of exactly 0 or 1 in by ${e.epsilon}.`, es: `La regresión beta mueve una LGD de exactamente 0 o 1 hacia adentro en ${eps(e.epsilon)}.` },
          }))}
          value={String(sel.epsilon)}
          onChange={(id) => setEpsilon(Number(id))}
        />
        <EndpointReadout sel={sel} />
      </>
    ),
  };
  const cohortSection: RailSection = {
    id: 'cohort',
    label: { en: 'Cohort', es: 'Cohorte' },
    content: (
      <>
        <RailSelect id="c08-cohort" label={{ en: 'Default cohort', es: 'Cohorte de incumplimiento' }} options={cohortIds(sel).map((id) => ({ id, label: cohortLabel(sel, id) }))} value={sel.cohort} onChange={setCohort} />
        <CohortReadout sel={sel} />
      </>
    ),
  };
  const floorSection: RailSection = {
    id: 'floor',
    label: { en: 'Floor', es: 'Piso' },
    content: (
      <>
        <RailSelect
          id="c08-segment"
          label={{ en: 'Segment', es: 'Segmento' }}
          options={o.floors_bite.rows.map((r) => {
            const cell = cells.find((c) => c.id === r.floor_id);
            const name = segmentLabel(r.segment_id);
            const floor = cell ? floorCellLabel(cell) : null;
            return {
              id: r.segment_id,
              label: SEGMENT_SHORT[r.segment_id] ?? name,
              hint: floor ? { en: `${name.en}; floor cell ${floor.en}`, es: `${name.es}; celda de piso ${floor.es}` } : name,
            };
          })}
          value={sel.segment}
          onChange={setSegment}
        />
        <FloorReadout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const severity = tabs(
    [
      { id: 'distribution', label: { en: 'Distribution', es: 'Distribución' }, content: <DistributionView sel={sel} /> },
      { id: 'proxy', label: { en: 'The proxy', es: 'La aproximación' }, content: <ProxyView sel={sel} /> },
    ],
    { en: 'Views of the severity', es: 'Vistas de la severidad' },
    'c08-severity',
  );
  const models = tabs(
    [
      { id: 'rungs', label: { en: 'Models and tests', es: 'Modelos y pruebas' }, content: <RungsView sel={sel} /> },
      { id: 'realised', label: { en: 'Realised and predicted', es: 'Realizada y predicha' }, content: <RealisedView sel={sel} /> },
      { id: 'calibration', label: { en: 'Calibration', es: 'Calibración' }, content: <CalibrationView sel={sel} /> },
      { id: 'endpoints', label: { en: 'Endpoints', es: 'Extremos' }, content: <EndpointsView sel={sel} /> },
    ],
    { en: 'Views of the models', es: 'Vistas de los modelos' },
    'c08-models',
  );
  const downturn = tabs(
    [
      { id: 'downturn', label: { en: 'Downturn', es: 'Recesión' }, content: <DownturnView sel={sel} /> },
      { id: 'floors', label: { en: 'Floors', es: 'Pisos' }, content: <FloorsView sel={sel} /> },
    ],
    { en: 'Views of the downturn and the floors', es: 'Vistas de la recesión y los pisos' },
    'c08-downturn',
  );
  return {
    sel,
    rail: [modelSection, endpointSection, cohortSection, floorSection],
    groups: [
      { id: 'severity', label: { en: 'Severity', es: 'Severidad' }, lane: 'replay', provenance: prov, content: severity },
      { id: 'models', label: { en: 'Models', es: 'Modelos' }, lane: 'replay', provenance: prov, content: models },
      { id: 'downturn', label: { en: 'Downturn and floors', es: 'Recesión y pisos' }, lane: 'replay', provenance: prov, content: downturn },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C08FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C08VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C08ContextView sel={sel} /> },
    controls: { model: sel.rung, epsilon: String(sel.epsilon), cohort: sel.cohort, segment: sel.segment },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC08Instrument = useInstrument;
