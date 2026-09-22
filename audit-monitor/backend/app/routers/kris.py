from fastapi import APIRouter, HTTPException

from ..models import Kri, KriStatusUpdate
from ..store import store

router = APIRouter(prefix="/api/kris", tags=["kris"])


@router.get("", response_model=list[Kri])
def list_kris() -> list[Kri]:
    return store.kris


@router.get("/{kri_id}", response_model=Kri)
def get_kri(kri_id: str) -> Kri:
    kri = store.kri(kri_id)
    if not kri:
        raise HTTPException(404, f"KRI {kri_id} not found")
    return kri


@router.put("/{kri_id}", response_model=Kri)
def upsert_kri(kri_id: str, body: Kri) -> Kri:
    """Create or replace a KRI configuration. Steps must contain at least one non-empty instruction."""
    body.steps = [s for s in body.steps if s.strip()]
    if not body.name.strip() or not body.steps:
        raise HTTPException(422, "A KRI needs a name and at least one test step")
    with store.lock():
        existing = store.kri(kri_id)
        if existing:
            body.lastRun = body.lastRun or existing.lastRun
            store.kris = [body if k.id == kri_id else k for k in store.kris]
        else:
            store.kris.append(body)
        store.save()
    return body


@router.patch("/{kri_id}/status", response_model=Kri)
def set_status(kri_id: str, body: KriStatusUpdate) -> Kri:
    with store.lock():
        kri = store.kri(kri_id)
        if not kri:
            raise HTTPException(404, f"KRI {kri_id} not found")
        kri.status = body.status
        store.save()
    return kri


@router.get("/export/config")
def export_config() -> list[dict]:
    """The configuration file the agents read – KRI definitions without run-state fields."""
    return [k.model_dump(exclude={"lastRun", "note"}) for k in store.kris]
