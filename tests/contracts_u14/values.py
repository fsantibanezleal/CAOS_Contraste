"""Values shared by the U14-S builders and tests: the proposed named parameters (decision Q8, conventions and never
regulatory), the HMDA field names (U14 research addendum H1), the legal mapping (H3 section 5) and the quoted sentences (H3 4.1, 4.3)."""
from __future__ import annotations

# Q8: proposed from the sample sizes of the sizing (Machine limits): Taiwan 30,000 rows, German credit 1,000, SGCD 1,000,
# Polish files 5,910 to 10,503 rows with 271 to 515 events, each Fed portfolio 200 loans. The main session approves them.
NAMED = {
    "perturbation_grid": ([0.05, 0.1, 0.25, 0.5, 1.0], "multiple of each feature's standard deviation",
                          "Noise scales for the perturbation robustness grid (06 C.7 l.1009-1012 gives the construction, no values)."),
    "perturbation_tolerance": (0.02, "AUC points", "Degradation of AUC tolerated at the preset scale 0.1; about 2.5 standard errors of an AUC on the Taiwan holdout (about 6,000 holdout rows)."),
    "n_seeds": (20, "retraining seeds", "Seeds of the seed sweep (06 I.1 l.1191 gives none); 20 gives a standard deviation of the AUC with a relative error near 16 percent."),
    "n_bootstrap_refits": (100, "bootstrap refits", "Refits of the reason-code stability (04 J.2 l.881-883 gives none)."),
    "overfit_tolerance": (0.05, "AUC points", "Train minus test AUC gap beyond which the overfit flag is raised (06 C.7 l.1016-1018 gives no value)."),
    "weak_spot_multiple": (2.0, "multiple of the average test error", "k: a slice is a weak spot when its test error exceeds k times the average (06 C.7 l.1016-1018)."),
    "shift_score": ("resemblance-classifier-probability", "name of the score", "The shift score ranking subsamples; a classifier of development against evaluation rows (06 C.7 l.1048-1051 resemblance AUC)."),
    "worst_subsample_share": (0.10, "share of the evaluation rows", "The dossier's example is the worst 10 percent (06 C.7 l.1013-1014)."),
    "decision_cutoff_reject_share": (0.20, "share of baseline decisions declined", "The cut-off is the baseline score quantile that declines this share; held fixed under every shift (decision Q10)."),
}
C20_NAMES = list(NAMED)
C02_NAMES = ["overfit_tolerance"]

# U14 research addendum H1 (sections 2.2 and 2.4), snapshot spellings.
ATTRIBUTE_FIELDS = ["derived_race", "derived_ethnicity", "derived_sex", "applicant_age"]
CONTROL_FIELDS = ["debt_to_income_ratio", "combined_loan_to_value_ratio", "income", "loan_amount", "property_value", "loan_type",
                  "loan_purpose", "lien_status", "occupancy_type"]
OTHER_FIELDS = ["applicant_age_above_62", "action_taken", "rate_spread", "denial_reason_1", "denial_reason_2", "denial_reason_3",
                "denial_reason_4"]
HMDA_FIELDS = ATTRIBUTE_FIELDS + CONTROL_FIELDS + OTHER_FIELDS
# H3 section 5: field, basis, ecoa, fha (age is ECOA only; ethnicity maps to national origin by convention, UNVERIFIED).
LEGAL = {
    "derived_race": ("race_color", True, True),
    "derived_ethnicity": ("national_origin_nearest_UNVERIFIED", True, True),
    "derived_sex": ("sex", True, True),
    "applicant_age": ("age_ecoa_only", True, False),
}
# H3 section 5, column "Theory and role": "disparate impact under the FHA only" for race, ethnicity and sex; age is ECOA only.
FHA_DI = ("not assessed (disparate impact under the FHA only; gross HMDA disparities are not appropriate for disproportionate adverse "
          "impact analysis, Interagency Procedures appendix, printed page 26)")
FHA_DI_AGE = "not applicable (age is a prohibited basis under ECOA only, not in 42 U.S.C. 3605(a))"
FHA_DISPARATE_IMPACT = {"derived_race": FHA_DI, "derived_ethnicity": FHA_DI, "derived_sex": FHA_DI, "applicant_age": FHA_DI_AGE}
GROUPS = {
    "derived_race": ["American Indian or Alaska Native", "Asian", "Black or African American",
                     "Native Hawaiian or Other Pacific Islander", "White", "2 or more minority races"],
    "derived_ethnicity": ["Hispanic or Latino", "Not Hispanic or Latino"],
    "derived_sex": ["Male", "Female"],
    "applicant_age": ["<25", "25-34", "35-44", "45-54", "55-64", "65-74", ">74"],
}
NON_GROUPS = {
    "derived_race": ["Joint", "Free Form Text Only", "Race Not Available"],
    "derived_ethnicity": ["Joint", "Free Form Text Only", "Ethnicity Not Available"],
    "derived_sex": ["Joint", "Sex Not Available"],
    "applicant_age": ["8888"],
}
TREATMENTS = ["unmodified", "binned", "rounded", "top-coded", "bottom-coded", "withheld", "not-applicable"]

QUOTES = {
    "reg_b": ("12 CFR 1002.6(a), as amended at 91 FR 21668 (2026-04-22, effective 2026-07-21)",
              "The Act does not provide that the 'effects test' applies for determining whether there is discrimination in violation of the Act."),
    "fha": ("91 FR 21620, recital of Texas Department of Housing & Community Affairs v. Inclusive Communities Project, Inc.",
            "the Supreme Court held that disparate-impact claims are cognizable under the Fair Housing Act (FHA)."),
    "procedures": ("Interagency Fair Lending Examination Procedures, August 2009, appendix, printed page 26",
                   "Gross HMDA denial or approval rate disparities are not appropriate for disproportionate adverse impact analysis because they typically cannot be attributed to a specific policy or criterion."),
}
SGCD_QUOTE = ("It is provided for research and benchmarking only and must not be used for real-world credit scoring or any "
              "production decision-making about individuals.")
SGCD_COMMIT = "8403fa9048f7159d51a0cec5a2d9a2e9712662bd"
FAIR_TESTS = ["fair.equalized_odds", "fair.equal_opportunity", "fair.calibration_within_groups", "fair.auc_by_group"]

# The tests a C21 document may carry (decision C2 and Q5): an allowlist, never a denylist of the outcome-conditioned ones.
C21_TESTS = ["fair.demographic_parity", "fair.adverse_impact", "fair.two_proportion_z", "fair.fisher_exact", "fair.conditional_disparity",
             "fair.rate_spread_disparity", "fair.replication", "fair.situation_testing"]
FAIR_ATTRIBUTES = ["sex", "age", "marital_status"]

# Decision V3: public HMDA withholds the loan identifier and the dates (addendum H1 2.5), so the reader writes two named conventions.
HMDA_ID_RULE = "<activity_year>-<row>"
HMDA_DATE_RULE = "<activity_year>-12-31"
# Decision C7 (addendum H2 3.3): the data licence stays UNVERIFIED; the views quote the platform software terms and the CFPB statement.
HMDA_PLATFORM_TERMS = ("As a work of the United States Government, this package (excluding any exceptions listed below) is in the public domain "
                       "within the United States. Additionally, we waive copyright and related rights in the work worldwide through the CC0 "
                       "1.0 Universal public domain dedication.")
HMDA_MODIFIED = "The publicly available data are modified to protect applicants' and borrowers' privacy"

HORIZON_YEARS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "pooled": None}
PAIRS = {f"{y}-{str(y + 1)[2:]}": (y, y + 1) for y in range(2018, 2024)}
