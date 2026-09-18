from __future__ import annotations

from dataclasses import dataclass
import math
import os
from typing import Any

import numpy as np

from .world import Sensors


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(v)))


@dataclass
class BrainOutputs:
    forward: float = 0.0
    turn: float = 0.0
    backward: float = 0.0
    escape: float = 0.0
    courtship: float = 0.0
    spike_count: int = 0


class MaleCNSBrain:
    """Thin controller around flybrain's full MaleCNS v1.0 LIF network."""

    def __init__(self, brain: Any | None = None, device: str | None = None):
        if brain is None:
            from flybrain import FlyBrain
            brain = FlyBrain(device=device or os.environ.get("FLY_DEVICE", "auto"), refractory=0.004)
        self.brain = brain
        self.t = 0.0
        self.groups = {
            "food_l": self._cells(["ORN_DM1"], "L"),
            "food_r": self._cells(["ORN_DM1"], "R"),
            "mate_l": self._cells(["LC10a"], "L"),
            "mate_r": self._cells(["LC10a"], "R"),
            "loom_l": self._cells(["LC4", "LPLC2"], "L"),
            "loom_r": self._cells(["LC4", "LPLC2"], "R"),
            "turn_l": self._cells(["DNa02"], "L"),
            "turn_r": self._cells(["DNa02"], "R"),
            "forward": self._cells(["DNg100"], None),
            "backward": self._cells(["MDN"], None),
            "escape": self._cells(["DNp01"], None),
            "courtship": self._cells(["pIP1"], None),
        }
        required = ["turn_l", "turn_r", "forward", "escape", "food_l", "food_r"]
        missing = [name for name in required if self.groups[name].size == 0]
        if missing:
            raise RuntimeError("MaleCNS populations missing from flybrain data: " + ", ".join(missing))
        self._ema = {k: 0.0 for k in ["turn_l", "turn_r", "forward", "backward", "escape", "courtship"]}

    def _cells(self, types: list[str], side: str | None) -> np.ndarray:
        try:
            arr = self.brain.cells(types, side=side) if side is not None else self.brain.cells(types)
        except TypeError:
            arr = self.brain.cells(types, side=side)
        return np.asarray(arr, dtype=np.int64).reshape(-1)

    def _add(self, inject: list[tuple[np.ndarray, float]], name: str, amount: float) -> None:
        amount = _clamp(amount, 0.0, 1.2)
        cells = self.groups[name]
        if amount > 1e-4 and cells.size:
            inject.append((cells, amount))

    def _rate(self, fired_set: set[int], name: str) -> float:
        cells = self.groups[name]
        if cells.size == 0:
            return 0.0
        hits = sum(1 for idx in cells.tolist() if int(idx) in fired_set)
        frac = hits / max(1, cells.size)
        self._ema[name] = 0.72 * self._ema[name] + 0.28 * frac
        return self._ema[name]

    def step(self, sensors: Sensors, hunger: float, fatigue: float, social_drive: float) -> BrainOutputs:
        inject: list[tuple[np.ndarray, float]] = []
        hunger_gain = 0.45 + 0.55 * _clamp(hunger)
        social_gain = 0.35 + 0.65 * _clamp(social_drive)

        self._add(inject, "food_l", (sensors.food_left + sensors.memory_food_left) * hunger_gain)
        self._add(inject, "food_r", (sensors.food_right + sensors.memory_food_right) * hunger_gain)
        self._add(inject, "mate_l", sensors.mate_left * social_gain)
        self._add(inject, "mate_r", sensors.mate_right * social_gain)
        self._add(inject, "loom_l", sensors.loom_left * 0.95)
        self._add(inject, "loom_r", sensors.loom_right * 0.95)

        # Modeled homeostatic drive: gentle current into real MaleCNS output populations.
        # This keeps the virtual animal active when the simplified world provides little sensory input.
        awake = 1.0 - _clamp(fatigue)
        self._add(inject, "forward", 0.13 + 0.13 * awake)
        wander = math.sin(self.t * 0.83) * 0.045
        if wander < 0:
            self._add(inject, "turn_l", -wander)
        else:
            self._add(inject, "turn_r", wander)
        if sensors.mate_visual > 0.1 and self.groups["courtship"].size:
            self._add(inject, "courtship", sensors.mate_visual * social_drive * 0.16)

        fired = self.brain.step(inject=inject)
        fired_arr = np.asarray(fired, dtype=np.int64).reshape(-1)
        fired_set = {int(v) for v in fired_arr.tolist()}
        self.t += float(getattr(self.brain, "dt", 0.02))

        l = self._rate(fired_set, "turn_l")
        r = self._rate(fired_set, "turn_r")
        fwd = self._rate(fired_set, "forward")
        back = self._rate(fired_set, "backward")
        esc = self._rate(fired_set, "escape")
        court = self._rate(fired_set, "courtship")

        return BrainOutputs(
            forward=_clamp(fwd * 25.0),
            turn=max(-1.0, min(1.0, (r - l) * 30.0)),
            backward=_clamp(back * 25.0),
            escape=_clamp(esc * 35.0),
            courtship=_clamp(court * 28.0),
            spike_count=int(fired_arr.size),
        )
