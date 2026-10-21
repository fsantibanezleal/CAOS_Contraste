"""The engine pin rule every case test reads (one copy, so the cases cannot drift apart).

The product pins `riskvalidation` by its PyPI release (`riskvalidation[market]==X.Y.Z`, since the 0.13.000 integration, when the engine
was first published) that the SDD technology row names; a git pin by a release tag is accepted too; during a batch, until the batch's
release, by a full 40-hex commit of the engine's integration branch that the SDD technology row names too (U11 decision X5).
"""
from __future__ import annotations

import re

ENGINE_PIN = re.compile(
    r"^riskvalidation(?:\[market\])? @ git\+https://github\.com/fsantibanezleal/CAOS_RiskValidation(?:\.git)?@(?P<ref>\S+)\s*$", re.M)
PYPI_PIN = re.compile(r"^riskvalidation(?:\[market\])?==(?P<version>\d+\.\d+\.\d+)\s*$", re.M)
SDD_ENGINE_ROW = re.compile(r"^\|\s*engine\s*\|\s*riskvalidation\s*\|\s*(?P<ref>[^|\s]+)\s*\|", re.M)
TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)")


def engine_pin_findings(requirements: str, sdd: str) -> list[str]:
    """The engine is pinned by a release tag, or (until the tag is cut) by a full 40-hex commit that the SDD technology row
    names too; a PyPI release pin is the release the SDD technology row names."""
    pypi = PYPI_PIN.search(requirements)
    if pypi is not None:
        row = SDD_ENGINE_ROW.search(sdd)
        if row is None or row.group("ref") != pypi.group("version"):
            return [f"the PyPI pin {pypi.group('version')} is not the release the SDD technology row names ({row.group('ref') if row else 'no row'})"]
        return []
    pin = ENGINE_PIN.search(requirements)
    if pin is None:
        return ["the requirements carry no riskvalidation pin"]
    ref = pin.group("ref")
    if TAG.fullmatch(ref):
        return []
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        return [f"the pin {ref} is neither a release tag nor a full 40-hex commit"]
    row = SDD_ENGINE_ROW.search(sdd)
    if row is None or row.group("ref") != ref:
        return [f"the commit pin {ref} is not the one the SDD technology row names ({row.group('ref') if row else 'no row'})"]
    return []


def released_version(requirements: str) -> tuple[int, int, int] | None:
    """The release a PyPI pin or a tag pin names (the tag v0.07.000 is the package release 0.7.0), or None for a commit pin."""
    pypi = PYPI_PIN.search(requirements)
    if pypi is not None:
        return tuple(int(x) for x in pypi.group("version").split("."))  # type: ignore[return-value]
    pin = ENGINE_PIN.search(requirements)
    tag = TAG.fullmatch(pin.group("ref")) if pin else None
    return tuple(int(x) for x in tag.groups()) if tag else None  # type: ignore[return-value]


def pinned_ref(requirements: str) -> str | None:
    """The PyPI release, the tag or the commit the requirements pin the engine by, or None."""
    pypi = PYPI_PIN.search(requirements)
    if pypi is not None:
        return pypi.group("version")
    pin = ENGINE_PIN.search(requirements)
    return pin.group("ref") if pin else None
