"""The constant check of the units rule (CONTRACT 3b, ``scripts/check_unit_constants.py``; requirements CT-2407 and CT-2408 of
``docs/design/features/units/``): every float literal of a reviewed method or parameter module carries a baseline entry with its
class, unit and reason; a module in none of the reviewed lists fails. Each test builds a throwaway module tree, plants the case
and runs the real script on it; the real tree is checked only for its module lists, whose baseline T6 classifies."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_unit_constants.py"
PIPELINE = ROOT / "data-pipeline" / "pipeline"
MODULES = ROOT / "scripts" / "unit_constants_modules.json"

CLASSES = ("probability", "ratio", "relative-tolerance", "training-hyperparameter", "single-observable-limit", "unit-conversion",
           "source-cited-input", "stated-assumption", "run-budget")


def build(tmp: Path, sources: dict[str, str], *, method=(), parameter=(), outside: dict[str, str] | None = None,
          baseline: dict | None = None) -> tuple[Path, Path, Path]:
    """A throwaway pipeline root, its module lists and its baseline; the three paths the script takes."""
    root = tmp / "pipeline"
    for rel, text in sources.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    modules = tmp / "modules.json"
    modules.write_text(json.dumps({"method": list(method), "parameter": list(parameter), "outside": outside or {}}), encoding="utf-8")
    base = tmp / "baseline.json"
    base.write_text(json.dumps(baseline if baseline is not None else {}), encoding="utf-8")
    return root, modules, base


def run(root: Path, modules: Path, base: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPT), "--root", str(root), "--modules", str(modules), "--baseline", str(base),
                           *flags], capture_output=True, text=True, timeout=120)


def entry(klass: str = "probability", unit: str = "probability", reason: str = "a significance level") -> dict:
    return {"class": klass, "unit": unit, "reason": reason}


def keys(base: Path) -> list[str]:
    return list(json.loads(base.read_text(encoding="utf-8")))


METHOD = "def fit(x):\n    return x * 0.37\n"


def test_a_new_literal_fails_until_justified(tmp_path):
    """CT-2407: a float literal without a reviewed entry fails at its line; justified, it passes; a second one fails again."""
    root, modules, base = build(tmp_path, {"cases/m.py": METHOD}, method=["cases/m"])
    out = run(root, modules, base)
    assert out.returncode == 1
    assert "cases/m.py:2" in out.stdout and "0.37" in out.stdout and "cases/m::fit::0.37::0" in out.stdout
    # --update records the literal as TODO, and a TODO still fails
    assert run(root, modules, base, "--update").returncode == 0
    assert json.loads(base.read_text(encoding="utf-8"))["cases/m::fit::0.37::0"]["class"] == "TODO"
    out = run(root, modules, base)
    assert out.returncode == 1 and "TODO" in out.stdout
    # justified, it passes
    base.write_text(json.dumps({"cases/m::fit::0.37::0": entry("ratio", "share of exposure", "the haircut of the sample")}), encoding="utf-8")
    assert run(root, modules, base).returncode == 0
    # a new literal in the same module fails at its own line
    (root / "cases" / "m.py").write_text(METHOD + "\n\ndef apply(y):\n    return y + 4.2\n", encoding="utf-8")
    out = run(root, modules, base)
    assert out.returncode == 1
    assert "cases/m.py:6" in out.stdout and "cases/m::apply::4.2::0" in out.stdout


def test_an_unlisted_module_fails(tmp_path):
    """CT-2408: a module under the root in none of the three lists fails, so a new module cannot escape review."""
    root, modules, base = build(tmp_path, {"cases/m.py": "X = 1\n", "cases/new.py": "Y = 2\n"}, method=["cases/m"])
    out = run(root, modules, base)
    assert out.returncode == 1
    assert "cases/new" in out.stdout and "no list" in out.stdout
    modules.write_text(json.dumps({"method": ["cases/m"], "parameter": [], "outside": {"cases/new": "an integer table only"}}), encoding="utf-8")
    assert run(root, modules, base).returncode == 0


def test_an_unlisted_module_with_no_literal_still_fails(tmp_path):
    root, modules, base = build(tmp_path, {"cases/m.py": "X = 1\n", "cases/pkg/__init__.py": ""}, method=["cases/m"])
    out = run(root, modules, base)
    assert out.returncode == 1 and "cases/pkg/__init__" in out.stdout


@pytest.mark.parametrize("entry_value, word", [
    ({"class": "TODO", "unit": "TODO", "reason": "TODO"}, "TODO"),
    (entry(reason="TODO"), "TODO"),
    (entry(unit="TODO"), "TODO"),
    (entry(reason=""), "reason"),
    (entry(unit="  "), "unit"),
    (entry(klass="magic-number"), "class"),
    ({"class": "probability", "unit": "probability"}, "reason"),
])
def test_an_unjustified_entry_fails(tmp_path, entry_value, word):
    root, modules, base = build(tmp_path, {"cases/m.py": METHOD}, method=["cases/m"], baseline={"cases/m::fit::0.37::0": entry_value})
    out = run(root, modules, base)
    assert out.returncode == 1 and word in out.stdout


@pytest.mark.parametrize("klass", CLASSES)
def test_every_class_of_the_closed_list_is_accepted(tmp_path, klass):
    root, modules, base = build(tmp_path, {"cases/m.py": METHOD}, method=["cases/m"], baseline={"cases/m::fit::0.37::0": entry(klass)})
    assert run(root, modules, base).returncode == 0


def test_the_exemptions_and_what_is_walked(tmp_path):
    """The design's exemptions are 0.0, 1.0, 0.5, 2.0, 10.0 and abs(v) < 1e-5; 100.0 and 1000.0 are walked; integers are not."""
    src = ("EXEMPT = (0.0, 1.0, 0.5, 2.0, 10.0, 1e-6, -0.5, -1.0, 0.000001)\n"
           "INTS = (3, 100, 1000, 7)\n"
           "WALKED = (100.0, 1000.0, 0.25, 1e-5)\n")
    root, modules, base = build(tmp_path, {"m.py": src}, method=["m"])
    run(root, modules, base, "--update")
    assert sorted(keys(base)) == sorted(["m::<module>::1e-05::0", "m::<module>::0.25::0", "m::<module>::100.0::0",
                                         "m::<module>::1000.0::0"])  # 1e-05 is not below 1e-5, so it is walked


def test_a_negative_literal_is_one_entry_with_its_sign(tmp_path):
    root, modules, base = build(tmp_path, {"m.py": "A = -0.25\nB = 0.25\nC = - 0.25\n"}, method=["m"])
    run(root, modules, base, "--update")
    assert sorted(keys(base)) == ["m::<module>::-0.25::0", "m::<module>::-0.25::1", "m::<module>::0.25::0"]


def test_the_key_carries_an_ordinal_and_the_qualified_name(tmp_path):
    """Two equal values in one function are two entries; the qualname is the enclosing class and function path."""
    src = ("def f(a):\n    x = a * 0.05\n    return x + 0.05\n\n"
           "class C:\n    def m(self):\n        def inner():\n            return 0.3\n        return inner() + 0.3\n\n"
           "Z = 0.05\n")
    root, modules, base = build(tmp_path, {"cases/c.py": src}, method=["cases/c"])
    run(root, modules, base, "--update")
    assert sorted(keys(base)) == sorted([
        "cases/c::f::0.05::0", "cases/c::f::0.05::1", "cases/c::C.m.inner::0.3::0", "cases/c::C.m::0.3::0",
        "cases/c::<module>::0.05::0"])


def test_a_default_argument_belongs_to_its_function(tmp_path):
    root, modules, base = build(tmp_path, {"m.py": "def f(t=90.0):\n    return t\n"}, method=["m"])
    run(root, modules, base, "--update")
    assert keys(base) == ["m::f::90.0::0"]


def test_update_adds_new_literals_as_todo_and_drops_the_gone_ones_and_keeps_the_reviewed(tmp_path):
    kept = entry("ratio", "share", "kept as reviewed")
    root, modules, base = build(tmp_path, {"m.py": "def f():\n    return 0.37 + 0.41\n"}, method=["m"],
                                baseline={"m::f::0.37::0": kept, "m::f::0.99::0": entry()})
    assert run(root, modules, base).returncode == 1  # a stale entry and a new literal
    assert run(root, modules, base, "--update").returncode == 0
    data = json.loads(base.read_text(encoding="utf-8"))
    assert sorted(data) == ["m::f::0.37::0", "m::f::0.41::0"]
    assert data["m::f::0.37::0"] == kept
    assert data["m::f::0.41::0"] == {"class": "TODO", "unit": "TODO", "reason": "TODO"}


def test_a_stale_entry_fails(tmp_path):
    root, modules, base = build(tmp_path, {"m.py": "X = 1\n"}, method=["m"], baseline={"m::<module>::0.3::0": entry()})
    out = run(root, modules, base)
    assert out.returncode == 1 and "m::<module>::0.3::0" in out.stdout and "--update" in out.stdout


def test_update_is_sorted_and_stable(tmp_path):
    src = "B = 0.7\nA = 0.3\n\ndef f():\n    return 0.9\n"
    root, modules, base = build(tmp_path, {"z.py": src, "a.py": src}, method=["z", "a"])
    run(root, modules, base, "--update")
    first = base.read_bytes()
    run(root, modules, base, "--update")
    assert base.read_bytes() == first
    ks = keys(base)
    assert ks == sorted(ks) and first.endswith(b"\n")
    assert first.count(b"\n") == len(ks) + 2  # one line per entry: a diff shows only the change


def test_a_module_in_two_lists_is_invalid(tmp_path):
    root, modules, base = build(tmp_path, {"m.py": "X = 1\n"}, method=["m"], parameter=["m"])
    out = run(root, modules, base)
    assert out.returncode == 1 and "more than one list" in out.stdout
    root, modules, base = build(tmp_path / "b", {"m.py": "X = 1\n"}, method=["m"], outside={"m": "reason"})
    assert run(root, modules, base).returncode == 1


def test_a_listed_module_that_no_longer_exists_fails(tmp_path):
    root, modules, base = build(tmp_path, {"m.py": "X = 1\n"}, method=["m", "gone"])
    out = run(root, modules, base)
    assert out.returncode == 1 and "gone" in out.stdout and "does not exist" in out.stdout


def test_an_outside_entry_needs_its_reason(tmp_path):
    root, modules, base = build(tmp_path, {"m.py": "X = 1\n"}, outside={"m": "  "})
    out = run(root, modules, base)
    assert out.returncode == 1 and "reason" in out.stdout


def test_a_literal_in_an_outside_module_is_not_walked(tmp_path):
    root, modules, base = build(tmp_path, {"page.py": "SCALE = 0.37\n"}, outside={"page": "renders a committed document"})
    assert run(root, modules, base).returncode == 0


def test_a_syntax_error_fails_and_is_named(tmp_path):
    root, modules, base = build(tmp_path, {"m.py": "def (:\n"}, method=["m"])
    out = run(root, modules, base)
    assert out.returncode == 1 and "m.py" in out.stdout


def test_a_malformed_module_file_fails(tmp_path):
    root, modules, base = build(tmp_path, {"m.py": "X = 1\n"}, method=["m"])
    modules.write_text(json.dumps({"method": ["m"], "parameter": []}), encoding="utf-8")
    assert run(root, modules, base).returncode == 1
    modules.write_text(json.dumps({"method": "m", "parameter": [], "outside": {}}), encoding="utf-8")
    assert run(root, modules, base).returncode == 1


def test_the_counts_are_reported_per_list_and_per_case_group(tmp_path):
    src = "A = 0.3\nB = 0.7\n"
    root, modules, base = build(tmp_path, {"cases/c04_x.py": src, "cases/c22/y.py": src, "model/gbm.py": src, "cases/c09/params.py": src},
                                method=["cases/c04_x", "cases/c22/y", "model/gbm"], parameter=["cases/c09/params"])
    out = run(root, modules, base, "--counts")
    assert "method: 3 modules, 6 literals" in out.stdout and "parameter: 1 modules, 2 literals" in out.stdout
    assert "C04 2" in out.stdout and "C22 2" in out.stdout and "C09 2" in out.stdout and "model 2" in out.stdout


# the real tree: the module lists (CT-2408) -------------------------------------------------------------------------------------

def load_script():
    spec = importlib.util.spec_from_file_location("check_unit_constants", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_every_module_of_the_pipeline_is_in_exactly_one_list():
    """The reviewed lists classify every module under data-pipeline/pipeline/, each exactly once; no entry is stale."""
    lists = json.loads(MODULES.read_text(encoding="utf-8"))
    assert set(lists) == {"method", "parameter", "outside"}
    on_disk = {p.relative_to(PIPELINE).with_suffix("").as_posix() for p in PIPELINE.rglob("*.py") if "__pycache__" not in p.parts}
    listed = [*lists["method"], *lists["parameter"], *lists["outside"]]
    assert len(listed) == len(set(listed)), sorted({m for m in listed if listed.count(m) > 1})
    assert set(listed) == on_disk, (sorted(on_disk - set(listed)), sorted(set(listed) - on_disk))
    assert all(isinstance(r, str) and r.strip() for r in lists["outside"].values())
    for name in ("method", "parameter"):
        assert lists[name] == sorted(lists[name])


def test_100_and_1000_are_walked_on_the_real_tree():
    """The conversions are where the unit is declared: the percent and thousand literals of the method modules are entries."""
    mod = load_script()
    lists = json.loads(MODULES.read_text(encoding="utf-8"))
    found = mod.walk(PIPELINE, [*lists["method"], *lists["parameter"]])
    values = {lit.value for lit in found.literals}
    assert 100.0 in values and 1000.0 in values
    assert not values & {0.0, 1.0, 0.5, 2.0, 10.0}


def test_the_real_tree_runs_in_about_two_seconds():
    import time
    start = time.monotonic()
    out = subprocess.run([sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True, timeout=120)
    assert time.monotonic() - start < 10.0
    assert out.returncode == 0 and "check_unit_constants:" in out.stdout and "202 modules walked" in out.stdout


def test_the_committed_baseline_classifies_every_literal_with_a_specific_reason():
    """T6: no entry is TODO, every class is in the closed list, unit and reason are written and a reason is never a class name."""
    base = json.loads((ROOT / "scripts" / "unit_constants_baseline.json").read_text(encoding="utf-8"))
    assert base, "the baseline is empty"
    for key, entry in base.items():
        assert entry["class"] in CLASSES, key
        for name in ("unit", "reason"):
            assert entry[name].strip() and entry[name].strip() != "TODO", (key, name)
        assert entry["reason"].strip() not in CLASSES and len(entry["reason"]) > 40, key


def test_the_real_tree_passes_the_constant_check():
    out = subprocess.run([sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stdout[-2000:]
    assert "check_unit_constants: OK" in out.stdout


@pytest.mark.parametrize("rel", (".github/workflows/ci.yml", "scripts/smoke.sh", "scripts/smoke.ps1"))
def test_the_constant_check_runs_in_ci_and_in_the_smoke_scripts(rel):
    """CT-2409: the check is a step of the existing job and of both smoke scripts, never a job of its own."""
    assert "check_unit_constants.py" in (ROOT / rel).read_text(encoding="utf-8")


def test_the_constant_check_adds_no_job_to_ci():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert text.count("check_unit_constants.py") == 1


POWERSHELL = shutil.which("powershell.exe")


def _smoke_copy(tmp: Path, artifacts_exit: int, constants_exit: int) -> Path:
    """A throwaway repo with the real smoke.ps1 and two stub checks that exit with the given codes."""
    scripts = tmp / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "smoke.ps1", scripts / "smoke.ps1")
    (scripts / "check_artifacts.py").write_text(f"import sys\nsys.exit({artifacts_exit})\n", encoding="utf-8")
    (scripts / "check_unit_constants.py").write_text(f"import sys\nsys.exit({constants_exit})\n", encoding="utf-8")
    return scripts / "smoke.ps1"


@pytest.mark.skipif(POWERSHELL is None, reason="Windows PowerShell 5.1 is not on this machine")
@pytest.mark.parametrize("artifacts_exit,constants_exit,expected", [(0, 0, 0), (0, 1, 1), (1, 0, 1), (3, 0, 3), (0, 7, 7)])
def test_smoke_ps1_exits_with_the_failing_check_under_windows_powershell(tmp_path, artifacts_exit, constants_exit, expected):
    """Windows PowerShell 5.1 does not propagate a native exit code to a script's own: each call needs `exit $LASTEXITCODE`."""
    smoke = _smoke_copy(tmp_path, artifacts_exit, constants_exit)
    env = {**os.environ, "PYTHON": sys.executable}
    out = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-File", str(smoke)], capture_output=True, text=True,
                         timeout=120, env=env, stdin=subprocess.DEVNULL)
    assert out.returncode == expected, out.stdout + out.stderr


def test_the_new_classes_are_in_the_script_and_the_design():
    spec = importlib.util.spec_from_file_location("check_unit_constants_classes", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    assert tuple(mod.CLASSES) == CLASSES
    design = (ROOT / "docs" / "design" / "features" / "units" / "design.md").read_text(encoding="utf-8")
    for klass in ("stated-assumption", "run-budget"):
        assert f"`{klass}`" in design


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^\x00-\x7f]", "_", text).replace('"', "'").split())


def test_a_reason_quotes_the_code_line_of_its_own_literal():
    """Review of T6 (m9): a reason that quotes code (`(code: ...)`) quotes the line its literal sits on, so a reason written for
    another literal fails. The correctness of the words stays with the reader; this guards the commonest slip."""
    spec = importlib.util.spec_from_file_location("check_unit_constants_reasons", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    lists, _ = mod.load_lists(MODULES)
    found = mod.walk(PIPELINE, [*lists["method"], *lists["parameter"]])
    base = json.loads((ROOT / "scripts" / "unit_constants_baseline.json").read_text(encoding="utf-8"))
    lines: dict[str, list[str]] = {}
    wrong = []
    for lit in found.literals:
        reason = base[lit.key]["reason"]
        if "(code: " not in reason:
            continue
        snippet = _norm(reason.rsplit("(code: ", 1)[1].rstrip(")"))[:40]
        src = lines.setdefault(lit.path, (ROOT / lit.path).read_text(encoding="utf-8").split("\n"))
        if snippet and snippet not in _norm(src[lit.line - 1]):
            wrong.append(f"{lit.path}:{lit.line} {lit.key}")
    assert not wrong, wrong[:10]


def _real_baseline() -> dict:
    return json.loads((ROOT / "scripts" / "unit_constants_baseline.json").read_text(encoding="utf-8"))


def test_no_unit_hedges_with_the_word_or():
    """Second fix of T6 (R6): a unit is the unit of its own literal, one unit and never "x or y". The selector is the plain word
    `or` in the unit text (the first fix counted 26 and the re-review found 197 with this selector)."""
    hedged = sorted(k for k, e in _real_baseline().items() if re.search(r"\bor\b", e["unit"]))
    assert not hedged, hedged[:10]


def test_no_unit_lists_several_meanings():
    """Third fix of T6 (F3): the word-"or" selector found 0 while 38 units still listed several meanings in another form
    ("as its key: default rate, AUC, PSI, p-value, share", "(coverage, stage 2 share)", "learning rate ...; L2 leaf ..."). The unit of
    a literal is one unit: no "as its key", no semicolon and no comma inside a parenthesis (a list of names)."""
    hedged = sorted(k for k, e in _real_baseline().items() if re.search(r"as its key|;|\([^()]*,[^()]*\)", e["unit"]))
    assert not hedged, hedged[:10]


def test_a_reason_names_one_role_not_two_with_or():
    """Third fix of T6 (item 4): a reason names the one role its literal has at its line. The word `or` stays only in a quoted
    phrase (a docstring or a source's wording), a name or a state of the data, never between two roles of the literal."""
    allowed = ("3 months or less", "three months or less", "'convention or case assumption'", "category 6 or worse", "at or above",
               "Black or African American", "arrears or in default")
    wrong = sorted(k for k, e in _real_baseline().items()
                   if re.search(r"\bor\b", e["reason"].split(" (code: ")[0]) and not any(a in e["reason"] for a in allowed))
    assert not wrong, wrong[:10]


def test_a_dimensionless_class_does_not_carry_a_dimension_and_a_stated_assumption_does_not_say_dimensionless():
    """Third fix of T6 (F1): the three error kinds of the third review. A `ratio` or `probability` whose unit names percentage points,
    a rate per period, basis points or a currency (C15 `cpi` 2.5 pp, a C17 axis in "decades of EUR"); a `stated-assumption` whose unit
    says dimensionless (C12 `IID_CRITICAL`, C13 `ecdf_step`)."""
    base = _real_baseline()
    dimension = re.compile(r"percentage points?|\bpp\b|\bper (year|day|quarter|month|period)\b|basis points?|\bof (USD|EUR|CLP)\b")
    with_dimension = sorted(k for k, e in base.items() if e["class"] in ("ratio", "probability") and dimension.search(e["unit"]))
    dimensionless_assumption = sorted(k for k, e in base.items() if e["class"] == "stated-assumption" and re.search(r"dimensionless", e["unit"], re.I))
    assert not with_dimension, with_dimension[:10]
    assert not dimensionless_assumption, dimensionless_assumption[:10]


def test_the_entries_of_the_third_review_say_what_their_code_does():
    base = _real_baseline()
    swap = [e for k, e in base.items() if k.startswith("cases/c22_validator::<module>::") and e["reason"].startswith("SWAP = ")]
    assert len(swap) == 4
    for e in swap:
        assert "fraction of the gap" in e["reason"] and "share of grades swapped" not in e["reason"]
    assert base["cases/c15/book::<module>::2.5::0"]["class"] == "stated-assumption"
    assert {base[f"cases/c12/backtest::<module>::{v}::0"]["class"] for v in ("2.492", "3.88")} == {"ratio"}
    assert base["cases/c13/params::<module>::0.004::0"]["class"] == "probability"
    count = base["cases/c22_validator::<module>::25.0::0"]
    assert "count" in count["unit"] and "rejection rate" not in count["unit"]


def test_every_run_timeout_is_a_run_budget():
    """Second fix of T6 (R3): a literal named RUN_MS (or RUN_MS_GATE) is the wall-clock limit of a run, whatever the case."""
    wrong = sorted(k for k, e in _real_baseline().items() if re.match(r"RUN_MS(_GATE)?\b", e["reason"]) and e["class"] != "run-budget")
    assert not wrong, wrong


def test_the_c20_stand_in_range_and_the_c15_page_threshold_are_not_baselined():
    """Second fix of T6 (R1 and R8): the stand-in range of a C20 subsample run and the C15 page's copy of the EVE threshold are
    rewritten against their source, so no entry is kept for either (the code tests are in tests/test_t6_code_findings.py)."""
    keys = _real_baseline()
    assert not [k for k in keys if k.startswith("cases/c20/bake::bake_case::") and "1000000000.0" in k]
    assert not [k for k in keys if k.startswith("cases/c15/page::")]
