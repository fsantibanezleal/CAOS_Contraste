// The C05 instrument (CT-210): the rail's sections, each with its controls and a live read-out, and the six groups of
// CT-112 with C05's views. The workbench calls this hook on every case and uses it when the case is C05.
import { ChipGroup, Knob, SubTabs, formatNumber, pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import type { CaseData } from '../../api/artifacts';
import type { Regime, Case1 } from '../../engine/credit';
import type { VariantArtifact } from '../../lib/contract.types';
import { COMMITTED, type PolicyAlphas } from '../../lib/policy';
import { provenanceOf } from '../model';
import { BoundsReadout, C05ContextView, C05FindingsView, C05PolicyReadout, C05VariantsView, CalibrationReadout, CapitalReadout } from './C05Common';
import { BoundsView, KnownTruthView, LdpImpactView, LdpTestsView, ScalingView } from './LdpViews';
import { CASE1, approachShort, isLdp, isSp, type C05Sel } from './selection';
import { ApproachesView, CurvesView, DefaultProfileView, GoldenSpView, GradeTestsView, ProfilesView, SpImpactView } from './SpViews';

const REGIMES: Array<{ id: Regime; label: BiText; hint: BiText }> = [
  { id: 'basel3', label: { en: 'Basel III', es: 'Basilea III' }, hint: { en: 'Basel III final (CRE31, in force 2023-01-01): PD floor 0.05%, no scaling factor.', es: 'Basilea III final (CRE31, vigente desde 2023-01-01): piso de PD 0,05%, sin factor de escala.' } },
  { id: 'crr3', label: { en: 'CRR3', es: 'CRR3' }, hint: { en: 'EU CRR3, Article 153 (applies from 2025-01-01): the Basel III formula.', es: 'CRR3 de la UE, artículo 153 (aplica desde 2025-01-01): la fórmula de Basilea III.' } },
  { id: 'basel2', label: { en: 'Basel II', es: 'Basilea II' }, hint: { en: 'Basel II (CRE30.4): the 1.06 scaling factor, PD floor 0.03%.', es: 'Basilea II (CRE30.4): el factor de escala 1,06, piso de PD 0,03%.' } },
];

// The rail is 248 px wide at 1280x800: the four approach chips keep the paper's order on two rows when the accuracy
// ratio goes by its usual abbreviation (the chip's hint carries the full title).
const RAIL_LABEL: Partial<Record<Case1, BiText>> = { 'A2-iar': { en: 'AR', es: 'AR' } };

export interface C05Instrument {
  sel: C05Sel | null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: ReturnType<typeof provenanceOf>; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

function PolicySection({ alphas, setAlphas }: { alphas: PolicyAlphas; setAlphas: (a: PolicyAlphas) => void }) {
  return (
    <div className="ct-pair">
      <Knob
        id="c05-alpha-amber"
        label={{ en: 'Amber below p', es: 'Ámbar bajo p' }}
        hint={{ en: 'A policy choice, not a regulatory one: no regulation fixes these thresholds.', es: 'Una elección de política, no regulatoria: ninguna regulación fija estos umbrales.' }}
        value={alphas.amber}
        min={0.01}
        max={0.2}
        step={0.005}
        format={{ decimals: 3 }}
        onChange={(amber) => setAlphas({ amber, red: Math.min(alphas.red, amber) })}
      />
      <Knob
        id="c05-alpha-red"
        label={{ en: 'Red below p', es: 'Rojo bajo p' }}
        hint={{ en: 'Never above the amber threshold.', es: 'Nunca sobre el umbral ámbar.' }}
        value={alphas.red}
        min={0.001}
        max={0.1}
        step={0.001}
        format={{ decimals: 3 }}
        onChange={(red) => setAlphas({ amber: Math.max(alphas.amber, red), red })}
      />
    </div>
  );
}

export function useC05Instrument(data: CaseData | null, onPick: (id: string) => void): C05Instrument | null {
  const lang = useShellLang();
  const [approach, setApproach] = useState<Case1>('A4-slr');
  const [p1, setP1] = useState<number | null>(null);
  const [gamma, setGamma] = useState(0.75);
  const [rho, setRho] = useState(0.12);
  const [scaled, setScaled] = useState(false);
  const [regime, setRegime] = useState<Regime>('basel3');
  const [lgd, setLgd] = useState(0.45);
  const [alphas, setAlphas] = useState<PolicyAlphas>(COMMITTED);

  const v = data && data.manifest.case_id === 'C05' ? (data.variant as VariantArtifact<unknown>) : null;
  const observed = v && isSp(v) ? v.outputs.pd1 : null;
  // a new variant starts the live calibration at its own observed PD
  useEffect(() => {
    setP1(observed);
  }, [v?.variant_id, observed]);

  const sel: C05Sel | null = useMemo(
    () => (v && data ? { data, alphas, approach, p1: p1 ?? observed ?? 0.01, gamma, rho, scaled, regime, lgd } : null),
    [v, data, alphas, approach, p1, observed, gamma, rho, scaled, regime, lgd],
  );
  if (!v || !data) return null;
  const prov = provenanceOf(v.provenance.truth_status);
  const sp = isSp(v) ? v : null;
  const ldp = isLdp(v) ? v : null;
  const moved = alphas.amber !== COMMITTED.amber || alphas.red !== COMMITTED.red;

  const capital: RailSection = {
    id: 'capital',
    label: { en: 'Capital', es: 'Capital' },
    content: (
      <>
        <ChipGroup
          id="c05-regime"
          label={{ en: 'Regime', es: 'Régimen' }}
          options={REGIMES.map((r) => ({ id: r.id, label: r.label, hint: r.hint }))}
          value={regime}
          onChange={(id) => setRegime(id as Regime)}
        />
        <Knob
          id="c05-lgd"
          label={{ en: 'LGD', es: 'LGD' }}
          hint={{ en: 'Loss given default for every obligor; 45% is the F-IRB senior unsecured LGD for financial institutions (CRE32.6).', es: 'Pérdida dado el incumplimiento de todo deudor; 45% es la LGD F-IRB senior no garantizada de instituciones financieras (CRE32.6).' }}
          value={lgd}
          min={0.1}
          max={0.9}
          step={0.05}
          format={{ percent: true, decimals: 0 }}
          onChange={setLgd}
        />
        <CapitalReadout sel={sel} />
      </>
    ),
  };
  const policy: RailSection = {
    id: 'policy',
    label: { en: 'Policy', es: 'Política' },
    content: (
      <>
        <PolicySection alphas={alphas} setAlphas={setAlphas} />
        <C05PolicyReadout sel={sel} />
        {moved && (
          <button type="button" className="ct-linkbutton" onClick={() => setAlphas(COMMITTED)}>
            {pick({ en: 'Back to the committed policy', es: 'Volver a la política comprometida' }, lang)}
          </button>
        )}
      </>
    ),
  };
  const first: RailSection = sp
    ? {
        id: 'calibration',
        label: { en: 'Calibration', es: 'Calibración' },
        content: (
          <>
            <ChipGroup
              id="c05-approach"
              label={{ en: 'Approach (case 1)', es: 'Enfoque (caso 1)' }}
              options={CASE1.map((id) => ({ id, label: RAIL_LABEL[id] ?? approachShort(sp, id), hint: sp.model.find((m) => m.id === id)?.title }))}
              value={approach}
              onChange={(id) => setApproach(id as Case1)}
            />
            <Knob
              id="c05-p1"
              label={{ en: 'Forecast PD', es: 'PD pronosticada' }}
              hint={{ en: `The unconditional PD the curve is calibrated to (a forecast or a stress PD); ${sp.outputs.year} observed ${formatNumber(sp.outputs.pd1, 'en', { percent: true, decimals: 2 })}.`, es: `La PD incondicional a la que se calibra la curva (un pronóstico o una PD de estrés); ${sp.outputs.year} observada ${formatNumber(sp.outputs.pd1, 'es', { percent: true, decimals: 2 })}.` }}
              value={sel?.p1 ?? sp.outputs.pd1}
              min={0.002}
              max={0.12}
              step={0.0005}
              format={{ percent: true, decimals: 2 }}
              onChange={setP1}
            />
            <CalibrationReadout sel={sel} />
          </>
        ),
      }
    : {
        id: 'bounds',
        label: { en: 'Bounds', es: 'Cotas' },
        content: (
          <>
            <div className="ct-pair">
              <Knob
                id="c05-gamma"
                label={{ en: 'Level', es: 'Nivel' }}
                hint={{ en: 'The confidence level of the most prudent bounds; the paper argues for moderate ones (below 95%).', es: 'El nivel de confianza de las cotas más prudentes; el artículo aboga por niveles moderados (bajo 95%).' }}
                value={gamma}
                min={0.5}
                max={0.995}
                step={0.005}
                format={{ percent: true, decimals: 1 }}
                onChange={setGamma}
              />
              <Knob
                id="c05-rho"
                label={{ en: 'Correlation', es: 'Correlación' }}
                hint={{ en: 'The asset correlation of the one-factor model (12% is the Basel minimum corporate correlation the paper uses).', es: 'La correlación de activos del modelo de un factor (12% es la mínima corporativa de Basilea que usa el artículo).' }}
                value={rho}
                min={0}
                max={0.3}
                step={0.01}
                format={{ percent: true, decimals: 0 }}
                onChange={setRho}
              />
            </div>
            <ChipGroup
              id="c05-scaled"
              label={{ en: 'Scaling', es: 'Escalado' }}
              options={[
                { id: 'raw', label: { en: 'Bounds', es: 'Cotas' }, hint: { en: 'The most prudent bounds themselves.', es: 'Las cotas más prudentes mismas.' } },
                { id: 'scaled', label: { en: 'Scaled', es: 'Escaladas' }, hint: { en: 'Scaled to the portfolio bound (section 5).', es: 'Escaladas a la cota de la cartera (sección 5).' } },
              ]}
              value={scaled ? 'scaled' : 'raw'}
              onChange={(id) => setScaled(id === 'scaled')}
            />
            <BoundsReadout sel={sel} />
          </>
        ),
      };
  const tabs = (items: Array<{ id: string; label: BiText; content: ReactElement }>, aria: BiText, key: string) => (
    <SubTabs key={key} ariaLabel={pick(aria, lang)} tabs={items.map((t) => ({ ...t, label: pick(t.label, lang) }))} />
  );
  const kind = sp ? 'sp' : 'ldp';
  const model = sp
    ? tabs(
        [
          { id: 'curves', label: { en: 'Curves', es: 'Curvas' }, content: <CurvesView sel={sel} /> },
          { id: 'profiles', label: { en: 'Profiles', es: 'Perfiles' }, content: <ProfilesView sel={sel} /> },
          { id: 'approaches', label: { en: 'Approaches', es: 'Enfoques' }, content: <ApproachesView sel={sel} /> },
        ],
        { en: 'Views of the rating system', es: 'Vistas del sistema de calificación' },
        `model-${kind}`,
      )
    : tabs(
        [
          { id: 'bounds', label: { en: 'Bounds', es: 'Cotas' }, content: <BoundsView sel={sel} /> },
          { id: 'scaling', label: { en: 'Scaling', es: 'Escalado' }, content: <ScalingView sel={sel} /> },
        ],
        { en: 'Views of the estimates', es: 'Vistas de las estimaciones' },
        `model-${kind}`,
      );
  const validation = sp
    ? tabs(
        [
          { id: 'default-profile', label: { en: 'Default profile', es: 'Perfil de incumpl.' }, content: <DefaultProfileView sel={sel} /> },
          { id: 'by-grade', label: { en: 'By grade', es: 'Por grado' }, content: <GradeTestsView sel={sel} /> },
          { id: 'golden', label: { en: 'Paper', es: 'Artículo' }, content: <GoldenSpView sel={sel} /> },
        ],
        { en: 'Views of the validation', es: 'Vistas de la validación' },
        `validation-${kind}`,
      )
    : tabs(
        [
          { id: 'tests', label: { en: 'Tests', es: 'Pruebas' }, content: <LdpTestsView sel={sel} /> },
          { id: 'truth', label: ldp?.outputs.golden ? { en: 'Paper', es: 'Artículo' } : { en: 'Known truth', es: 'Verdad conocida' }, content: <KnownTruthView sel={sel} /> },
        ],
        { en: 'Views of the validation', es: 'Vistas de la validación' },
        `validation-${kind}`,
      );
  return {
    sel,
    rail: [first, capital, policy],
    groups: [
      { id: 'model', label: { en: 'Model', es: 'Modelo' }, lane: 'replay', provenance: prov, content: model },
      { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'replay', provenance: prov, content: validation },
      { id: 'impact', label: { en: 'Impact', es: 'Impacto' }, lane: 'live', provenance: prov, content: sp ? <SpImpactView sel={sel} /> : <LdpImpactView sel={sel} /> },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <C05FindingsView sel={sel} /> },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <C05VariantsView sel={sel} onPick={onPick} /> },
    context: { content: <C05ContextView sel={sel} /> },
    controls: { approach, p1: sel?.p1 ?? 0, gamma, rho, scaled, regime, lgd, amber: alphas.amber, red: alphas.red },
  };
}
