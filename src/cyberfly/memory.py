from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any


@dataclass(eq=True)
class PetSnapshot:
    x: float = 550.0
    y: float = 350.0
    heading: float = 0.0
    hunger: float = 0.35
    fatigue: float = 0.15
    social_drive: float = 0.25
    age_seconds: float = 0.0
    food_eaten: int = 0
    courtship_events: int = 0
    known_food_spots: list[list[float]] = field(default_factory=list)


class MemoryStore:
    """Persistent cyber-pet state and episodic event log."""

    def __init__(self, root: str | Path | None = None):
        if root is None:
            root = os.environ.get("FLY_PET_HOME", r"J:\FLY")
        self.root = Path(root)
        self.save_dir = self.root / "save"
        self.snapshot_path = self.save_dir / "pet_state.json"
        self.episodes_path = self.save_dir / "memories.jsonl"
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, snapshot: PetSnapshot) -> None:
        payload = asdict(snapshot)
        payload["saved_at_utc"] = datetime.now(timezone.utc).isoformat()
        tmp = self.snapshot_path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.snapshot_path)

    def load_snapshot(self) -> PetSnapshot | None:
        if not self.snapshot_path.exists():
            return None
        with self.snapshot_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        allowed = set(PetSnapshot.__dataclass_fields__)
        return PetSnapshot(**{k: v for k, v in raw.items() if k in allowed})

    def append_episode(self, kind: str, salience: float, details: dict[str, Any]) -> None:
        event = {
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "salience": float(max(0.0, min(1.0, salience))),
            "details": details,
        }
        with self.episodes_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def load_recent_episodes(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.episodes_path.exists() or limit <= 0:
            return []
        lines = self.episodes_path.read_text(encoding="utf-8").splitlines()
        result: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result
