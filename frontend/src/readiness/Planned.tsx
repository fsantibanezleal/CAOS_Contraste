// The instrument of a case that is declared absent (ADR-0080 decision 3). A planned case is an index entry whose
// manifest the readiness lists as missing; the same instrument says "not available yet" for a case whose manifest
// could not be read. Every group draws one `data-state="unavailable"` line with the reason, in both languages, and
// nothing else: no number, no chart, no test result. The Context group adds what the index entry itself says.
import { pick, useShellLang, type BiText, type RailSection } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import type { CaseIndex, Text } from '../lib/contract.types';
import { Unavailable } from '../workbench/Pending';

type IndexEntry = CaseIndex['cases'][number];

/** The reason a planned case gives: its title, that it is planned and not built, and the readiness row's own reason. */
export function plannedReason(title: Text, readinessReason: Text | null): Text {
  return {
    en: `${title.en} is planned and not built yet.${readinessReason ? ` ${readinessReason.en}` : ''}`,
    es: `${title.es} está planificado y aún no construido.${readinessReason ? ` ${readinessReason.es}` : ''}`,
  };
}

/** The reason for a case whose artifacts could not be read although nothing declares it absent. */
export function unreadableReason(title: Text | null, detail: string): Text {
  const name = title ?? { en: 'The case', es: 'El caso' };
  return {
    en: `${name.en} is not available yet: its artifacts could not be read (${detail}).`,
    es: `${name.es} aún no está disponible: no se pudieron leer sus artefactos (${detail}).`,
  };
}

const KIND: Record<string, Text> = {
  real: { en: 'real data', es: 'datos reales' },
  synthetic: { en: 'synthetic data with known truth', es: 'datos sintéticos con verdad conocida' },
};

function AbsentContext({ entry, reason }: { entry: IndexEntry | null; reason: Text }) {
  const lang = useShellLang();
  return (
    <div className="ct-absent" data-case={entry?.case_id}>
      {entry && (
        <dl className="ct-defs" data-index-entry={entry.case_id}>
          <dt>{lang === 'es' ? 'Caso' : 'Case'}</dt>
          <dd>
            {entry.case_id}: {pick(entry.title, lang)}
          </dd>
          <dt>{lang === 'es' ? 'Categoría' : 'Category'}</dt>
          <dd>{pick(entry.category, lang)}</dd>
          <dt>{lang === 'es' ? 'Tipo de datos' : 'Data kind'}</dt>
          <dd>{pick(KIND[entry.kind] ?? { en: entry.kind, es: entry.kind }, lang)}</dd>
        </dl>
      )}
      <Unavailable reason={reason} />
    </div>
  );
}

const absent = (reason: Text): ReactElement => (
  <div className="ct-absent">
    <Unavailable reason={reason} />
  </div>
);

export interface AbsentInstrument {
  sel: null;
  rail: RailSection[];
  groups: Array<{ id: string; label: BiText; lane: 'live' | 'replay'; provenance: 'real' | 'synthetic'; content: ReactElement }>;
  compare: { label: BiText; lane: 'replay'; provenance: 'real' | 'synthetic'; content: ReactElement };
  context: { content: ReactElement };
  controls: Record<string, string | number | boolean>;
}

/** The instrument of an absent case: `entry` is the case's index entry when it has one. */
export function absentInstrument(reason: Text, entry: IndexEntry | null): AbsentInstrument {
  const provenance = entry?.kind === 'synthetic' ? 'synthetic' : 'real';
  return {
    sel: null,
    rail: [],
    groups: [
      { id: 'model', label: { en: 'Model', es: 'Modelo' }, lane: 'replay', provenance, content: absent(reason) },
      { id: 'validation', label: { en: 'Validation', es: 'Validación' }, lane: 'replay', provenance, content: absent(reason) },
      { id: 'impact', label: { en: 'Impact', es: 'Impacto' }, lane: 'live', provenance, content: absent(reason) },
      { id: 'findings', label: { en: 'Findings', es: 'Hallazgos' }, lane: 'replay', provenance, content: absent(reason) },
    ],
    compare: { label: { en: 'Variants', es: 'Variantes' }, lane: 'replay', provenance, content: absent(reason) },
    context: { content: <AbsentContext entry={entry} reason={reason} /> },
    controls: {},
  };
}
