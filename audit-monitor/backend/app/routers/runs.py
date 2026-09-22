from fastapi import APIRouter, HTTPException

from ..models import Run, RunRequest, RunResult
from ..services import simulate_run, today_iso
from ..store import store

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("", response_model=list[Run])
def list_runs() -> list[Run]:
    return store.runs


@router.post("", response_model=RunResult, status_code=201)
def start_run(req: RunRequest) -> RunResult:
    """Run a KRI on demand for the requested period / region / business group.

    The run is executed synchronously and its exceptions are stored as open items.
    """
    with store.lock():
        kri = store.kri(req.kriId)
        if not kri:
            raise HTTPException(404, f"KRI {req.kriId} not found")
        if kri.status != "active":
            raise HTTPException(409, f"KRI {req.kriId} is not active")
        result = simulate_run(store, kri, req)
        store.runs.insert(0, result.run)
        store.exceptions = result.exceptions + store.exceptions
        kri.lastRun = today_iso()
        store.save()
    return result
