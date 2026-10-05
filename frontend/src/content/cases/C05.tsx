// The deep write-up of case C05, transcribed from docs/design/features/c05-ldp-calibration/design.md, Contraste
// research dossier 10 (the golden values, read at the primary sources on 2026-10-05) and riskvalidation's
// docs/engines/02_low-default.md and 03_pd-curve-calibration.md. The Context view shows it under the sources.
import { Cite, Equation } from '@fasl-work/caos-app-shell';
import { L, P, useT } from '../bi';

export function C05WriteUp() {
  const t = useT();
  return (
    <>
      <h3>{t('The question', 'La pregunta')}</h3>
      <P
        en={<>A rating system is estimated on one year and used in the next. Carrying its PD curve to the new year means deciding what stays fixed between the two: the default profile, the accuracy ratio, the shape of the PD curve or the shape of the likelihood ratio <Cite id="tasche2013" />. And where a portfolio has almost no defaults, the PDs must still be estimated, conservatively, from the number of obligors observed without default and the ordering of the grades <Cite id="plutotasche2005" />. The case asks which calibration holds up against what happened, what each implies for capital, and what a validator can and cannot see in a low-default portfolio.</>}
        es={<>Un sistema de calificación se estima con un año y se usa en el siguiente. Llevar su curva de PD al nuevo año exige decidir qué queda fijo entre ambos: el perfil de incumplimiento, la razón de precisión, la forma de la curva de PD o la forma de la razón de verosimilitud <Cite id="tasche2013" />. Y donde una cartera casi no tiene incumplimientos, las PD igual deben estimarse, con prudencia, desde el número de deudores observados sin incumplir y el orden de los grados <Cite id="plutotasche2005" />. El caso pregunta qué calibración resiste frente a lo ocurrido, qué implica cada una para el capital, y qué puede y qué no puede ver un validador en una cartera de bajo incumplimiento.</>}
      />
      <h3>{t('The rating model and its three descriptions', 'El modelo de calificación y sus tres descripciones')}</h3>
      <P
        en="A grade X at the start of the year and a state at its end (default D or survival N) have a joint distribution, fixed equally by the profile and the PD curve, by the PD and the two conditional profiles, or by the PD and the likelihood ratio (Tasche 2013, Proposition 3.1):"
        es="Un grado X al inicio del año y un estado al final (incumplimiento D o supervivencia N) tienen una distribución conjunta, fijada igualmente por el perfil y la curva de PD, por la PD y los dos perfiles condicionales, o por la PD y la razón de verosimilitud (Tasche 2013, proposición 3.1):"
      />
      <Equation
        tex={String.raw`\Pr[D \mid X = x] = \frac{p}{p + (1 - p)\,\lambda(x)}, \qquad \lambda(x) = \frac{\Pr[X = x \mid N]}{\Pr[X = x \mid D]}`}
        caption={t(
          'The PD curve from the unconditional PD p and the likelihood ratio λ of the survival profile over the default profile (Tasche 2013, equations 3.8 and 3.9a); fixing the shape of λ while p moves is the scaled likelihood ratio approach.',
          'La curva de PD desde la PD incondicional p y la razón de verosimilitud λ del perfil de supervivencia sobre el de incumplimiento (Tasche 2013, ecuaciones 3.8 y 3.9a); fijar la forma de λ mientras p se mueve es el enfoque de razón de verosimilitud escalada.',
        )}
      />
      <P
        en={<>The 2009 curve is smoothed by quasi moment matching: a robust logistic curve on the grades, its two parameters set so that its unconditional PD and its accuracy ratio equal the observed 3.99% and 82.7% <Cite id="tasche2009" />. Recomputed from the S&P counts it reproduces the paper's Table 5 to one unit of the third decimal.</>}
        es={<>La curva 2009 se suaviza por cuasi ajuste de momentos: una curva logística robusta sobre los grados, con sus dos parámetros fijados para que su PD incondicional y su razón de precisión igualen el 3,99% y el 82,7% observados <Cite id="tasche2009" />. Recalculada desde los conteos de S&P reproduce la Tabla 5 del artículo a una unidad del tercer decimal.</>}
      />
      <h3>{t('What happened in 2010 and 2011', 'Lo que pasó en 2010 y 2011')}</h3>
      <L
        items={[
          { en: 'With the profile and the PD of the year known (the observed one, as the paper does, to compare the approaches fairly), the scaled likelihood ratio and the invariant accuracy ratio fit the 2010 default profile best; scaled PDs and the invariant default profile are amber (p near 4%). In 2011 every approach fits.', es: 'Con el perfil y la PD del año conocidos (la observada, como el artículo, para comparar los enfoques en igualdad), la razón de verosimilitud escalada y la razón de precisión invariante ajustan mejor el perfil de 2010; las PD escaladas y el perfil de incumplimiento invariante quedan en ámbar (p cerca de 4%). En 2011 todos ajustan.' },
          { en: 'In 2010 every case 1 curve underestimates CCC-C: 22% of those obligors defaulted against 13% to 16% forecast (Jeffreys, red).', es: 'En 2010 toda curva del caso 1 subestima CCC-C: incumplió el 22% de esos deudores contra un 13% a 16% pronosticado (Jeffreys, rojo).' },
          { en: 'Without the year\'s PD, the case 3 approaches forecast it from the profile alone: 4.3% to 5.4% for 2010 against 1.14% observed. The invariances fail on these data.', es: 'Sin la PD del año, los enfoques del caso 3 la pronostican solo desde el perfil: 4,3% a 5,4% para 2010 contra 1,14% observado. Las invarianzas no se cumplen en estos datos.' },
          { en: 'Carrying the 2009 curve unchanged into 2010 would ask about 65% more capital than the scaled likelihood ratio: the calibration choice is a capital choice.', es: 'Llevar la curva 2009 sin cambios a 2010 pediría cerca de un 65% más de capital que la razón de verosimilitud escalada: la elección de calibración es una elección de capital.' },
        ]}
      />
      <P
        en="The paper's backtest on Moody's data for 1987 to 2012 ranks the scaled likelihood ratio first on average and the invariant accuracy ratio last; its conclusion is that scaled PDs mix up the unconditional PD of the estimation period with the target one."
        es="El backtest del artículo con datos de Moody's para 1987 a 2012 pone primera en promedio a la razón de verosimilitud escalada y última a la razón de precisión invariante; su conclusión es que las PD escaladas mezclan la PD incondicional del período de estimación con la objetivo."
      />
      <h3>{t('Low-default portfolios', 'Carteras de bajo incumplimiento')}</h3>
      <P
        en="The most prudent principle bounds a grade's PD by pooling it with every worse grade, under the ordering the rating system asserts; the bound is the largest PD under which what was observed is still not too unlikely:"
        es="El principio más prudente acota la PD de un grado agrupándolo con todos los peores, bajo el orden que afirma el sistema de calificación; la cota es la mayor PD con la que lo observado todavía no es demasiado improbable:"
      />
      <Equation
        tex={String.raw`1 - \gamma = \int \varphi(y) \sum_{i=0}^{D} \binom{N}{i}\, p(y)^i \big(1 - p(y)\big)^{N - i} dy, \qquad p(y) = \Phi\!\left(\frac{\Phi^{-1}(p) - \sqrt{\rho}\,y}{\sqrt{1 - \rho}}\right)`}
        caption={t(
          'The most prudent bound p at confidence γ for N pooled obligors with D defaults, with asset correlation ρ through the systematic factor y (Pluto and Tasche 2005, equations 4.1 and 4.3a); at ρ = 0 the integral drops and the bound is the Clopper-Pearson one.',
          'La cota más prudente p a confianza γ para N deudores agrupados con D incumplimientos, con correlación de activos ρ a través del factor sistémico y (Pluto y Tasche 2005, ecuaciones 4.1 y 4.3a); con ρ = 0 la integral desaparece y la cota es la de Clopper-Pearson.',
        )}
      />
      <L
        items={[
          { en: 'Every published bound of the paper is recomputed: 204 cells. The independent ones are exact except Table 4 at 75%, a computation the paper carries into Table 11; the correlated ones with defaults (Table 8) and the five-year ones (Tables 13 and 14) lie above the exact bounds, conservatively.', es: 'Se recalcula cada cota publicada del artículo: 204 celdas. Las independientes son exactas salvo la Tabla 4 al 75%, un cálculo que el artículo arrastra a la Tabla 11; las correlacionadas con incumplimientos (Tabla 8) y las de cinco años (tablas 13 y 14) quedan sobre las cotas exactas, con prudencia.' },
          { en: 'On 20,000 generated years, from the 75% level up every one-year bound covers the truth (even a year without defaults gives grade C 0.77% at 90%, against a true 0.20%), several times above it. At 50% a year without defaults puts grade B at 0.099%, just under its true 0.10%, so it covers in less than half of the years; scaled to the portfolio bound at 50%, so does grade C.', es: 'En 20.000 años generados, desde el nivel 75% toda cota de un año cubre la verdad (incluso un año sin incumplimientos da al grado C 0,77% al 90%, contra un 0,20% verdadero), varias veces por encima. Al 50% un año sin incumplimientos deja al grado B en 0,099%, justo bajo su 0,10% verdadero, así que cubre en menos de la mitad de los años; escalado a la cota de la cartera al 50%, lo mismo el grado C.' },
          { en: 'Against an expert model at half the truth, the test that keeps its size under correlation (the Vasicek binomial) rejects in about 8% of the years: the battery cannot see the underestimation. The Jeffreys portfolio test rejects more, but it also rejects the true PDs in 13% of the years at 5%, the warning of BCBS WP14 on correlated defaults.', es: 'Frente a un modelo experto a la mitad de la verdad, la prueba que mantiene su tamaño con correlación (la binomial de Vasicek) rechaza en cerca del 8% de los años: la batería no ve la subestimación. La prueba de Jeffreys de la cartera rechaza más, pero también rechaza las PD verdaderas en el 13% de los años al 5%, la advertencia del WP14 de BCBS sobre incumplimientos correlacionados.' },
        ]}
      />
      <h3>{t('What the capital says', 'Lo que dice el capital')}</h3>
      <P
        en={<>The impact applies the IRB corporate function <Cite id="cre31" /> with the F-IRB senior unsecured LGD for financial institutions (45%) and maturity 2.5 years, one unit of EAD per obligor; the rail moves the regime (Basel III final, CRR3 <Cite id="crr3" />, Basel II with its 1.06 factor) and the LGD. The function is the 99.9% quantile of the one-factor model's large homogeneous portfolio <Cite id="gordy2003" /> <Cite id="bcbs2005irb" />, recomputed in the browser and held to riskvalidation, which reproduces every cell of BCBS CRE99 Table 1 <Cite id="cre99" />. The PD floor lifts the expert PDs of the best grades, which is what it fixes; it does not fix the grades above it.</>}
        es={<>El impacto aplica la función IRB corporativa <Cite id="cre31" /> con la LGD F-IRB senior no garantizada de instituciones financieras (45%) y vencimiento 2,5 años, una unidad de EAD por deudor; el panel mueve el régimen (Basilea III final, CRR3 <Cite id="crr3" />, Basilea II con su factor 1,06) y la LGD. La función es el cuantil 99,9% de la cartera homogénea grande del modelo de un factor <Cite id="gordy2003" /> <Cite id="bcbs2005irb" />, recalculada en el navegador y sujeta a riskvalidation, que reproduce cada celda de la Tabla 1 de BCBS CRE99 <Cite id="cre99" />. El piso de PD eleva las PD expertas de los mejores grados, que es lo que corrige; no corrige los grados por encima de él.</>}
      />
      <h3>{t('Limits', 'Límites')}</h3>
      <L
        items={[
          { en: 'The S&P table is quoted from the paper and treated as derived-only: the PDF stays in the device data root, the artifacts publish rates and results, never the grade counts.', es: 'La tabla S&P se cita desde el artículo y se trata como solo derivados: el PDF queda en la raíz de datos del dispositivo y los artefactos publican tasas y resultados, nunca los conteos por grado.' },
          { en: 'The Moody\'s backtest cannot be rerun from the paper: it needs Moody\'s yearly grade frequencies, which the paper prints for 1986 only.', es: 'El backtest con Moody\'s no se puede repetir desde el artículo: requiere las frecuencias anuales por grado de Moody\'s, que el artículo imprime solo para 1986.' },
          { en: 'Nothing here certifies a calibration: the approaches are the paper\'s, and which one suits a portfolio is the validator\'s judgement, which the tests inform.', es: 'Nada aquí certifica una calibración: los enfoques son los del artículo, y cuál conviene a una cartera es juicio del validador, que las pruebas informan.' },
        ]}
      />
    </>
  );
}
