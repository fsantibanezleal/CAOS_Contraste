// The C04 instrument (CT-410 to CT-412): the rail's sections, each with its controls and a live read-out, and the six
// groups of CT-112 with C04's views by variant kind (an agency's CEREP pages, a generator family's known truth, the
// published answers). The workbench calls this hook on every case and uses it when the case is C04. Every control
// sets a field of the selection, so every move changes the workbench's state key (gate G9).
import { ChipGroup, Knob, SubTabs, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { provenanceOf } from '../model';
import { GeneratorsView, MatrixView } from './AgencyModelViews';
import { MobilityView, SemestersView, TestsView } from './AgencyTestsViews';
import { ByYearView, DefinitionsView, LifetimeView, PdByGradeView } from './AgencyValidationViews';
import { C04ContextView, C04FindingsView, C04VariantsView, GradeReadout, IntervalReadout, ProjectionReadout } from './C04Common';
import { FamilyValidationView, GeneratorView } from './FamilyViews';
import { ImpactView } from './LiveViews';
import type { MapScale } from './MatrixMap';
import { PapersView, PublishedImpactView, PublishedModelView } from './PublishedViews';
import {
  DEFINITION_HINT,
  DEFINITIONS,
  ESTIMATOR_LABEL,
  ESTIMATORS,
  GRADES,
  LEVELS,
  START_LABEL,
  STARTS,
  definitionsOf,
  isAgency,
  isFamily,
  isPublished,
  type C04Sel,
  type Definition,
  type Estimator,
  type StartPortfolio,
} from './selection';

export interface C04Instrument {
  sel: C04Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

/** The definition chips carry short labels (the rail is 248 px wide at 1280 x 800); each chip's hint says what the
 * definition counts. */
const DEFINITION_CHIP: Record<Definition, BiText> = {
  d2: { en: 'D2', es: 'D2' },
  d3: { en: 'D3', es: 'D3' },
  d4: { en: 'D4', es: 'D4' },
  keep: { en: 'Keep', es: 'Con retiros' },
};

const GRADE_HINT: Partial<Record<string, BiText>> = {
  'CCC-C': { en: 'CCC to C: the categories below B, pooled as CEREP pools them.', es: 'CCC a C: las categorías bajo B, agrupadas como las agrupa CEREP.' },
};

export function useC04Instrument(data: CaseData | null, onPick: (id: string) => void): C04Instrument | null {
  const lang = useShellLang();
  const [grade, setGrade] = useState(6);
  const [definition, setDefinition] = useState<Definition>('d2');
  const [estimator, setEstimator] = useState<Estimator>('em');
  // a cohort index belongs to the variant it was picked on (S&P's and Fitch's cohorts start in different years)
  const [cohortOf, setCohortOf] = useState<{ variant: string; k: number } | null>(null);
  const [mapScale, setMapScale] = useState<MapScale>('migrations');
  const [start, setStart] = useState<StartPortfolio>('origination');
  const [horizon, setHorizon] = useState(20);
  const [rho, setRho] = useState(0);
  const [level, setLevel] = useState(0.95);
  const [lgd, setLgd] = useState(0.45);

  const v = data && data.manifest.case_id === 'C04' ? (data.variant as VariantArtifact<unknown>) : null;
  const agency = v && isAgency(v) ? v : null;
  const family = v && isFamily(v) ? v : null;
  const published = v && isPublished(v) ? v : null;
  // an agency without a definition (Moody's has no D4 or Keep) shows the default-rate page's
  const available = agency ? definitionsOf(agency.outputs) : DEFINITIONS;
  const def: Definition = available.includes(definition) ? definition : 'd2';
  const cohort = cohortOf && v && cohortOf.variant === v.variant_id ? cohortOf.k : null;
  const variantId = v?.variant_id ?? '';

  const sel: C04Sel | null = useMemo(
    () =>
      v && data
        ? {
            data,
            grade,
            definition: def,
            estimator,
            cohort,
            mapScale,
            start,
            horizon,
            rho,
            level,
            lgd,
            act: {
              setGrade,
              setCohort: (k: number | null) => setCohortOf(k === null ? null : { variant: variantId, k }),
              setMapScale,
              setLgd,
            },
          }
        : null,
    [v, data, grade, def, estimator, cohort, mapScale, start, horizon, rho, level, lgd, variantId],
  );
  if (!v || !data || !sel || !(agency || family || published)) return null;
  const prov = provenanceOf(v.provenance.truth_status);
  const agencyName = agency?.outputs.agency.name ?? '';

  const gradeChips = (
    <ChipGroup
      id="c04-grade"
      label={{ en: 'Grade', es: 'Grado' }}
      options={GRADES.map((g, i) => ({ id: String(i), label: { en: g, es: g }, hint: GRADE_HINT[g] }))}
      value={String(grade)}
      onChange={(id) => setGrade(Number(id))}
    />
  );
  const gradeSection: RailSection = {
    id: 'grade',
    label: agency ? { en: 'Grade and definition', es: 'Grado y definición' } : { en: 'Grade', es: 'Grado' },
    content: (
      <>
        {gradeChips}
        {agency && (
          <ChipGroup
            id="c04-definition"
            label={{ en: 'Default definition', es: 'Definición de incumplimiento' }}
            options={DEFINITIONS.map((d) =>
              available.includes(d)
                ? { id: d, label: DEFINITION_CHIP[d], hint: DEFINITION_HINT[d] }
                : {
                    id: d,
                    label: DEFINITION_CHIP[d],
                    disabled: true,
                    hint: {
                      en: `Not available for ${agencyName}: its transition page has no default category, so the matrix has no default column to read.`,
                      es: `No disponible para ${agencyName}: su página de transiciones no tiene categoría de incumplimiento, así que la matriz no tiene columna de incumplimiento que leer.`,
                    },
                  },
            )}
            value={def}
            onChange={(id) => setDefinition(id as Definition)}
          />
        )}
        {family?.outputs.family === 'markov' && (
          <ChipGroup
            id="c04-estimator"
            label={{ en: 'Estimator', es: 'Estimador' }}
            options={ESTIMATORS.map((e) => ({ id: e, label: ESTIMATOR_LABEL[e] }))}
            value={estimator}
            onChange={(id) => setEstimator(id as Estimator)}
          />
        )}
        <GradeReadout sel={sel} />
      </>
    ),
  };
  const projectionSection: RailSection = {
    id: 'projection',
    label: { en: 'Projection', es: 'Proyección' },
    content: (
      <>
        <ChipGroup
          id="c04-start"
          label={{ en: 'Starting portfolio', es: 'Cartera inicial' }}
          options={STARTS.map((s) => ({ id: s, label: START_LABEL[s], hint: START_HINT[s] }))}
          value={start}
          onChange={(id) => setStart(id as StartPortfolio)}
        />
        <Knob
          id="c04-horizon"
          label={{ en: 'Horizon', es: 'Horizonte' }}
          hint={{ en: 'Years the one-year matrix is applied to the portfolio (Engelmann 2024, equation 9).', es: 'Años en que la matriz anual se aplica a la cartera (Engelmann 2024, ecuación 9).' }}
          value={horizon}
          min={5}
          max={50}
          step={1}
          unit={{ en: 'years', es: 'años' }}
          format={{ decimals: 0 }}
          onChange={(h) => setHorizon(Math.round(h))}
        />
        <ProjectionReadout sel={sel} />
      </>
    ),
  };
  const intervalSection: RailSection = {
    id: 'interval',
    label: { en: 'Interval', es: 'Intervalo' },
    content: (
      <>
        <Knob
          id="c04-rho"
          label={{ en: 'Default correlation', es: 'Correlación de incumplimiento' }}
          hint={{
            en: 'The correlation between two obligors\' default indicators; the Wald and Agresti-Coull intervals widen by the effective number of obligors (Schuermann and Hanson 2004). Jeffreys has no correction.',
            es: 'La correlación entre los indicadores de incumplimiento de dos deudores; los intervalos de Wald y Agresti-Coull se ensanchan por el número efectivo de deudores (Schuermann y Hanson 2004). Jeffreys no tiene corrección.',
          }}
          value={rho}
          min={0}
          max={0.05}
          step={0.0025}
          format={{ percent: true, decimals: 2 }}
          onChange={setRho}
        />
        <ChipGroup
          id="c04-level"
          label={{ en: 'Level', es: 'Nivel' }}
          options={LEVELS.map((l) => ({ id: String(l), label: { en: `${Math.round(l * 100)}%`, es: `${Math.round(l * 100)}%` } }))}
          value={String(level)}
          onChange={(id) => setLevel(Number(id))}
        />
        <IntervalReadout sel={sel} />
      </>
    ),
  };

  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  let model: ReactElement;
  let validation: ReactElement;
  let impact: ReactElement;
  let rail: RailSection[];
  if (agency) {
    model = tabs(
      [
        { id: 'matrix', label: { en: 'Matrix', es: 'Matriz' }, content: <MatrixView sel={sel} /> },
        { id: 'generators', label: { en: 'Generators', es: 'Generadores' }, content: <GeneratorsView sel={sel} /> },
        { id: 'mobility', label: { en: 'Mobility', es: 'Movilidad' }, content: <MobilityView sel={sel} /> },
      ],
      { en: "Views of the agency's matrices", es: 'Vistas de las matrices de la agencia' },
      'model-agency',
    );
    validation = tabs(
      [
        { id: 'pd-by-grade', label: { en: 'PD by grade', es: 'PD por grado' }, content: <PdByGradeView sel={sel} /> },
        { id: 'by-year', label: { en: 'By year', es: 'Por año' }, content: <ByYearView sel={sel} /> },
        { id: 'definitions', label: { en: 'Definitions', es: 'Definiciones' }, content: <DefinitionsView sel={sel} /> },
        { id: 'lifetime', label: { en: 'Lifetime', es: 'Vida' }, content: <LifetimeView sel={sel} /> },
        { id: 'tests', label: { en: 'Markov tests', es: 'Pruebas de Markov' }, content: <TestsView sel={sel} /> },
        { id: 'semesters', label: { en: 'Semesters', es: 'Semestres' }, content: <SemestersView sel={sel} /> },
      ],
      { en: "Views of the agency's PDs and checks", es: 'Vistas de las PD y verificaciones de la agencia' },
      'validation-agency',
    );
    impact = <ImpactView sel={sel} />;
    // Moody's has no route to default, but its portfolio still migrates: the Drift view draws the composition
    rail = [gradeSection, projectionSection, intervalSection];
  } else if (family) {
    model = <GeneratorView sel={sel} />;
    validation = <FamilyValidationView key={`validation-${family.outputs.family}`} sel={sel} />;
    impact = <ImpactView sel={sel} />;
    rail = [gradeSection, projectionSection, intervalSection];
  } else {
    model = <PublishedModelView sel={sel} />;
    validation = <PapersView sel={sel} />;
    impact = <PublishedImpactView sel={sel} />;
    rail = [intervalSection];
  }
  return {
    sel,
    rail,
    groups: [
      { id: 'model', label: { en: 'Model', es: 'Modelo' }, lane: 'replay', provenance: prov, content: model },
      { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'replay', provenance: prov, content: validation },
      { id: 'impact', label: { en: 'Impact', es: 'Impacto' }, lane: 'live', provenance: prov, content: impact },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C04FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C04VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C04ContextView sel={sel} /> },
    controls: { grade, definition: def, estimator, cohort: cohort ?? -1, mapScale, start, horizon, rho, level, lgd },
  };
}

const START_HINT: Record<StartPortfolio, BiText> = {
  origination: { en: "The pooled cohorts' mix by grade: the portfolio as the agency rates it.", es: 'La mezcla por grado de las cohortes agrupadas: la cartera como la califica la agencia.' },
  best: { en: 'Every obligor in AAA: the drift of a portfolio that can only migrate down.', es: 'Todo deudor en AAA: la deriva de una cartera que solo puede migrar hacia abajo.' },
  uniform: { en: 'The same share in each of the seven grades.', es: 'La misma fracción en cada uno de los siete grados.' },
  speculative: { en: 'A third each in BB, B and CCC to C.', es: 'Un tercio en cada uno de BB, B y CCC a C.' },
};
