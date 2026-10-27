// The C13 instrument (U8-W): FRTB desk eligibility on a generator of desk P&L with a planted model deficiency, one
// deficiency per variant (the truth is known). The rail is split in two sections (ADR-0071 rule 6: Level, Statistic),
// each with its control and a live read-out; the groups are the validator's questions: does the P&L attribution test catch
// the deficiency (PLA), does the desk back-test (Desk back-test), with the Findings, the Variants (the deficiencies) and
// Context views. The workbench calls this hook on every case and uses it when the case is C13.
import { ChipGroup, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import { provenanceOf } from '../model';
import { C13ContextView, C13FindingsView, C13VariantsView, LevelReadout, StatisticReadout } from './C13Common';
import { DeskView } from './DeskViews';
import { DetectionView, EcdfView, RanksView, ZonesView } from './PlaViews';
import { STATISTIC_TEXT, defaultSel, levelLabel, levelShort, outputsOf, type C13Alpha, type C13Sel, type C13Statistic } from './selection';

export interface C13Instrument {
  sel: C13Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

export function useInstrument(data: CaseData | null, onPick: (id: string) => void): C13Instrument | null {
  const lang = useShellLang();
  const base = useMemo(() => defaultSel(data), [data]);
  const [alpha, setAlpha] = useState<C13Alpha | null>(null);
  const [statistic, setStatistic] = useState<C13Statistic | null>(null);
  const variantId = data?.variant.variant_id;
  // a new deficiency starts every control on its own defaults
  useEffect(() => {
    setAlpha(null);
    setStatistic(null);
  }, [variantId]);

  const o = base ? outputsOf(base) : null;
  const sel: C13Sel | null = useMemo(() => {
    if (!base || !o) return null;
    return {
      ...base,
      alpha: alpha !== null && o.desk_backtest.some((l) => l.alpha === alpha) ? alpha : base.alpha,
      statistic: statistic ?? base.statistic,
    };
  }, [base, o, alpha, statistic]);
  if (!sel || !o || !data) return null;
  const prov = provenanceOf(data.variant.provenance.truth_status);

  const levelSection: RailSection = {
    id: 'level',
    label: { en: 'Level', es: 'Nivel' },
    content: (
      <>
        <ChipGroup
          id="c13-level"
          label={{ en: 'Desk back-test level', es: 'Nivel de la prueba de la mesa' }}
          options={o.desk_backtest.map((l) => ({ id: String(l.alpha), label: { en: levelShort(l.alpha, 'en'), es: levelShort(l.alpha, 'es') }, hint: { en: levelLabel(l.alpha, 'en'), es: levelLabel(l.alpha, 'es') } }))}
          value={String(sel.alpha)}
          onChange={(v) => setAlpha(Number(v) as C13Alpha)}
        />
        <LevelReadout sel={sel} />
      </>
    ),
  };
  const statisticSection: RailSection = {
    id: 'statistic',
    label: { en: 'Statistic', es: 'Estadístico' },
    content: (
      <>
        <ChipGroup
          id="c13-statistic"
          label={{ en: 'PLA statistic', es: 'Estadístico PLA' }}
          options={(['overall', 'spearman', 'ks'] as const).map((k) => ({ id: k, label: STATISTIC_TEXT[k] }))}
          value={sel.statistic}
          onChange={(v) => setStatistic(v as C13Statistic)}
        />
        <StatisticReadout sel={sel} />
      </>
    ),
  };

  const pla = (
    <SubTabs
      key="c13-pla"
      ariaLabel={pick({ en: 'Views of the PLA test', es: 'Vistas de la prueba PLA' }, lang)}
      tabs={[
        { id: 'ranks', label: pick({ en: 'Ranks', es: 'Rangos' }, lang), content: <RanksView sel={sel} /> },
        { id: 'ecdf', label: pick({ en: 'ECDFs', es: 'ECDF' }, lang), content: <EcdfView sel={sel} /> },
        { id: 'zones', label: pick({ en: 'Zones', es: 'Zonas' }, lang), content: <ZonesView sel={sel} /> },
        { id: 'detection', label: pick({ en: 'Detection', es: 'Detección' }, lang), content: <DetectionView sel={sel} /> },
      ]}
    />
  );
  return {
    sel,
    rail: [levelSection, statisticSection],
    groups: [
      { id: 'pla', label: { en: 'PLA', es: 'PLA' }, lane: 'replay', provenance: prov, content: pla },
      { id: 'desk', label: { en: 'Desk back-test', es: 'Prueba retrospectiva' }, lane: 'replay', provenance: prov, content: <DeskView sel={sel} /> },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C13FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C13VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C13ContextView sel={sel} /> },
    controls: { level: sel.alpha, statistic: sel.statistic },
  };
}

/** The registry's name for this hook is `useInstrument`; the old-style name stays for the test that imports it. */
export const useC13Instrument = useInstrument;
