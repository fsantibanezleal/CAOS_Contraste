// The App route (ADR-0016 s9 as amended, ADR-0071, SDD section 10): one CaseWorkbench for every case. C01's instrument
// is built here; C05's by workbench/c05/instrument.tsx (CT-210) and C22's by workbench/c22/instrument.tsx (CT-309), chosen
// by the selected case. The rail holds the case picker,
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
import { ImpactGroup } from './ImpactView';
import { atApproval, CHAMPION, challengers, defaultChallenger, provenanceOf, rung, shortName, test, type Selection } from './model';
import { ModelGroup } from './ModelViews';
import { ValidationGroup } from './ValidationViews';
import { VariantsView } from './VariantsView';
import { useC05Instrument } from './c05/instrument';
import { useC22Instrument } from './c22/instrument';

const LGD_FLOOR = 0.5; // CRE32.58: the Basel III LGD input floor for QRRE, the default assumption

function DecisionReadout({ sel }: { sel: Selection | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const v = sel?.data.variant;
  const champ = v && sel ? atApproval(v.outputs.rungs[CHAMPION].cutoff, sel.approval) : null;
  const chall = v && sel ? atApproval(v.outputs.rungs[sel.challenger]?.cutoff ?? v.outputs.rungs[CHAMPION].cutoff, sel.approval) : null;
  return (
    <Readout
      title={{ en: 'Bad rate of the approved', es: 'Tasa de malos aprobados' }}
      lane="live"
      provenance={provenanceOf(v?.provenance.truth_status)}
      dataKey={stateKey}
      items={[
        { label: shortName(v ? rung(v, CHAMPION) : undefined, CHAMPION), value: champ?.bad ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'From the committed cut-off curve; the Impact group draws it.', es: 'Desde la curva de corte comprometida; el grupo Impacto la dibuja.' } },
        { label: shortName(v && sel ? rung(v, sel.challenger) : undefined, sel?.challenger ?? ''), value: chall?.bad ?? null, unitless: true, format: { percent: true, decimals: 2 } },
      ]}
    />
  );
}

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
        { label: { en: 'Red lights', es: 'Luces rojas' }, value: counts?.red ?? null, unit: { en: 'tests', es: 'pruebas' }, hint: { en: 'Of the champion and the challenger.', es: 'Del campeón y del retador.' } },
        { label: { en: 'Amber lights', es: 'Luces ámbar' }, value: counts?.amber ?? null, unit: { en: 'tests', es: 'pruebas' } },
        {
          label: { en: 'Jeffreys, champion', es: 'Jeffreys, campeón' },
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
        { label: { en: 'Score', es: 'Puntaje' }, value: live?.score ?? null, unit: { en: 'points', es: 'puntos' }, format: { decimals: 0 }, hint: { en: 'The scorecard, from the committed points table.', es: 'La scorecard, desde la tabla de puntos comprometida.' } },
        { label: { en: 'PD, scorecard', es: 'PD, scorecard' }, value: live?.pdScorecard ?? null, unitless: true, format: { percent: true, decimals: 2 } },
        { label: { en: 'PD, EBM (raw)', es: 'PD, EBM (cruda)' }, value: live?.pdEbm ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'Before its calibration map.', es: 'Antes de su mapa de calibración.' } },
        { label: { en: 'Outcome', es: 'Resultado' }, text: live ? (live.defaulted ? { en: 'defaulted', es: 'incumplió' } : { en: 'did not default', es: 'no incumplió' }) : undefined, unitless: true },
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
    () => (data && chosen && data.manifest.case_id === 'C01' ? { data, challenger: chosen, alphas, approval, lgd, applicant } : null),
    [data, chosen, alphas, approval, lgd, applicant],
  );
  // every case's instrument hook runs on every render (hooks keep their order); the selected case picks which is shown
  const c05 = useC05Instrument(data, setVariantId);
  const c22 = useC22Instrument(data, setVariantId);
  const inst = c05 ?? c22;

  const cases: CaseDef[] = index.state === 'ready' ? index.data.cases.map((c) => ({ id: c.case_id, name: c.title[lang], category: c.category[lang], kind: c.kind })) : [];
  const variants = data
    ? data.manifest.artifacts
        .filter((a) => a.role === 'variant')
        .map((a) => ({ id: a.variant_id, label: a.short_title, note: a.title, lane: 'replay' as const }))
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
            options={options.map((o) => {
              const name = shortName(o, o.id);
              const bare = (t: string) => t.replace(/^P\d[a-z]?\s+/, '');
              return { id: o.id, label: { en: bare(name.en), es: bare(name.es) }, hint: o.title };
            })}
            value={chosen ?? ''}
            onChange={setChallenger}
          />
          <div className="ct-pair">
          <Knob
            id="approval"
            label={{ en: 'Approval', es: 'Aprobación' }}
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
            label={{ en: 'LGD', es: 'LGD' }}
            hint={{ en: 'Loss given default, assumed for every approved account; 50% is the Basel III input floor for QRRE (CRE32.58).', es: 'Pérdida dado el incumplimiento, supuesta para toda cuenta aprobada; 50% es el piso de Basilea III para QRRE (CRE32.58).' }}
            value={lgd}
            min={0.1}
            max={1}
            step={0.05}
            format={{ percent: true, decimals: 0 }}
            onChange={setLgd}
          />
          </div>
          <DecisionReadout sel={sel} />
        </>
      ),
    },
    {
      id: 'policy',
      label: { en: 'Policy', es: 'Política' },
      content: (
        <>
          <div className="ct-pair">
          <Knob
            id="alpha-amber"
            label={{ en: 'Amber below p', es: 'Ámbar bajo p' }}
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
          <PolicyReadout sel={sel} />
          {moved && (
            <button type="button" className="ct-linkbutton" onClick={() => setAlphas(COMMITTED)}>
              {pick({ en: 'Back to the committed policy', es: 'Volver a la política comprometida' }, lang)}
            </button>
          )}
        </>
      ),
    },
    {
      id: 'applicant',
      label: { en: 'Applicant', es: 'Solicitante' },
      content: sample ? (
        <>
          <Knob
            id="applicant"
            label={{ en: 'Applicant of the sample', es: 'Solicitante de la muestra' }}
            hint={{ en: 'One of the 50 holdout applicants scored live from the committed points table and EBM.', es: 'Uno de los 50 solicitantes de la muestra reservada puntuados en vivo con la tabla de puntos y el EBM comprometidos.' }}
            value={applicant + 1}
            min={1}
            max={sample.ids.length}
            step={1}
            format={{ decimals: 0 }}
            onChange={(n) => setApplicant(Math.round(n) - 1)}
          />
          <ApplicantReadout sel={sel} />
        </>
      ) : (
        <p className="ct-note">{pick({ en: 'This variant resamples the holdout, so it carries no scored applicants: pick Holdout or German.', es: 'Esta variante remuestrea la muestra reservada, así que no trae solicitantes puntuados: elija Reservada o Alemán.' }, lang)}</p>
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
      }}
      controls={inst ? inst.controls : { challenger: chosen, amber: alphas.amber, red: alphas.red, approval, lgd, applicant }}
      variants={{ variants, activeId: activeVariant, onSelect: setVariantId, title: { en: 'Variant', es: 'Variante' }, lane: 'replay' }}
      rail={inst ? inst.rail : rail}
      groups={
        inst
          ? inst.groups
          : [
              { id: 'model', label: { en: 'Model', es: 'Modelo' }, lane: 'replay', provenance: prov, content: <ModelGroup sel={sel} /> },
              { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'replay', provenance: prov, content: <ValidationGroup sel={sel} /> },
              { id: 'impact', label: { en: 'Impact', es: 'Impacto' }, lane: 'live', provenance: prov, content: <ImpactGroup sel={sel} /> },
              { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance: prov, content: <FindingsView sel={sel} /> },
            ]
      }
      compare={inst ? inst.compare : { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance: prov, content: <VariantsView sel={sel} onPick={setVariantId} /> }}
      context={inst ? inst.context : { content: <ContextView sel={sel} /> }}
    />
  );
}
