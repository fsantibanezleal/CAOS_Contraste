// The references of the Methodology sections on the proposed methods and the two published methods that have notebooks and
// engine code (adaptive conformal recalibration of the VaR, the scale-and-level complement to the PLA test, the PD anchored
// under informative withdrawals, the sequential monitors, reject inference and PC-Hazard). Every entry is transcribed from the
// reference list of the notebook that runs the method (notebooks/en/...) or of the engine page it cites (riskvalidation 1.1.0,
// docs/market/08, docs/market/09, docs/transitions/06, docs/sequential/README). The DOI or URL of each was opened on 2026-11-04
// (Crossref for MacKinnon and White, arXiv for the preprints, the NBER catalogue for Mincer and Zarnowitz); the DOIs of
// Cro et al. and Hand and Henley are the ones the engine page and the notebook print, the publisher answering the automated
// request with an access refusal, and that of Cox is the one the notebook prints. An id already in base.ts or another unit's file is not repeated here.
import type { Citation } from '@fasl-work/caos-app-shell';

export const CITATIONS: Citation[] = [
  // adaptive conformal recalibration of the VaR
  { id: 'gibbscandes2021', label: { en: 'Gibbs and Candes 2021', es: 'Gibbs y Candes 2021' }, citation: 'Gibbs, I. and Candes, E. (2021). Adaptive conformal inference under distribution shift. Advances in Neural Information Processing Systems 34. arXiv 2106.00170.', url: 'https://arxiv.org/abs/2106.00170' },
  // the scale-and-level complement to the PLA test
  { id: 'mincerzarnowitz1969', label: { en: 'Mincer and Zarnowitz 1969', es: 'Mincer y Zarnowitz 1969' }, citation: 'Mincer, J. and Zarnowitz, V. (1969). The evaluation of economic forecasts. In J. Mincer (ed.), Economic Forecasts and Expectations: Analysis of Forecasting Behavior and Performance, NBER.', url: 'https://www.nber.org/books-and-chapters/economic-forecasts-and-expectations-analysis-forecasting-behavior-and-performance' },
  { id: 'mackinnonwhite1985', label: { en: 'MacKinnon and White 1985', es: 'MacKinnon y White 1985' }, citation: 'MacKinnon, J. G. and White, H. (1985). Some heteroskedasticity-consistent covariance matrix estimators with improved finite sample properties. Journal of Econometrics 29(3), 305-325.', doi: '10.1016/0304-4076(85)90158-7' },
  // the PD anchored under informative withdrawals
  { id: 'manski1989', label: 'Manski 1989', citation: 'Manski, C. F. (1989). Anatomy of the selection problem. Journal of Human Resources 24(3).', doi: '10.2307/145818' },
  { id: 'cro2020', label: { en: 'Cro et al. 2020', es: 'Cro y otros 2020' }, citation: 'Cro, S. et al. (2020). Sensitivity analysis for clinical trials with missing continuous outcome data using controlled multiple imputation: a practical guide. Statistics in Medicine 39(21).', doi: '10.1002/sim.8569' },
  // the sequential monitors
  { id: 'ramdas2023', label: { en: 'Ramdas et al. 2023', es: 'Ramdas y otros 2023' }, citation: 'Ramdas, A., Grunwald, P., Vovk, V. and Shafer, G. (2023). Game-theoretic statistics and safe anytime-valid inference. Statistical Science 38(4), 576-601. arXiv 2210.01948.', url: 'https://arxiv.org/abs/2210.01948' },
  { id: 'wang2022ebacktesting', label: { en: 'Wang, Wang and Ziegel 2022', es: 'Wang, Wang y Ziegel 2022' }, citation: 'Wang, Wang and Ziegel (2022). E-backtesting. arXiv 2209.00991.', url: 'https://arxiv.org/abs/2209.00991' },
  // reject inference
  { id: 'banasikcrook2007', label: { en: 'Banasik and Crook 2007', es: 'Banasik y Crook 2007' }, citation: 'Banasik, J. and Crook, J. (2007). Reject inference, augmentation, and sample selection. European Journal of Operational Research 183(3), 1582-1594.', doi: '10.1016/j.ejor.2006.06.072' },
  { id: 'handhenley1993', label: { en: 'Hand and Henley 1993', es: 'Hand y Henley 1993' }, citation: 'Hand, D. J. and Henley, W. E. (1993). Can reject inference ever work? IMA Journal of Mathematics Applied in Business and Industry 5(1), 45-55.', doi: '10.1093/imaman/5.1.45' },
  { id: 'crookbanasik2004', label: { en: 'Crook and Banasik 2004', es: 'Crook y Banasik 2004' }, citation: 'Crook, J. and Banasik, J. (2004). Does reject inference really improve the performance of application scoring models? Journal of Banking and Finance 28(4), 857-874.', doi: '10.1016/j.jbankfin.2003.10.010' },
  // PC-Hazard
  { id: 'kvamme2019', label: { en: 'Kvamme and Borgan 2019', es: 'Kvamme y Borgan 2019' }, citation: 'Kvamme, H. and Borgan, O. (2019). Continuous and discrete-time survival prediction with neural networks. arXiv 1910.06724.', url: 'https://arxiv.org/abs/1910.06724' },
  { id: 'cox1972', label: 'Cox 1972', citation: 'Cox, D. R. (1972). Regression models and life-tables. Journal of the Royal Statistical Society B 34(2), 187-202.', doi: '10.1111/j.2517-6161.1972.tb00899.x' },
];
