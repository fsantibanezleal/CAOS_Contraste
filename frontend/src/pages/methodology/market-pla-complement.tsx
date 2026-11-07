// The Methodology section on the scale-and-level complement to the P&L attribution test of the FRTB (case C13). Transcribed
// from the engine page docs/market/09_pla-complement.md of riskvalidation 1.1.0 (the statistics, the calibration of the
// decision, the evaluation and its limits) and from notebook 08 of the market-risk topic
// (notebooks/en/07-market-risk/08-a-scale-and-level-complement-to-the-pla-test.ipynb), whose numbers are the notebook's printed
// outputs; the per-variant table reads the committed C13 documents (data/derived/C13/<variant>.json, block pla_complement), which
// carry the product's measurement on 1,000 replications per variant. Every display equation carries a caption that defines its
// symbols. The figure draws the table of the variants beside it. The registry mounts it as one tab of the market group.
import { Callout, Cite, DocSection, Figure } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { Equation, P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';
import { GroupedBars } from '../MethodFigures';

const NB = 'https://github.com/fsantibanezleal/CAOS_Contraste/blob/main/notebooks';
const NB_PATH = '07-market-risk/08-a-scale-and-level-complement-to-the-pla-test.ipynb';

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
      title={{ en: 'A scale-and-level complement to the PLA test', es: 'Un complemento de escala y nivel para la prueba PLA' }}
      refs={['mar32', 'mincerzarnowitz1969', 'mackinnonwhite1985']}
    >
      <P
        en={<>The P&amp;L attribution test of the FRTB compares the desk&apos;s hypothetical P&amp;L (HPL) with the P&amp;L of the risk model (RTPL) by rank, with a Spearman correlation, and by distribution, with a Kolmogorov-Smirnov distance, and the desk is green when both are close <Cite id="mar32" />. Both are blind to when the scale moves. On the desk generator of case C13 (two correlated risk factors, a volatility that wanders and is known at the start of the day, a risk model whose truth is known), a model that applies the right shocks with a volatility 20 days old ranks the days almost as the desk does and, over a year, draws P&amp;L from almost the same distribution: in 1,000 replications none is amber or red. The proposed method adds three statistics on the same 250 days, and a decision calibrated on a simulated null. It is added beside the regulatory zone and never in place of it: the zone is returned unchanged next to the complement&apos;s own decision, and the complement has no regulatory standing.</>}
        es={<>La prueba de atribución de P&amp;L de la FRTB compara el P&amp;L hipotético de la mesa (HPL) con el P&amp;L del modelo de riesgo (RTPL) por rango, con una correlación de Spearman, y por distribución, con una distancia de Kolmogorov-Smirnov, y la mesa es verde cuando ambas están cerca <Cite id="mar32" />. Las dos son ciegas a cuándo se mueve la escala. En el generador de mesa del caso C13 (dos factores de riesgo correlacionados, una volatilidad que deambula y se conoce al inicio del día, un modelo de riesgo cuya verdad se conoce), un modelo que aplica los choques correctos con una volatilidad de 20 días ordena los días casi como la mesa y, en un año, saca P&amp;L de casi la misma distribución: en 1.000 réplicas ninguna es ámbar ni roja. El método propuesto agrega tres estadísticos sobre los mismos 250 días, y una decisión calibrada con una nula simulada. Se agrega junto a la zona regulatoria y nunca en su lugar: la zona se devuelve sin cambio al lado de la decisión propia del complemento, y el complemento no tiene valor regulatorio.</>}
      />
      <Equation
        tex={String.raw`\mathrm{HPL}_t = a + b\,\mathrm{RTPL}_t + e_t, \qquad W = (\hat\beta - (0,1))^{\top}\,\hat V_{\mathrm{HC3}}^{-1}\,(\hat\beta - (0,1))`}
        caption={<T en={<>The first statistic: the Mincer-Zarnowitz regression of the desk&apos;s HPL on the model&apos;s RTPL over the 250 days (t the day, a the intercept, b the slope, e<sub>t</sub> the residual) <Cite id="mincerzarnowitz1969" />, and the Wald statistic W of the joint hypothesis (a, b) = (0, 1), with β̂ = (â, b̂) the least-squares estimate and V̂<sub>HC3</sub> its HC3 covariance matrix, which holds when the P&amp;L volatility changes in time <Cite id="mackinnonwhite1985" />. W sees a model that is mis-scaled or shifted. The p-value returned is the asymptotic chi-square tail with 2 degrees of freedom, a reference only.</>} es={<>El primer estadístico: la regresión de Mincer-Zarnowitz del HPL de la mesa sobre el RTPL del modelo en los 250 días (t el día, a el intercepto, b la pendiente, e<sub>t</sub> el residuo) <Cite id="mincerzarnowitz1969" />, y el estadístico de Wald W de la hipótesis conjunta (a, b) = (0, 1), con β̂ = (â, b̂) la estimación de mínimos cuadrados y V̂<sub>HC3</sub> su matriz de covarianza HC3, que vale cuando la volatilidad del P&amp;L cambia en el tiempo <Cite id="mackinnonwhite1985" />. W ve un modelo mal escalado o desplazado. El valor p devuelto es la cola chi-cuadrado asintótica con 2 grados de libertad, solo una referencia.</>} />}
      />
      <Equation
        tex={String.raw`\rho_{\mathrm{abs}} = \rho_S\big(|\mathrm{HPL}_t|,\ |\mathrm{RTPL}_t|\big), \qquad \rho_{\mathrm{roll}} = \rho_S\big(m_t(|\mathrm{HPL}|),\ m_t(|\mathrm{RTPL}|)\big), \quad m_t(x) = \frac{1}{L}\sum_{s=0}^{L-1} x_{t-s}`}
        caption={<T en={<>The two Spearman statistics: ρ<sub>S</sub> the Spearman rank correlation, ρ<sub>abs</sub> that of the absolute values of HPL and RTPL, which sees a model that misreads the size of the day&apos;s move, and ρ<sub>roll</sub> that of their L-day rolling means m<sub>t</sub> with L = 20 (an engine window from 2 to 247 days). The daily shock is shared by HPL and RTPL, so the rolling mean removes it and leaves the two scales; a model fed a volatility that is L days old moves its scale L days late, and ρ<sub>roll</sub> falls as that age grows toward the window. The two are unchanged by scaling RTPL, and W is not.</>} es={<>Los dos estadísticos de Spearman: ρ<sub>S</sub> la correlación de rangos de Spearman, ρ<sub>abs</sub> la de los valores absolutos de HPL y RTPL, que ve un modelo que juzga mal el tamaño del movimiento del día, y ρ<sub>roll</sub> la de sus medias móviles m<sub>t</sub> de L días con L = 20 (una ventana del motor de 2 a 247 días). El choque diario lo comparten HPL y RTPL, así que la media móvil lo elimina y deja las dos escalas; un modelo alimentado con una volatilidad de L días de atraso mueve su escala L días tarde, y ρ<sub>roll</sub> cae a medida que esa edad crece hacia la ventana. Los dos no cambian al escalar RTPL, y W sí cambia.</>} />}
      />
      <Equation
        tex={String.raw`k = \lfloor p\,N \rfloor, \qquad p = \frac{\tau}{3} \ \ (\mathrm{Bonferroni}) \quad \mathrm{or} \quad p = \tau`}
        caption={<T en={<>The calibration of the decision: N the number of desk-years of a model with nothing planted, simulated from the caller&apos;s own generator, τ the size wanted (1%) and p the share each statistic may flag. With k = floor(pN), the critical value is the (k + 1)-th largest of the null values for W and the (k + 1)-th smallest for the two Spearman statistics, so that at most pN null desk-years are flagged by each statistic; the Bonferroni form takes p as τ over 3, which holds the union of the three flags to τ, and the plain form takes p equal to τ for each. A null too small to resolve p (N below 1/p) is refused. Nothing in the module draws a random number.</>} es={<>La calibración de la decisión: N el número de años de mesa de un modelo sin nada plantado, simulados con el generador propio de quien llama, y p τ el tamaño buscado (1 %) y p la parte que cada estadístico puede marcar. Con k = piso(pN), el valor crítico es el (k + 1)-ésimo mayor de los valores nulos para W y el (k + 1)-ésimo menor para los dos estadísticos de Spearman, de modo que cada estadístico marca a lo más pN años de mesa nulos; la forma de Bonferroni toma p como τ dividido por 3, lo que mantiene la unión de las tres marcas en τ, y la forma simple toma p igual a τ para cada uno. Una nula demasiado pequeña para resolver p (N bajo 1/p) se rechaza. Nada en el módulo sortea un número aleatorio.</>} />}
      />
      <h3>{t('What it is compared against and what it measured', 'Con qué se compara y qué midió')}</h3>
      <P
        en={<>The method it is set against is the regulatory zone itself, the only test the standard applies to a desk&apos;s attribution. The claim was fixed before any run: at a size of at most 1%, the complement flags the model with a 20-day-old volatility in at least 30% of the replications, and it is refuted below 10%. The thresholds were calibrated on 10,000 null desk-years under ten case seeds that the committed run never uses (5013 to 5022) and applied unchanged to the committed replications. At 1% per statistic they are W above 9.833, ρ<sub>abs</sub> below 0.9353 and ρ<sub>roll</sub> below 0.9619; for the union at 1% (Bonferroni, a third of a percent each) W above 12.007, ρ<sub>abs</sub> below 0.9263 and ρ<sub>roll</sub> below 0.9493. In the notebook, on 200 stale-volatility desk-years and 300 exact ones with the thresholds calibrated on 300 null desk-years, the zone flags none of the 200; the complement flags 99.5% of them (the rolling statistic alone 99.0%, ρ<sub>abs</sub> 73.0%, W 11.5%) and raises 1.0% false alarms on the exact desks. The committed measurement on 1,000 replications reads 999 flags for the union at 1%, and 9 false alarms in 1,000 exact desk-years (0.9%).</>}
        es={<>El método frente al que se pone es la propia zona regulatoria, la única prueba que la norma aplica a la atribución de una mesa. La afirmación se fijó antes de toda corrida: con un tamaño de a lo más 1 %, el complemento marca el modelo con una volatilidad de 20 días de atraso en al menos 30 % de las réplicas, y se refuta bajo 10 %. Los umbrales se calibraron con 10.000 años de mesa nulos bajo diez semillas de caso que la corrida versionada nunca usa (5013 a 5022) y se aplicaron sin cambio a las réplicas versionadas. Al 1 % por estadístico son W sobre 9,833, ρ<sub>abs</sub> bajo 0,9353 y ρ<sub>roll</sub> bajo 0,9619; para la unión al 1 % (Bonferroni, un tercio de por ciento cada uno) W sobre 12,007, ρ<sub>abs</sub> bajo 0,9263 y ρ<sub>roll</sub> bajo 0,9493. En el notebook, con 200 años de mesa de volatilidad rezagada y 300 exactos, y umbrales calibrados con 300 años de mesa nulos, la zona no marca ninguno de los 200; el complemento marca 99,5 % de ellos (el estadístico móvil solo 99,0 %, ρ<sub>abs</sub> 73,0 %, W 11,5 %) y levanta 1,0 % de falsas alarmas en las mesas exactas. La medición versionada con 1.000 réplicas lee 999 marcas para la unión al 1 %, y 9 falsas alarmas en 1.000 años de mesa exactos (0,9 %).</>}
      />
      <Tbl
        id="pla-variants"
        head={[t('Variant (1,000 desk-years each)', 'Variante (1.000 años de mesa cada una)'), t('Regulatory zone amber or red', 'Zona regulatoria ámbar o roja'), 'W', 'ρ abs', 'ρ roll', t('Union of the three, 1%', 'Unión de las tres, 1 %')]}
        rows={[
          [t('Exact model', 'Modelo exacto'), t('0.0%', '0,0 %'), t('0.8%', '0,8 %'), t('1.6%', '1,6 %'), t('1.2%', '1,2 %'), t('0.9%', '0,9 %')],
          [t('Missing basis', 'Base omitida'), t('96.0%', '96,0 %'), t('0.9%', '0,9 %'), t('100.0%', '100,0 %'), t('99.9%', '99,9 %'), t('100.0%', '100,0 %')],
          [t('Volatility 20 days old', 'Volatilidad de 20 días de atraso'), t('0.0%', '0,0 %'), t('14.2%', '14,2 %'), t('76.7%', '76,7 %'), t('99.9%', '99,9 %'), t('99.9%', '99,9 %')],
          [t('Wrong correlation', 'Correlación errónea'), t('100.0%', '100,0 %'), t('100.0%', '100,0 %'), t('8.7%', '8,7 %'), t('4.5%', '4,5 %'), t('100.0%', '100,0 %')],
          [t('Omitted factor', 'Factor omitido'), t('90.1%', '90,1 %'), t('0.6%', '0,6 %'), t('100.0%', '100,0 %'), t('98.7%', '98,7 %'), t('100.0%', '100,0 %')],
          [t('One-day time misalignment', 'Desfase de un día'), t('100.0%', '100,0 %'), t('100.0%', '100,0 %'), t('100.0%', '100,0 %'), t('42.3%', '42,3 %'), t('100.0%', '100,0 %')],
        ]}
      />
      <P
        en={<>Along the age of the volatility (100 desk-years at each lag in the notebook) the zone stays at zero from a lag of 5 days to one of 40, and the complement flags 0.23 of the desk-years at 5 days, 0.84 at 10 and all of them from 20 days on; in the committed run the rolling statistic at 1% per statistic flags 57.6% at 5 days, 97.5% at 10, 99.9% at 20 and 100.0% at 40. A volatility a week old is hard to tell from the noise of one year of data, and the complement says so instead of claiming it.</>}
        es={<>A lo largo de la edad de la volatilidad (100 años de mesa por cada rezago en el notebook) la zona se queda en cero desde un rezago de 5 días hasta uno de 40, y el complemento marca 0,23 de los años de mesa a 5 días, 0,84 a 10 y todos desde 20 días; en la corrida versionada el estadístico móvil al 1 % por estadístico marca 57,6 % a 5 días, 97,5 % a 10, 99,9 % a 20 y 100,0 % a 40. Una volatilidad de una semana es difícil de distinguir del ruido de un año de datos, y el complemento lo dice en vez de afirmarlo.</>}
      />
      <Figure
        caption={t(
          'The share of 1,000 desk-years of each planted variant that the regulatory zone (amber or red), the rolling-scale statistic and the union of the three statistics at 1% flag (the table above): the complement catches the volatility that is 20 days old where the zone sees nothing, and the exact model stays near the 1% size.',
          'La parte de 1.000 años de mesa de cada variante sembrada que marcan la zona regulatoria (ámbar o roja), el estadístico de escala móvil y la unión de los tres estadísticos al 1 % (la tabla de arriba): el complemento detecta la volatilidad de 20 días de atraso donde la zona no ve nada, y el modelo exacto queda cerca del tamaño de 1 %.',
        )}
      >
        <GroupedBars
          groups={[
            { en: 'Exact|model', es: 'Modelo|exacto' },
            { en: 'Missing|basis', es: 'Base|omitida' },
            { en: 'Volatility|20 days old', es: 'Volatilidad|20 días atraso' },
            { en: 'Wrong|correlation', es: 'Correlación|errónea' },
            { en: 'Omitted|factor', es: 'Factor|omitido' },
            { en: 'One-day|misalignment', es: 'Desfase|de un día' },
          ]}
          series={[
            { id: 'zone', label: { en: 'Regulatory zone', es: 'Zona regulatoria' }, token: '--color-magenta', values: [0, 96, 0, 100, 90.1, 100] },
            { id: 'rolling', label: { en: 'Rolling statistic', es: 'Estadístico móvil' }, token: '--color-accent', values: [1.2, 99.9, 99.9, 4.5, 98.7, 42.3] },
            { id: 'union', label: { en: 'Union, 1%', es: 'Unión, 1 %' }, token: '--color-good', values: [0.9, 100, 99.9, 100, 100, 100] },
          ]}
          axis={{ min: 0, max: 100, decimals: 1, percent: true, tickDecimals: 0, title: { en: 'Desk-years flagged', es: 'Años de mesa marcados' } }}
          reference={{ value: 1, label: { en: 'Size', es: 'Tamaño' } }}
          label={{ en: 'Grouped bars of the share of desk-years flagged by the regulatory zone, the rolling statistic and their union in six variants, against the 1 percent size', es: 'Barras agrupadas de la parte de años de mesa marcados por la zona regulatoria, el estadístico móvil y su unión en seis variantes, contra el tamaño de 1 por ciento' }}
        />
      </Figure>
      <h3>{t('Where it fails', 'Dónde falla')}</h3>
      <P
        en={<>The rolling statistic is weak against a one-day time misalignment (42.3%, where the regulatory zone flags 100%) and against a wrong correlation (4.5%, where the zone flags 100%): the complement is a supplement to the zone, not a replacement, and the union with the zone flags 100% on the five planted variants. The Wald statistic does not see a missing basis (0.9%, against 86.7% for the Kolmogorov-Smirnov statistic alone), for a structural reason: the basis noise sits in HPL and is independent of RTPL, so the regression of HPL on RTPL keeps an intercept of 0 and a slope of 1; ρ<sub>abs</sub> is the statistic that sees it (100%). The Wald statistic also flags the stale volatility only weakly (14.2%), because a stale volatility leaves the average slope close to one. Below a lag of about ten days the complement loses power (0.23 at 5 days), which is the limit of one year of data. The secondary clause of the research brief, that the Wald statistic would flag the planted deficiencies the Kolmogorov-Smirnov statistic flags, is in part not supported.</>}
        es={<>El estadístico móvil es débil frente a un desfase de un día (42,3 %, donde la zona regulatoria marca 100 %) y frente a una correlación errónea (4,5 %, donde la zona marca 100 %): el complemento es un suplemento de la zona, no un reemplazo, y la unión con la zona marca 100 % en las cinco variantes plantadas. El estadístico de Wald no ve una base omitida (0,9 %, contra 86,7 % del estadístico de Kolmogorov-Smirnov solo), por una razón estructural: el ruido de la base está en HPL y es independiente de RTPL, así que la regresión de HPL sobre RTPL mantiene un intercepto de 0 y una pendiente de 1; ρ<sub>abs</sub> es el estadístico que la ve (100 %). El estadístico de Wald marca además la volatilidad rezagada solo débilmente (14,2 %), porque una volatilidad rezagada deja la pendiente media cerca de uno. Bajo un rezago de unos diez días el complemento pierde potencia (0,23 a 5 días), que es el límite de un año de datos. La cláusula secundaria del encargo de investigación, que el estadístico de Wald marcaría las deficiencias plantadas que marca el de Kolmogorov-Smirnov, se sostiene solo en parte.</>}
      />
      <Callout variant="honest" title={t('What the complement claims and what it does not', 'Qué afirma el complemento y qué no')}>
        <T
          en={<>The thresholds are specific to the null generator that produced them: a desk with another P&amp;L process needs its own null. Under two changed nulls (less persistent volatility, then less dispersed volatility) the union at 1% per statistic flags 1.0% and 2.1%, and the union at 1% for the union 0.1% and 0.5%, so the size did not rise when the volatility was smoother; that is evidence, not a guarantee. The cross-check of size on the case C22 generators named in the plan could not be run, because those generators produce default counts, scores, migrations and samples, none a P&amp;L pair. The Mincer-Zarnowitz and MacKinnon-White references are cited from the standard references and were not re-read for the engine page (UNVERIFIED there); the power study of the regulatory thresholds by Montoro, Spinaci and Georgi is paywalled and was not read. The complement does not change any paragraph of MAR32 and has no regulatory standing.</>}
          es={<>Los umbrales son específicos del generador nulo que los produjo: una mesa con otro proceso de P&amp;L necesita su propia nula. Bajo dos nulas cambiadas (volatilidad menos persistente, luego volatilidad menos dispersa) la unión al 1 % por estadístico marca 1,0 % y 2,1 %, y la unión al 1 % para la unión 0,1 % y 0,5 %, así que el tamaño no subió con una volatilidad más suave; eso es evidencia, no una garantía. La verificación cruzada del tamaño con los generadores del caso C22 que nombra el plan no pudo correrse, porque esos generadores producen conteos de incumplimiento, puntajes, migraciones y muestras, ninguno un par de P&amp;L. Las referencias de Mincer-Zarnowitz y de MacKinnon-White se citan de las referencias estándar y no se releyeron para la página del motor (UNVERIFIED allí); el estudio de potencia de los umbrales regulatorios de Montoro, Spinaci y Georgi es de pago y no se leyó. El complemento no cambia ningún párrafo de MAR32 y no tiene valor regulatorio.</>}
        />
      </Callout>
      <P
        en={<>The notebook that runs this method on the product&apos;s data, from the three statistics on one desk-year to the lag ladder and the claim: <a href={`${NB}/en/${NB_PATH}`}><code>notebooks/en/{NB_PATH}</code></a>. The engine page: <Ref>docs/market/09_pla-complement.md</Ref> of riskvalidation 1.1.0.</>}
        es={<>El notebook que corre este método con los datos del producto, desde los tres estadísticos en un año de mesa hasta la escalera de rezagos y la afirmación: <a href={`${NB}/es/${NB_PATH}`}><code>notebooks/es/{NB_PATH}</code></a>. La página del motor: <Ref>docs/market/09_pla-complement.md</Ref> de riskvalidation 1.1.0.</>}
      />
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'pla-complement',
  group: 'market',
  order: 160,
  title: { en: 'Complement to the PLA test', es: 'Complemento de la prueba PLA' },
  Body,
};
