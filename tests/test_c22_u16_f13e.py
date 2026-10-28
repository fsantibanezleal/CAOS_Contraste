"""U16-F13e (fix round 6, the fifth capture review R5, batches c28 and c29): the C22 producer texts.

c28 B1 a generator model is titled by its scenario words, never by its configuration key (R5 ruling 8: "Binomial (port-5000-k1.5)"
in a finding's evidence is a raw id); the Spanish scenarios write their counts and decimals in the Spanish form ("5.000 deudores",
never "5,000 deudores" from a blanket replace of the decimal point); c28 m2 a Spanish percent takes its no-break space; c28 m6 "all
odds are"; c29 m13 a study's scenario does not repeat the study label its row already carries, and no title nests a parenthesis;
c29 N1 "G − 2" with a minus sign; c29 N3 the documented-excess finding of a run within its bound does not call it "this excess"."""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

from pipeline.cases import c22_studies as cs
from pipeline.cases import c22_validator as cv

ROOT = Path(__file__).resolve().parents[1]
NBSP = " "
KEY = re.compile(r"\b[a-z]+(?:-[a-z0-9.]+)+\b")
NESTED = re.compile(r"\([^()]*\([^()]*\)[^()]*\)")


def _sim(gen: str, en: str, es: str) -> dict:
    return {"generator": gen, "scenario": {"en": en, "es": es}}


def test_c28_b1_a_generator_is_titled_by_its_first_scenario() -> None:
    rows = [_sim("port-5000-k1.5", "5,000 obligors, PD applied 2%, true 3%", "5.000 deudores, PD aplicada 2 %, verdadera 3 %"),
            _sim("port-5000-k1.5", "later scenario", "escenario posterior"),
            _sim("logistic-5000", "5,000 obligors, mean PD 5%", "5.000 deudores, PD media 5 %")]
    titles = cv.generator_titles(rows)
    assert titles["port-5000-k1.5"] == {"en": "5,000 obligors, PD applied 2%, true 3%", "es": "5.000 deudores, PD aplicada 2 %, verdadera 3 %"}
    assert titles["logistic-5000"]["en"] == "5,000 obligors, mean PD 5%"


def test_c28_b1_every_committed_generator_has_a_scenario_title_with_no_key() -> None:
    for p in sorted((ROOT / "data" / "derived" / "C22").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        sims = (d.get("outputs") or {}).get("simulations")
        if sims is None:
            continue
        titles = cv.generator_titles(sims)
        for m in d["model"]:
            t = titles[m["id"]]
            for lang in ("en", "es"):
                assert m["id"] not in t[lang] and not KEY.fullmatch(t[lang]), (p.name, m["id"], t[lang])


def test_c28_spanish_scenarios_write_spanish_numbers() -> None:
    for k in cv.MISCAL:
        for name, s in cv.miscalibration_scenarios(k).items():
            assert "5,000" not in s["es"] and not re.search(r"\d\.\d{1,2}\b", s["es"]), (k, name, s["es"])
            assert re.search(r"\d%", s["es"]) is None, (k, name, s["es"])
    p = cv.miscalibration_scenarios(1.1)["portfolio"]
    assert p["es"] == f"5.000 deudores, PD aplicada 2{NBSP}%, verdadera 2,2{NBSP}%", p["es"]
    assert p["en"] == "5,000 obligors, PD applied 2%, true 2.2%", p["en"]
    for s in cv.DRIFT:
        for name, sc in cv.drift_scenarios(s).items():
            assert "1,000" not in sc["es"] and "5,000" not in sc["es"] and not re.search(r"\d\.\d{1,2}\b", sc["es"]), (s, name, sc["es"])
    d = cv.drift_scenarios(0.2)["two_sample"]
    assert d["es"] == "dos muestras de 1.000, la actual desplazada 0,2 DE", d["es"]
    m = cv.migration_scenario(1.5, 2000)
    assert m["es"] == "grado 4 a grado 2 a 1,5 veces grado 4 a grado 3; 2.000 deudores por grado", m["es"]
    assert m["en"] == "grade 4 to grade 2 at 1.5 times grade 4 to grade 3; 2,000 obligors per grade", m["en"]


def test_c28_m2_a_spanish_percent_takes_its_no_break_space() -> None:
    t = cv._t("size at 5% and 1%", "tamaño al 5% y 1%")
    assert t == {"en": "size at 5% and 1%", "es": f"tamaño al 5{NBSP}% y 1{NBSP}%"}


def test_c28_m6_all_odds_are() -> None:
    assert cv.HL_POWER_LABEL["en"] == "Hosmer-Lemeshow power at 5% when all odds are 1.25 times too low"
    assert "todas las razones de chances son 1,25 veces" in cv.HL_POWER_LABEL["es"]


def test_c29_n1_g_minus_2_has_a_minus_sign() -> None:
    src = Path(cv.__file__).read_text(encoding="utf-8")
    assert "G - 2" not in src and "G − 2" in src


def test_c29_n3_a_run_within_its_bound_names_no_excess_of_its_own() -> None:
    ex = {"measured": 0.01325, "bound": 0.0148616, "exceeds": False, "page": "docs/portfolio/07_validation-tests.md",
          "engine": {"en": "The engine's page states the measured size, 1.55% at 1% ...", "es": "La página del motor declara ..."}}
    en, es = cv.mc_excess_title(ex)
    assert "this excess" not in en and "within it in this run" in en and "documents an excess" in en, en
    assert "este exceso" not in es and "documenta un exceso" in es, es
    en2, _ = cv.mc_excess_title({**ex, "measured": 0.0155, "exceeds": True})
    assert "above it in this run" in en2 and "documents this excess" in en2, en2


def test_c29_m13_a_study_scenario_does_not_repeat_its_row_label() -> None:
    texts = {"label": {"en": "60 years at the 95% level", "es": "60 años al nivel de 95 %"}}
    text = {"en": "the test's null holds at its boundary", "es": "la nula de la prueba se cumple en su frontera"}
    many = cs.study_scenario(texts, text, n_studies=2)
    assert many == text, many
    one = cs.study_scenario(texts, text, n_studies=1)
    assert one["en"] == "60 years at the 95% level; the test's null holds at its boundary", one


def test_c29_m13_a_power_title_nests_no_parenthesis() -> None:
    assert cv._with("14 %", "Dynamic quantile test (250 days at 1%)") == "14 %, Dynamic quantile test (250 days at 1%)"
    assert cv._with("100 %", "Kupiec proportion of failures") == "100 % (Kupiec proportion of failures)"
    s = SimpleNamespace(label="250 days at 1%", null_text=None, alternative_text="250 days at 1%")
    label = cs.row_label("market.dynamic_quantile_test", s, 0, 3)
    assert not NESTED.search(f"from {cv._with('14 %', label['en'])} to {cv._with('100 %', 'Kupiec')}")
