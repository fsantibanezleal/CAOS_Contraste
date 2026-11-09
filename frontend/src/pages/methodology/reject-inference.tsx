// The Methodology section on reject inference (case C01): the treatments of the applicants a legacy policy turned away,
// measured on a sample whose rejected outcomes are known. Transcribed from the C01 case page (content/cases/C01.tsx, its
// reject-inference section, whose numbers are the committed German Credit twin, data/derived/C01/german-twin.json, block
// reject_inference, 100 repetitions), from the reject-inference section of notebook 06 of the credit-scoring topic
// (notebooks/en/02-credit-scoring/06-challengers-against-the-scorecard.ipynb, whose population drawn in the notebook has a known
// logistic law, 1,000 applicants, 40 repetitions per policy, seed 20261030), from the pipeline module that runs it
// (data-pipeline/pipeline/cases/c01_reject.py: the rung definitions, the policy, the reduction) and from the ladder of the SDD
// (docs/design/SDD.md, the reject-inference row). Every display equation carries a caption that defines its symbols. The second
// equation is the legacy policy of that module (legacy_acceptance) and the figure draws the bias table beside it. The registry
// mounts it as one tab of the models group.
import { Callout, Cite, DocSection, Figure } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { Equation, P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';
import { GroupedBars } from '../MethodFigures';

const NB = 'https://github.com/fsantibanezleal/CAOS_Contraste/blob/main/notebooks';
const NB_PATH = '02-credit-scoring/06-challengers-against-the-scorecard.ipynb';

/** A small results table: a head row and the rows, the first column text and the others numbers. */
function Tbl({ head, rows, id }: { head: ReactNode[]; rows: ReactNode[][]; id: string }) {
  return (
    <table className="caos-table ct-wrap-head" data-table={id}>
      <thead>
        <tr>
          {head.map((h, i) => (
            <th key={i} className={i === 0 ? 'caos-col-text' : undefined}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {r.map((c, j) => (
              <td key={j} className={j === 0 ? 'caos-col-text' : undefined}>{c}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Body() {
  const t = useT();
  return (
    <DocSection
      area="method"
      kind="classical"
      title={{ en: 'Reject inference on a known rejected population', es: 'Inferencia de rechazados sobre una población rechazada conocida' }}
      refs={['banasikcrook2007', 'handhenley1993', 'crookbanasik2004', 'siddiqi2017']}
    >
      <P
        en={<>An application scorecard learns from the applicants a legacy policy accepted, never from those it turned away, and it is then used on everyone who applies: its sample is selected. Reject inference is the family of methods that tries to repair that with the rejected applicants, whose outcomes are never observed. Whether it works cannot be learned from a lender&apos;s book, where those outcomes do not exist, so the proposed method is a test bench: a fully labelled population stands for everyone who applies, a legacy policy is simulated on it, the outcomes of the rejected are hidden, each treatment is fitted on what a lender would have, and each is scored on a held-out accept-all population that no policy screened. One regularised logistic regression is the learner of every treatment, so only the treatment of the rejected differs.</>}
        es={<>Una tarjeta de puntuación de solicitudes aprende de los solicitantes que una política heredada aceptó, nunca de los que rechazó, y luego se usa con todos los que postulan: su muestra está seleccionada. La inferencia de rechazados es la familia de métodos que intenta repararlo con los solicitantes rechazados, cuyos resultados nunca se observan. Si funciona no puede aprenderse de la cartera de un prestamista, donde esos resultados no existen, así que el método propuesto es un banco de pruebas: una población totalmente etiquetada hace de todos los que postulan, se simula sobre ella una política heredada, se ocultan los resultados de los rechazados, cada tratamiento se ajusta con lo que tendría un prestamista y cada uno se puntúa con una población de aceptación total reservada que ninguna política filtró. Una regresión logística regularizada es el aprendiz de todos los tratamientos, así que solo cambia el tratamiento de los rechazados.</>}
      />
      <P
        en={<>The treatments are the accepted-only model (the bias to repair); augmentation by the inverse acceptance probability <Cite id="banasikcrook2007" />, where an acceptance model is fitted on every applicant and each accepted applicant weighs 1/p with p floored at 0.05; a hard cut-off, where the accepted-only model scores the rejected and the riskiest are labelled bad in the share the model itself expects; parcelling, where the rejected are split into ten score bands and given random outcomes at the bad rate of the accepted of their band <Cite id="siddiqi2017" />; parcelling with a prudence factor of 2, which assumes the rejected twice as bad as the accepted of their band, capped at 1; and fuzzy augmentation, where each rejected applicant enters twice, as a bad weighing p and as a good weighing 1 - p, p the accepted-only PD. An oracle fitted on every outcome is the reference no lender can fit.</>}
        es={<>Los tratamientos son el modelo de solo aceptados (el sesgo por reparar); la aumentación por el inverso de la probabilidad de aceptación <Cite id="banasikcrook2007" />, donde se ajusta un modelo de aceptación con todos los solicitantes y cada aceptado pesa 1/p con p acotado abajo en 0,05; un corte duro, donde el modelo de solo aceptados puntúa a los rechazados y los más riesgosos se etiquetan malos en la fracción que el propio modelo espera; la parcelación, donde los rechazados se reparten en diez tramos de puntaje y reciben resultados al azar con la tasa de malos de los aceptados de su tramo <Cite id="siddiqi2017" />; la parcelación con factor de prudencia 2, que supone a los rechazados el doble de malos que los aceptados de su tramo, con tope en 1; y la aumentación difusa, donde cada rechazado entra dos veces, como malo con peso p y como bueno con peso 1 - p, con p la PD del modelo de solo aceptados. Un oráculo ajustado con todos los resultados es la referencia que ningún prestamista puede ajustar.</>}
      />
      <Equation
        tex={String.raw`b_r = \overline{\hat p}_r - \overline{y}, \qquad R_r = 1 - \frac{|\,b_r\,|}{|\,b_0\,|}, \qquad w_i = \frac{1}{\max(p_i,\ 0.05)}, \qquad \tilde y_j \sim \mathrm{Bernoulli}\big(\min(1,\ f\,\pi_{g(j)})\big)`}
        caption={<T en={<>The measures and two of the treatments. On the accept-all population, b<sub>r</sub> is the bias of treatment r, the mean predicted default rate of r minus the observed default rate ȳ, and b<sub>0</sub> that of the accepted-only model; R<sub>r</sub> is the reduction of the bias, 1 when r removes it, 0 when it does nothing and negative when it makes it larger, reported with a percentile interval over the repetitions. Augmentation: w<sub>i</sub> the weight of accepted applicant i and p<sub>i</sub> its acceptance probability. Parcelling: ỹ<sub>j</sub> the outcome given to rejected applicant j, π<sub>g(j)</sub> the bad rate of the accepted in the score band g(j) of j (the model&apos;s mean PD where a band has fewer than ten accepted applicants), and f the prudence factor (1 for plain parcelling, 2 for the prudent one).</>} es={<>Las medidas y dos de los tratamientos. Sobre la población de aceptación total, b<sub>r</sub> es el sesgo del tratamiento r, la tasa de incumplimiento predicha media de r menos la tasa de incumplimiento observada ȳ, y b<sub>0</sub> el del modelo de solo aceptados; R<sub>r</sub> es la reducción del sesgo, 1 cuando r lo elimina, 0 cuando no hace nada y negativa cuando lo agranda, informada con un intervalo percentil sobre las repeticiones. Aumentación: w<sub>i</sub> el peso del aceptado i y p<sub>i</sub> su probabilidad de aceptación. Parcelación: ỹ<sub>j</sub> el resultado dado al rechazado j, π<sub>g(j)</sub> la tasa de malos de los aceptados en el tramo de puntaje g(j) de j (la PD media del modelo donde un tramo tiene menos de diez aceptados), y f el factor de prudencia (1 para la parcelación simple, 2 para la prudente).</>} />}
      />
      <Equation
        tex={String.raw`u_i = z_i + \kappa\,\frac{y_i - \bar y}{s_y} + \varepsilon_i, \qquad \varepsilon_i \sim \mathcal{N}(0,1), \qquad a_i = \mathbb{1}\{\mathrm{rank}(u_i) \le \lfloor 0.6\,n \rceil\}`}
        caption={<T en={<>The legacy policy simulated on the labelled population: z<sub>i</sub> the standardised logit of a model fitted on every development outcome, the policy&apos;s view of the inputs; y<sub>i</sub> the outcome of applicant i (1 for a default) with mean ȳ and standard deviation s<sub>y</sub>, so the second term is the underwriter&apos;s private signal of strength κ (0, 0.25, 0.5 or 1); ε<sub>i</sub> the noise, drawn first so two policies with one seed share it; a<sub>i</sub> equal to 1 when the applicant is among the n·0.6 lowest scores u<sub>i</sub>, rounded to the nearest whole number, that is, the best 60% are accepted (<Ref>data-pipeline/pipeline/cases/c01_reject.py</Ref>, <Ref>legacy_acceptance</Ref>).</>} es={<>La política heredada simulada sobre la población etiquetada: z<sub>i</sub> el logit estandarizado de un modelo ajustado con todos los resultados de desarrollo, la visión de la política sobre las entradas; y<sub>i</sub> el resultado del solicitante i (1 si incumple) con media ȳ y desviación estándar s<sub>y</sub>, de modo que el segundo término es la señal privada del analista de intensidad κ (0; 0,25; 0,5 o 1); ε<sub>i</sub> el ruido, sorteado primero para que dos políticas con una semilla lo compartan; a<sub>i</sub> igual a 1 cuando el solicitante está entre los n·0,6 puntajes u<sub>i</sub> más bajos, redondeado al entero más cercano, es decir, se acepta al mejor 60 % (<Ref>data-pipeline/pipeline/cases/c01_reject.py</Ref>, <Ref>legacy_acceptance</Ref>).</>} />}
      />
      <h3>{t('What it is compared against and what it measured', 'Con qué se compara y qué midió')}</h3>
      <P
        en={<>The legacy policy accepts the best 60% on a score that adds the underwriter&apos;s private view of the outcome, of strength κ: κ = 0 is a policy blind to the outcome once the inputs are known (the control), and κ = 0.25, 0.5 and 1 add a judgement the model does not see, the case Hand and Henley <Cite id="handhenley1993" /> and Crook and Banasik <Cite id="crookbanasik2004" /> say no reject inference can repair. The hypotheses were written before the run and are judged on κ = 0.5: the accepted-only model understates the default rate (H1); the best treatment cuts that bias by at least 25% (H2); no treatment gains more than 0.01 of AUC (H3). The notebook draws its own population of 1,000 applicants with a known logistic law and 40 repetitions per policy (seed 20261030); the product&apos;s committed measurement is the 1,000 applicants of the German Credit data, whose every outcome is known, with 100 repetitions.</>}
        es={<>La política heredada acepta al mejor 60 % con un puntaje que suma la visión privada del analista sobre el resultado, de intensidad κ: κ = 0 es una política ciega al resultado una vez conocidas las entradas (el control), y κ = 0,25; 0,5 y 1 suman un juicio que el modelo no ve, el caso que Hand y Henley <Cite id="handhenley1993" /> y Crook y Banasik <Cite id="crookbanasik2004" /> dicen que ninguna inferencia de rechazados puede reparar. Las hipótesis se escribieron antes de la corrida y se juzgan con κ = 0,5: el modelo de solo aceptados subestima la tasa de incumplimiento (H1); el mejor tratamiento reduce ese sesgo en al menos 25 % (H2); ningún tratamiento gana más de 0,01 de AUC (H3). El notebook sortea su propia población de 1.000 solicitantes con una ley logística conocida y 40 repeticiones por política (semilla 20261030); la medición versionada del producto son los 1.000 solicitantes de los datos German Credit, cuyos resultados se conocen todos, con 100 repeticiones.</>}
      />
      <Tbl
        id="reject-bias"
        head={[t('Bias of the predicted default rate, points (drawn population)', 'Sesgo de la tasa de incumplimiento predicha, puntos (población sorteada)'), t('κ = 0 (blind)', 'κ = 0 (ciega)'), t('κ = 0.25', 'κ = 0,25'), t('κ = 0.5', 'κ = 0,5'), 'κ = 1']}
        rows={[
          [t('Oracle', 'Oráculo'), t('-0.09', '-0,09'), t('-0.09', '-0,09'), t('-0.09', '-0,09'), t('-0.09', '-0,09')],
          [t('Accepted only', 'Solo aceptados'), t('-0.76', '-0,76'), t('-7.65', '-7,65'), t('-13.00', '-13,00'), t('-17.94', '-17,94')],
          [t('Parcelling with prudence factor 2', 'Parcelación con factor de prudencia 2'), t('+9.69', '+9,69'), t('-2.10', '-2,10'), t('-10.66', '-10,66'), t('-17.84', '-17,84')],
          [t('Default rate of the accepted / the rejected', 'Tasa de incumplimiento de los aceptados / los rechazados'), t('0.135 / 0.272', '0,135 / 0,272'), t('0.094 / 0.334', '0,094 / 0,334'), t('0.057 / 0.389', '0,057 / 0,389'), t('0.012 / 0.457', '0,012 / 0,457')],
        ]}
      />
      <P
        en={<>The default rate of the population is 0.190 under every policy, as it should be: the policy changes who is accepted, not who defaults. With the private signal the accepted book shrinks to a population with almost no defaulters, and the accepted-only model carries that rate to everyone. Under the moderate policy on the drawn population the reductions of the bias are -0.010 for augmentation, +0.006 for the hard cut-off, -0.001 for parcelling, 0.000 for fuzzy augmentation and +0.180 (interval 0.150 to 0.211) for prudent parcelling, whose AUC against the accepted-only model is +0.0513 while the others change it by -0.0441, -0.0222, -0.0201 and 0.0000. On the German Credit applicants the moderate policy gives an accepted book with 8.9% defaulters against 30% in the population, and the accepted-only model understates the default rate by 17.2 points (95% interval 16.7 to 17.7); augmentation, the hard cut-off, parcelling and fuzzy augmentation cut that bias by 0% to 2% and rank worse than accepted only, and prudent parcelling cuts it by 44% (41% to 48%) with +0.021 of AUC. H1 holds in both; H2 holds for prudent parcelling alone on the German data (0.443) and does not hold on the drawn population (0.180); H3 does not hold in either, since the gain of prudent parcelling is above 0.01 of AUC.</>}
        es={<>La tasa de incumplimiento de la población es 0,190 bajo toda política, como debe ser: la política cambia quién es aceptado, no quién incumple. Con la señal privada la cartera aceptada se reduce a una población casi sin incumplidores, y el modelo de solo aceptados lleva esa tasa a todos. Bajo la política moderada en la población sorteada las reducciones del sesgo son -0,010 para la aumentación, +0,006 para el corte duro, -0,001 para la parcelación, 0,000 para la aumentación difusa y +0,180 (intervalo de 0,150 a 0,211) para la parcelación prudente, cuyo AUC frente al modelo de solo aceptados es +0,0513 mientras los demás lo cambian en -0,0441, -0,0222, -0,0201 y 0,0000. En los solicitantes de German Credit la política moderada da una cartera aceptada con 8,9 % de incumplidores contra 30 % en la población, y el modelo de solo aceptados subestima la tasa de incumplimiento en 17,2 puntos (intervalo de 95 % de 16,7 a 17,7); la aumentación, el corte duro, la parcelación y la aumentación difusa reducen ese sesgo entre 0 % y 2 % y ordenan peor que solo aceptados, y la parcelación prudente lo reduce en 44 % (41 % a 48 %) con +0,021 de AUC. H1 se cumple en ambas; H2 se cumple solo para la parcelación prudente en los datos alemanes (0,443) y no se cumple en la población sorteada (0,180); H3 no se cumple en ninguna, pues la ganancia de la parcelación prudente supera 0,01 de AUC.</>}
      />
      <Figure
        caption={t(
          'The bias of the predicted default rate, in points, on the accept-all population drawn in the notebook, by strength of the private signal of the underwriter (the table above): the accepted-only model understates the rate more as the signal grows, from 0.76 to 17.94 points; prudent parcelling cuts the understatement at weak and moderate signals, overstates the rate by 9.69 points under the blind policy and barely moves it at the strongest signal.',
          'El sesgo de la tasa de incumplimiento predicha, en puntos, en la población sin rechazo sorteada en el notebook, según la intensidad de la señal privada del analista (la tabla de arriba): el modelo de solo aceptados subestima la tasa más cuanto mayor es la señal, de 0,76 a 17,94 puntos; la parcelación prudente reduce la subestimación con señales débiles y moderadas, sobrestima la tasa en 9,69 puntos con la política ciega y casi no la mueve con la señal más fuerte.',
        )}
      >
        <GroupedBars
          groups={[
            { en: 'κ = 0|(blind)', es: 'κ = 0|(ciega)' },
            { en: 'κ = 0.25', es: 'κ = 0,25' },
            { en: 'κ = 0.5', es: 'κ = 0,5' },
            { en: 'κ = 1', es: 'κ = 1' },
          ]}
          series={[
            { id: 'oracle', label: { en: 'Oracle', es: 'Oráculo' }, token: '--color-good', values: [-0.09, -0.09, -0.09, -0.09] },
            { id: 'accepted-only', label: { en: 'Accepted only', es: 'Solo aceptados' }, token: '--color-accent', values: [-0.76, -7.65, -13, -17.94] },
            { id: 'parcelling-prudent', label: { en: 'Prudent parcelling', es: 'Parcelación prudente' }, token: '--color-magenta', values: [9.69, -2.1, -10.66, -17.84] },
          ]}
          axis={{ min: -20, max: 20, decimals: 2, tickDecimals: 0, title: { en: 'Bias, points', es: 'Sesgo, puntos' } }}
          label={{ en: 'Grouped bars of the bias of the predicted default rate of the oracle, the accepted-only model and prudent parcelling at four strengths of the private signal', es: 'Barras agrupadas del sesgo de la tasa de incumplimiento predicha del oráculo, del modelo de solo aceptados y de la parcelación prudente en cuatro intensidades de la señal privada' }}
        />
      </Figure>
      <h3>{t('Where it fails', 'Dónde falla')}</h3>
      <Callout variant="honest" title={t('Reject inference repairs a selection only through an assumption about the rejected', 'La inferencia de rechazados repara una selección solo mediante un supuesto sobre los rechazados')}>
        <T
          en={<>Augmentation, the hard cut-off, plain parcelling and fuzzy augmentation lie on the accepted-only line: each infers the outcomes of the rejected from the accepted-only model itself, so it reproduces that model&apos;s bias; they assume the policy looked at the inputs alone. Only prudent parcelling moves away, because the factor of 2 is an assumption about the rejected that the data do not contain, and it pays for it. Under the blind policy it overstates the default rate by 9.69 points on the drawn population, where the accepted-only model was off by 0.76; on the German data its reduction of the bias is -6.629 under the blind policy (the bias becomes several times larger), +0.867 under the weak one, +0.443 under the moderate one and +0.064 under the strong one, which is the 6% a strong private signal allows it to recover. At the strong policy the drawn population gives -17.84 points against -17.94 for accepted only. The verdict therefore depends on the prudence factor being right, which a lender cannot check without the outcomes of the rejected, the point Hand and Henley made. Only a sample that accepts everyone says which world the book is in. The population is a simulation on a known law and on the German applicants, not a lender&apos;s book, and the accepted book at the strong policy is almost free of defaulters, a limit case no lender has.</>}
          es={<>La aumentación, el corte duro, la parcelación simple y la aumentación difusa quedan sobre la línea de solo aceptados: cada una infiere los resultados de los rechazados con el propio modelo de solo aceptados, así que reproduce el sesgo de ese modelo; suponen que la política miró solo las entradas. Solo la parcelación prudente se aleja, porque el factor 2 es un supuesto sobre los rechazados que los datos no contienen, y lo paga. Bajo la política ciega sobrestima la tasa de incumplimiento en 9,69 puntos en la población sorteada, donde el modelo de solo aceptados erraba en 0,76; en los datos alemanes su reducción del sesgo es -6,629 bajo la política ciega (el sesgo se vuelve varias veces mayor), +0,867 bajo la débil, +0,443 bajo la moderada y +0,064 bajo la fuerte, que es el 6 % que una señal privada fuerte le permite recuperar. Con la política fuerte la población sorteada da -17,84 puntos contra -17,94 de solo aceptados. El veredicto depende entonces de que el factor de prudencia sea el correcto, lo que un prestamista no puede verificar sin los resultados de los rechazados, el punto que hicieron Hand y Henley. Solo una muestra que acepta a todos dice en qué mundo está la cartera. La población es una simulación con una ley conocida y con los solicitantes alemanes, no la cartera de un prestamista, y la cartera aceptada con la política fuerte está casi libre de incumplidores, un caso límite que ningún prestamista tiene.</>}
        />
      </Callout>
      <P
        en={<>The notebook that runs this method on the product&apos;s data, in the reject-inference section of the challengers lesson (the drawn population, the four policies, the rungs, the three hypotheses and the German Credit result): <a href={`${NB}/en/${NB_PATH}`}><code>notebooks/en/{NB_PATH}</code></a>. The case page of C01 carries the committed result, and the ladder of the design document lists the method as its own row with the bias of the accepted-only model and each treatment&apos;s reduction, with its interval, as the check (<Ref>tests/test_c01.py</Ref>).</>}
        es={<>El notebook que corre este método con los datos del producto, en la sección de inferencia de rechazados de la lección de los retadores (la población sorteada, las cuatro políticas, los tratamientos, las tres hipótesis y el resultado de German Credit): <a href={`${NB}/es/${NB_PATH}`}><code>notebooks/es/{NB_PATH}</code></a>. La página del caso C01 lleva el resultado versionado, y la escalera del documento de diseño lista el método como una fila propia, con el sesgo del modelo de solo aceptados y la reducción de cada tratamiento, con su intervalo, como verificación (<Ref>tests/test_c01.py</Ref>).</>}
      />
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'reject-inference',
  group: 'models',
  order: 400,
  title: { en: 'Reject inference', es: 'Inferencia de rechazados' },
  Body,
};
