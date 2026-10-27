// The Context group (ADR-0016 s9.B, CT-114): the case's question, its sources with their licence classes and
// attributions, the rungs with their engines and licences, the truth status of every variant, the split and the
// contract-1 report of its inputs, then the case's own write-up.
import { PlotCard, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { C01WriteUp } from '../content/cases/C01';
import { REPLAY, provenanceOf, type Selection } from './model';
import { Pending } from './Pending';
import { engineText, licenceParts, licenceText } from './c01Text';
import { CONTRACT_RULES, inputName, ruleNames } from './names';

/** A rung's title with its input named (the documents of the U8 bake write "Single variable (PAY_0)"; the producer names it from the
 * re-bake on, and this leaves a named title as it is; R3 c01 B2, B4). */
const rungTitle = (t: BiText, lang: 'en' | 'es'): string => ruleNames(pick(t, lang), lang);

const WRITE_UPS: Record<string, () => ReactNode> = { C01: () => <C01WriteUp /> };

const CLASS_TEXT: Record<string, BiText> = {
  'mirror-allowed': { en: 'mirror-allowed: rows may be redistributed with attribution', es: 'espejo permitido: las filas pueden redistribuirse con atribución' },
  'derived-only': { en: 'derived-only: only aggregates and results are published', es: 'solo derivados: solo se publican agregados y resultados' },
  'link-only': { en: 'link-only: linked, never read', es: 'solo enlace: enlazada, nunca leída' },
  unusable: { en: 'unusable: the terms forbid this use', es: 'inutilizable: los términos prohíben este uso' },
};

const TRUTH_TEXT: Record<string, BiText> = {
  'real-outcomes': { en: 'real outcomes', es: 'resultados reales' },
  'synthetic-known-truth': { en: 'real rows perturbed by a known amount (known truth)', es: 'filas reales perturbadas en una cantidad conocida (verdad conocida)' },
  'synthetic-calibrated': { en: 'synthetic, calibrated to public aggregates', es: 'sintéticos, calibrados a agregados públicos' },
  'published-answer': { en: 'a published answer', es: 'una respuesta publicada' },
};

export function ContextView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  if (!sel) return <Pending />;
  const m = sel.data.manifest;
  const fit = sel.data.models.fit;
  const WriteUp = WRITE_UPS[m.case_id];
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} lane={REPLAY} provenance={provenanceOf(sel.data.variant.provenance.truth_status)} dataKey={stateKey}>
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <table className="caos-table" data-sources={m.sources.join(' ')}>
          <thead>
            <tr>
              <th className="caos-col-text">{pick({ en: 'Source', es: 'Fuente' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Licence and class', es: 'Licencia y clase' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Attribution', es: 'Atribución (texto exigido por la fuente, en su idioma)' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {m.sources.map((id) => {
              const s = m.source_details[id];
              return (
                <tr key={id} data-source={id} data-licence-class={s?.class}>
                  <td className="caos-col-text">
                    <a href={s?.landing} rel="noreferrer" target="_blank">
                      {s?.name ?? id}
                    </a>{' '}
                    ({s?.publisher})
                  </td>
                  <td className="caos-col-text">
                    {s && lang === 'es' && licenceText(id, s.licence, 'es') !== s.licence ? (
                      // the Spanish gloss is read as Spanish; the licence's own name, with its version, is not translated
                      (() => {
                        const [before, name, after] = licenceParts(licenceText(id, s.licence, 'es'));
                        return <span>{before}{name ? <span translate="no">{name}</span> : null}{after}</span>;
                      })()
                    ) : (
                      <span translate="no">{s ? s.licence : ''}</span>
                    )}{' '}<em>{s ? pick(CLASS_TEXT[s.class] ?? { en: s.class, es: s.class }, lang) : ''}</em>
                  </td>
                  {/* the source's required wording, verbatim in its own language */}
                  <td className="caos-col-text" translate="no" lang="en">
                    {s?.attribution}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </PlotCard>
      <PlotCard title={{ en: 'The rungs: engines, versions and licences', es: 'Los peldaños: motores, versiones y licencias' }} lane={REPLAY} provenance={provenanceOf(sel.data.variant.provenance.truth_status)} dataKey={stateKey}>
        <table className="caos-table" data-engines="">
          <thead>
            <tr>
              <th>{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Engine and version', es: 'Motor y versión' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Licence', es: 'Licencia' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {sel.data.models.model.map((r) => (
              <tr key={r.id} data-rung={r.id}>
                <td>{pick(r.short_title, lang)}</td>
                <td className="caos-col-text">{rungTitle(r.title, lang)}</td>
                <td className="caos-col-text">
                  {engineText(r.engine, lang)}
                  {r.engine_version !== 'n/a' ? `, ${r.engine_version}` : ''}
                </td>
                <td className="caos-col-text" translate="no">
                  {r.licence}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </PlotCard>
      <PlotCard title={{ en: 'Variants and their truth status', es: 'Variantes y su estado de verdad' }} lane={REPLAY} provenance={provenanceOf(sel.data.variant.provenance.truth_status)} dataKey={stateKey}>
        <table className="caos-table">
          <thead>
            <tr>
              <th className="caos-col-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Regime', es: 'Régimen' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Truth status', es: 'Estado de verdad' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {m.artifacts
              .filter((a) => a.role === 'variant')
              .map((a) => (
                <tr key={a.variant_id} data-truth={a.truth_status}>
                  <td className="caos-col-text">{pick(a.title, lang)}</td>
                  <td className="caos-col-text">{pick(a.regime, lang)}</td>
                  <td className="caos-col-text">{pick(TRUTH_TEXT[a.truth_status] ?? { en: a.truth_status, es: a.truth_status }, lang)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </PlotCard>
      <PlotCard title={{ en: 'The split and the inputs', es: 'La partición y las entradas' }} lane={REPLAY} provenance={provenanceOf(sel.data.variant.provenance.truth_status)} dataKey={stateKey}>
        <table className="caos-table">
          <thead>
            <tr>
              <th>{pick({ en: 'Slice', es: 'Partición' }, lang)}</th>
              <th>N</th>
              <th>{pick({ en: 'Defaults', es: 'Incumplimientos' }, lang)}</th>
              <th>{pick({ en: 'Default rate', es: 'Tasa' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {(
              [
                ['train', { en: 'training', es: 'entrenamiento' }],
                ['calibration', { en: 'calibration', es: 'calibración' }],
                ['holdout', { en: 'holdout', es: 'reservada' }],
              ] as const
            ).map(([k, label]) => (
              <tr key={k}>
                <td>{pick(label, lang)}</td>
                <td>{formatNumber(fit.split[k].n, lang)}</td>
                <td>{formatNumber(fit.split[k].defaults, lang)}</td>
                <td>{formatNumber(fit.split[k].default_rate, lang, { percent: true, decimals: 2 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {fit.train_rows < fit.split.train.n ? (
          // the models of a variant fitted on fewer rows than the training split (small-sample; R3 c02 m8)
          <p className="ct-note" data-train-rows={fit.train_rows}>
            {pick(
              {
                en: `The models of this variant were fitted on ${formatNumber(fit.train_rows, 'en')} of the ${formatNumber(fit.split.train.n, 'en')} training rows.`,
                es: `Los modelos de esta variante se ajustaron con ${formatNumber(fit.train_rows, 'es')} de las ${formatNumber(fit.split.train.n, 'es')} filas de entrenamiento.`,
              },
              lang,
            )}
          </p>
        ) : null}
        <p className="ct-note">
          {Object.entries(m.contract)
            .map(([src, c]) =>
              pick(
                {
                  // the rules and the columns by name, never their ids (R3 c01 B1, B2, c02 B1, B2)
                  en: `${m.source_details[src]?.name ?? src}: ${formatNumber(c.counts.input, 'en')} records, ${formatNumber(c.counts.accepted, 'en')} accepted, ${formatNumber(c.counts.rejected, 'en')} rejected, ${formatNumber(c.counts.flagged, 'en')} flags (${Object.entries(c.by_rule.flagged).map(([r, n]) => `${formatNumber(n, 'en')} for ${CONTRACT_RULES[r]?.en ?? r}`).join('; ') || 'none'}); not used: ${c.ignored_columns.map((k) => inputName(k)?.en ?? k).join(', ') || 'nothing'}.`,
                  es: `${m.source_details[src]?.name ?? src}: ${formatNumber(c.counts.input, 'es')} registros, ${formatNumber(c.counts.accepted, 'es')} aceptados, ${formatNumber(c.counts.rejected, 'es')} rechazados, ${formatNumber(c.counts.flagged, 'es')} marcas (${Object.entries(c.by_rule.flagged).map(([r, n]) => `${formatNumber(n, 'es')} por ${CONTRACT_RULES[r]?.es ?? r}`).join('; ') || 'ninguna'}); sin usar: ${c.ignored_columns.map((k) => inputName(k)?.es ?? k).join(', ') || 'nada'}.`,
                },
                lang,
              ),
            )
            .join(' ')}
        </p>
      </PlotCard>
      <PlotCard title={{ en: 'Write-up', es: 'Desarrollo' }} lane={REPLAY} provenance={provenanceOf(sel.data.variant.provenance.truth_status)} dataKey={stateKey}>
        <div className="ct-prose">{WriteUp ? WriteUp() : null}</div>
      </PlotCard>
    </div>
  );
}
