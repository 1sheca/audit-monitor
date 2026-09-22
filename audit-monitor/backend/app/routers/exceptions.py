from fastapi import APIRouter, HTTPException

from ..models import AuditException, ExceptionUpdate, PlannerItem
from ..services import planner_item_from_exception
from ..store import store

router = APIRouter(prefix="/api/exceptions", tags=["exceptions"])


@router.get("", response_model=list[AuditException])
def list_exceptions() -> list[AuditException]:
    return store.exceptions


@router.patch("/{exc_id}", response_model=AuditException)
def update_exception(exc_id: str, body: ExceptionUpdate) -> AuditException:
    """Record a reviewer decision: open / accepted / anomaly, with an optional note."""
    with store.lock():
        exc = store.exception(exc_id)
        if not exc:
            raise HTTPException(404, f"Exception {exc_id} not found")
        if body.status is not None:
            exc.status = body.status
        if body.reviewNote is not None:
            exc.reviewNote = body.reviewNote
        store.save()
    return exc


@router.post("/{exc_id}/planner", response_model=PlannerItem, status_code=201)
def send_to_planner(exc_id: str) -> PlannerItem:
    """Escalate an exception to the Audit planner as a spot-audit candidate."""
    with store.lock():
        exc = store.exception(exc_id)
        if not exc:
            raise HTTPException(404, f"Exception {exc_id} not found")
        item = planner_item_from_exception(store, exc)
        store.planner.insert(0, item)
        exc.status = "planner"
        store.save()
    return item
