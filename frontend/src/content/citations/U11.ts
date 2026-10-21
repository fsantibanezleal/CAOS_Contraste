// The references of unit U11 (liquidity: case C16 and the Methodology section on the liquidity ladder, the LCR and the
// run of March 2023). Every entry is transcribed from research dossier 05 (section E and the source list), dossier 01
// (sections G and J.3) and the U11 research addendum (L1 and L4), where each DOI or URL was read at its primary source on
// 2026-10-04 or 2026-10-18; a published version that the dossier marks UNVERIFIED keeps its bibliographic record and the
// text says it is not confirmed. An id already in another file (fedsvb2023, defined by U10) is not repeated here.
import type { Citation } from '@fasl-work/caos-app-shell';

export const CITATIONS: Citation[] = [
  // the ECB stress test the ladder is read against
  { id: 'ecblist', label: 'ECB LiST 2019', citation: 'ECB Banking Supervision (2019). Sensitivity analysis of liquidity risk, stress test 2019: methodological note, 6 February 2019.', url: 'https://www.bankingsupervision.europa.eu/ecb/pub/pdf/ssm.ECB_sensitivity_analysis_of_liquidity_risk-stress_test_2019-methodological_note_20190206~6771e88926.en.pdf' },
  { id: 'ecblistannex', label: { en: 'ECB LiST 2019 results', es: 'Resultados de ECB LiST 2019' }, citation: 'ECB Banking Supervision (2019). Sensitivity analysis of liquidity risk, stress test 2019: final results, annex, 7 October 2019.', url: 'https://www.bankingsupervision.europa.eu/press/pr/date/2019/html/ssm.pr191007_annex~537c259b6d.en.pdf' },
  { id: 'ecbilaap', label: { en: 'ECB ILAAP guide', es: 'Guía ILAAP del BCE' }, citation: 'ECB Banking Supervision (2018). Guide to the internal liquidity adequacy assessment process (ILAAP), November 2018.', url: 'https://www.bankingsupervision.europa.eu/ecb/pub/pdf/ssm.ilaap_guide_201811.en.pdf' },
  // the Basel liquidity standards and principles
  { id: 'lcr', label: 'Basel LCR', citation: 'Basel Committee on Banking Supervision. The Basel Framework, LCR20, LCR30, LCR40 and LCR99: liquidity coverage ratio (in force 2019-12-15).', url: 'https://www.bis.org/committees/bcbs/basel-framework/standard/lcr/' },
  { id: 'nsfr', label: 'Basel NSFR', citation: 'Basel Committee on Banking Supervision. The Basel Framework, NSF20, NSF30 and NSF99: net stable funding ratio (in force 2019-12-15).', url: 'https://www.bis.org/committees/bcbs/basel-framework/standard/nsf/99/inforce/2019-12-15/published/2019-12-15' },
  { id: 'srp50', label: 'Basel SRP50', citation: 'Basel Committee on Banking Supervision. The Basel Framework, SRP50: liquidity monitoring metrics (in force 2019-12-15).', url: 'https://www.bis.org/committees/bcbs/basel-framework/standard/srp/50/inforce/2019-12-15/published/2019-12-15' },
  { id: 'bcbs144', label: 'BCBS 144', citation: 'Basel Committee on Banking Supervision (2008). Principles for sound liquidity risk management and supervision, 25 September 2008.', url: 'https://www.bis.org/publications/200809-guidelines-principles-sound-liquidity-risk-management-and-supervision' },
  { id: 'bcbs248', label: 'BCBS 248', citation: 'Basel Committee on Banking Supervision (2013). Monitoring tools for intraday liquidity management, 11 April 2013.', url: 'https://www.bis.org/publications/201304-standards-monitoring-tools-intraday-liquidity-management' },
  // the lessons of the 2023 failure
  { id: 'bcbsd555', label: 'BCBS d555', citation: 'Basel Committee on Banking Supervision (2023). Report on the 2023 banking turmoil, October 2023, Box A, Table A.1.', url: 'https://www.bis.org/bcbs/publ/d555.htm' },
  { id: 'fedmargins', label: { en: 'Federal Reserve discount window margins', es: 'Márgenes de la ventana de descuento de la Reserva Federal' }, citation: 'Federal Reserve Discount Window. Margins for securities, effective March 14, 2022 to March 12, 2023.', url: 'https://www.frbdiscountwindow.org/generalpages/historical_margins/2022/03142022_03122023_securities_table' },
  { id: 'jiang2024', label: { en: 'Jiang, Matvos, Piskorski and Seru 2024', es: 'Jiang, Matvos, Piskorski y Seru 2024' }, citation: 'Jiang, Matvos, Piskorski and Seru (2024). Journal of Financial Economics 159, 103899 (NBER Working Paper 31048).', doi: '10.1016/j.jfineco.2024.103899' },
  { id: 'cookson2026', label: { en: 'Cookson et al. 2026', es: 'Cookson et al. 2026' }, citation: 'Cookson, Fox, Gil-Bazo, Imbet and Schiller (2026). Social media as a bank run catalyst. Journal of Financial Economics 176, 104218 (SSRN 4422754).', doi: '10.1016/j.jfineco.2025.104218' },
  // the theory of the run
  { id: 'diamonddybvig1983', label: { en: 'Diamond and Dybvig 1983', es: 'Diamond y Dybvig 1983' }, citation: 'Diamond, D. W. and Dybvig, P. H. (1983). Bank runs, deposit insurance, and liquidity. Journal of Political Economy 91(3), 401-419.', doi: '10.1086/261155' },
];
