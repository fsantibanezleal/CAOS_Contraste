// The "Inventory and tiers" tab (U15-W): the model inventory with its dependency map, the 4 by 4 tier matrix with the
// rubric sensitivity, the related links drawn apart, the entries the inventory leaves out with their reason, and the
// findings of the inventory itself. Every number is read from the inventory document (governance/inventory.json); a
// missing document is the declared "not available yet" state. The inventory records Contraste's own models: it approves
// nothing and certifies nothing (SDD non-goals 1 and 8).
import { PlotCard, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo, useState } from 'react';
import { P } from '../../content/bi';
import { AsOf, Basis, ConventionNote, Doc, GovernanceDoc, Tag } from './common';
import { DependencyMap, EDGE_COLOR, SEVERITY_RING, tierColor } from './DependencyMap';
import { GOVERNANCE_FILES, adoptedCell, severityText, tierName, worstOpen, type GovInventory, type InvEntry } from './model';
import { SensitivityTable, TierMatrix, type CellPick } from './TierMatrix';

const LIFECYCLE_NAME: Record<string, { en: string; es: string }> = {
  proposed: { en: 'proposed', es: 'propuesto' },
  in_development: { en: 'in development', es: 'en desarrollo' },
  in_validation: { en: 'in validation', es: 'en validación' },
  approved: { en: 'approved', es: 'aprobado' },
  in_use: { en: 'in use', es: 'en uso' },
  under_review: { en: 'under review', es: 'en revisión' },
  retired: { en: 'retired', es: 'retirado' },
};

const EDGE_NAME = { document: { en: 'document: the downstream reads the upstream document', es: 'documento: el posterior lee el documento del anterior' }, code: { en: 'code: the downstream imports the upstream code', es: 'código: el posterior importa el código del anterior' } } as const;

const SELECT_NOTE = { en: 'A matrix cell picks its entries for the table.', es: 'Una celda de la matriz elige sus entradas para la tabla.' };

function InventoryTable({ inv, entries, onClear, filtered }: { inv: GovInventory; entries: InvEntry[]; onClear: () => void; filtered: boolean }) {
  const lang = useShellLang();
  const number = new Map(inv.entries.map((e, i) => [e.key, i + 1]));
  return (
    <>
      {filtered && (
        <p className="ct-note">
          {formatNumber(entries.length, lang, { decimals: 0 })} {pick({ en: 'of', es: 'de' }, lang)} {formatNumber(inv.entries.length, lang, { decimals: 0 })} {pick({ en: 'entries shown. ', es: 'entradas mostradas. ' }, lang)}
          <button type="button" className="ct-linkbutton" onClick={onClear}>
            {pick({ en: 'Show all', es: 'Mostrar todas' }, lang)}
          </button>
        </p>
      )}
      <div style={{ overflowX: 'auto', minWidth: 0 }}>
        <table className="caos-table" data-state="ready" data-inventory>
          <thead>
            <tr>
              <th>#</th>
              <th className="caos-col-text">{pick({ en: 'Entry', es: 'Entrada' }, lang)}</th>
              <th className="caos-col-text ct-wide-only">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
              <th>{pick({ en: 'Tier', es: 'Nivel' }, lang)}</th>
              <th className="ct-wide-only">M</th>
              <th className="ct-wide-only">C</th>
              <th className="caos-col-text">{pick({ en: 'Open findings', es: 'Hallazgos abiertos' }, lang)}</th>
              <th className="caos-col-text ct-wide-only">{pick({ en: 'State', es: 'Estado' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Next review', es: 'Próxima revisión' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => {
              const cell = adoptedCell(e);
              const worst = worstOpen(e);
              const a37 = e.attributes.A37.value as Record<string, number> | null;
              return (
                <tr key={e.key} data-entry={e.key} data-tier={e.tier_block.tier}>
                  <td>{number.get(e.key)}</td>
                  <td className="caos-col-text">
                    <span translate="no">{e.key}</span>
                  </td>
                  <td className="caos-col-text ct-wide-only">{pick(e.title, lang)}</td>
                  <td>{tierName(e.tier_block.tier, lang)}</td>
                  <td className="ct-wide-only">{cell ? cell.m : '-'}</td>
                  <td className="ct-wide-only">{cell ? cell.c : '-'}</td>
                  <td className="caos-col-text">
                    {worst && a37
                      ? (['S1', 'S2', 'S3', 'S4'] as const)
                          .filter((s) => (a37[s] ?? 0) > 0)
                          .map((s) => `${s} ${formatNumber(a37[s], lang, { decimals: 0 })}`)
                          .join(', ')
                      : pick({ en: 'none', es: 'ninguno' }, lang)}
                  </td>
                  <td className="caos-col-text ct-wide-only">{pick(LIFECYCLE_NAME[e.lifecycle.state] ?? { en: e.lifecycle.state, es: e.lifecycle.state }, lang)}</td>
                  <td className="ct-wide-only">{e.schedule.next_review}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

/** The legend of the map: what a node colour, a ring and an edge mean, and the related links apart, dashed. */
function MapLegend({ inv }: { inv: GovInventory }) {
  const lang = useShellLang();
  return (
    <div data-map-legend>
      <ul className="ct-evidence" style={{ listStyle: 'none', paddingLeft: 0, display: 'flex', flexWrap: 'wrap', gap: '0.4rem 1rem' }}>
        {[1, 2, 3, 4].map((t) => (
          <li key={t}>
            <span aria-hidden style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 6, background: tierColor(t), marginRight: 6, verticalAlign: 'middle' }} />
            {tierName(t, lang)}
          </li>
        ))}
        {(['S1', 'S2', 'S3', 'S4'] as const).map((s) => (
          <li key={s}>
            <span aria-hidden style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 6, border: `${SEVERITY_RING[s].width}px solid ${SEVERITY_RING[s].color}`, boxSizing: 'border-box', marginRight: 6, verticalAlign: 'middle' }} />
            {pick({ en: `ring: worst open ${s}`, es: `anillo: peor ${s} abierto` }, lang)}
          </li>
        ))}
        {(['document', 'code'] as const).map((k) => (
          <li key={k}>
            <span aria-hidden style={{ display: 'inline-block', width: 22, height: 0, borderTop: `3px solid ${EDGE_COLOR[k]}`, marginRight: 6, verticalAlign: 'middle' }} />
            {pick(EDGE_NAME[k], lang)}
          </li>
        ))}
        <li>
          <span aria-hidden style={{ display: 'inline-block', width: 22, height: 0, borderTop: '2px solid var(--color-fg-faint)', opacity: 0.5, marginRight: 6, verticalAlign: 'middle' }} />
          {pick({ en: `every entry depends on the engine ${inv.engine_node.key} (shown once)`, es: `toda entrada depende del motor ${inv.engine_node.key} (se muestra una vez)` }, lang)}
        </li>
      </ul>
    </div>
  );
}

/** The dependency edges as a table, each with its kind: what the map draws, readable without the drawing. */
function EdgeTable({ inv }: { inv: GovInventory }) {
  const lang = useShellLang();
  const number = new Map(inv.entries.map((e, i) => [e.key, i + 1]));
  if (!inv.edges.length) return null;
  return (
    <table className="caos-table" data-state="ready" data-edges>
      <thead>
        <tr>
          <th className="caos-col-text">{pick({ en: 'Upstream', es: 'Anterior' }, lang)}</th>
          <th className="caos-col-text">{pick({ en: 'Downstream', es: 'Posterior' }, lang)}</th>
          <th className="caos-col-text">{pick({ en: 'Kind', es: 'Tipo' }, lang)}</th>
        </tr>
      </thead>
      <tbody>
        {inv.edges.map((ed) => (
          <tr key={`${ed.upstream}>${ed.downstream}`}>
            <td className="caos-col-text">{number.get(ed.upstream)}: <span translate="no">{ed.upstream}</span></td>
            <td className="caos-col-text">{number.get(ed.downstream)}: <span translate="no">{ed.downstream}</span></td>
            <td className="caos-col-text">{pick(EDGE_NAME[ed.kind as keyof typeof EDGE_NAME] ?? { en: ed.kind, es: ed.kind }, lang)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** The related links: statements the record makes that are not a dependency, drawn apart and dashed, never as an edge of the map. */
function RelatedLinks({ inv }: { inv: GovInventory }) {
  const lang = useShellLang();
  if (!inv.related.length) return null;
  return (
    <div data-related>
      <h3 className="ct-sub">{pick({ en: 'Related, not a dependency', es: 'Relacionados, no una dependencia' }, lang)}</h3>
      <ul className="ct-evidence" style={{ listStyle: 'none', paddingLeft: 0 }}>
        {inv.related.map((r) => (
          <li key={`${r.a}~${r.b}`} data-related-link={`${r.a}~${r.b}`}>
            <span translate="no">{r.a}</span>
            <svg width={44} height={10} aria-hidden style={{ margin: '0 6px', verticalAlign: 'middle' }}>
              <line x1={1} y1={5} x2={43} y2={5} stroke="var(--color-fg-subtle)" strokeWidth={2} strokeDasharray="4 3" />
            </svg>
            <span translate="no">{r.b}</span> ({r.kind})
          </li>
        ))}
      </ul>
    </div>
  );
}

function Excluded({ inv }: { inv: GovInventory }) {
  const lang = useShellLang();
  if (!inv.excluded.length) return null;
  return (
    <div data-excluded>
      <h3 className="ct-sub">{pick({ en: 'Left out of the inventory, with the reason', es: 'Fuera del inventario, con la razón' }, lang)}</h3>
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th>{pick({ en: 'Case', es: 'Caso' }, lang)}</th>
            <th className="caos-col-text">{pick({ en: 'Reason', es: 'Razón' }, lang)}</th>
          </tr>
        </thead>
        <tbody>
          {inv.excluded.map((x) => (
            <tr key={`${x.case_id}/${x.variant_id ?? ''}`}>
              <td>{x.variant_id ? `${x.case_id}/${x.variant_id}` : x.case_id}</td>
              <td className="caos-col-text"><Doc t={x.reason} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InventoryOwn({ inv }: { inv: GovInventory }) {
  const lang = useShellLang();
  return (
    <div data-inventory-findings>
      <h3 className="ct-sub">{pick({ en: 'Findings of the inventory itself', es: 'Hallazgos del propio inventario' }, lang)}</h3>
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th className="caos-col-text">{pick({ en: 'Severity, with its ECB F equivalent', es: 'Severidad, con su equivalente F del BCE' }, lang)}</th>
            <th className="caos-col-text">{pick({ en: 'Finding', es: 'Hallazgo' }, lang)}</th>
          </tr>
        </thead>
        <tbody>
          {inv.governance_findings.map((f) => (
            <tr key={f.id}>
              <td className="caos-col-text">{severityText(f.severity, f.ecb_f, lang)}</td>
              <td className="caos-col-text">
                <strong><Doc t={f.title} /></strong>
                <br />
                <Doc t={f.description} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Completeness({ inv }: { inv: GovInventory }) {
  const lang = useShellLang();
  const totals = useMemo(() => {
    const t = { present: 0, derivable: 0, convention: 0, not_applicable: 0, missing: 0 };
    for (const c of Object.values(inv.completeness.attributes)) for (const k of Object.keys(t) as Array<keyof typeof t>) t[k] += c[k];
    return t;
  }, [inv]);
  const n = (v: number) => formatNumber(v, lang, { decimals: 0 });
  return (
    <p data-completeness>
      {pick(
        {
          en: `Of the 40 attributes of the B.2 record for each of the ${n(inv.completeness.entries)} entries: ${n(totals.present)} present, ${n(totals.derivable)} derivable, ${n(totals.convention)} a stated convention, ${n(totals.not_applicable)} not applicable and ${n(totals.missing)} missing, each with the reason in the document.`,
          es: `De los 40 atributos del registro B.2 de cada una de las ${n(inv.completeness.entries)} entradas: ${n(totals.present)} presentes, ${n(totals.derivable)} derivables, ${n(totals.convention)} una convención declarada, ${n(totals.not_applicable)} no aplicables y ${n(totals.missing)} faltantes, cada uno con su razón en el documento.`,
        },
        lang,
      )}
    </p>
  );
}

/** The inventory, the map and the tier matrix, drawn from one inventory document. */
export function InventoryTab({ inv }: { inv: GovInventory }) {
  const lang = useShellLang();
  const [picked, setPicked] = useState<CellPick | null>(null);
  const shown = useMemo(() => {
    if (!picked) return inv.entries;
    return inv.entries.filter((e) => {
      const cell = adoptedCell(e);
      return cell?.m === picked.m && cell.c === picked.c;
    });
  }, [inv, picked]);
  const adopted = inv.conventions.adopted_reading;
  return (
    <>
      <P
        en="The inventory records the models Contraste validates, one entry per fit, each with its components (champion, challenger, benchmark rung or reference), its tier and what is open on it. It records Contraste's own models: it approves nothing and certifies nothing, and a tier says how much a model matters for validation effort, not whether it may be used."
        es="El inventario registra los modelos que Contraste valida, una entrada por ajuste, cada una con sus componentes (campeón, retador, peldaño de referencia o referencia), su nivel y lo que hay abierto en ella. Registra los modelos de Contraste mismo: no aprueba nada ni certifica nada, y un nivel dice cuánto importa un modelo para el esfuerzo de validación, no si puede usarse."
      />
      <P
        en="To read the page: the map shows what each model reads from another and how much of the inventory rests on one entry; the matrix shows how many entries sit at each combination of materiality and complexity, and the table beneath the sensitivity says how much that depends on the rubric rather than on the models. A cell of the matrix picks its entries in the table. What is open on each entry, its next review and its record completeness come from the inventory document, and the attributes the product holds nothing behind are listed as missing, each with the reason, never filled in."
        es="Para leer la página: el mapa muestra qué lee cada modelo de otro y cuánto del inventario descansa en una entrada; la matriz muestra cuántas entradas hay en cada combinación de materialidad y complejidad, y la tabla de sensibilidad dice cuánto de eso depende de la rúbrica y no de los modelos. Una celda de la matriz elige sus entradas en la tabla. Lo que está abierto en cada entrada, su próxima revisión y la completitud de su registro vienen del documento del inventario, y los atributos sobre los que el producto no tiene nada se listan como faltantes, cada uno con su razón, nunca rellenados."
      />
      <Completeness inv={inv} />
      <ConventionNote />
      <AsOf asOf={inv.as_of} basis={inv.as_of_basis} />
      <PlotCard
        title={{ en: 'The dependency map', es: 'El mapa de dependencias' }}
        lane="replay"
        provenance="synthetic"
        note={{
          en: 'Each node is an entry, numbered as in the table; its colour is its tier and its ring the worst severity among its open findings. A line with an arrow is a dependency, by the kind of the edge.',
          es: 'Cada nodo es una entrada, numerada como en la tabla; su color es su nivel y su anillo la peor severidad entre sus hallazgos abiertos. Una línea con flecha es una dependencia, según el tipo de la arista.',
        }}
      >
        <DependencyMap inv={inv} />
        <MapLegend inv={inv} />
        <EdgeTable inv={inv} />
      </PlotCard>
      <RelatedLinks inv={inv} />
      <PlotCard
        title={{ en: 'The tier matrix: materiality by complexity', es: 'La matriz de niveles: materialidad por complejidad' }}
        lane="replay"
        provenance="synthetic"
        note={{
          en: `Entries per cell under the adopted reading ${adopted.reading}; the tier each cell gives follows the stated rule (Methodology). ${pick(SELECT_NOTE, 'en')}`,
          es: `Entradas por celda bajo la lectura adoptada ${adopted.reading}; el nivel de cada celda sigue la regla declarada (Metodología). ${pick(SELECT_NOTE, 'es')}`,
        }}
      >
        <TierMatrix inv={inv} picked={picked} onPick={setPicked} />
      </PlotCard>
      <h3 className="ct-sub">{pick({ en: 'How much the tier rests on the rubric', es: 'Cuánto descansa el nivel en la rúbrica' }, lang)}</h3>
      <SensitivityTable inv={inv} />
      <p className="ct-note">
        <Tag tag={adopted.label} />. <Basis label={adopted.reading} text={adopted.basis} />
      </p>
      <h3 className="ct-sub">{pick({ en: 'The entries', es: 'Las entradas' }, lang)}</h3>
      <InventoryTable inv={inv} entries={shown} filtered={picked !== null} onClear={() => setPicked(null)} />
      <Excluded inv={inv} />
      <InventoryOwn inv={inv} />
    </>
  );
}

/** The tab: the inventory document in its declared state. */
export function InventoryTabLoader() {
  return <GovernanceDoc<GovInventory> file={GOVERNANCE_FILES.inventory}>{(inv) => <InventoryTab inv={inv} />}</GovernanceDoc>;
}
