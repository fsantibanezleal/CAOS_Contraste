// The Methodology section on model governance (U15): how the inventory tiers a model (materiality by complexity), how the
// findings register maps the product's severity to the ECB F scale, how the overall opinion and its recommendation follow
// from the open findings, and the model risk appetite. Transcribed from dossier 06 (B.3 l.553-575, B.6 l.604-612, B.7
// l.614-628, I.3 l.1219-1237, I.6 l.1261-1277, UNVERIFIED item 30 l.1321-1322) and the U15 research addendum (D6), where
// SR 26-2, PRA SS1/23, OSFI E-23 and the ECB reporting instructions were read at their primary sources on 2026-10-20. Every
// tier count, band, deadline, frequency, threshold and the opinion rule is a stated convention of Contraste, said to be one
// wherever it appears. The recommendation is the rule's output on the evidence; Contraste approves no model (SDD non-goal 1).
import { Callout, Cite, DocSection, Figure, useShellLang } from '@fasl-work/caos-app-shell';
import { Equation, P, T, useT } from '../../content/bi';
import { tierColor } from '../../workbench/governance/DependencyMap';
import { RULE_OUTPUT_LABEL, TIER_RULE_TEX, tierOf } from '../../workbench/governance/model';
import type { MethodologySection } from '../methodologyRegistry';

/** The tier rule as a grid: the tier each (M, C) pair gives, from the same function the inventory is checked against. */
function TierRuleFigure() {
  const t = useT();
  const W = 360;
  const H = 230;
  const L = 70;
  const T0 = 40;
  const cw = (W - L - 8) / 4;
  const ch = 44;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('The 4 by 4 tier matrix: the tier of each pair of materiality and complexity scores', 'La matriz de niveles de 4 por 4: el nivel de cada par de puntajes de materialidad y complejidad')} style={{ width: '100%', height: 'auto', maxWidth: 480 }}>
      <text x={L + 2 * cw} y={14} textAnchor="middle" fontSize={11} fill="var(--color-fg-subtle)">{t('Complexity C', 'Complejidad C')}</text>
      <text x={L - 8} y={T0 - 8} textAnchor="end" fontSize={11} fill="var(--color-fg-subtle)">M</text>
      {[1, 2, 3, 4].map((c) => (
        <text key={c} x={L + (c - 0.5) * cw} y={T0 - 8} textAnchor="middle" fontSize={11} fill="var(--color-fg)">{c}</text>
      ))}
      {[4, 3, 2, 1].map((m, r) => (
        <g key={m}>
          <text x={L - 8} y={T0 + (r + 0.5) * ch + 4} textAnchor="end" fontSize={11} fill="var(--color-fg)">{m}</text>
          {[1, 2, 3, 4].map((c) => {
            const tier = tierOf(m, c);
            return (
              <g key={c}>
                <rect x={L + (c - 1) * cw + 0.5} y={T0 + r * ch + 0.5} width={cw - 1} height={ch - 1} fill={tierColor(tier)} />
                <text x={L + (c - 0.5) * cw} y={T0 + (r + 0.5) * ch + 4} textAnchor="middle" fontSize={12} fontWeight={600} fill={tier >= 3 ? '#141414' : '#f4f4f4'}>{t(`Tier ${tier}`, `Nivel ${tier}`)}</text>
              </g>
            );
          })}
        </g>
      ))}
    </svg>
  );
}

function Body() {
  const t = useT();
  const lang = useShellLang();
  return (
    <>
      <DocSection area="method" kind="classical" title={{ en: 'Model governance: tiers, findings, opinion and appetite', es: 'Gobernanza de modelos: niveles, hallazgos, opinión y apetito' }} refs={['ss123', 'sr262', 'osfie23', 'ecbtrim', 'ecb2019', 'osfibackgrounder', 'osfie23letter']}>
        <h3 className="ct-sub">
          <T en="Model tiering: materiality by complexity" es="Clasificación de modelos: materialidad por complejidad" />
        </h3>
        <P
          en={<>The PRA expects a firm-wide tiering of models by a materiality rating and a complexity rating, and reviews the tiering approach and its individual assignments <Cite id="ss123" />. The US guidance of 2026 sets model materiality from exposure and purpose and prescribes neither a number of tiers nor a rating scale <Cite id="sr262" />, and OSFI ties the frequency and intensity of review to an inherent model risk rating that reflects vulnerabilities and materiality <Cite id="osfie23" />. None of them fixes a formula, so the rubric below is a convention of Contraste, transparent and configurable (dossier 06, B.3, l.553-575).</>}
          es={<>La PRA espera una clasificación de modelos de toda la entidad por una calificación de materialidad y una de complejidad, y revisa el enfoque de clasificación y sus asignaciones individuales <Cite id="ss123" />. La guía estadounidense de 2026 fija la materialidad de un modelo desde la exposición y el propósito y no prescribe ni un número de niveles ni una escala de calificación <Cite id="sr262" />, y OSFI ata la frecuencia e intensidad de la revisión a una calificación de riesgo inherente del modelo que refleja vulnerabilidades y materialidad <Cite id="osfie23" />. Ninguna fija una fórmula, así que la rúbrica de abajo es una convención de Contraste, transparente y configurable (dossier 06, B.3, l.553-575).</>}
        />
        <P
          en="Materiality M is the maximum of three scores from 1 to 4: the exposure band (the share of the stated balance, at cut points that are a convention), the regulatory use (graded: 4 where the output is itself the reported or binding figure, 3 where it is a parameter or a back-test that feeds one, 2 for compliance monitoring, 1 for none), and the decision criticality. Complexity C is the mean of the factor scores, rounded half up (methodology, data, explainability, implementation and dependency depth). The tier is read from the matrix of M and C. An override of a computed tier is never silent: it needs a recorded rationale and an approver."
          es="La materialidad M es el máximo de tres puntajes de 1 a 4: la banda de exposición (la fracción del saldo declarado, con puntos de corte que son una convención), el uso regulatorio (graduado: 4 donde el resultado es la cifra reportada o vinculante, 3 donde es un parámetro o una prueba retrospectiva que alimenta una, 2 para el monitoreo de cumplimiento, 1 ninguno) y la criticidad de la decisión. La complejidad C es la media de los puntajes de los factores, redondeada hacia arriba en la mitad (metodología, datos, explicabilidad, implementación y profundidad de dependencias). El nivel se lee de la matriz de M y C. Una excepción al nivel calculado nunca es silenciosa: exige una justificación registrada y un aprobador."
        />
        <Equation
          tex={TIER_RULE_TEX}
          caption={<T en={<>The tier rule: M the materiality and C the complexity score, each from 1 to 4; Tier 1 is the most material. It is the 4 by 4 matrix of dossier 06 B.3, a convention of Contraste.</>} es={<>La regla de nivel: M la materialidad y C el puntaje de complejidad, cada uno de 1 a 4; el Nivel 1 es el más material. Es la matriz de 4 por 4 del dossier 06 B.3, una convención de Contraste.</>} />}
        />
        <Figure caption={t('The tier of each cell of the matrix under the stated rule: materiality M down the side, complexity C along the top.', 'El nivel de cada celda de la matriz bajo la regla declarada: materialidad M en el costado, complejidad C arriba.')}>
          <TierRuleFigure />
        </Figure>
        <P
          en="The rubric rests on two choices, so the inventory shows the tier under four readings: the regulatory use literal or graded, and the complexity as the mean or as the maximum of its factors. The adopted reading is graded and mean; the other three are shown beside it so that a reader sees how much a tier rests on the rubric. The rubric has a blind spot: it counts feeders in complexity and has no term for fan-out in materiality, so the validator of the validator keeps the tier its own inputs give. The inventory records it as a finding of its own."
          es="La rúbrica descansa en dos decisiones, por lo que el inventario muestra el nivel bajo cuatro lecturas: el uso regulatorio literal o graduado, y la complejidad como la media o como el máximo de sus factores. La lectura adoptada es graduado y media; las otras tres se muestran al lado para que el lector vea cuánto descansa un nivel en la rúbrica. La rúbrica tiene un punto ciego: cuenta los alimentadores en la complejidad y no tiene un término de dependencia en la materialidad, así que el validador del validador conserva el nivel que dan sus propios insumos. El inventario lo registra como un hallazgo propio."
        />
        <h3 className="ct-sub">
          <T en="Findings: severity, status and deadlines" es="Hallazgos: severidad, estado y plazos" />
        </h3>
        <P
          en={<>The ECB scores supervisory findings on a scale from F1, a low impact, to F4, a very high one <Cite id="ecbtrim" />. The product keeps its own direction, S1 critical to S4 minor, because 637 finding rows in 21 cases and their views already use it, and shows beside every severity its ECB F equivalent: S1 is F4, S2 is F3, S3 is F2 and S4 is F1. The direction of dossier 06 (S1 low) is a convention, not a requirement, so the mapping is stated rather than the direction changed.</>}
          es={<>El BCE califica los hallazgos supervisores en una escala de F1, un impacto bajo, a F4, uno muy alto <Cite id="ecbtrim" />. El producto conserva su propia dirección, S1 crítico a S4 menor, porque 637 filas de hallazgos en 21 casos y sus vistas ya la usan, y muestra junto a cada severidad su equivalente F del BCE: S1 es F4, S2 es F3, S3 es F2 y S4 es F1. La dirección del dossier 06 (S1 bajo) es una convención, no un requisito, así que se declara la correspondencia en vez de cambiar la dirección.</>}
        />
        <P
          en="The register adds what the validation workflow needs and the case documents lack: the quantitative anchor (the statistic or metric of the cited test row, or an absence with its reason), the owner role, a due date counted from the raised date by a deadline table of severity by tier, the ageing and an overdue flag. The seven states (open, action plan agreed, in progress, submitted for closure, validated and closed, overdue, risk accepted) are those of the workflow; the product's three statuses map to them (open to open, accepted to risk accepted, closed to validated and closed). Every deadline is a convention: no regulatory source prescribes days."
          es="El registro agrega lo que el flujo de validación necesita y los documentos de los casos no tienen: el ancla cuantitativa (el estadístico o la métrica de la fila de prueba citada, o una ausencia con su razón), el rol responsable, una fecha de vencimiento contada desde la fecha de registro por una tabla de plazos de severidad por nivel, la antigüedad y una marca de vencido. Los siete estados (abierto, plan de acción acordado, en curso, enviado a cierre, validado y cerrado, vencido, riesgo aceptado) son los del flujo; los tres estados del producto se mapean a ellos (abierto a abierto, aceptado a riesgo aceptado, cerrado a validado y cerrado). Cada plazo es una convención: ninguna fuente regulatoria prescribe días."
        />
        <h3 className="ct-sub">
          <T en="The overall opinion, the recommendation and the model risk appetite" es="La opinión global, la recomendación y el apetito de riesgo de modelo" />
        </h3>
        <P
          en={<>The ECB reporting instructions grade a validation on four levels: adequate with no deficiencies, adequate with minor deficiencies, major deficiencies (an RWEA impact of at least 5 percent and below 10 percent) and severe deficiencies (at least 10 percent) <Cite id="ecb2019" />. Contraste computes the level of an entry from its open findings, those that are open or overdue and not risk accepted, by a rule that is a convention: level 1 with none, level 2 with S3 or S4 only, level 3 with any S2, level 4 with any S1. Where a finding's anchor is a share of RWEA, the ECB cut points can only raise the level, so a critical finding is never lowered by a small share.</>}
          es={<>Las instrucciones de reporte del BCE califican una validación en cuatro niveles: adecuada sin deficiencias, adecuada con deficiencias menores, deficiencias mayores (un impacto en RWEA de al menos 5 por ciento y menos de 10 por ciento) y deficiencias severas (al menos 10 por ciento) <Cite id="ecb2019" />. Contraste calcula el nivel de una entrada desde sus hallazgos abiertos, los que están abiertos o vencidos y no tienen el riesgo aceptado, con una regla que es una convención: nivel 1 sin ninguno, nivel 2 con solo S3 o S4, nivel 3 con algún S2, nivel 4 con algún S1. Donde el ancla de un hallazgo es una fracción de RWEA, los puntos de corte del BCE solo pueden subir el nivel, así que un hallazgo crítico nunca baja por una fracción pequeña.</>}
        />
        <Equation
          tex="L=\max\left(L_{\mathrm{sev}},\,L_{\mathrm{RWEA}}\right),\quad L_{\mathrm{sev}}=\begin{cases}4&\exists\,S1\\3&\exists\,S2\\2&\exists\,S3\ \text{or}\ S4\\1&\text{none}\end{cases},\quad L_{\mathrm{RWEA}}=\begin{cases}4&s\ge 0.10\\3&0.05\le s<0.10\\\text{none}&s<0.05\end{cases}"
          caption={<T en={<>The opinion level L of an entry: L<sub>sev</sub> from the most severe open finding, L_RWEA from the share s of RWEA of a finding's anchor where it has one. The rule is a convention of Contraste (dossier 06 UNVERIFIED item 30); the 5 and 10 percent cut points are the ECB's.</>} es={<>El nivel de opinión L de una entrada: L<sub>sev</sub> desde el hallazgo abierto más severo, L_RWEA desde la fracción s de RWEA del ancla de un hallazgo donde la tiene. La regla es una convención de Contraste (dossier 06 SIN VERIFICAR punto 30); los puntos de corte de 5 y 10 por ciento son los del BCE.</>} />}
        />
        <P
          en="The recommendation is the rule's text for the level: approve, approve with conditions, or remediate before use. It is shown with its label, and the label is part of the recommendation:"
          es="La recomendación es el texto de la regla para el nivel: aprobar, aprobar con condiciones o remediar antes del uso. Se muestra con su rótulo, y el rótulo es parte de la recomendación:"
        />
        <blockquote>
          <em>{RULE_OUTPUT_LABEL[lang]}</em>
        </blockquote>
        <P
          en={<>The model risk appetite is stated as seven metrics (dossier 06, B.6): the share of Tier 1 entries validated on time, the open high-severity findings, the overdue remediation, the entries used under exception, the entries in breach of their thresholds, the PMA magnitude relative to the model output, and the share of entries with an owner role and a complete record <Cite id="ss123" />. The count metrics count distinct findings, which is what the appetite states, and the register rows behind them are shown beside. Each light follows a threshold that is a convention.</>}
          es={<>El apetito de riesgo de modelo se declara como siete métricas (dossier 06, B.6): la proporción de entradas de Nivel 1 validadas a tiempo, los hallazgos abiertos de severidad alta, la remediación vencida, las entradas usadas bajo excepción, las entradas que incumplen sus umbrales, la magnitud de PMA relativa al resultado del modelo, y la proporción de entradas con rol responsable y registro completo <Cite id="ss123" />. Las métricas de conteo cuentan hallazgos distintos, que es lo que el apetito declara, y las filas del registro detrás se muestran al lado. Cada luz sigue un umbral que es una convención.</>}
        />
        <h3 className="ct-sub">
          <T en="Sources, what is a convention and what is not verified" es="Fuentes, qué es una convención y qué no está verificado" />
        </h3>
        <P
          en={<>SR 26-2 was issued on 2026-04-17 and replaces SR 11-7; it sets no enforceable standards and leaves generative and agentic AI out of its scope <Cite id="sr262" />. The PRA statement SS1/23 was updated in April 2026 <Cite id="ss123" />. OSFI Guideline E-23 takes effect on 2027-05-01 <Cite id="osfie23letter" />, following, in OSFI's words, "an 18-month transition period" <Cite id="osfibackgrounder" />; pension plans are outside its scope. The inventory attributes follow the minimum fields of E-23 and the principles of SS1/23 <Cite id="osfie23" />.</>}
          es={<>SR 26-2 se emitió el 2026-04-17 y reemplaza a SR 11-7; no fija estándares exigibles y deja fuera de su alcance la IA generativa y agéntica <Cite id="sr262" />. La declaración SS1/23 de la PRA se actualizó en abril de 2026 <Cite id="ss123" />. La Guía E-23 de OSFI entra en vigor el 2027-05-01 <Cite id="osfie23letter" />, tras, en palabras de OSFI, "an 18-month transition period" (un período de transición de 18 meses) <Cite id="osfibackgrounder" />; los planes de pensiones quedan fuera de su alcance. Los atributos del inventario siguen los campos mínimos de E-23 y los principios de SS1/23 <Cite id="osfie23" />.</>}
        />
        <Callout variant="honest" title={t('What is a convention, what is unverified and what these views are not', 'Qué es una convención, qué no está verificado y qué no son estas vistas')}>
          <T
            en={<>Every tier count, exposure band, deadline, revalidation frequency, appetite threshold and the opinion rule are conventions of Contraste, proposals and not requirements. Four items stay unverified: the April 2026 text of SS1/23 was read for the inventory and tiering principles but not compared line by line with the 2023 text; that OSFI E-23 (2027) rescinds the 2017 guideline is stated by the dossier and by none of the OSFI pages read; the reading of Annex III 5(b) of the EU AI Act rests on a reproduction of the text; and a later ECB reporting instruction than 2019 is not ruled out, nor is the final form of the EBA draft standard on material model changes. The inventory is Contraste's own and approves nothing: a passed test is evidence, not compliance, the opinion is the output of a rule, and the recommendation is {RULE_OUTPUT_LABEL.en}.</>}
            es={<>Cada conteo por nivel, banda de exposición, plazo, frecuencia de revalidación, umbral de apetito y la regla de opinión son convenciones de Contraste, propuestas y no requisitos. Cuatro puntos siguen sin verificar: el texto de abril de 2026 de SS1/23 se leyó para los principios de inventario y clasificación pero no se comparó línea a línea con el de 2023; que OSFI E-23 (2027) derogue la guía de 2017 lo afirma el dossier y ninguna de las páginas de OSFI leídas; la lectura del Anexo III 5(b) de la Ley de IA de la UE descansa en una reproducción del texto; y no se descarta una instrucción de reporte del BCE posterior a 2019, ni la forma final del borrador de norma de la EBA sobre cambios materiales de modelos. El inventario es el propio de Contraste y no aprueba nada: una prueba aprobada es evidencia, no cumplimiento, la opinión es el resultado de una regla, y la recomendación es {RULE_OUTPUT_LABEL.es}.</>}
          />
        </Callout>
      </DocSection>
    </>
  );
}

export const methodologySection: MethodologySection = {
  id: 'governance',
  group: 'models',
  order: 300,
  title: { en: 'Model governance', es: 'Gobernanza de modelos' },
  Body,
};
