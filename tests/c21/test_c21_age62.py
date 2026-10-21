"""BL-087 (U16-P3): the contrast of applicants 62 and over against applicants under 62 (Regulation B 1002.6(b)(2)), beside the age bands.

The new attribute is ``applicant_age_above_62`` (HMDA values ``Yes``, ``No``, ``NA``). Its groups are ``62 or over`` and ``under 62``, its
reference group is ``under 62`` (a convention) and ``NA`` is its own excluded group. Every statistic comes from the engine calls the other
attributes use; the old contrasts, tests and models stay byte-identical (digests of ``data/age62-baseline.json``, made from the documents
before this unit).
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import contract_schemas as cs
import pytest
from c21_support import API_HEADER, C21, MODELS, PAIRS, ROOT, VARIANTS, committed, make_year, semantics, write_file

from pipeline.cases.c21 import bake, legal, reader

FIELD = "applicant_age_above_62"
GROUPS = ("62 or over", "under 62")
OLD_FIELDS = ("derived_race", "derived_ethnicity", "derived_sex", "applicant_age")
SEG = f"{FIELD}|62 or over vs under 62"
BASELINE = json.loads((Path(__file__).resolve().parent / "data" / "age62-baseline.json").read_text(encoding="utf-8"))
ECFR = "https://www.ecfr.gov/current/title-12/chapter-X/part-1002/section-1002.6"
ECFR_DATED = "https://www.ecfr.gov/on/2026-09-01/title-12/chapter-X/part-1002/section-1002.6"
QUOTE_II = ("In an empirically derived, demonstrably and statistically sound, credit scoring system, a creditor may use an applicant's age "
            "as a predictive variable, provided that the age of an elderly applicant is not assigned a negative factor or value.")
QUOTE_IV = ("In any system of evaluating creditworthiness, a creditor may consider the age of an elderly applicant when such age is used "
            "to favor the elderly applicant in extending credit.")
ELDERLY = "Elderly means age 62 or older."


def _file(path: Path, rows: list[list[str]]) -> Path:
    write_file(path, rows)
    return path


def digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def attr(doc: dict, field: str) -> dict:
    return next(a for a in doc["outputs"]["attributes"] if a["field"] == field)


# --- 1 the attribute, its groups and its reference ----------------------------------------------------------------------------
def test_the_attribute_its_groups_its_reference_and_its_excluded_group_are_declared() -> None:
    assert legal.ATTRIBUTES == (*OLD_FIELDS, FIELD)
    assert legal.GROUPS[FIELD] == GROUPS and legal.NON_GROUPS[FIELD] == ("NA",) and legal.REFERENCE[FIELD] == "under 62"
    assert legal.BASIS[FIELD] == ("age_ecoa_only", True, False)
    assert legal.attribute_legal(FIELD)["fha_disparate_impact"] == legal.FHA_DISPARATE_IMPACT_AGE
    assert not set(legal.GROUPS[FIELD]) & set(legal.NON_GROUPS[FIELD])
    assert {f: legal.REFERENCE[f] for f in OLD_FIELDS} == {"derived_race": "White", "derived_ethnicity": "Not Hispanic or Latino",
                                                          "derived_sex": "Male", "applicant_age": "35-44"}
    assert legal.GROUPS["applicant_age"] == ("<25", "25-34", "35-44", "45-54", "55-64", "65-74", ">74")


def test_adversarial_the_reader_maps_yes_no_na_to_the_groups_and_refuses_another_value_or_a_missing_column(tmp_path: Path) -> None:
    rows = [list(r) for r in make_year(2019, 400)]
    col = API_HEADER.index(FIELD)
    assert {r[col] for r in rows} == {"Yes", "No", "NA"}
    y = reader.read_year(_file(tmp_path / "f.csv", rows), 2019)
    got = {r[FIELD] for r in y.rows}
    assert got == {"62 or over", "under 62", "NA"}
    n_yes = sum(1 for r in rows if r[API_HEADER.index("action_taken")] in ("1", "2", "3") and r[col] == "Yes")
    assert sum(1 for r in y.rows if r[FIELD] == "62 or over") == n_yes > 0
    bad = [list(r) for r in rows]
    bad[3][col] = "Maybe"
    with pytest.raises(reader.HmdaFormatError, match=FIELD):
        reader.read_year(_file(tmp_path / "g.csv", bad), 2019)
    keep = [i for i, h in enumerate(API_HEADER) if h != FIELD]
    write_file(tmp_path / "h.csv", [[r[i] for i in keep] for r in rows], [API_HEADER[i] for i in keep])
    with pytest.raises(reader.HmdaFormatError, match=FIELD):
        reader.read_year(tmp_path / "h.csv", 2019)


def test_contract_1_carries_the_new_field_as_an_enum() -> None:
    fields = {f.name: f for f in reader.CONTRACT_FIELDS}
    assert FIELD in fields and set(fields[FIELD].values) == {"62 or over", "under 62", "NA"}


# --- 2 the NA exclusion and the not-evaluated state --------------------------------------------------------------------------
def test_na_is_an_excluded_group_counted_apart_and_never_in_a_pairwise_test() -> None:
    for name in VARIANTS:
        doc = committed(name)
        a = attr(doc, FIELD)
        assert [g["group"] for g in a["groups"]] == list(GROUPS) and a["reference_group"] == "under 62"
        assert [e["group"] for e in a["excluded_groups"]] == ["NA"] and a["excluded_groups"][0]["n"] > 0
        assert sum(g["n"] for g in a["groups"]) + a["excluded_groups"][0]["n"] == doc["outputs"]["scope"]["rows_fit"]
        assert [c["group"] for c in a["contrasts"]] == ["62 or over"] and a["contrasts"][0]["reference_group"] == "under 62"
        assert all("NA" not in r["segment"] for r in doc["tests"] if r["segment"].startswith(FIELD))


def test_adversarial_a_pair_without_one_group_is_not_evaluated_with_its_reason_and_no_test_runs_on_an_empty_group(tmp_path: Path) -> None:
    rows = [list(r) for r in make_year(2019, 600)]
    col = API_HEADER.index(FIELD)
    for r in rows:
        if r[col] == "Yes":
            r[col] = "NA"          # no applicant 62 or over has a decision: the group is empty
    y = reader.read_year(_file(tmp_path / "f.csv", rows), 2019)
    s = reader.to_sample(y)
    from pipeline.cases.c21 import estimates as est

    reason = est.not_evaluated(FIELD, s)
    assert reason is not None and "62 or over" in reason["en"] and "62 o más" in reason["es"]
    notes = {n["field"]: n for n in est.data_notes(s, y.action_counts)}
    assert "not evaluated" in notes[FIELD]["reason"]["en"] and "no evaluado" in notes[FIELD]["reason"]["es"]
    assert notes[FIELD]["n_missing"] == sum(1 for r in y.rows if r[FIELD] == "NA")
    full = reader.to_sample(reader.read_year(_planted(tmp_path), 2019))
    assert est.not_evaluated(FIELD, full) is None
    with pytest.raises(ValueError, match="no decision row"):
        est.attribute_result(FIELD, s, est.build_design(s), s, est.build_design(s))


def _planted(tmp_path: Path) -> Path:
    return _file(tmp_path / "full.csv", make_year(2019, 600))


# --- 3 the contrast rows in every pair document ---------------------------------------------------------------------------------
def test_every_pair_document_carries_every_row_of_the_other_attributes_for_the_new_contrast() -> None:
    for name in VARIANTS:
        doc = committed(name)
        c = attr(doc, FIELD)["contrasts"][0]
        for key in ("adverse_impact_ratio", "z_test", "fisher_exact", "controlled", "rate_spread", "confirmation"):
            assert key in c, (name, key)
        assert c["n_group"] > 0 and c["n_reference"] > 0
        assert c["controlled"]["estimate"] is not None and c["rate_spread"]["estimate"] is not None
        ids = {(r["test_id"], r["segment"]) for r in doc["tests"] if r["segment"].startswith(FIELD)}
        assert ids == {("fair.demographic_parity", FIELD), ("fair.adverse_impact", FIELD), ("fair.two_proportion_z", SEG),
                       ("fair.fisher_exact", SEG), ("fair.conditional_disparity", SEG), ("fair.rate_spread_disparity", SEG),
                       ("fair.replication", f"{SEG}|controlled"), ("fair.replication", f"{SEG}|rate_spread")}, name
        assert all(r["notes"].count("no legal claim") >= 1 for r in doc["tests"] if r["segment"].startswith(FIELD))
        assert FIELD in {n["field"] for n in doc["outputs"]["data_notes"]}
        assert any(f for f in doc["findings"]) and all("no legal claim" in f["title"]["en"] for f in doc["findings"])


def test_the_new_contrast_is_the_engines_own_number_on_the_group_counts() -> None:
    from fractions import Fraction

    for name in VARIANTS:
        a = attr(committed(name), FIELD)
        counts = {g["group"]: (g["n_approved"], g["n"]) for g in a["groups"]}
        (x1, n1), (x2, n2) = counts["62 or over"], counts["under 62"]
        c = a["contrasts"][0]
        assert c["selection_rate_group"] == pytest.approx(x1 / n1, abs=1e-12) and c["selection_rate_reference"] == pytest.approx(x2 / n2, abs=1e-12)
        assert c["parity_ratio"] == pytest.approx((x1 / n1) / (x2 / n2), rel=1e-9)
        flag = {r["group"]: r["flag"] for r in a["four_fifths"]["groups"]}
        top = max(counts, key=lambda g: Fraction(*counts[g]))
        assert a["four_fifths"]["highest_rate_group"] == top
        xh, nh = counts[top]
        for g, (x, n) in counts.items():
            assert flag[g] == (5 * x * nh < 4 * xh * n)


# --- 4 the 1002.6(b)(2) text and its source ------------------------------------------------------------------------------------
def test_the_regulation_text_is_transcribed_from_the_ecfr_with_its_url_in_both_languages() -> None:
    assert legal.AGE62_SOURCE == ECFR
    assert legal.AGE62_QUOTES["1002.6(b)(2)(ii)"] == QUOTE_II and legal.AGE62_QUOTES["1002.6(b)(2)(iv)"] == QUOTE_IV
    assert legal.AGE62_QUOTES["1002.2(o)"] == ELDERLY
    for name in VARIANTS:
        note = attr(committed(name), FIELD)["legal"]["note"]
        for lang in ("en", "es"):
            text = note[lang]
            assert ECFR in text and ECFR_DATED in text and "2026-09-01" in text and QUOTE_II in text and QUOTE_IV in text and ELDERLY in text, (name, lang)
            assert "1002.6(b)(2)" in text
            assert "negative factor or value" in text or "factor o valor negativo" in text   # the proviso of (b)(2)(ii) stays in the summary
        assert "no legal claim" in note["en"] and "convention" in note["en"] and "convención" in note["es"] and "sin afirmación legal" in note["es"]
        assert "mide" in note["es"] or "medición" in note["es"]
        assert "cita en inglés" in note["es"] and "no genera un hallazgo" in note["es"] and "raises no finding" in note["en"]


def test_the_models_document_names_the_field_as_an_attribute() -> None:
    fields = {f["name"]: f for f in committed(MODELS)["fit"]["fields"]}
    assert fields[FIELD]["role"] == "attribute" and fields[FIELD]["alias"] is None
    terms = {t["term"] for m in committed(MODELS)["fit"]["decision_models"] for t in m["terms"]}
    assert f"{FIELD}=62 or over" in terms


# --- 5 the old contrasts are byte-identical -----------------------------------------------------------------------------------------
def test_adversarial_every_old_contrast_test_and_model_is_byte_identical_to_the_documents_before_this_unit() -> None:
    for name in VARIANTS:
        doc = committed(name)
        want = BASELINE[name]
        o = doc["outputs"]
        assert digest([attr(doc, f) for f in OLD_FIELDS]) == want["attributes"], name
        assert digest(o["situation_testing"]) == want["situation_testing"], name
        conv = {k: v for k, v in o["conventions"].items() if k != "group_exclusion"}     # the reference-group sentence names the new reference
        assert digest({**{k: o[k] for k in ("kind", "pair_id", "fit_year", "confirm_year", "scope", "legal", "licence")}, "conventions": conv}) == want["head"]
        assert "under 62" in o["conventions"]["group_exclusion"]["en"] and "menores de 62" in o["conventions"]["group_exclusion"]["es"]
        assert digest([r for r in doc["tests"] if not r["segment"].startswith(FIELD) and r["test_id"] != "fair.situation_testing"]) == want["tests"]
        assert digest([r for r in doc["tests"] if r["test_id"] == "fair.situation_testing"]) == want["situation_tests"]
        assert digest([n for n in o["data_notes"] if n["field"] != FIELD]) == want["data_notes"], name
    m = committed(MODELS)["fit"]
    assert digest([d for d in m["decision_models"] if not any(t["term"].startswith(FIELD) for t in d["terms"])]) == BASELINE[MODELS]["decision_models"]
    assert digest([f for f in m["fields"] if f["name"] != FIELD]) == BASELINE[MODELS]["fields"]


# --- 6 the schema refuses an unknown group and an unknown field -----------------------------------------------------------------------
def test_adversarial_the_schema_refuses_an_unknown_group_a_reference_of_another_attribute_and_a_wrong_basis() -> None:
    doc = committed(VARIANTS[0])
    path = C21 / f"{VARIANTS[0]}.json"
    ref = cs.schema_for_document(path, doc)
    assert list(cs.errors(ref, doc)) == []
    i = next(k for k, a in enumerate(doc["outputs"]["attributes"]) if a["field"] == FIELD)

    def broken(mutate) -> list:
        bad = copy.deepcopy(doc)
        mutate(bad["outputs"]["attributes"][i])
        return list(cs.errors(ref, bad))

    assert broken(lambda a: a["groups"][0].update(group="62-64"))
    assert broken(lambda a: a["contrasts"][0].update(group="35-44"))
    assert broken(lambda a: a.update(reference_group="35-44"))
    assert broken(lambda a: a["excluded_groups"][0].update(group="8888"))
    assert broken(lambda a: a["legal"].update(fha=True))
    assert broken(lambda a: a.update(field="applicant_age_above_65"))
    assert semantics().check_c21(doc) == []


# --- 7 the bake -------------------------------------------------------------------------------------------------------------------------
def test_the_planted_bake_carries_the_contrast_in_every_pair_and_two_bakes_agree(built) -> None:
    for vid in built.order:
        a = attr(built.variants[vid], FIELD)
        assert [g["group"] for g in a["groups"]] == list(GROUPS) and a["contrasts"][0]["controlled"]["estimate"] is not None
        assert bake.check(built.variants[vid]) == []


def test_the_bake_stops_naming_the_file_when_a_raw_file_is_absent(tmp_path: Path) -> None:
    from c21_support import planted_root

    root = planted_root(tmp_path, years=(2018,))
    with pytest.raises(FileNotFoundError, match="2019"):
        bake.build(1, root)
    assert not (tmp_path / "derived").exists()


# --- the findings: favouring the elderly is permitted (1002.6(b)(2)(iv)) ------------------------------------------------------------
def _rows(segment: str, odds_ratio: float, same_sign: bool = True) -> list[dict]:
    effect = {"coefficient": 0.0 if odds_ratio == 1 else (1 if odds_ratio > 1 else -1) * abs(odds_ratio - 1), "odds_ratio": odds_ratio, "lo": 0.1 if odds_ratio > 1 else -0.9, "hi": 0.3 if odds_ratio > 1 else -0.1}
    logit = {"test_id": "fair.conditional_disparity", "model_id": "hmda-logistic-decision", "segment": segment, "light": "amber",
             "extras": {"effect": effect}}
    rep = {"test_id": "fair.replication", "model_id": "hmda-logistic-decision", "segment": f"{segment}|controlled", "light": "green",
           "extras": {"same_sign": same_sign}}
    return [logit, rep]


def test_a_disparity_that_favours_the_62_group_raises_no_finding_and_one_against_it_does() -> None:
    from pipeline.cases.c21 import findings

    seg62 = f"{FIELD}|62 or over vs under 62"
    ids = {f["id"]: f for f in findings.build(_rows(seg62, 1.2))}
    assert "F-CONTROLLED-HIGHER-ODDS" not in ids and "F-CONTROLLED-LOWER-ODDS" not in ids          # favoured: measured, not raised
    ids = {f["id"]: f for f in findings.build(_rows(seg62, 0.8))}
    assert ids["F-CONTROLLED-LOWER-ODDS"]["evidence"] == [f"fair.conditional_disparity@hmda-logistic-decision@{seg62}",
                                                          f"fair.replication@hmda-logistic-decision@{seg62}|controlled"]
    ids = {f["id"]: f for f in findings.build(_rows(seg62, 1.2, same_sign=False))}
    assert "F-CONTROLLED-NOT-REPEATED" in ids and "F-CONTROLLED-HIGHER-ODDS" not in ids          # no repeat: raised in either direction
    other = "derived_sex|Female vs Male"
    ids = {f["id"]: f for f in findings.build(_rows(other, 1.2) + _rows(seg62, 1.2))}
    assert len(ids["F-CONTROLLED-HIGHER-ODDS"]["evidence"]) == 2 and other in ids["F-CONTROLLED-HIGHER-ODDS"]["evidence"][0]   # other groups as before


def test_the_committed_documents_do_not_cite_the_62_contrast_in_the_higher_odds_finding() -> None:
    for name in VARIANTS:
        doc = committed(name)
        c = attr(doc, FIELD)["contrasts"][0]["controlled"]["estimate"]
        assert c["odds_ratio"] > 1                              # the elderly are favoured in every pair of the real data
        cited = [e for f in doc["findings"] for e in f["evidence"] if FIELD in e and f["id"] == "F-CONTROLLED-HIGHER-ODDS"]
        assert cited == [], name
