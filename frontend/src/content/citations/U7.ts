// The references of unit U7 (portfolio credit capital: case C10 and the Methodology section on portfolio credit capital).
// Every entry is transcribed from research dossier 04 (credit-risk models, sections C.4 and H and the source list) and
// dossier 08 (data sources, row 23: the Federal Reserve charge-off release), where each DOI or URL was read at its primary
// source on 2026-10-04; a source the dossier read only through a summary keeps its bibliographic record and nothing more.
// The shell reports an entry without a DOI or URL. An id already in base.ts (gordy2003, vasicek2002, bcbs2005irb) is not
// repeated here.
import type { Citation } from '@fasl-work/caos-app-shell';

export const CITATIONS: Citation[] = [
  // the single-factor model and the regulatory formula
  { id: 'vasicek2015', label: 'Vasicek 2015', citation: 'Vasicek, O. A. (2015). Finance, Economics and Mathematics. Wiley. Reprints "Probability of Loss on Loan Portfolio" (1987, chapter 17) and "Limiting Loan Loss Probability Distribution" (1991, chapter 18).', doi: '10.1002/9781119186229' },
  // portfolio loss, risk measures and capital allocation
  { id: 'tasche2008euler', label: 'Tasche 2008', citation: 'Tasche, D. (2008). Capital allocation to business units and sub-portfolios: the Euler principle. arXiv 0708.2542 (v3, 2008-06-22).', url: 'https://arxiv.org/abs/0708.2542' },
  { id: 'tasche2009kernel', label: 'Tasche 2009b', citation: 'Tasche, D. (2009). Capital allocation for credit portfolios with kernel estimators. Quantitative Finance 9(5), 581-595.', doi: '10.1080/14697680802620599' },
  { id: 'emmertasche2005', label: { en: 'Emmer and Tasche 2005', es: 'Emmer y Tasche 2005' }, citation: 'Emmer, S. and Tasche, D. (2005). Calculating credit risk capital charges with the one-factor model. Journal of Risk 7(2), 85-101.', doi: '10.21314/jor.2005.110' },
  // structural and actuarial models
  { id: 'gupton1997', label: { en: 'Gupton et al. 1997', es: 'Gupton et al. 1997' }, citation: 'Gupton, G. M., Finger, C. C. and Bhatia, M. (1997). CreditMetrics Technical Document. J.P. Morgan; 2007 RiskMetrics Group reprint.', url: 'https://www.msci.com/documents/10199/93396227-d449-4229-9143-24a94dab122f' },
  { id: 'li2000', label: 'Li 2000', citation: 'Li, D. X. (2000). On default correlation: a copula function approach. Journal of Fixed Income 9(4), 43-54.', doi: '10.3905/jfi.2000.319253' },
  { id: 'freymcneil2003', label: { en: 'Frey and McNeil 2003', es: 'Frey y McNeil 2003' }, citation: 'Frey, R. and McNeil, A. J. (2003). Dependent defaults in models of portfolio credit risk. Journal of Risk 6(1), 59-92.', doi: '10.21314/jor.2003.089' },
  { id: 'demartamcneil2005', label: { en: 'Demarta and McNeil 2005', es: 'Demarta y McNeil 2005' }, citation: 'Demarta, S. and McNeil, A. J. (2005). The t copula and related copulas. International Statistical Review 73(1), 111-129.', doi: '10.1111/j.1751-5823.2005.tb00254.x' },
  { id: 'gordy2000', label: 'Gordy 2000', citation: 'Gordy, M. B. (2000). A comparative anatomy of credit risk models. Journal of Banking and Finance 24(1-2), 119-149. FEDS 1998-47.', doi: '10.1016/S0378-4266(99)00054-0' },
  { id: 'haaf2004', label: { en: 'Haaf et al. 2004', es: 'Haaf et al. 2004' }, citation: 'Haaf, H., Reiss, O. and Schoenmakers, J. (2004). Numerically stable computation of CreditRisk+. Journal of Risk 6(4), 1-10.', doi: '10.21314/jor.2004.097' },
  // granularity and concentration
  { id: 'gordylutkebohmert2013', label: { en: 'Gordy and Lutkebohmert 2013', es: 'Gordy y Lutkebohmert 2013' }, citation: 'Gordy, M. B. and Lutkebohmert, E. (2013). Granularity adjustment for regulatory capital assessment. International Journal of Central Banking 9(3), 33-70.', url: 'https://www.ijcb.org/sites/default/files/journal/v9n3/ijcb-v9n3-granularity-adjustment-regulatory-capital-assessment.pdf' },
  { id: 'gordymarrone2012', label: { en: 'Gordy and Marrone 2012', es: 'Gordy y Marrone 2012' }, citation: 'Gordy, M. B. and Marrone, J. (2012). Granularity adjustment for mark-to-market credit risk models. Journal of Banking and Finance 36(7), 1896-1910.', doi: '10.1016/j.jbankfin.2012.02.010' },
  { id: 'dullmann2007', label: { en: 'Dullmann and Masschelein 2007', es: 'Dullmann y Masschelein 2007' }, citation: 'Dullmann, K. and Masschelein, N. (2007). A tractable model to measure sector concentration risk in credit portfolios. Journal of Financial Services Research 32(1-2), 55-79.', doi: '10.1007/s10693-007-0014-3' },
  { id: 'bcbs2006wp15', label: { en: 'BCBS 2006 concentration studies', es: 'Estudios de concentración BCBS 2006' }, citation: 'Basel Committee on Banking Supervision (2006). Studies on credit risk concentration: an overview of the issues and a synopsis of the results from the Research Task Force project. BCBS Working Paper No. 15, November 2006.', url: 'https://www.bis.org/publ/bcbs_wp15.pdf' },
  // rare-event simulation
  { id: 'glassermanli2005', label: { en: 'Glasserman and Li 2005', es: 'Glasserman y Li 2005' }, citation: 'Glasserman, P. and Li, J. (2005). Importance sampling for portfolio credit risk. Management Science 51(11), 1643-1656.', doi: '10.1287/mnsc.1050.0415' },
  { id: 'glassermanheidelberger2002', label: { en: 'Glasserman et al. 2002', es: 'Glasserman et al. 2002' }, citation: 'Glasserman, P., Heidelberger, P. and Shahabuddin, P. (2002). Portfolio value-at-risk with heavy-tailed risk factors. Mathematical Finance 12(3), 239-269.', doi: '10.1111/1467-9965.00141' },
  // the data
  { id: 'fedchargeoff', label: { en: 'Federal Reserve charge-off release', es: 'Publicación de castigos de la Reserva Federal' }, citation: 'Board of Governors of the Federal Reserve System. Charge-off and delinquency rates on loans and leases at commercial banks, quarterly, all banks, seasonally adjusted, from 1985:Q1 (table chgallsa). Public domain.', url: 'https://www.federalreserve.gov/releases/chargeoff/' },
];
