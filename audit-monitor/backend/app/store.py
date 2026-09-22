"""A small JSON-file store.

Good enough for a pilot / single-instance deployment. The whole state is one
document (`DATA_DIR/store.json`) written atomically after every mutation.
Swap this module for a database repository when moving to multi-instance.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .models import AuditException, CalendarSettings, Kri, PlannerItem, Run

APP_DIR = Path(__file__).resolve().parent
SEED_PATH = APP_DIR / "seed.json"
DATA_DIR = Path(os.environ.get("DATA_DIR", APP_DIR.parent / "data"))
STORE_PATH = DATA_DIR / "store.json"


class Store:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.seed: dict[str, Any] = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        self.kris: list[Kri] = []
        self.runs: list[Run] = []
        self.exceptions: list[AuditException] = []
        self.planner: list[PlannerItem] = []
        self.calendar: CalendarSettings = CalendarSettings()
        self._load()

    # ---------- persistence ----------
    def _load(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if STORE_PATH.exists():
            raw = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        else:
            raw = {**self.seed, "calendar": CalendarSettings().model_dump()}
        self.kris = [Kri(**k) for k in raw["kris"]]
        self.runs = [Run(**r) for r in raw["runs"]]
        self.exceptions = [AuditException(**e) for e in raw["exceptions"]]
        self.planner = [PlannerItem(**p) for p in raw["planner"]]
        self.calendar = CalendarSettings(**raw.get("calendar", {}))
        if not STORE_PATH.exists():
            self.save()

    def save(self) -> None:
        with self._lock:
            doc = {
                "kris": [k.model_dump() for k in self.kris],
                "runs": [r.model_dump() for r in self.runs],
                "exceptions": [e.model_dump() for e in self.exceptions],
                "planner": [p.model_dump() for p in self.planner],
                "calendar": self.calendar.model_dump(),
            }
            tmp = STORE_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, STORE_PATH)

    def reset(self) -> None:
        with self._lock:
            if STORE_PATH.exists():
                STORE_PATH.unlink()
            self._load()

    # ---------- helpers ----------
    def lock(self) -> threading.RLock:
        return self._lock

    def kri(self, kri_id: str) -> Kri | None:
        return next((k for k in self.kris if k.id == kri_id), None)

    def exception(self, exc_id: str) -> AuditException | None:
        return next((e for e in self.exceptions if e.id == exc_id), None)

    def planner_item(self, item_id: str) -> PlannerItem | None:
        return next((p for p in self.planner if p.id == item_id), None)

    def seed_exceptions_for(self, kri_id: str) -> list[dict[str, Any]]:
        pool = [e for e in self.seed["exceptions"] if e["kriId"] == kri_id]
        return pool or self.seed["exceptions"][:2]


store = Store()
