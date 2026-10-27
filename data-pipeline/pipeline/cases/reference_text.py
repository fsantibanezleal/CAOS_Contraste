"""The reference of a validation test in both languages (U16-F6, review U16-R2 b05 M4 and the reference column of C08 to C13).

riskvalidation writes each test's ``reference`` as one English string: a citation (authors, title, venue, year, DOI, a
locator such as a section or a paragraph) with, often, a remark of the dossier attached to it. The citation stays as
published; the locator words and the remark are reader text and get their Spanish, so a Spanish view never prints an English
sentence in the reference column. ``reference_text`` returns the bilingual text the documents carry in
``extras.reference_text`` of every test row; a reference this module does not know raises, so a new engine reference cannot
reach a Spanish view untranslated.

A plan, unit or contract id inside the engine's string is not a citation (U16-R4 ruling 1): the English reader text names the
engine's ML contract in words and drops the plan unit of a research addendum ("research addendum R4", never "U9 research
addendum R4"), and the Spanish says the same. A third-party program and its function (SciPy ks_2samp, probatus
sample_similarity, QuantLib discountBondOption) is a citation and stays (ruling 2).
"""
from __future__ import annotations

import re

from typing import Any

_ECB = "ECB (2019), Instructions for reporting the validation results of internal models: IRB Pillar I models for credit risk"
_BCBS14 = "BCBS (2005), Studies on the validation of internal rating systems, Working Paper 14 (revised)"
_YN = "Yurdakul and Naranjo (2020), Statistical properties of the population stability index, Journal of Risk Model Validation 14(4), doi:10.21314/JRMV.2020.227"
_EBA23 = "EBA (2023), IFRS 9 implementation by EU institutions, 2023 Monitoring report, EBA/Rep/2023/36, doi:10.2853/269836"
_LOT = "Loterman, Brown, Martens, Mues and Baesens (2012), Benchmarking regression algorithms for loss given default modeling, Int. J. Forecasting 28(1):161-170, doi:10.1016/j.ijforecast.2011.01.006"
_QZ = "Qi and Zhao (2011), Comparison of modeling methods for Loss Given Default, J. Banking and Finance 35(11):2842-2855, doi:10.1016/j.jbankfin.2011.03.011"
_TONG = "Tong, Mues, Brown and Thomas (2016), Exposure at default models with and without the credit conversion factor, EJOR 252(3):910-920, doi:10.1016/j.ejor.2016.01.054"
_QI = "Qi (2009), Exposure at default of unsecured credit cards, OCC Economics Working Paper 2009-2, https://www.occ.gov/publications-and-resources/publications/economics/working-papers-archived/pub-econ-working-paper-2009-2.pdf"
_AG = "Anderson and Goodman (1957), Statistical inference about Markov chains, Annals of Mathematical Statistics 28(1), doi:10.1214/aoms/1177707039"
_G5 = "dossier 05 G.5 (validation tests of an economic capital model: check the allocation sums to the total, the sensitivity checks)"
_G5_ES = "dossier 05 G.5 (pruebas de validación de un modelo de capital económico: verificar que la asignación suma el total, las verificaciones de sensibilidad)"
_D06 = "dossier 06 (model risk management and validation) C.7 ML/AI validation and I.1, the validation engine catalogue"
_D06_ES = "dossier 06 (gestión del riesgo de modelo y validación) C.7 validación de ML/IA e I.1, el catálogo de pruebas del motor de validación"
_B185 = "BCBS 185 (2010), Sound practices for backtesting counterparty credit risk models"
#: the engine's ML contract by its id, as riskvalidation writes it, and in words (U16-R4 ruling 1: a contract id is a raw id)
_API = "contract engine-ml-api 2.0.0"
_API_EN = "the engine's documented ML validation interface, version 2.0.0"
_API_ES = "la interfaz documentada de validación de ML del motor, versión 2.0.0"
_D04_ES = "dossier 04 (modelos de riesgo de crédito)"
_GL19 = "BCBS (2015), Guidance on credit risk and accounting for expected credit losses (d350)"

#: English reference -> Spanish. The citation parts are verbatim; the locators and the remarks are translated.
REFERENCE_ES: dict[str, str] = {
    f"{_ECB}, Annex 3.1; Hanley and McNeil (1982), doi:10.1148/radiology.143.1.7063747":
        f"{_ECB}, Anexo 3.1; Hanley and McNeil (1982), doi:10.1148/radiology.143.1.7063747",
    f"{_ECB}, section 2.5.3.1; Brown, Cai and DasGupta (2001), doi:10.1214/ss/1009213286":
        f"{_ECB}, sección 2.5.3.1; Brown, Cai and DasGupta (2001), doi:10.1214/ss/1009213286",
    f"{_BCBS14}, section on calibration (binomial test; an early warning when defaults are correlated)":
        f"{_BCBS14}, sección sobre calibración (prueba binomial; una alerta temprana cuando los incumplimientos están correlacionados)",
    f"{_BCBS14}, appendix (one-factor model with asset correlation)":
        f"{_BCBS14}, apéndice (modelo de un factor con correlación de activos)",
    "Spiegelhalter (1986), Statistics in Medicine 5(5), doi:10.1002/sim.4780050506; formula as in the Stata brier manual":
        "Spiegelhalter (1986), Statistics in Medicine 5(5), doi:10.1002/sim.4780050506; fórmula como en el manual de brier de Stata",
    "Brier (1950), doi:10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2; Murphy (1973), doi:10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2":
        "Brier (1950), doi:10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2; Murphy (1973), doi:10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2",
    "Naeini, Cooper and Hauskrecht (2015), AAAI, doi:10.1609/aaai.v29i1.9602; Guo et al. (2017), arXiv:1706.04599":
        "Naeini, Cooper and Hauskrecht (2015), AAAI, doi:10.1609/aaai.v29i1.9602; Guo et al. (2017), arXiv:1706.04599",
    f"{_ECB}, section 2.5.5.3; Miller (1991), Communications in Statistics, Theory and Methods 20(10)":
        f"{_ECB}, sección 2.5.5.3; Miller (1991), Communications in Statistics, Theory and Methods 20(10)",
    f"{_ECB}, section 2.5.4.1 and Annex 3.1": f"{_ECB}, sección 2.5.4.1 y Anexo 3.1",
    "DeLong, DeLong and Clarke-Pearson (1988), Biometrics 44(3), doi:10.2307/2531595":
        "DeLong, DeLong and Clarke-Pearson (1988), Biometrics 44(3), doi:10.2307/2531595",
    "BCBS (2005), Working Paper 14; two-sample Kolmogorov-Smirnov statistic (SciPy ks_2samp)":
        "BCBS (2005), Working Paper 14; estadístico de Kolmogorov-Smirnov de dos muestras (SciPy ks_2samp)",
    f"{_BCBS14}, calibration (Hosmer-Lemeshow type statistic over rating grades)":
        f"{_BCBS14}, calibración (estadístico tipo Hosmer-Lemeshow sobre los grados de calificación)",
    "Hosmer and Lemeshow (1980), Communications in Statistics, Theory and Methods 9(10), doi:10.1080/03610928008827941":
        "Hosmer and Lemeshow (1980), Communications in Statistics, Theory and Methods 9(10), doi:10.1080/03610928008827941",
    _YN: _YN,
    f"{_YN}; the PSI formula applied to one characteristic (scorecard practice)":
        f"{_YN}; la fórmula del PSI aplicada a una característica (práctica de tarjeta de puntuación)",
    f"{_D06}; {_API} (C.7 l.1016-1018, I.1 l.1187); ECB guide to internal models, paragraph 43 (randomness of the training process, overfitting) and 59 (stored seeds)(a); EBA recommendation (i)":
        f"{_D06_ES}; {_API_ES} (C.7 l.1016-1018, I.1 l.1187); guía del BCE sobre modelos internos, párrafos 43 (aleatoriedad del proceso de entrenamiento, sobreajuste) y 59 (semillas almacenadas)(a); recomendación (i) de la EBA",
    f"{_D06}; {_API} (C.7 l.1041-1044, I.1 l.1196); SS1/23 principle 3.3(b)(iii); ECB guide paragraph 60":
        f"{_D06_ES}; {_API_ES} (C.7 l.1041-1044, I.1 l.1196); SS1/23 principio 3.3(b)(iii); guía del BCE párrafo 60",
    f"{_ECB}, section 2.5.5.1": f"{_ECB}, sección 2.5.5.1",
    f"{_ECB}, section 2.5.5.2; Holm (1979) adjustment across cells added by riskvalidation":
        f"{_ECB}, sección 2.5.5.2; ajuste de Holm (1979) entre celdas agregado por riskvalidation",
    f"{_AG}, section 3.2, equations (3.5) and (3.8)": f"{_AG}, sección 3.2, ecuaciones (3.5) y (3.8)",
    f"{_AG}, section 3.1, equation (3.1) and its likelihood-ratio analogue":
        f"{_AG}, sección 3.1, ecuación (3.1) y su análogo de razón de verosimilitud",
    "Tasche (2013), The art of probability-of-default curve calibration, Journal of Credit Risk 9(4), doi:10.21314/jcr.2013.169, sections 3.3 and 4.2.5; Pearson (1900), doi:10.1080/14786440009463897":
        "Tasche (2013), The art of probability-of-default curve calibration, Journal of Credit Risk 9(4), doi:10.21314/jcr.2013.169, secciones 3.3 y 4.2.5; Pearson (1900), doi:10.1080/14786440009463897",
    f"{_EBA23}, paras 114 to 118; Vasicek (2002), The distribution of loan portfolio value, Risk 15(12); Kaplan-Meier product-limit and Aalen-Johansen cumulative incidence estimators (dossier 02 B.2, C.2)":
        f"{_EBA23}, párrafos 114 a 118; Vasicek (2002), The distribution of loan portfolio value, Risk 15(12); estimadores de producto-límite de Kaplan-Meier y de incidencia acumulada de Aalen-Johansen (dossier 02 B.2, C.2)",
    f"{_EBA23}, paras 94 to 99 and Figure 42; {_GL19}, A38; dossier 02 I.2":
        f"{_EBA23}, párrafos 94 a 99 y Figura 42; {_GL19}, A38; dossier 02 I.2",
    f"{_EBA23}, paras 29 to 33; EBA (2021), IFRS 9 implementation by EU institutions, Monitoring report, EBA/Rep/2021/35, doi:10.2853/631076":
        f"{_EBA23}, párrafos 29 a 33; EBA (2021), IFRS 9 implementation by EU institutions, Monitoring report, EBA/Rep/2021/35, doi:10.2853/631076",
    f"{_EBA23}, para 97; Anderson and Goodman (1957), doi:10.1214/aoms/1177707039, equation (3.1)":
        f"{_EBA23}, párrafo 97; Anderson and Goodman (1957), doi:10.1214/aoms/1177707039, ecuación (3.1)",
    f"IFRS 9 B5.5.52; {_EBA23}, paras 100 to 104": f"IFRS 9 B5.5.52; {_EBA23}, párrafos 100 a 104",
    f"{_GL19}, para 36(a); GPPC (2016), The implementation of IFRS 9 impairment requirements by banks, 2016-06-17, 2.8.1.2; IFRS 9 5.5.17(a), B5.5.42":
        f"{_GL19}, párrafo 36(a); GPPC (2016), The implementation of IFRS 9 impairment requirements by banks, 2016-06-17, 2.8.1.2; IFRS 9 5.5.17(a), B5.5.42",
    "dossier 02 B.4 and C.1 (BCBS 2005 explanatory note; Vasicek 2002; Gordy 2003, doi:10.1016/S1042-9573(03)00040-8)":
        "dossier 02 B.4 y C.1 (nota explicativa de BCBS 2005; Vasicek 2002; Gordy 2003, doi:10.1016/S1042-9573(03)00040-8)",
    f"ECB Banking Supervision (2024), IFRS 9 overlays and model improvements for novel risks, doi:10.2866/034127; ECB letter SSM-2020-0744 (2020-12-04); {_GL19}, paras 50 and 51":
        f"ECB Banking Supervision (2024), IFRS 9 overlays and model improvements for novel risks, doi:10.2866/034127; carta del BCE SSM-2020-0744 (2020-12-04); {_GL19}, párrafos 50 y 51",
    "IFRS 7 35H and 35I; dossier 02 I.1 items 9 and 10 and I.2": "IFRS 7 35H y 35I; dossier 02 I.1 puntos 9 y 10 e I.2",
    f"{_LOT}; {_QZ}; dossier 04 F.3 (calibration by segment, not R2 alone)":
        f"{_LOT}; {_QZ}; dossier 04 F.3 (calibración por segmento, no solo R2)",
    f"{_LOT}; Spearman (1904), doi:10.2307/1412159": f"{_LOT}; Spearman (1904), doi:10.2307/1412159",
    f"{_LOT}; {_QZ}; dossier 04 F.3 (calibration over time)": f"{_LOT}; {_QZ}; dossier 04 F.3 (calibración en el tiempo)",
    f"EBA/GL/2019/03 and EBA/RTS/2018/04 are cross-references only; the add-on is Contraste's cohort-based one (dossier 04 F.4); {_LOT}":
        f"EBA/GL/2019/03 y EBA/RTS/2018/04 son solo referencias cruzadas; el ajuste es el propio de Contraste, basado en cohortes (dossier 04 F.4); {_LOT}",
    f"{_TONG}; {_QI}; dossier 04 G.1 to G.3 (the CCF estimators and their reference-date designs)":
        f"{_TONG}; {_QI}; dossier 04 G.1 a G.3 (los estimadores del CCF y sus diseños de fecha de referencia)",
    f"{_TONG}; {_QI}; dossier 04 G.3 (back-test in currency by utilisation band)":
        f"{_TONG}; {_QI}; dossier 04 G.3 (prueba retrospectiva en moneda por tramo de utilización)",
    f"exceedance counts against the Binomial(n, 1 - q) of the fitted Vasicek quantile (dossier 04 C.4; Vasicek 2002, Risk 12/2002); {_G5}":
        f"conteos de excedencias contra la Binomial(n, 1 - q) del cuantil de Vasicek ajustado (dossier 04 C.4; Vasicek 2002, Risk 12/2002); {_G5_ES}",
    f"Tasche (2008), Capital allocation to business units and sub-portfolios: the Euler principle, arXiv 0708.2542 (full allocation); {_G5}":
        f"Tasche (2008), Capital allocation to business units and sub-portfolios: the Euler principle, arXiv 0708.2542 (asignación completa); {_G5_ES}",
    f"{_G5}; dossier 04 ladder rung C2 (the Monte Carlo quantile converges to C1 within its interval)":
        f"{_G5_ES}; dossier 04 peldaño C2 de la escalera (el cuantil de Monte Carlo converge a C1 dentro de su intervalo)",
    f"Haaf, Reiss and Schoenmakers (2004), Numerically stable computation of CreditRisk+, doi:10.21314/jor.2004.097; Kolmogorov distance and its asymptotic law (Kolmogorov 1933; Smirnov 1948); {_G5}; dossier 04 ladder rung C4":
        f"Haaf, Reiss and Schoenmakers (2004), Numerically stable computation of CreditRisk+, doi:10.21314/jor.2004.097; distancia de Kolmogorov y su ley asintótica (Kolmogorov 1933; Smirnov 1948); {_G5_ES}; dossier 04 peldaño C4 de la escalera",
    f"Wilson (1927), Probable inference, the law of succession, and statistical inference, JASA 22(158):209-212; {_G5}; dossier 04 C.4 (the Vasicek correlation) on a simulator with a known truth":
        f"Wilson (1927), Probable inference, the law of succession, and statistical inference, JASA 22(158):209-212; {_G5_ES}; dossier 04 C.4 (la correlación de Vasicek) sobre un simulador con verdad conocida",
    "Kupiec (1995), J. Derivatives 3(2):73-84, doi:10.3905/jod.1995.407942":
        "Kupiec (1995), J. Derivatives 3(2):73-84, doi:10.3905/jod.1995.407942",
    "Christoffersen (1998), Int. Economic Review 39(4):841-862, doi:10.2307/2527341":
        "Christoffersen (1998), Int. Economic Review 39(4):841-862, doi:10.2307/2527341",
    "Christoffersen and Pelletier (2004), J. Financial Econometrics 2(1):84-108, doi:10.1093/jjfinec/nbh004":
        "Christoffersen and Pelletier (2004), J. Financial Econometrics 2(1):84-108, doi:10.1093/jjfinec/nbh004",
    "Engle and Manganelli (2004), J. Business and Economic Statistics 22(4):367-381, doi:10.1198/073500104000000370":
        "Engle and Manganelli (2004), J. Business and Economic Statistics 22(4):367-381, doi:10.1198/073500104000000370",
    "Acerbi and Szekely (2014), Backtesting expected shortfall, Risk, December 2014 (primary text not retrieved); the reference point -0.70 and -1.8 through Moldenhauer and Pitera, arXiv 1709.01337, section 6":
        "Acerbi and Szekely (2014), Backtesting expected shortfall, Risk, December 2014 (texto primario no recuperado); el punto de referencia -0,70 y -1,8 a través de Moldenhauer and Pitera, arXiv 1709.01337, sección 6",
    "U9 research addendum R4: the theta fit reprices today's curve, so discounted bond prices are martingales (QuantLib 1.44 hullwhite.hpp)":
        "adenda de investigación R4: el ajuste de theta revalora la curva de hoy, así que los precios descontados de bonos son martingalas (QuantLib 1.44 hullwhite.hpp)",
    "BCBS CRE53.12 and CRE53.13, Effective EE and Effective EPE (addendum R9); dossier 05 C.1":
        "BCBS CRE53.12 y CRE53.13, EE efectiva y EPE efectiva (adenda R9); dossier 05 C.1",
    "dossier 05 C.2, CVA = sum PD LGD EPE (ORE xva.tex, the advanced discretisation)":
        "dossier 05 C.2, CVA = suma PD LGD EPE (ORE xva.tex, la discretización avanzada)",
    "dossier 05, counterparty ladder: convergence in the number of paths; ORE xva.tex":
        "dossier 05, escalera de contrapartes: convergencia en el número de trayectorias; ORE xva.tex",
    "BCBS 185 paragraph 25 (reliability); Formenti, Spadafora, Terraneo and Ramponi, arXiv 1505.04593 (PIT and Anderson-Darling); critical values simulated under the model (addendum R5; Ruiz 2014 and Anfuso et al. 2014 not read)":
        "BCBS 185 párrafo 25 (confiabilidad); Formenti, Spadafora, Terraneo and Ramponi, arXiv 1505.04593 (PIT y Anderson-Darling); valores críticos simulados bajo el modelo (adenda R5; Ruiz 2014 y Anfuso et al. 2014 no leídos)",
    f"{_B185}, paragraphs 25 to 31; CRE53.33 (addendum R5)": f"{_B185}, párrafos 25 a 31; CRE53.33 (adenda R5)",
    "QuantLib 1.44 hullwhite.cpp discountBondOption (addendum R4); relative difference gate 1e-6":
        "QuantLib 1.44 hullwhite.cpp discountBondOption (adenda R4); umbral de diferencia relativa 1e-6",
    "QuantLib 1.44 jamshidianswaptionengine.cpp (addendum R4); relative difference gate 1e-6":
        "QuantLib 1.44 jamshidianswaptionengine.cpp (adenda R4); umbral de diferencia relativa 1e-6",
    "ORE 1.8.17.0 (OpenSourceRisk Engine), xva.tex and the exposure example inputs; addendum R2 and R3":
        "ORE 1.8.17.0 (OpenSourceRisk Engine), xva.tex y las entradas del ejemplo de exposición; adendas R2 y R3",
    "dossier 05 C.4 and the U9 research addendum R4: the Hull-White one-factor closed forms (QuantLib 1.44 hullwhite.cpp and jamshidianswaptionengine.cpp); ladder rung 2 against rung 3 (dossier 05, counterparty ladder)":
        "dossier 05 C.4 y la adenda de investigación R4: las formas cerradas de Hull-White de un factor (QuantLib 1.44 hullwhite.cpp y jamshidianswaptionengine.cpp); peldaño 2 de la escalera contra el peldaño 3 (dossier 05, escalera de contrapartes)",
    "BCBS MAR32.36 to MAR32.42 and MAR32.20 (dossier 01 D.4)": "BCBS MAR32.36 a MAR32.42 y MAR32.20 (dossier 01 D.4)",
    "BCBS MAR32.18 to MAR32.19 (dossier 01 D.4)": "BCBS MAR32.18 a MAR32.19 (dossier 01 D.4)",
    # C20 (the ML robustness and drift probes, U16-F12g): the engine's references of the six variants
    "Hardt, Price and Srebro (2016), Equality of opportunity in supervised learning, arXiv:1610.02413; dossier 06 (Contraste research) section C.7 l.1029-1040 l.1029-1033":
        "Hardt, Price and Srebro (2016), Equality of opportunity in supervised learning, arXiv:1610.02413; dossier 06 (investigación de Contraste) sección C.7 l.1029-1040 l.1029-1033",
    "Pearson chi-square test of homogeneity on a 2 x B contingency table (SciPy chi2_contingency)":
        "prueba chi-cuadrado de homogeneidad de Pearson sobre una tabla de contingencia de 2 x B (SciPy chi2_contingency)",
    "Two-sample Kolmogorov-Smirnov test (SciPy ks_2samp)": "prueba de Kolmogorov-Smirnov de dos muestras (SciPy ks_2samp)",
    f"dossier 04 (credit risk models) J.2 l.881-883 and ladder P4 l.968; {_D06}; {_API}":
        f"{_D04_ES} J.2 l.881-883 y peldaño P4 de la escalera l.968; {_D06_ES}; {_API_ES}",
    "dossier 04 section J.3 l.897-905; Hanley and McNeil (1982), doi:10.1148/radiology.143.1.7063747":
        "dossier 04 sección J.3 l.897-905; Hanley and McNeil (1982), doi:10.1148/radiology.143.1.7063747",
    "dossier 04 section J.3 l.897-905; Naeini, Cooper and Hauskrecht (2015), doi:10.1609/aaai.v29i1.9602":
        "dossier 04 sección J.3 l.897-905; Naeini, Cooper and Hauskrecht (2015), doi:10.1609/aaai.v29i1.9602",
    f"{_D06}; {_API} (C.7 l.1006-1008, I.1 l.1193); EBA/REP/2023/28 on machine learning for IRB models, recommendation 3; ECB paragraph 43(d), 62 and 64 to 66":
        f"{_D06_ES}; {_API_ES} (C.7 l.1006-1008, I.1 l.1193); EBA/REP/2023/28 sobre aprendizaje automático para modelos IRB, recomendación 3; BCE párrafos 43(d), 62 y 64 a 66",
    f"{_D06}; {_API} (C.7 l.1009-1012, I.1 l.1189); SR 11-7 sensitivity analysis (historical reference text, superseded in the US by SR 26-2; dossier 06 A.1): unexpectedly large changes in outputs for small changes in inputs":
        f"{_D06_ES}; {_API_ES} (C.7 l.1009-1012, I.1 l.1189); análisis de sensibilidad de SR 11-7 (texto de referencia histórico, reemplazado en EE. UU. por SR 26-2; dossier 06 A.1): cambios inesperadamente grandes en los resultados ante cambios pequeños en las entradas",
    f"{_D06}; {_API} (C.7 l.1013-1015, I.1 l.1190); PiML resilience; SS1/23 operating boundaries; Monte Carlo test against development-only draws (Phipson and Smyth 2010, doi:10.2202/1544-6115.1585)":
        f"{_D06_ES}; {_API_ES} (C.7 l.1013-1015, I.1 l.1190); resiliencia de PiML; límites de operación de SS1/23; prueba de Monte Carlo contra extracciones solo del desarrollo (Phipson and Smyth 2010, doi:10.2202/1544-6115.1585)",
    f"{_D06}; {_API} (C.7 l.1016-1018, I.1 l.1188); PiML WeakSpot": f"{_D06_ES}; {_API_ES} (C.7 l.1016-1018, I.1 l.1188); WeakSpot de PiML",
    f"{_D06}; {_API} (C.7 l.1019-1028, I.1 l.1194); Angelopoulos and Bates, arXiv 2107.07511; Vovk, Gammerman and Shafer (2022), doi:10.1007/978-3-031-06649-8":
        f"{_D06_ES}; {_API_ES} (C.7 l.1019-1028, I.1 l.1194); Angelopoulos and Bates, arXiv 2107.07511; Vovk, Gammerman and Shafer (2022), doi:10.1007/978-3-031-06649-8",
    f"{_D06}; {_API} (C.7 l.1045-1047, I.1 l.1198); ECB paragraph 52(h)(vii) and Overarching paragraph 11":
        f"{_D06_ES}; {_API_ES} (C.7 l.1045-1047, I.1 l.1198); BCE párrafo 52(h)(vii) y párrafo 11 de la parte general",
    f"{_D06}; {_API} (C.7 l.1048-1051, I.1 l.1197); dossier 07 D pattern 3 l.597-600; ING probatus sample_similarity":
        f"{_D06_ES}; {_API_ES} (C.7 l.1048-1051, I.1 l.1197); dossier 07 D patrón 3 l.597-600; ING probatus sample_similarity",
    f"{_D06}; {_API} (C.7 l.1052-1058, I.1 l.1199); NannyML CBPE, https://nannyml.readthedocs.io/en/stable/how_it_works/performance_estimation.html":
        f"{_D06_ES}; {_API_ES} (C.7 l.1052-1058, I.1 l.1199); NannyML CBPE, https://nannyml.readthedocs.io/en/stable/how_it_works/performance_estimation.html",
    f"{_D06}; {_API} (C.7 l.990: f(x) = phi_0 + sum phi_i); Lundberg and Lee (2017), arXiv 1705.07874":
        f"{_D06_ES}; {_API_ES} (C.7 l.990: f(x) = phi_0 + suma de phi_i); Lundberg and Lee (2017), arXiv 1705.07874",
    f"{_D06}; {_API} (I.1 l.1191); ECB guide to internal models, paragraph 43 (randomness of the training process, overfitting) and 59 (stored seeds)":
        f"{_D06_ES}; {_API_ES} (I.1 l.1191); guía del BCE sobre modelos internos, párrafos 43 (aleatoriedad del proceso de entrenamiento, sobreajuste) y 59 (semillas almacenadas)",
}

#: an author list in a Spanish reference joins its last two names with "y" (R5 c15 B1: "Christoffersen and Pelletier" in a Spanish
#: view is English body text, ruling 6); the match ends at the year, so a published title or journal ("Theory and Methods") keeps its words
_AUTHORS_AND = re.compile(r"(?<![\w])((?:[A-Z][\w'À-ɏ.-]+, )*[A-Z][\w'À-ɏ.-]+) and ([A-Z][\w'À-ɏ.-]+(?: et al\.)? \(\d{4}[a-z]?\))")


def _spanish_authors(text: str) -> str:
    return _AUTHORS_AND.sub(r"\1 y \2", text)


REFERENCE_ES = {k: _spanish_authors(v) for k, v in REFERENCE_ES.items()}

#: the English reader text of an engine reference: a contract id and a plan unit are said in words or dropped (U16-R4 ruling 1)
READER_EN: tuple[tuple[str, str], ...] = (
    (_API, _API_EN),
    ("U9 research addendum R4", "research addendum R4"),
)


def reader_en(reference: str) -> str:
    """The English of an engine reference as a reader sees it (``READER_EN`` applied; the citation otherwise verbatim)."""
    for raw, words in READER_EN:
        reference = reference.replace(raw, words)
    return reference


def reference_text(reference: str) -> dict[str, str]:
    """The bilingual text of one engine reference (its English through ``reader_en``); an unknown reference is an error (add it
    to ``REFERENCE_ES``)."""
    try:
        return {"en": reader_en(reference), "es": REFERENCE_ES[reference]}
    except KeyError:
        raise ValueError(f"the test reference {reference!r} has no Spanish text: add it to REFERENCE_ES") from None


def with_reference_text(tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The test rows with ``extras.reference_text`` (a copy; the input rows are not touched)."""
    out = []
    for row in tests:
        r = dict(row)
        r["extras"] = {**row.get("extras", {}), "reference_text": reference_text(row["reference"])}
        out.append(r)
    return out
