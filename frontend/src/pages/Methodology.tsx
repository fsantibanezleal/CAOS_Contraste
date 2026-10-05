import { Cite, DocPage, DocSection, Equation, Tabs, useShellLang } from '@fasl-work/caos-app-shell';
import { P, useT } from '../content/bi';

function Model() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'The model', es: 'El modelo' }} refs={['km1927', 'hethcote2000']}>
        <P
          en={<>A closed population of N people is split into the susceptible S, the infected I and the recovered R <Cite id="km1927" />. Contacts are homogeneous: each infected person infects susceptible people at a rate proportional to their share of the population, with contact rate β, and recovers at rate γ, so the infectious period is exponential with mean 1/γ <Cite id="hethcote2000" />.</>}
          es={<>Una población cerrada de N personas se divide en susceptibles S, contagiados I y recuperados R <Cite id="km1927" />. Los contactos son homogéneos: cada persona contagiada contagia a los susceptibles a una tasa proporcional a su fracción de la población, con tasa de contacto β, y se recupera a tasa γ, de modo que el período infeccioso es exponencial con media 1/γ <Cite id="hethcote2000" />.</>}
        />
        <Equation
          tex="\frac{dS}{dt} = -\beta \frac{S I}{N}, \qquad \frac{dI}{dt} = \beta \frac{S I}{N} - \gamma I, \qquad \frac{dR}{dt} = \gamma I"
          caption={t('The SIR system; S + I + R = N at every time.', 'El sistema SIR; S + I + R = N en todo instante.')}
        />
        <P
          en="The assumptions are the limits of the example: no births or deaths, no waning immunity, no structure by age or place, and a deterministic population large enough for fractions to be meaningful. A product replaces this model with the one its research chose; the structure of the page stays."
          es="Los supuestos son los límites del ejemplo: sin nacimientos ni muertes, sin pérdida de inmunidad, sin estructura por edad o lugar, y una población determinista lo bastante grande para que las fracciones tengan sentido. Un producto reemplaza este modelo por el que eligió su investigación; la estructura de la página se mantiene."
        />
      </DocSection>
      <DocSection title={{ en: 'The threshold', es: 'El umbral' }} refs={['diekmann1990', 'vdd2002']}>
        <P
          en={<>The basic reproduction number R0 is the expected number of infections caused by one infected person in a fully susceptible population <Cite id="diekmann1990" />. For this model it is the contact rate times the mean infectious period. While the effective number R0 S/N stays above one, infections grow; the epidemic peaks when it crosses one <Cite id="vdd2002" />.</>}
          es={<>El número reproductivo básico R0 es el número esperado de contagios que causa una persona contagiada en una población totalmente susceptible <Cite id="diekmann1990" />. En este modelo es la tasa de contacto por el período infeccioso medio. Mientras el número efectivo R0 S/N se mantiene sobre uno, los contagios crecen; la epidemia alcanza su pico cuando cruza uno <Cite id="vdd2002" />.</>}
        />
        <Equation tex="R_0 = \frac{\beta}{\gamma}, \qquad R_t = R_0 \frac{S(t)}{N}, \qquad p_c = 1 - \frac{1}{R_0}" caption={t('The basic and effective reproduction numbers, and the share p_c that must be immune to prevent an outbreak.', 'Los números reproductivos básico y efectivo, y la fracción p_c que debe ser inmune para impedir un brote.')} />
        <P
          en="The immunisation variants of the App move a share v of the susceptible to R at the start. The outbreak is prevented when v exceeds p_c, which is why the 60% variant suppresses the fast-burn case only partly and the slow-spread case entirely."
          es="Las variantes de inmunización de la App mueven una fracción v de los susceptibles a R al inicio. El brote se impide cuando v supera p_c; por eso la variante de 60% suprime sólo en parte el caso de combustión rápida y por completo el de propagación lenta."
        />
      </DocSection>
    </>
  );
}

function FinalSize() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The final size', es: 'El tamaño final' }} refs={['km1927', 'miller2012']}>
      <P
        en={<>Dividing the first equation by the third gives dS/dR = -R0 S/N, so S falls exponentially in R. When the epidemic ends, I is zero and R is N minus S, which closes the relation that fixes how many are ever infected <Cite id="km1927" />. Miller derives it, and its extensions, directly from this argument <Cite id="miller2012" />.</>}
        es={<>Al dividir la primera ecuación por la tercera se obtiene dS/dR = -R0 S/N, de modo que S decae exponencialmente en R. Cuando la epidemia termina, I es cero y R es N menos S, lo que cierra la relación que fija cuántos se contagian alguna vez <Cite id="km1927" />. Miller la deriva, junto con sus extensiones, directamente desde este argumento <Cite id="miller2012" />.</>}
      />
      <Equation tex="S_\infty = S_0 \, e^{-R_0 (N - S_\infty)/N} \quad \Longrightarrow \quad z = 1 - e^{-R_0 z} \;\; (S_0 \to N)" caption={t('The final-size relation; z is the share of the population ever infected.', 'La relación de tamaño final; z es la fracción de la población alguna vez contagiada.')} />
      <P
        en="It does not depend on the time course, only on R0, so it is an independent check of any engine: run long enough, the simulated attack rate must reach z. The Validation group of the App plots both. Where they part, either the horizon ended the run before the epidemic did, or R0 is so close to one that the epidemic is still burning."
        es="No depende de la trayectoria temporal, sólo de R0, así que es una verificación independiente de cualquier motor: con una corrida lo bastante larga, la tasa de ataque simulada debe llegar a z. El grupo Validación de la App grafica ambas. Donde se separan, o el horizonte terminó la corrida antes que la epidemia, o R0 está tan cerca de uno que la epidemia sigue activa."
      />
    </DocSection>
  );
}

function Numerics() {
  const t = useT();
  return (
    <DocSection title={{ en: 'The numerical scheme', es: 'El esquema numérico' }} refs={['hairer1993']}>
      <P
        en={<>Both engines integrate the system with the explicit Euler method at a step of a quarter of a day. It is first order: the global error shrinks in proportion to the step <Cite id="hairer1993" />. Each compartment is clamped at zero, which only acts when a large step would otherwise drive it negative.</>}
        es={<>Ambos motores integran el sistema con el método de Euler explícito a un paso de un cuarto de día. Es de primer orden: el error global disminuye en proporción al paso <Cite id="hairer1993" />. Cada compartimento se limita a cero, lo que sólo actúa cuando un paso grande lo llevaría a valores negativos.</>}
      />
      <Equation
        tex="\begin{aligned} S_{k+1} &= \max\!\left(0,\; S_k - \beta \tfrac{S_k I_k}{N} \Delta t\right) \\ I_{k+1} &= \max\!\left(0,\; I_k + \beta \tfrac{S_k I_k}{N} \Delta t - \gamma I_k \Delta t\right) \\ R_{k+1} &= R_k + \gamma I_k \Delta t \end{aligned}"
        caption={t('One step of the scheme, with Δt = 0.25 days; the Python and TypeScript engines perform the same operations in the same order.', 'Un paso del esquema, con Δt = 0,25 días; los motores en Python y en TypeScript hacen las mismas operaciones en el mismo orden.')}
      />
      <P
        en="Both engines perform the same floating-point operations in the same order. The committed trace rounds values to two decimals, and the parity test holds the live engine to that rounding on every baked case. A first-order scheme is enough for an example; a product picks its integrator from its own error budget."
        es="Ambos motores hacen las mismas operaciones de punto flotante en el mismo orden. La traza comprometida redondea a dos decimales, y la prueba de paridad exige al motor en vivo ese redondeo en cada caso precalculado. Un esquema de primer orden basta para un ejemplo; un producto elige su integrador según su propio presupuesto de error."
      />
    </DocSection>
  );
}

export function Methodology() {
  const lang = useShellLang();
  const t = useT();
  return (
    <DocPage title={{ en: 'Methodology', es: 'Metodología' }} lede={t('The model behind the example, its threshold, its final size, and how it is integrated.', 'El modelo detrás del ejemplo, su umbral, su tamaño final y cómo se integra.')}>
      <Tabs
        ariaLabel={lang === 'es' ? 'Partes de la metodología' : 'Parts of the methodology'}
        tabs={[
          { id: 'model', label: t('Model and threshold', 'Modelo y umbral'), content: <Model /> },
          { id: 'final-size', label: t('Final size', 'Tamaño final'), content: <FinalSize /> },
          { id: 'numerics', label: t('Numerical scheme', 'Esquema numérico'), content: <Numerics /> },
        ]}
      />
    </DocPage>
  );
}
