"""Pipeline smoke + determinism: a case regenerates deterministically (same seed -> identical artifact), the
degenerate control runs without crashing, and run_all writes the flat index."""
import json

from pipeline import pipeline, registry


def test_case_deterministic_same_seed(tmp_path):
    out = tmp_path / "derived"
    a = pipeline.precompute("EX02_epidemic", seed=7, output_root=out)
    b = pipeline.precompute("EX02_epidemic", seed=7, output_root=out)
    assert a["artifact"]["bytes"] == b["artifact"]["bytes"]
    trace = json.loads((out / a["artifact"]["path"]).read_text(encoding="utf-8"))
    assert trace["summary"]["peak_I"] > 0


def test_degenerate_control_runs(tmp_path):
    out = tmp_path / "derived"
    m = pipeline.precompute("CTRL_degenerate", seed=1, output_root=out)
    trace = json.loads((out / m["artifact"]["path"]).read_text(encoding="utf-8"))
    assert trace["summary"]["peak_I"] == 0.0
    assert trace["summary"]["attack_rate"] == 0.0


def test_run_all_writes_index(tmp_path):
    out = tmp_path / "derived"
    entries = pipeline.run_all(seed=42, output_root=out)
    assert len(entries) == len(registry.list_cases()) >= 4
    idx = json.loads((out / "manifests" / "index.json").read_text(encoding="utf-8"))
    assert idx["n_cases"] == len(entries)
    assert idx["schema"].startswith("example.index/")
