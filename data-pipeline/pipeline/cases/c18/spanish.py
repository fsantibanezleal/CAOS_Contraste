"""The Spanish of every prose text of the C18 documents that the code writes once, by its English (U16-R2, b09 B1).

``params.text(en)`` reads it when a call gives no Spanish: a text of three words or more with no entry here is refused at bake time, so
a document never carries the English sentence in its Spanish slot again. The numbers inside a text are not here: a text that has one
is written with ``pipeline.core.text`` at its call site.
"""
from __future__ import annotations

SPANISH: dict[str, str] = {
    "2008 to 2009, the episode the satellites are back-cast through and the EBA documents severity against (05 l.422)":
        "2008 a 2009, el episodio por el que se retroproyectan los satélites y contra el que la EBA documenta la severidad (05 l.422)",
    "A Contraste approximation consistent with FAQ 24: the CMF calibration grid is not public and this is not a P2G requirement. The usable buffers are the conservation and countercyclical buffers and the voluntary stress buffer c_d; no mitigation is assumed.":
        "Una aproximación de Contraste coherente con la FAQ 24: la grilla de calibración de la CMF no es pública y esto no es un requerimiento P2G. Los colchones utilizables son los de conservación y contracíclico y el colchón voluntario de estrés c_d; no se supone ninguna mitigación.",
    "A stated constant cost-to-income ratio of the PPNR row (decision Q10, T3)":
        "Una razón constante declarada de costos sobre ingresos de la fila PPNR (decisión Q10, T3)",
    "A stated constant ratio of the PPNR row (decision Q10, T3); not a Banco Andino or CMF figure":
        "Una razón constante declarada de la fila PPNR (decisión Q10, T3); no es una cifra de Banco Andino ni de la CMF",
    "Banco Andino is a synthetic bank. Its book and capital are calibrated to public aggregates (the CMF system aggregates of August 2026, the Banco Santander-Chile Form 20-F 2025 as ratios only); the satellites are fitted on United States data and applied to it, a US-calibrated adaptation; every figure is a result of the stated method and no claim about a real bank.":
        "Banco Andino es un banco sintético. Su cartera y su capital se calibran con agregados públicos (los agregados del sistema de la CMF de agosto de 2026 y el Formulario 20-F 2025 de Banco Santander-Chile solo como razones); los satélites se ajustan con datos de Estados Unidos y se aplican a él, una adaptación calibrada en EE. UU.; cada cifra es resultado del método declarado y no afirma nada sobre un banco real.",
    "C11's mixed-portfolio VaR and ES scaled to the market share of RWA":
        "El VaR y el ES de la cartera mixta de C11 escalados a la parte de mercado de los APR",
    "CET1 ratio at the end of year 3 under the stress without mitigation":
        "Razón CET1 al final del año 3 bajo el estrés sin mitigación",
    "CET1 ratio at the failure point: the legal minimum stack":
        "Razón CET1 en el punto de quiebre: el mínimo legal apilado",
    "CET1 ratio at the jump-off (this variant runs the baseline aggregation, not a stress)":
        "Razón CET1 en el punto de partida (esta variante corre la agregación base, no un estrés)",
    "Degrees of freedom of the t copula: 4, 8 and 30 (30 approaches the Gaussian copula); a convention of the case, G.5 asks for several nu (05 l.378)":
        "Grados de libertad de la cópula t: 4, 8 y 30 (30 se acerca a la cópula gaussiana); una convención del caso, G.5 pide varios nu (05 l.378)",
    "Derived at bake time: Banco Andino's total assets (the C15 Tier 1 proxy over its equity-over-assets calibration target) over the C17 synthetic bank's stated assets, converted at the rate (decision Q5, W5)":
        "Derivado al hornear: los activos totales de Banco Andino (el sustituto del capital de nivel 1 de C15 sobre su meta de calibración de patrimonio sobre activos) sobre los activos declarados del banco sintético de C17, convertidos a la tasa (decisión Q5, W5)",
    "Derived at bake time: the observed EUR to CLP rate of the as-of date from the Banco Central de Chile (decision Q5, W5)":
        "Derivado al hornear: la tasa EUR a CLP observada en la fecha de corte, del Banco Central de Chile (decisión Q5, W5)",
    "Expected aggregate loss under the Gaussian copula, and its worst case over reweightings of the sample within the relative entropy budget":
        "Pérdida agregada esperada bajo la cópula gaussiana, y su peor caso sobre reponderaciones de la muestra dentro del presupuesto de entropía relativa",
    "Headline capital: the simple sum of the four marginals":
        "Capital principal: la suma simple de las cuatro marginales",
    "Headroom of the PE ratio over the internal target at the jump-off":
        "Holgura de la razón PE sobre la meta interna en el punto de partida",
    "Information, not capital: a diversified or bound figure shown for the validator":
        "Información, no capital: una cifra diversificada o acotada que se muestra al validador",
    "Information, not capital: an allocation of the aggregate expected shortfall shown for the validator":
        "Información, no capital: una asignación del déficit esperado agregado que se muestra al validador",
    "Information, not capital: model risk measures are sensitivity information for the validator":
        "Información, no capital: las medidas de riesgo de modelo son información de sensibilidad para el validador",
    "Information, not capital: the diversification of the Gaussian copula row against the simple sum":
        "Información, no capital: la diversificación de la fila de la cópula gaussiana contra la suma simple",
    "Mortgage to residential, consumer to credit cards and other consumer, commercial to C&I and commercial real estate (decision Q6); the weights are the case's mapping of Banco Andino's classes to Fed loan types, an adaptation and no estimate":
        "Hipotecario a residencial, consumo a tarjetas de crédito y otro consumo, comercial a C&I e inmobiliario comercial (decisión Q6); los pesos son la asignación del caso de las clases de Banco Andino a los tipos de préstamo de la Fed, una adaptación y no una estimación",
    "No scaling: the engine's Hull-White one-factor simulation runs on C15's curve and book of Banco Andino (the paths, parameters and seed of C15); the economic value lost on each path is taken per currency leg and the two legs are added (EVE is additive across the legs of one balance sheet; the standardised measure of C15 nets nothing across currencies, a rule of the prescribed shocks that a simulation of one rate factor does not need).":
        "Sin escalamiento: la simulación Hull-White de un factor del motor corre sobre la curva y la cartera de Banco Andino de C15 (las trayectorias, los parámetros y la semilla de C15); el valor económico perdido en cada trayectoria se toma por tramo de moneda y los dos tramos se suman (el EVE es aditivo entre los tramos de un balance; la medida estandarizada de C15 no compensa nada entre monedas, una regla de los choques prescritos que una simulación de un solo factor de tasa no necesita).",
    "Not computed in this variant": "No se calcula en esta variante",
    "Not computed in this variant (it runs the aggregation only)": "No se calcula en esta variante (solo corre la agregación)",
    "P2G proxy, a Contraste approximation": "Sustituto del P2G, una aproximación de Contraste",
    "Ratios only, computed from the Banco Santander-Chile Form 20-F 2025 (SEC EDGAR), cited as the source; the absolute figures are not carried (decision Q4, E5).":
        "Solo razones, calculadas del Formulario 20-F 2025 de Banco Santander-Chile (SEC EDGAR), citado como fuente; las cifras absolutas no se incluyen (decisión Q4, E5).",
    "Satellites fitted on 1985 to 2019 (1991 to 2019 for the two real estate segments), run from 2019 Q4 on the realised regressors of 2020 Q1 to 2025 Q4 and compared with the realised net charge-off rates; 2026 Q1 and Q2 are shown as realised rates only, with no forecast claim.":
        "Satélites ajustados de 1985 a 2019 (de 1991 a 2019 para los dos segmentos inmobiliarios), corridos desde 2019 T4 sobre los regresores realizados de 2020 T1 a 2025 T4 y comparados con las tasas netas de castigo realizadas; 2026 T1 y T2 se muestran solo como tasas realizadas, sin afirmar pronóstico.",
    "Smallest headroom of the PE ratio over the internal target in the stress without mitigation":
        "Menor holgura de la razón PE sobre la meta interna en el estrés sin mitigación",
    "Square-root-of-time scaling from one day to one year with 250 trading days: a convention of the case":
        "Escalamiento por raíz cuadrada del tiempo de un día a un año con 250 días hábiles de mercado: una convención del caso",
    "The C17 generator frequency scaled by assets, the loss distribution recomputed through oprisk.aggregate (Fourier aggregation of the Poisson-generalised-Pareto compound) and converted at the BCCh EUR to CLP rate of the as-of date.":
        "La frecuencia del generador de C17 escalada por activos, la distribución de pérdidas recalculada con oprisk.aggregate (agregación de Fourier del compuesto Poisson y Pareto generalizada) y convertida a la tasa EUR a CLP del BCCh de la fecha de corte.",
    "The CET1 share of the Pillar 2 requirement in the legal minimum stack (03 G.4: at most 4 percent in total, composition set bank by bank)":
        "La parte CET1 del requerimiento del Pilar 2 en el mínimo legal apilado (03 G.4: como máximo 4 por ciento en total, composición fijada banco por banco)",
    "The United States NiGEM deviations of the three years in which the policy shock acts, added to the Baseline run and transposed onto the last observed value; the satellites are US-calibrated.":
        "Las desviaciones NiGEM de Estados Unidos de los tres años en que actúa el choque de política, sumadas a la corrida Base y trasladadas al último valor observado; los satélites están calibrados en EE. UU.",
    "The adverse annual values of the United States for 2025 to 2027, read as year-end levels joined linearly from year-end 2024 (the workbook says annual averages; the year-end reading is UNVERIFIED), transposed onto the last observed value of the United States history; the satellites are US-calibrated.":
        "Los valores anuales adversos de Estados Unidos para 2025 a 2027, leídos como niveles de fin de año unidos linealmente desde fin de 2024 (la planilla dice promedios anuales; la lectura de fin de año está SIN VERIFICAR), trasladados al último valor observado de la historia de Estados Unidos; los satélites están calibrados en EE. UU.",
    "The bank's own capital for risks outside Pillar 1, at least the art. 66 quinquies requirement (03 l.152-169, decision Q4); the 4 percent cap binds the requirement p2r, never this estimate (decision W3)":
        "El capital propio del banco para riesgos fuera del Pilar 1, al menos el requerimiento del art. 66 quinquies (03 l.152-169, decisión Q4); el tope de 4 por ciento obliga al requerimiento p2r, nunca a esta estimación (decisión W3)",
    "The engine's Hull-White simulation on C15's curve and book":
        "La simulación Hull-White del motor sobre la curva y la cartera de C15",
    "The headline capital of C18 is the simple sum: the IAPE adds up the capital needed for each risk and the ECB does not recognise inter-risk diversification in the SREP":
        "El capital principal de C18 es la suma simple: el IAPE suma el capital necesario para cada riesgo y el BCE no reconoce diversificación entre riesgos en el SREP",
    "The largest absolute deviation from the 2007 Q4 value inside 2008 Q1 to 2009 Q4, read from the Federal Reserve historic table (an agency series).":
        "La mayor desviación absoluta respecto del valor de 2007 T4 dentro de 2008 T1 a 2009 T4, leída de la tabla histórica de la Reserva Federal (una serie de agencia).",
    "The market share of the 20-F RWA mix, as a ratio (decision Q5, Q4); C11's mixed-portfolio VaR and ES are scaled to the market RWA it gives, taken as the position value":
        "La parte de mercado de la mezcla de APR del 20-F, como razón (decisión Q5, Q4); el VaR y el ES de la cartera mixta de C11 se escalan a los APR de mercado que da, tomados como valor de la posición",
    "The path is a United States path transposed onto the last observed value of the United States history; the satellites are fitted on United States charge-off rates and applied to Banco Andino (decision Q6): a US-calibrated adaptation.":
        "La trayectoria es una trayectoria de Estados Unidos trasladada al último valor observado de la historia de Estados Unidos; los satélites se ajustan con tasas de castigo de Estados Unidos y se aplican a Banco Andino (decisión Q6): una adaptación calibrada en EE. UU.",
    "The policy shock acts in 2031 to 2033: zero deviation through 2030 and the first deviation in 2031 (F8 of the research addendum). NGFS is the only Phase 5 scenario NGFS itself classes as disorderly (decision E2).":
        "El choque de política actúa de 2031 a 2033: desviación cero hasta 2030 y la primera desviación en 2031 (F8 de la adenda de investigación). NGFS es el único escenario de la Fase 5 que la propia NGFS clasifica como desordenado (decisión E2).",
    "The voluntary stress buffer, component d of the internal target (03 l.152-169, decision Q4)":
        "El colchón voluntario de estrés, componente d de la meta interna (03 l.152-169, decisión Q4)",
    "oprisk.aggregate on the C17 generator parameters scaled by assets and converted at the observed rate":
        "oprisk.aggregate sobre los parámetros del generador de C17 escalados por activos y convertidos a la tasa observada",
}
