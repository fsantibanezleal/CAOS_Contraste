// The references of unit U14 (ML model validation and fair-lending disparity: cases C02, C20 and C21 and the Methodology
// section on the ML validation tests, the explainers and the fairness metrics). Every entry is transcribed from research
// dossier 06 (section C.7, A.7 to A.9 and I.6), dossier 04 (section J), dossier 07 (the SGCD dataset card) and the U14
// research addendum (H3 and H4), where each DOI or URL was read at its primary source on 2026-10-04, 2026-10-17 or
// 2026-10-18. An id already in another file (lundberg2017, lundberg2020, lou2013, nori2019, kozodoi2022, yurdakul2020,
// delong1988, naeini2015, sr117, ss123, egim, aiact, regb) is not repeated here.
import type { Citation } from '@fasl-work/caos-app-shell';

export const CITATIONS: Citation[] = [
  // the explainers
  { id: 'friedman2001', label: { en: 'Friedman 2001', es: 'Friedman 2001' }, citation: 'Friedman, J. H. (2001). Greedy function approximation: A gradient boosting machine. Annals of Statistics 29(5).', doi: '10.1214/aos/1013203451' },
  { id: 'goldstein2015', label: { en: 'Goldstein et al. 2015', es: 'Goldstein et al. 2015' }, citation: 'Goldstein, A., Kapelner, A., Bleich, J., Pitkin, E. (2015). Peeking inside the black box: Visualizing statistical learning with plots of individual conditional expectation. Journal of Computational and Graphical Statistics 24(1), 44-65.', doi: '10.1080/10618600.2014.907095' },
  { id: 'apleyzhu2020', label: { en: 'Apley and Zhu 2020', es: 'Apley y Zhu 2020' }, citation: 'Apley, D. W., Zhu, J. (2020). Visualizing the effects of predictor variables in black box supervised learning models. Journal of the Royal Statistical Society B 82(4), 1059-1086.', doi: '10.1111/rssb.12377' },
  // conformal prediction and the label-free estimate
  { id: 'angelopoulos2021', label: { en: 'Angelopoulos and Bates 2021', es: 'Angelopoulos y Bates 2021' }, citation: 'Angelopoulos, A. N., Bates, S. (2021). A gentle introduction to conformal prediction and distribution-free uncertainty quantification. arXiv 2107.07511.', doi: '10.48550/arXiv.2107.07511' },
  { id: 'vovk2022', label: { en: 'Vovk, Gammerman and Shafer 2022', es: 'Vovk, Gammerman y Shafer 2022' }, citation: 'Vovk, V., Gammerman, A., Shafer, G. (2022). Algorithmic Learning in a Random World, 2nd ed. Springer.', doi: '10.1007/978-3-031-06649-8' },
  { id: 'nannyml', label: 'NannyML CBPE', citation: 'NannyML documentation. Performance estimation: confidence-based performance estimation (CBPE), how it works.', url: 'https://nannyml.readthedocs.io/en/stable/how_it_works/performance_estimation.html' },
  // the fairness metrics and the legal sentences
  { id: 'hardt2016', label: { en: 'Hardt, Price and Srebro 2016', es: 'Hardt, Price y Srebro 2016' }, citation: 'Hardt, M., Price, E., Srebro, N. (2016). Equality of opportunity in supervised learning. NeurIPS 2016. arXiv 1610.02413.', doi: '10.48550/arXiv.1610.02413' },
  { id: 'feldman2015', label: { en: 'Feldman et al. 2015', es: 'Feldman et al. 2015' }, citation: 'Feldman, M., Friedler, S. A., Moeller, J., Scheidegger, C., Venkatasubramanian, S. (2015). Certifying and removing disparate impact. KDD 2015.', doi: '10.1145/2783258.2783311' },
  { id: 'cfr1607', label: '29 CFR 1607.4', citation: 'Uniform Guidelines on Employee Selection Procedures, 29 CFR 1607.4(D): evidence of adverse impact, the four-fifths rule.', url: 'https://www.law.cornell.edu/cfr/text/29/1607.4' },
  { id: 'fr202607804', label: { en: 'Regulation B final rule 2026', es: 'Regla final de la Regulación B 2026' }, citation: 'Consumer Financial Protection Bureau (2026). Equal Credit Opportunity Act (Regulation B), final rule. 91 FR 21620, 2026-04-22, effective 2026-07-21.', url: 'https://www.govinfo.gov/content/pkg/FR-2026-04-22/pdf/2026-07804.pdf' },
  { id: 'fha3605', label: '42 U.S.C. 3605', citation: 'Fair Housing Act, 42 U.S.C. 3605(a): discrimination in residential real estate-related transactions.', url: 'https://www.law.cornell.edu/uscode/text/42/3605' },
  { id: 'interagency2009', label: { en: 'Interagency Fair Lending Examination Procedures', es: 'Procedimientos interagenciales de examen de crédito justo' }, citation: 'OCC, FDIC, Federal Reserve Board, OTS and NCUA (2009). Interagency Fair Lending Examination Procedures, August 2009 (attachment to CA letter 09-6).', url: 'https://www.federalreserve.gov/boarddocs/caletters/2009/0906/09-06_attachment.pdf' },
  // the supervisory reading of machine learning and the data card
  { id: 'ebarep202328', label: { en: 'EBA report on machine learning for IRB models', es: 'Informe de la EBA sobre aprendizaje automático para modelos IRB' }, citation: 'European Banking Authority (2023). Follow-up report on machine learning for IRB models, EBA/REP/2023/28, August 2023.', url: 'https://www.eba.europa.eu/sites/default/files/document_library/Publications/Reports/2023/1061483/Follow-up%20report%20on%20machine%20learning%20for%20IRB%20models.pdf' },
  { id: 'nistai1001', label: 'NIST AI RMF 1.0', citation: 'National Institute of Standards and Technology (2023). Artificial Intelligence Risk Management Framework (AI RMF 1.0), NIST AI 100-1, 2023-01-26.', doi: '10.6028/NIST.AI.100-1' },
  { id: 'sgcd', label: { en: 'SGCD dataset card', es: 'Ficha del conjunto SGCD' }, citation: 'SantanderAI. sota-stressed-datasets: Stressed German Credit Dataset (SGCD-v0.1), dataset card, codebook and metadata, at commit 8403fa9. Data CC BY 4.0, tooling Apache-2.0.', url: 'https://github.com/SantanderAI/sota-stressed-datasets' },
];
