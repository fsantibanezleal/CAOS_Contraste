// The C10 instrument (U7-W): portfolio credit capital on the Federal Reserve charge-off rates by loan type and on a
// simulator with a known correlation. A loan-type variant has four rail sections (Rung, Level, Estimator, Group), each
// with its control and a live read-out, and the groups are the validator's questions: the Fit (how wrong is the
// single-factor capital, how sure is the correlation, did the crisis years fall where the fit said), the Capital (the
// loss distribution by rung, the Euler contributions and the granularity), the Model and the Findings. A correlation-grid
// variant has two sections (Known correlation, Estimator) and the Simulator group. The workbench calls this hook on every
// case and uses it when the case is C10.
import { ChipGroup, SubTabs, formatNumber, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { RailSelect } from '../c06/RailSelect';
import { C10ContextView, C10FindingsView, C10VariantsView, CellReadout, EstimatorReadout, GridEstimatorReadout, GroupReadout, LevelReadout, RungReadout } from './C10Common';
import { ContributionsView, GranularityView, LossView, RungsView } from './CapitalViews';
import { BacktestView, CorrelationView, FittedView, IrbView } from './FitViews';
import { EstimatorsView, LadderView, PortfolioView } from './ModelViews';
import { EstimatesView, SizePowerView } from './SimulatorViews';
import { ESTIMATOR_HINT, ESTIMATOR_SHORT, LEVELS, cellKey, defaultSel, gridOf, groupLabel, levelBi, outputsOf, text, type C10Sel, type Level } from './selection';

export interface C10Instrument {
  sel: C10Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

const LEVEL_HINT: Record<number, BiText> = {
  0.99: { en: 'The 99% quantile of the loss: one year in a hundred is worse.', es: 'El cuantil del 99 % de la pérdida: uno de cada cien años es peor.' },
  0.999: { en: 'The 99.9% quantile, the level of the Basel IRB capital: one year in a thousand is worse.', es: 'El cuantil del 99,9 %, el nivel del capital IRB de Basilea: uno de cada mil años es peor.' },
};

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C10Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [rung, setRung] = useState<string | null>(null);
  const [level, setLevel] = useState<Level | null>(null);
  const [estimator, setEstimator] = useState<string | null>(null);
  const [group, setGroup] = useState<string | null>(null);
  const [cell, setCell] = useState<string | null>(null);
  const variantId = data?.variant.variant_id;
  // a new variant starts every control on its own defaults
  useEffect(() => {
    setRung(null);
    setLevel(null);
    setEstimator(null);
    setGroup(null);
    setCell(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const g = base ? gridOf(base) : null;
  const sel: C10Sel | null = useMemo(() => {
    if (!base) return null;
    return {
      ...base,
      rung: rung !== null && o?.rungs.some((r) => r.id === rung) ? rung : base.rung,
      level: level !== null && LEVELS.includes(level) ? level : base.level,
      estimator: estimator === 'moments' || estimator === 'maximum-likelihood' ? estimator : base.estimator,
      group: group !== null && o?.portfolio.groups.some((x) => x.id === group) ? group : base.group,
      cell: cell !== null && g?.cells.some((c) => cellKey(c) === cell) ? cell : base.cell,
    };
  }, [base, o, g, rung, level, estimator, group, cell]);
  if (!sel || !data || (!o && !g)) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);

  const estimatorChips = (
    <ChipGroup
      id="c10-estimator"
      label={{ en: 'Correlation estimator', es: 'Estimador de la correlación' }}
      options={(['maximum-likelihood', 'moments'] as const).map((e) => ({ id: e, label: text(ESTIMATOR_SHORT, e), hint: text(ESTIMATOR_HINT, e) }))}
      value={sel.estimator}
      onChange={setEstimator}
    />
  );
  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const model = tabs(
    [
      { id: 'ladder', label: { en: 'Ladder', es: 'Escalera' }, content: <LadderView sel={sel} /> },
      { id: 'portfolio', label: { en: 'Portfolio', es: 'Cartera' }, content: <PortfolioView sel={sel} /> },
    ],
    { en: 'Views of the model', es: 'Vistas del modelo' },
    'c10-model',
  );
  const modelGroup = { id: 'model', label: { en: 'Model', es: 'Modelo' }, lane: 'replay' as const, provenance: prov, content: model };
  const findings = { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay' as const, provenance: prov, content: <C10FindingsView sel={sel} /> };
  const compare = { label: { en: 'Variants', es: 'Variantes' } as BiText, lane: 'replay' as const, provenance: prov, content: <C10VariantsView sel={sel} onPick={onPick} /> };
  const context = { content: (<C10ContextView sel={sel}><EstimatorsView sel={sel} /></C10ContextView>) };
  const controls = { rung: sel.rung, level: sel.level, estimator: sel.estimator, group: sel.group, cell: sel.cell };

  if (g && !o) {
    const cellSection: RailSection = {
      id: 'cell',
      label: { en: 'Known correlation', es: 'Correlación conocida' },
      content: (
        <>
          <RailSelect
            id="c10-cell"
            label={{ en: 'Known correlation', es: 'Correlación conocida' }}
            options={g.cells.map((c) => ({ id: cellKey(c), label: { en: formatNumber(c.known_rho, 'en', { percent: true, decimals: 1 }), es: formatNumber(c.known_rho, 'es', { percent: true, decimals: 1 }) } }))}
            value={sel.cell}
            onChange={setCell}
          />
          <CellReadout sel={sel} />
        </>
      ),
    };
    const estimatorSection: RailSection = {
      id: 'estimator',
      label: { en: 'Estimator', es: 'Estimador' },
      content: (
        <>
          {estimatorChips}
          <GridEstimatorReadout sel={sel} />
        </>
      ),
    };
    return {
      sel,
      rail: [cellSection, estimatorSection],
      groups: [
        {
          id: 'simulator',
          label: { en: 'Size and power', es: 'Tamaño y potencia' },
          lane: 'replay',
          provenance: prov,
          content: tabs(
            [
              { id: 'size-power', label: { en: 'Size and power', es: 'Tamaño y potencia' }, content: <SizePowerView sel={sel} /> },
              { id: 'estimates', label: { en: 'Estimates', es: 'Estimaciones' }, content: <EstimatesView sel={sel} /> },
            ],
            { en: 'Views of the simulator', es: 'Vistas del simulador' },
            'c10-simulator',
          ),
        },
        modelGroup,
        findings,
      ],
      compare,
      context,
      controls,
    };
  }

  const rungSection: RailSection = {
    id: 'rung',
    label: { en: 'Rung', es: 'Escalón' },
    content: (
      <>
        <RailSelect id="c10-rung" label={{ en: 'Rung of the ladder', es: 'Escalón de la escalera' }} options={(o?.rungs ?? []).map((r) => ({ id: r.id, label: { en: r.label.en, es: r.label.es } }))} value={sel.rung} onChange={setRung} />
        <RungReadout sel={sel} />
      </>
    ),
  };
  const levelSection: RailSection = {
    id: 'level',
    label: { en: 'Level', es: 'Nivel' },
    content: (
      <>
        <ChipGroup
          id="c10-level"
          label={{ en: 'Confidence level', es: 'Nivel de confianza' }}
          options={LEVELS.map((l) => ({ id: String(l), label: levelBi(l), hint: LEVEL_HINT[l] }))}
          value={String(sel.level)}
          onChange={(v) => setLevel(Number(v) as Level)}
        />
        <LevelReadout sel={sel} />
      </>
    ),
  };
  const estimatorSection: RailSection = {
    id: 'estimator',
    label: { en: 'Estimator', es: 'Estimador' },
    content: (
      <>
        {estimatorChips}
        <EstimatorReadout sel={sel} />
      </>
    ),
  };
  const groupSection: RailSection = {
    id: 'group',
    label: { en: 'Group', es: 'Grupo' },
    content: (
      <>
        <RailSelect id="c10-group" label={{ en: 'Group of the portfolio', es: 'Grupo de la cartera' }} options={(o?.portfolio.groups ?? []).map((x) => ({ id: x.id, label: groupLabel(o?.portfolio.groups ?? [], x.id) }))} value={sel.group} onChange={setGroup} />
        <GroupReadout sel={sel} />
      </>
    ),
  };
  const fit = tabs(
    [
      { id: 'fitted', label: { en: 'Fitted distribution', es: 'Distribución ajustada' }, content: <FittedView sel={sel} /> },
      { id: 'correlation', label: { en: 'Correlation', es: 'Correlación' }, content: <CorrelationView sel={sel} /> },
      { id: 'backtest', label: { en: 'Back-test', es: 'Backtest' }, content: <BacktestView sel={sel} /> },
      { id: 'irb', label: { en: 'Against IRB', es: 'Contra IRB' }, content: <IrbView sel={sel} /> },
    ],
    { en: 'Views of the fit', es: 'Vistas del ajuste' },
    'c10-fit',
  );
  const capital = tabs(
    [
      { id: 'loss', label: { en: 'Loss distribution', es: 'Distribución de pérdidas' }, content: <LossView sel={sel} /> },
      { id: 'rungs', label: { en: 'Rungs', es: 'Escalones' }, content: <RungsView sel={sel} /> },
      { id: 'contributions', label: { en: 'Contributions', es: 'Contribuciones' }, content: <ContributionsView sel={sel} /> },
      { id: 'granularity', label: { en: 'Granularity', es: 'Granularidad' }, content: <GranularityView sel={sel} /> },
    ],
    { en: 'Views of the capital', es: 'Vistas del capital' },
    'c10-capital',
  );
  return {
    sel,
    rail: [rungSection, levelSection, estimatorSection, groupSection],
    groups: [
      { id: 'fit', label: { en: 'Fit', es: 'Ajuste' }, lane: 'replay', provenance: prov, content: fit },
      { id: 'capital', label: { en: 'Capital', es: 'Capital' }, lane: 'replay', provenance: prov, content: capital },
      modelGroup,
      findings,
    ],
    compare,
    context,
    controls,
  };
}
