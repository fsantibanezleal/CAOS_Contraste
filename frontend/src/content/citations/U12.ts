// The references of unit U12 (operational risk: case C17 and the Methodology section on the loss distribution approach,
// the single loss approximation and the Basel III standardised approach). Every entry is transcribed from research
// dossier 05 (section F: F.1 to F.6, where Shevchenko 2010 was verified from arXiv 1008.1108 and the BCBS 160 text from
// the BIS PDF) and dossier 01 (section F: OPE25, in force 2023-01-01, published 2024-07-05), each DOI or URL as the
// dossier gives it. A source the dossier gives without a DOI or URL (Bocker and Kluppelberg 2005; Bocker and Sprittulla
// 2006) is named in the text and not listed here: the shell reports an entry without one. An id already in base.ts or
// another unit's file is not repeated here.
import type { Citation } from '@fasl-work/caos-app-shell';

export const CITATIONS: Citation[] = [
  // the framework: the standardised approach and the removal of the advanced measurement approach
  { id: 'ope25', label: 'Basel OPE25', citation: 'Basel Committee on Banking Supervision. The Basel Framework, OPE25: operational risk, standardised approach (in force 2023-01-01, published 2024-07-05).', url: 'https://www.bis.org/committees/bcbs/basel-framework/standard/ope/25/inforce/2023-01-01/published/2024-07-05' },
  { id: 'bcbsd355', label: 'BCBS d355', citation: 'Basel Committee on Banking Supervision (2016). Standardised Measurement Approach for operational risk, consultative document, 2016-03-04, BCBS d355.', url: 'https://www.bis.org/bcbs/publ/d355.htm' },
  { id: 'bcbsd424', label: 'BCBS d424', citation: 'Basel Committee on Banking Supervision (2017). Basel III: Finalising post-crisis reforms, December 2017, BCBS d424.', url: 'https://www.bis.org/bcbs/publ/d424.htm' },
  { id: 'peters2016', label: 'Peters et al. 2016', citation: 'Peters, G. W., Shevchenko, P. V., Hassani, B. and Chapelle, A. (2016). Journal of Operational Risk 11(3), 1-49: a critical response to the Standardised Measurement Approach proposal (less risk sensitive, can be unstable).', url: 'https://arxiv.org/abs/1607.02319' },
  { id: 'mignola2016', label: 'Mignola et al. 2016', citation: 'Mignola, G., Ugoccioni, R. and Cope, E. (2016). Journal of Operational Risk 11(3), 51-69: a critical response to the Standardised Measurement Approach proposal.', doi: '10.21314/JOP.2016.184' },
  // the loss distribution approach
  { id: 'chavez2006', label: { en: 'Chavez-Demoulin et al. 2006', es: 'Chavez-Demoulin et al. 2006' }, citation: 'Chavez-Demoulin, V., Embrechts, P. and Neslehova, J. (2006). Quantitative models for operational risk: extremes, dependence and aggregation. Journal of Banking and Finance 30(10), 2635-2658.', doi: '10.1016/j.jbankfin.2005.11.008' },
  { id: 'mignola2007', label: { en: 'Mignola and Ugoccioni 2007', es: 'Mignola y Ugoccioni 2007' }, citation: 'Mignola, G. and Ugoccioni, R. (2007). Journal of Operational Risk 1(4), 35-47: the severity above a reporting threshold fitted as a truncated distribution with the frequency rescaled.', doi: '10.21314/JOP.2006.019' },
  { id: 'cope2009', label: 'Cope et al. 2009', citation: 'Cope, E. W., Mignola, G., Antonini, G. and Ugoccioni, R. (2009). Challenges and pitfalls in measuring operational risk from loss data. Journal of Operational Risk 4(4), 3-27.', doi: '10.21314/JOP.2009.069' },
  // aggregation: Panjer, FFT and the single loss approximation
  { id: 'panjer1981', label: 'Panjer 1981', citation: 'Panjer, H. H. (1981). ASTIN Bulletin 12(1), 22-26: the recursion for compound distributions with a frequency of the (a, b, 0) class.', doi: '10.1017/S0515036100006796' },
  { id: 'shevchenko2010', label: 'Shevchenko 2010', citation: 'Shevchenko, P. V. (2010). Journal of Operational Risk 5(2), 3-40 (arXiv 1008.1108): Monte Carlo, Panjer recursion and FFT for the aggregate loss, with the Poisson(100) and LN(0, 2) benchmark of Example 9.4 and Table 2.', doi: '10.21314/JOP.2010.077' },
  { id: 'degen2010', label: 'Degen 2010', citation: 'Degen, M. (2010). Journal of Operational Risk 5(4), 3-17: the single loss approximation as a function of the tail index, with a problematic zone near a tail index of 1.', doi: '10.21314/JOP.2010.084' },
  { id: 'peters2013', label: { en: 'Peters et al. 2013', es: 'Peters et al. 2013' }, citation: 'Peters, G. W., Targino, R. S. and Shevchenko, P. V. (2013). Second-order expansions of the single loss approximation (arXiv 1303.2910).', url: 'https://arxiv.org/abs/1303.2910' },
  // scenarios and calibration
  { id: 'shevchenko2006', label: { en: 'Shevchenko and Wuthrich 2006', es: 'Shevchenko y Wuthrich 2006' }, citation: 'Shevchenko, P. V. and Wuthrich, M. V. (2006). The structural modeling of operational risk via Bayesian inference: combining loss data with expert opinions. Journal of Operational Risk 1(3), 3-26.', doi: '10.21314/JOP.2006.016' },
  { id: 'shevchenko2011', label: 'Shevchenko 2011', citation: 'Shevchenko, P. V. (2011). Modelling Operational Risk Using Bayesian Inference. Springer.', doi: '10.1007/978-3-642-15923-7' },
  { id: 'bcbs160', label: 'BCBS 160', citation: 'Basel Committee on Banking Supervision (2009). Results from the 2008 Loss Data Collection Exercise for Operational Risk, 2009-07-28, BCBS 160.', url: 'https://www.bis.org/publ/bcbs160.htm' },
];
