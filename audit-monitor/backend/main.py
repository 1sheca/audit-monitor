"""
Audit Monitor — backend (B4 thin slice)
----------------------------------------
One endpoint: POST /plan
The frontend's "Draft the audit steps" button now calls THIS instead of
building the plan in the browser. Same output shape, real server.

Run it:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Then open http://localhost:8000/docs to see it live.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Audit Monitor API", version="0.1.0")

# The browser (your index.html opened locally) must be allowed to call us.
# "*" is fine for a demo; lock this down later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- what the frontend sends us ----
class PlanRequest(BaseModel):
    policy: str          # e.g. "v4.1"
    item_id: str | None = None


# ---- the plan the frontend expects back: list of {step, status, note} ----
def build_plan(policy_id: str) -> list[dict]:
    using_old = policy_id == "v3.2"
    return [
        {"step": "Confirm scope: WBS family N.10871.* (4 WBSs), P7–P8, MI business group.",
         "status": "new",
         "note": "Derived from the KRI trigger; not in the generic checklist."},
        {"step": "Obtain the CPO and any revised CPO / change orders from the account manager.",
         "status": "kept",
         "note": "Standard step, unchanged."},
        {"step": "Reconcile each reversal to a customer document; a scope change must leave a reduced OI, not zero.",
         "status": "updated",
         "note": ("v3.2 has no scope-change rule – step written against v4.1 §4.3 anyway."
                  if using_old else "Updated to policy v4.1 §4.3 (scope changes).")},
        {"step": "Confirm revenue true-up for every reversal where revenue was already recognised.",
         "status": "new",
         "note": "Not a legacy step; added because OI-02 found a broken OI → revenue link."},
        {"step": "Interview the accepting manager (R. Haddad) on the period-end timing of the six reversals.",
         "status": "new",
         "note": "Pointed step from OI-03 evidence."},
        {"step": "Test OI against the quarterly forecast submission for the project.",
         "status": "dropped",
         "note": "Forecast comparison is now covered by OBL-01 and adds no evidence here."},
        {"step": "Sample 25 bookings across the region for accuracy re-performance.",
         "status": "dropped",
         "note": "Population already tested at 100% by OI-01; sampling would duplicate the KRI."},
        {"step": "Document conclusion at KRI level and update the residual-risk rating for MEA / MI.",
         "status": "kept",
         "note": "Closing step; anchors on risk, not process."},
    ]


@app.get("/")
def health():
    return {"status": "ok", "service": "audit-monitor", "version": "0.1.0"}


@app.post("/plan")
def draft_plan(req: PlanRequest):
    plan = build_plan(req.policy)
    # The extra 'meta' block is what makes progress visible: the plan now
    # carries where it came from. Next step (B3) replaces build_plan with
    # real retrieval over ingested policies + prior work papers.
    return {
        "plan": plan,
        "meta": {
            "policy_used": req.policy,
            "generated_by": "audit-monitor backend v0.1",
            "grounded": False,  # flips to True once B2/B3 retrieval is wired
        },
    }
