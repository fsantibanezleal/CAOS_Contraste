# Cuadernos, español

El índice del árbol en español. Los temas van de lo simple a lo complejo; dentro de un tema el orden de lectura es el número del
cuaderno y el nivel nunca baja. La contraparte en inglés de cada cuaderno está en la misma ruta bajo [`../en/`](../en/README.md).
Cómo instalarlos y correrlos está en [`../README.md`](../README.md).

Niveles: 1 fundamentos, 2 el método en la práctica, 3 estado del arte, 4 más allá del estado del arte.

## Temas

Un tema sin cuaderno de nivel 3 explica por qué en su fila. Los temas posteriores al 01 figuran con la unidad que los escribe y
pasan a ser enlaces cuando existe su carpeta.

| Tema | Requiere | Nivel 3 |
|---|---|---|
| [01-getting-started](01-getting-started/) | ninguno, es el tema de entrada | Sin nivel 3: el tema enseña el contrato del motor y el recorrido por los datos versionados, ningún dosier de investigación trae trabajo de estado del arte sobre él, y el estado del arte de las pruebas que llama se presenta en los temas 02, 03 y 14 |
| 02-credit-scoring (unidad U17-B) | tema 01 | se planifica con su unidad |
| 03-ratings-and-calibration (unidad U17-C) | temas 01 y 02 | se planifica con su unidad |
| 04-provisions (unidad U17-D) | temas 01 y 03 | se planifica con su unidad |
| 05-lgd-and-ead (unidad U17-E) | temas 01 y 04 | se planifica con su unidad |
| 06-portfolio-capital (unidad U17-F) | tema 03 | se planifica con su unidad |
| 07-market-risk (unidad U17-G) | tema 01 | se planifica con su unidad |
| 08-counterparty-and-regulatory-calculators (unidades U17-L a U17-O) | temas 06 y 07 | se planifica con su unidad |
| 09-irrbb (unidad U17-H) | tema 01 | se planifica con su unidad |
| 10-liquidity (unidad U17-K) | temas 04 y 09 | se planifica con su unidad |
| 11-operational-risk (unidad U17-I) | tema 01 | se planifica con su unidad |
| 12-capital-and-stress (unidades U17-L a U17-O) | temas 06, 07, 09 y 11 | se planifica con su unidad |
| 13-ml-and-ai-risk (unidades U17-L a U17-O) | tema 02 | se planifica con su unidad |
| 14-validating-the-validator (unidad U17-J) | temas 01 y 03 | se planifica con su unidad |

## Cuadernos

| Cuaderno | Nivel | Qué enseña |
|---|---|---|
| [01-getting-started/01-install-the-engine-and-open-an-artifact.ipynb](01-getting-started/01-install-the-engine-and-open-an-artifact.ipynb) | 1 | instalar el motor, listar su catálogo de pruebas de validación y abrir los tres tipos de documento versionado (el índice, el manifiesto de un caso y un artefacto), con la versión del motor que calculó cada uno |
| [01-getting-started/02-a-first-testresult-on-a-real-slice.ipynb](01-getting-started/02-a-first-testresult-on-a-real-slice.ipynb) | 1 | una prueba del motor sobre 50 tarjetas reales: el AUC, la prueba de Jeffreys y el puntaje de Brier, cada campo de un `TestResult`, y las mismas pruebas sobre las 9.000 tarjetas versionadas |
| [01-getting-started/03-policies-and-traffic-lights.ipynb](01-getting-started/03-policies-and-traffic-lights.ipynb) | 1 | cómo una política con versión convierte un valor p en una luz, por qué una política más estricta cambia el color y no el estadístico, y por qué los umbrales son política y nunca regulación |
| [01-getting-started/04-a-battery-on-your-own-scored-sample.ipynb](01-getting-started/04-a-battery-on-your-own-scored-sample.ipynb) | 2 | la ruta de la puerta para traer tu propio modelo: el contrato 1, la escala maestra, una batería corrida con `run_suite` que nunca se detiene en la primera falla, y cómo leer su tabla de luces |

## Más allá del estado del arte

Todavía no se afirma ninguna: la sección Beyond the state of the art del SDD dice "None claimed." El tema 01 no demuestra nada más
allá del estado del arte. Cada afirmación entra al SDD junto con el cuaderno de nivel 4 que la demuestra, en la unidad de su tema.
