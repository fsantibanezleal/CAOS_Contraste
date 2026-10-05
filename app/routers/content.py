"""GET-only endpoints serving the committed documents unchanged (read-only). No write paths."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..services import content

router = APIRouter(prefix="/api")


@router.get("/cases")
def list_cases() -> dict:
    """The index (contract 2): every baked case and the path of its manifest."""
    return content.load_index()


@router.get("/cases/{case_id}/manifest")
def get_manifest(case_id: str) -> dict:
    m = content.load_manifest(case_id)
    if m is None:
        raise HTTPException(status_code=404, detail="unknown case")
    return m


@router.get("/artifacts/{rel_path:path}")
def get_artifact(rel_path: str):
    """Any artifact a manifest names, by its path under data/derived (for example `<case>/<variant>.json`)."""
    art = content.load_artifact(rel_path)
    if art is None:
        raise HTTPException(status_code=404, detail="no such artifact")
    return art
