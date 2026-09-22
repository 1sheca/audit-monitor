from fastapi import APIRouter, HTTPException

from ..models import DraftRequest, PlannerCreate, PlannerItem, PlannerUpdate
from ..services import PRIOR_WORK, build_plan, next_planner_id, today_iso
from ..store import store

router = APIRouter(prefix="/api/planner", tags=["planner"])


@router.get("", response_model=list[PlannerItem])
def list_items() -> list[PlannerItem]:
    return store.planner


@router.get("/reference")
def reference() -> dict:
    return {"policies": store.seed["policies"], "priorWork": PRIOR_WORK}


@router.post("", response_model=PlannerItem, status_code=201)
def create_item(body: PlannerCreate) -> PlannerItem:
    if not body.title.strip():
        raise HTTPException(422, "Title is required")
    with store.lock():
        item = PlannerItem(
            id=next_planner_id(store), type="Manual", source="Planning schedule", createdAt=today_iso(),
            status="New", policyDefault="v4.1", link="—", **body.model_dump(),
        )
        store.planner.insert(0, item)
        store.save()
    return item


@router.post("/{item_id}/draft", response_model=PlannerItem)
def draft_plan(item_id: str, body: DraftRequest) -> PlannerItem:
    """Draft pointed audit steps against the chosen policy and prior work papers."""
    with store.lock():
        item = store.planner_item(item_id)
        if not item:
            raise HTTPException(404, f"Planner item {item_id} not found")
        if item.status == "Live":
            raise HTTPException(409, "A live plan cannot be re-drafted")
        item.plan = build_plan(body.policy)
        item.policyDefault = body.policy
        item.status = "Plan drafted"
        store.save()
    return item


@router.patch("/{item_id}", response_model=PlannerItem)
def update_item(item_id: str, body: PlannerUpdate) -> PlannerItem:
    with store.lock():
        item = store.planner_item(item_id)
        if not item:
            raise HTTPException(404, f"Planner item {item_id} not found")
        if body.clearPlan:
            item.plan = None
        elif body.plan is not None:
            item.plan = body.plan
        if body.status is not None:
            item.status = body.status
        if body.policyDefault is not None:
            item.policyDefault = body.policyDefault
        store.save()
    return item
