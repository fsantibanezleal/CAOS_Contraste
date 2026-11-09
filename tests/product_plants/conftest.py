"""The product's own planted-defect tests that need the pipeline (numpy, the engine, the case code). They sit outside
tests/adversarial because CI runs that folder alone with the standard library and jsonschema (scripts/check_ci_budget.py,
ADR-0074): these run locally with the rest of the suite. They share the adversarial fixtures and the product planting helpers."""
import sys
from pathlib import Path

ADVERSARIAL = Path(__file__).resolve().parents[1] / "adversarial"
if str(ADVERSARIAL) not in sys.path:
    sys.path.insert(0, str(ADVERSARIAL))

from adversarial_fixtures import _sandboxed_pipeline, base_copy, docs, repo, sdd_repo  # noqa: E402, F401
