// The deep write-up of case C22, transcribed from docs/design/features/c22-validator/design.md, Contraste research
// dossier 12 (read at the primary sources on 2026-10-05: Morris, White and Crowther 2019; BCBS WP14 pages 41 to 67;
// Yurdakul and Naranjo 2020; Demler, Pencina and D'Agostino 2012; Brown, Cai and DasGupta 2001) and riskvalidation's
// docs/generators/ and docs/tests/ pages. The Context view shows it under the sources.
import { Cite, Equation } from '@fasl-work/caos-app-shell';
import { L, P, useT } from '../bi';

export function C22WriteUp() {
  const t = useT();
  return (
    <>
      <h3>{t('The question', 'La pregunta')}</h3>
      <P
        en={<>A validator reads p-values every day, and each one is evidence only as far as two numbers are known: how often the test rejects a model that is right (its size), and how often it catches a model that is wrong in a given way (its power). With real outcomes neither can be measured, because the truth is unknown. On generators whose truth is known both can, and the measurement is itself an experiment with an error that must be reported <Cite id="morris2019" />. The case measures every test with a p-value that Contraste has built so far, against eight families of data: the null, and seven planted defects.</>}
        es={<>Un validador lee valores p todos los días, y cada uno es evidencia solo en la medida en que se conocen dos números: con qué frecuencia la prueba rechaza un modelo correcto (su tamaño), y con qué frecuencia detecta un modelo equivocado de cierta forma (su potencia). Con resultados reales ninguno se puede medir, porque la verdad es desconocida. En generadores cuya verdad se conoce ambos se pueden medir, y la medición es en sí un experimento con un error que debe reportarse <Cite id="morris2019" />. El caso mide cada prueba con valor p que Contraste ha construido hasta ahora, contra ocho familias de datos: la nula, y siete defectos plantados.</>}
      />
      <h3>{t('A rate and its error', 'Una tasa y su error')}</h3>
      <Equation
        tex={String.raw`\hat r = \frac{1}{n_{sim}}\sum_{i=1}^{n_{sim}} \mathbb 1(p_i < \alpha), \qquad \widehat{\mathrm{SE}}(\hat r) = \sqrt{\frac{\hat r\,(1-\hat r)}{n_{sim}}}`}
        caption={t(
          'The rejection rate over n_sim repetitions and its Monte Carlo standard error (Morris, White and Crowther 2019, Table 6); each repetition draws its data from its own random stream, so it re-runs alone to the same result. The interval shown with every rate is Wilson\'s.',
          'La tasa de rechazo en n_sim repeticiones y su error estándar de Monte Carlo (Morris, White y Crowther 2019, tabla 6); cada repetición toma sus datos de su propio flujo aleatorio, así que se repite sola con el mismo resultado. El intervalo de cada tasa es el de Wilson.',
        )}
      />
      <P
        en={<>A test holds its size when its rate under the null is at most the level plus 3.09 standard errors, the bound a true size of the level crosses one time in a thousand. Where a rejection probability is exact, no simulation is needed and none is trusted over it: the three count tests (binomial, Vasicek-corrected binomial, Jeffreys) see the data only through one default count, so they reject exactly from a critical count k*, and</>}
        es={<>Una prueba mantiene su tamaño cuando su tasa bajo la nula es a lo más el nivel más 3,09 errores estándar, la cota que un tamaño verdadero igual al nivel cruza una vez en mil. Donde una probabilidad de rechazo es exacta, no se necesita simulación y ninguna vale más que ella: las tres pruebas de conteo (binomial, binomial corregida de Vasicek, Jeffreys) ven los datos solo a través de un conteo de incumplimientos, así que rechazan exactamente desde un conteo crítico k*, y</>}
      />
      <Equation
        tex={String.raw`P(\text{reject}) = \int \Pr\big[\mathrm{Bin}(n, p(x)) \ge k^*\big]\,\varphi(x)\,dx, \qquad p(x) = \Phi\!\left(\frac{\Phi^{-1}(\pi) - \sqrt{\rho}\,x}{\sqrt{1-\rho}}\right)`}
        caption={t(
          'The exact rejection probability of a count test when the true PD is π and the true asset correlation ρ, k* found by evaluating the test itself. Every simulated rate of these tests agrees with it within 3.29 standard errors; the Impact group recomputes it in your browser for your own portfolio.',
          'La probabilidad exacta de rechazo de una prueba de conteo cuando la PD verdadera es π y la correlación de activos verdadera ρ, con k* hallado evaluando la propia prueba. Cada tasa simulada de estas pruebas concuerda con ella dentro de 3,29 errores estándar; el grupo Impacto la recalcula en su navegador para su propia cartera.',
        )}
      />
      <h3>{t('The published simulations, reproduced', 'Las simulaciones publicadas, reproducidas')}</h3>
      <L
        items={[
          {
            en: <>The Basel Committee simulated the normal and traffic-lights tests on five years of 1,000 obligors, 25,000 runs per scenario <Cite id="wp14" />. Rerun from the tables read out of its PDF, 143 of its 144 published rates agree within the combined Monte Carlo error. The traffic lights agree only when a year with exactly the expected number of defaults takes the worse colour, the opposite of the printed mapping; the one cell that does not agree looks like a misprint.</>,
            es: <>El Comité de Basilea simuló las pruebas normal y de semáforo en cinco años de 1.000 deudores, 25.000 corridas por escenario <Cite id="wp14" />. Repetida desde las tablas leídas de su PDF, 143 de sus 144 tasas publicadas concuerdan dentro del error de Monte Carlo combinado. El semáforo concuerda solo cuando un año con exactamente el número esperado de incumplimientos toma el color peor, lo contrario de la asignación impresa; la única celda que no concuerda parece una errata.</>,
          },
          {
            en: <>Yurdakul and Naranjo measured the PSI's rules of thumb against a chi-square benchmark <Cite id="yurdakul2020" />: 50 of their 54 cells agree with this case's seed (53 with the engine's), the harness sitting slightly above the paper on average, an offset the Papers view states. The 0.10 rule raises a false alarm in most samples of 100 when nothing changed, and the fixed bands lose power as samples grow.</>,
            es: <>Yurdakul y Naranjo midieron las reglas empíricas del PSI contra una referencia chi-cuadrado <Cite id="yurdakul2020" />: concuerdan 50 de sus 54 celdas con la semilla de este caso (53 con la del motor), con el arnés levemente sobre el artículo en promedio, un desfase que la vista Artículos declara. La regla 0,10 da una falsa alarma en la mayoría de las muestras de 100 cuando nada cambió, y las bandas fijas pierden potencia al crecer las muestras.</>,
          },
          {
            en: <>Demler, Pencina and D'Agostino showed that DeLong's test on nested models fitted on the same data almost never rejects: 0.001 at the 5% level <Cite id="demler2012" /> <Cite id="delong1988" />. Their design rerun gives two rejections in 1,000 (one in the engine's suite); two non-nested scores on an independent sample hold the size.</>,
            es: <>Demler, Pencina y D'Agostino mostraron que la prueba de DeLong en modelos anidados ajustados en los mismos datos casi nunca rechaza: 0,001 al nivel 5% <Cite id="demler2012" /> <Cite id="delong1988" />. Su diseño repetido da dos rechazos en 1.000 (uno en la suite del motor); dos puntajes no anidados en una muestra independiente mantienen el tamaño.</>,
          },
        ]}
      />
      <h3>{t('What the measurements changed', 'Lo que cambiaron las mediciones')}</h3>
      <L
        items={[
          {
            en: <>The Hosmer-Lemeshow statistic of a model fitted on the same data has G - 2 degrees of freedom <Cite id="hosmer1980" />; a validator tests PDs set before the outcomes, where each group adds one, as WP14 states for the test over grades. With G - 2 on such samples the test rejects right PDs more than one time in nine at the 5% level. riskvalidation now uses G by default, and C01 was re-baked.</>,
            es: <>El estadístico de Hosmer-Lemeshow de un modelo ajustado en los mismos datos tiene G - 2 grados de libertad <Cite id="hosmer1980" />; un validador prueba PD fijadas antes de los resultados, donde cada grupo aporta uno, como dice WP14 para la prueba por grados. Con G - 2 en tales muestras la prueba rechaza PD correctas más de una vez en nueve al nivel 5%. riskvalidation ahora usa G por omisión, y C01 se recalculó.</>,
          },
          {
            en: <>The ECB's test of the AUC against the development AUC treats the latter as known <Cite id="ecb2019" />. When it was estimated on a sample of similar size the test over-rejects: about one time in six at C01's slice sizes. C01 now adds the development estimate's variance, an extension the results state.</>,
            es: <>La prueba del BCE del AUC contra el AUC de desarrollo trata a esta como conocida <Cite id="ecb2019" />. Cuando se estimó en una muestra de tamaño parecido la prueba sobrerrechaza: cerca de una vez en seis con los tamaños de tramo de C01. C01 ahora suma la varianza de la estimación de desarrollo, una extensión que los resultados declaran.</>,
          },
          {
            en: <>The ECB's concentration statistic is bounded: as the current coefficient of variation c grows it peaks and falls back, so with ten grades and an initial CV of 0.6 no current distribution is rejected at 5%.</>,
            es: <>El estadístico de concentración del BCE es acotado: al crecer el coeficiente de variación actual c alcanza un máximo y vuelve a caer, así que con diez grados y un CV inicial de 0,6 ninguna distribución actual se rechaza al 5%.</>,
          },
        ]}
      />
      <Equation
        tex={String.raw`S(c) = \frac{\sqrt{K-1}\,(c - CV_{init})}{c\,\sqrt{0.5 + c^2}} \;\longrightarrow\; 0 \quad (c \to \infty)`}
        caption={t(
          'The ECB concentration statistic as a function of the current CV (ECB 2019, section 2.5.5.3, as transcribed in dossier 06): the variance term treats the K grade frequencies as the sample, so the number of obligors never enters. A chi-square test of homogeneity on the counts catches a 5% concentration shift almost always.',
          'El estadístico de concentración del BCE en función del CV actual (BCE 2019, sección 2.5.5.3, transcrito en el dossier 06): el término de varianza trata las K frecuencias por grado como la muestra, así que el número de deudores nunca entra. Una prueba chi-cuadrado de homogeneidad en los conteos detecta casi siempre un desplazamiento de concentración del 5%.',
        )}
      />
      <h3>{t('What not to read into it', 'Lo que no debe leerse')}</h3>
      <L
        items={[
          { en: 'A test that holds its size on a generator holds it for that generator\'s assumptions, not for every portfolio; each rate names its mechanism, its sample sizes and its number of repetitions.', es: 'Una prueba que mantiene su tamaño en un generador lo mantiene para los supuestos de ese generador, no para toda cartera; cada tasa nombra su mecanismo, sus tamaños de muestra y su número de repeticiones.' },
          { en: 'Power against a planted defect is not a probability of detecting a real bank\'s problem: the severity ladders are Contraste\'s design choices, printed on every view.', es: 'La potencia contra un defecto plantado no es una probabilidad de detectar el problema de un banco real: las escalas de severidad son elecciones de diseño de Contraste, impresas en cada vista.' },
          { en: 'No size or power figure is a regulatory threshold, and a test that holds its size does not make a model compliant.', es: 'Ninguna cifra de tamaño o potencia es un umbral regulatorio, y una prueba que mantiene su tamaño no vuelve conforme a un modelo.' },
        ]}
      />
    </>
  );
}
