// The App route (ADR-0016 s9 as amended, ADR-0071, SDD section 10): one CaseWorkbench. The rail holds the case picker,
// the variants, and the live inputs, in sections: the decision (the challenger, the approval rate, the LGD, whose
// numbers the Impact group draws), the policy (the thresholds that turn p-values into lights, with their counts) and
// the live scorer (one applicant of the holdout sample, with its scores). Chips carry the short labels the artifacts
// declare, so every section fits the rail without scrolling at 1280x800 (ADR-0071 rule 6). The instrument holds one
// row of six groups: Model, Validation, Impact, Findings, Variants, Context (CT-112).
import {
  CaseWorkbench,
  ChipGroup,
  Knob,
  Readout,
  pick,
  useShellLang,
  useWorkbenchState,
  type CaseDef,
  type RailSection,
} from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useState } from 'react';
import { loadCase, loadIndex, useArtifact, type CaseData } from '../api/artifacts';
import type { EbmExport, ScorecardDetails } from '../lib/contract.types';
import { COMMITTED, LIGHT_TEXT, LIGHT_TONE, relight, type PolicyAlphas } from '../lib/policy';
import { ebmLogit, scoreScorecard, sigmoid } from '../engine/scorer';
import { ContextView } from './ContextView';
import { FindingsView } from './FindingsView';
import { ImpactView } from './ImpactView';
import { CHAMPION, challengers, defaultChallenger, provenanceOf, shortName, test, type Selection } from './model';
import { ModelGroup } from './ModelViews';
import { ValidationGroup } from './ValidationViews';
import { VariantsView } from './VariantsView';

const LGD_FLOOR = 0.5; // CRE32.58: the Basel III LGD input floor for QRRE, the default assumption

function PolicyReadout({ sel }: { sel: Selection | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const counts = useMemo(() => {
    if (!sel) return null;
    const rows = sel.data.variant.tests.filter((t) => t.model_id === CHAMPION || t.model_id === sel.challenger);
    let red = 0;
    let amber = 0;
    for (const t of rows) {
      const l = relight(t, sel.alphas);
      if (l === 'red') red++;
      if (l === 'amber') amber++;
    }
    const jeff = test(sel.data.variant, 'pd.jeffreys', CHAMPION);
    return { red, amber, jeffreys: jeff ? relight(jeff, sel.alphas) : null };
  }, [sel]);
  return (
    <Readout
      title={{ en: 'Under this policy', es: 'Con esta política' }}
      lane="live"
      provenance={provenanceOf(sel?.data.variant.provenance.truth_status)}
      dataKey={stateKey}
      items={[
        { label: { en: 'Red lights, champion and challenger', es: 'Luces rojas, campeón y retador' }, value: counts?.red ?? null, unit: { en: 'tests', es: 'pruebas' } },
        { label: { en: 'Amber lights', es: 'Luces ámbar' }, value: counts?.amber ?? null, unit: { en: 'tests', es: 'pruebas' } },
        {
          label: { en: 'Jeffreys test of the champion (portfolio)', es: 'Prueba de Jeffreys del campeón (cartera)' },
          text: counts?.jeffreys ? LIGHT_TEXT[counts.jeffreys] : undefined,
          unitless: true,
          tone: counts?.jeffreys ? LIGHT_TONE[counts.jeffreys] : 'neutral',
        },
      ]}
    />
  );
}

function ApplicantReadout({ sel }: { sel: Selection | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const live = useMemo(() => liveScores(sel), [sel]);
  return (
    <Readout
      title={{ en: 'Live scores of this applicant', es: 'Puntajes en vivo de este solicitante' }}
      lane="live"
      provenance={provenanceOf(sel?.data.variant.provenance.truth_status)}
      dataKey={stateKey}
      items={[
        { label: { en: 'Scorecard score', es: 'Puntaje de la scorecard' }, value: live?.score ?? null, unit: { en: 'points', es: 'puntos' }, format: { decimals: 0 } },
        { label: { en: 'PD, scorecard', es: 'PD, scorecard' }, value: live?.pdScorecard ?? null, unitless: true, format: { percent: true, decimals: 2 } },
        { label: { en: 'PD, EBM (before calibration)', es: 'PD, EBM (antes de calibrar)' }, value: live?.pdEbm ?? null, unitless: true, format: { percent: true, decimals: 2 } },
        { label: { en: 'Observed outcome', es: 'Resultado observado' }, text: live ? (live.defaulted ? { en: 'defaulted', es: 'incumplió' } : { en: 'did not default', es: 'no incumplió' }) : undefined, unitless: true },
      ]}
    />
  );
}

/** The live scores of the chosen applicant, from the committed points table and EBM export alone. */
export function liveScores(sel: Selection | null) {
  const sample = sel?.data.variant.outputs.sample;
  if (!sel || !sample) return null;
  const sc = sel.data.models.model.find((m) => m.id === CHAMPION)?.details as ScorecardDetails | undefined;
  const ebm = (sel.data.models.model.find((m) => m.id === 'P3-ebm')?.details as { export: EbmExport } | undefined)?.export;
  if (!sc || !ebm) return null;
  const i = Math.min(sel.applicant, sample.ids.length - 1);
  const inputs = Object.fromEntries(Object.entries(sample.inputs).map(([k, v]) => [k, v[i]]));
  const card = scoreScorecard(sc, inputs);
  const e = ebmLogit(ebm, inputs);
  return { id: sample.ids[i], inputs, card, ebm: e, score: card.score, pdScorecard: card.pd, pdEbm: sigmoid(e.logit), defaulted: sample.targets[i] === 1 };
}

export function Workbench() {
  const lang = useShellLang();
  const index = useArtifact((s) => loadIndex(s), []);
  const [caseId, setCaseId] = useState<string | null>(null);
  const selected = caseId ?? (index.state === 'ready' ? index.data.default_case : null);
  const [variantId, setVariantId] = useState<string | null>(null);
  const loaded = useArtifact((s) => (selected ? loadCase(selected, variantId, s) : new Promise<CaseData>(() => undefined)), [selected, variantId]);
  const data = loaded.state === 'ready' && loaded.data.manifest.case_id === selected ? loaded.data : null;

  const [challenger, setChallenger] = useState<string | null>(null);
  const [alphas, setAlphas] = useState<PolicyAlphas>(COMMITTED);
  const [approval, setApproval] = useState(0.8);
  const [lgd, setLgd] = useState(LGD_FLOOR);
  const [applicant, setApplicant] = useState(0);

  // a challenger that the variant does not have (the German twin has TabPFN, Taiwan has XGBoost) falls back
  const options = data ? challengers(data.variant) : [];
  const chosen = data && challenger && options.some((o) => o.id === challenger) ? challenger : data ? defaultChallenger(data.variant) : null;
  useEffect(() => {
    if (data && chosen !== challenger) setChallenger(chosen);
  }, [data, chosen, challenger]);

  const sel: Selection | null = useMemo(
    () => (data && chosen ? { data, challenger: chosen, alphas, approval, lgd, applicant } : null),
    [data, chosen, alphas, approval, lgd, applicant],
  );

  const cases: CaseDef[] = index.state === 'ready' ? index.data.cases.map((c) => ({ id: c.case_id, name: c.title[lang], category: c.category[lang], kind: c.kind })) : [];
  const variants = data
    ? data.manifest.artifacts
        .filter((a) => a.role === 'variant')
        .map((a) => ({ id: a.variant_id, label: a.short_title, note: a.regime, lane: 'replay' as const }))
    : [];
  const activeVariant = data?.variant.variant_id ?? '';
  const moved = alphas.amber !== COMMITTED.amber || alphas.red !== COMMITTED.red;
  const sample = data?.variant.outputs.sample ?? null;

  const rail: RailSection[] = [
    {
      id: 'decision',
      label: { en: 'Decision', es: 'Decisión' },
      content: (
        <>
          <ChipGroup
            id="challenger"
            label={{ en: 'Challenger', es: 'Retador' }}
            options={options.map((o) => ({ id: o.id, label: shortName(o, o.id), hint: o.title }))}
            value={chosen ?? ''}
            onChange={setChallenger}
          />
          <Knob
            id="approval"
            label={{ en: 'Approval rate', es: 'Tasa de aprobación' }}
            hint={{ en: 'The share of applicants approved, lowest PD first.', es: 'La fracción de solicitantes aprobados, de menor PD a mayor.' }}
            value={approval}
            min={0.5}
            max={0.95}
            step={0.01}
            format={{ percent: true, decimals: 0 }}
            onChange={setApproval}
          />
          <Knob
            id="lgd"
            label={{ en: 'Loss given default', es: 'Pérdida dado el incumplimiento' }}
            hint={{ en: 'Assumed for every approved account; 50% is the Basel III input floor for QRRE (CRE32.58).', es: 'Supuesta para toda cuenta aprobada; 50% es el piso de Basilea III para QRRE (CRE32.58).' }}
            value={lgd}
            min={0.1}
            max={1}
            step={0.05}
            format={{ percent: true, decimals: 0 }}
            onChange={setLgd}
          />
        </>
      ),
    },
    {
      id: 'policy',
      label: { en: 'Policy', es: 'Política' },
      content: (
        <>
          <Knob
            id="alpha-amber"
            label={{ en: 'Amber below p =', es: 'Ámbar bajo p =' }}
            hint={{ en: 'A policy choice, not a regulatory one: the ECB 2019 instructions set no pass or fail thresholds.', es: 'Una elección de política, no regulatoria: las instrucciones del BCE de 2019 no fijan umbrales de aprobación.' }}
            value={alphas.amber}
            min={0.01}
            max={0.2}
            step={0.005}
            format={{ decimals: 3 }}
            onChange={(amber) => setAlphas({ amber, red: Math.min(alphas.red, amber) })}
          />
          <Knob
            id="alpha-red"
            label={{ en: 'Red below p =', es: 'Rojo bajo p =' }}
            hint={{ en: 'Never above the amber threshold.', es: 'Nunca sobre el umbral ámbar.' }}
            value={alphas.red}
            min={0.001}
            max={0.1}
            step={0.001}
            format={{ decimals: 3 }}
            onChange={(red) => setAlphas({ amber: Math.max(alphas.amber, red), red })}
          />
          <PolicyReadout sel={sel} />
        </>
      ),
    },
    {
      id: 'applicant',
      label: { en: 'Applicant', es: 'Solicitante' },
      content: (
        <>
          <Knob
            id="applicant"
            label={{ en: 'Applicant of the sample', es: 'Solicitante de la muestra' }}
            hint={{ en: 'One of the 50 holdout applicants scored live from the committed points table and EBM.', es: 'Uno de los 50 solicitantes de la muestra reservada puntuados en vivo con la tabla de puntos y el EBM comprometidos.' }}
            value={applicant + 1}
            min={1}
            max={sample ? sample.ids.length : 1}
            step={1}
            format={{ decimals: 0 }}
            disabled={!sample}
            onChange={(n) => setApplicant(Math.round(n) - 1)}
          />
          {!sample && <p className="caos-pending">{pick({ en: 'This variant resamples the holdout, so it carries no scored sample; pick the holdout or the German twin.', es: 'Esta variante remuestrea la muestra reservada, así que no trae muestra puntuada; elija la muestra reservada o el gemelo alemán.' }, lang)}</p>}
          <ApplicantReadout sel={sel} />
        </>
      ),
    },
  ];

  const prov = provenanceOf(data?.variant.provenance.truth_status);
  return (
    <CaseWorkbench
      caseId={selected ?? ''}
      source={prov}
      cases={{
        cases,
        selectedId: selected ?? '',
        onSelect: (id) => {
          setCaseId(id);
          setVariantId(null);
        },
        layout: 'select',
        deepLink: true,
        modifiedFromId: moved ? selected : null,
        onResetToCanonical: () => setAlphas(COMMITTED),
      }}
      controls={{ challenger: chosen, amber: alphas.amber, red: alphas.red, approval, lgd, applicant }}
      variants={{ variants, activeId: activeVariant, onSelect: setVariantId, title: { en: 'Variant', es: 'Variante' }, lane: 'replay' }}
      rail={rail}
      groups={[
        { id: 'model', label: { en: 'Model', es: 'Modelo' }, lane: 'replay', provenance: prov, content: <ModelGroup sel={sel} /> },
        { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'replay', provenance: prov, content: <ValidationGroup sel={sel} /> },
        { id: 'impact', label: { en: 'Impact', es: 'Impacto' }, lane: 'live', provenance: prov, content: <ImpactView sel={sel} /> },
        { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <FindingsView sel={sel} /> },
      ]}
      compare={{ label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <VariantsView sel={sel} onPick={setVariantId} /> }}
      context={{ content: <ContextView sel={sel} /> }}
    />
  );
}
