// Every catalog row with its declared state: the Implementation page's "what is real in this build".
import { useShellLang } from '@fasl-work/caos-app-shell';
import { NoteLine, PROVENANCE_LABEL, STATE_LABEL, WRAP } from './ReadinessNote';
import { useReadiness } from './useReadiness';
import { viewState } from './readiness';

/** The catalog status of a contract in words (scripts/check_skeleton.py: real or live, else served by a provider). */
const CATALOG_STATUS: Record<string, { en: string; es: string }> = {
  real: { en: 'real', es: 'real' },
  live: { en: 'live', es: 'en vivo' },
  active: { en: 'served by a provider', es: 'servido por un proveedor' },
  provider: { en: 'served by a provider', es: 'servido por un proveedor' },
  stub: { en: 'stub', es: 'sustituto' },
  simulator: { en: 'simulator', es: 'simulador' },
  fixture: { en: 'fixture', es: 'datos de prueba' },
  baseline: { en: 'baseline', es: 'línea base' },
};

export function ReadinessTable() {
  const lang = useShellLang();
  const doc = useReadiness();
  if (doc === undefined) {
    return (
      <p className="caos-pending" data-state="loading">
        {lang === 'es' ? 'Cargando el documento de disponibilidad' : 'Loading the readiness document'}
      </p>
    );
  }
  if (doc === null) return <NoteLine view={viewState(null, [])} lang={lang} />;
  const head = lang === 'es' ? ['Contrato', 'Versión', 'Estado del catálogo', 'Procedencia', 'Estado', 'Razón'] : ['Contract', 'Version', 'Catalog status', 'Provenance', 'State', 'Reason'];
  return (
    <table className="caos-table" data-state="ready">
      <thead>
        <tr>
          {head.map((h, i) => (
            <th key={h} className={i === 5 ? 'caos-col-text' : undefined}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {doc.contracts.map((c) => (
          <tr key={c.id} data-readiness={c.state}>
            {/* the contract by its catalog id, a name of the catalog (the R2b page review c24: the status was printed unmapped) */}
            <td>
              <code translate="no">{c.id}</code>
            </td>
            <td>{c.version}</td>
            <td>{CATALOG_STATUS[c.status]?.[lang] ?? c.status}</td>
            <td>{c.provenance ? PROVENANCE_LABEL[c.provenance][lang] : '-'}</td>
            <td>{STATE_LABEL[c.state][lang]}</td>
            <td className="caos-col-text" style={WRAP}>{c.reason ? c.reason[lang] : '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
