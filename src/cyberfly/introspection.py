from __future__ import annotations

from dataclasses import dataclass

from .brain_adapter import BrainOutputs
from .learning import LearningBias
from .world import PersonView, Sensors


def _clamp(
    value: float,
    lo: float = 0.0,
    hi: float = 1.0,
) -> float:
    return max(
        lo,
        min(hi, float(value)),
    )


@dataclass(frozen=True)
class NeuralIntent:
    dominant: str
    confidence: float
    action: str
    scores: dict[str, float]
    raw: dict[str, float]


def interpret_neural_intent(
    view: PersonView,
    sensors: Sensors,
    outputs: BrainOutputs,
    bias: LearningBias,
) -> NeuralIntent:
    food_signal = max(
        sensors.food_odor,
        sensors.food_left,
        sensors.food_right,
        sensors.memory_food_left,
        sensors.memory_food_right,
    )
    wall_signal = max(
        sensors.loom_left,
        sensors.loom_right,
    )
    mate_signal = max(
        sensors.mate_visual,
        sensors.mate_left,
        sensors.mate_right,
    )
    game_signal = max(
        sensors.game_odor,
        sensors.game_left,
        sensors.game_right,
    )

    survival_gate = _clamp(
        1.0
        - view.hunger * 0.72
        - view.pain * 0.28
    )
    learned_motion = _clamp(
        bias.forward
        + bias.backward
        + bias.escape
        + abs(bias.turn)
    )

    avoid = _clamp(
        view.pain * 0.78
        + wall_signal
        * (
            0.52
            + outputs.escape * 0.92
        )
    )
    feed = _clamp(
        view.hunger * view.hunger * 0.58
        + food_signal
        * (
            0.58
            + outputs.forward * 0.52
        )
    )
    reproduce = _clamp(
        view.reproduction_drive
        * mate_signal
        * (
            0.42
            + outputs.courtship * 1.18
        )
        * max(
            0.05,
            survival_gate,
        )
    )
    play = _clamp(
        game_signal
        * (
            0.38
            + (1.0 - view.mood) * 0.62
        )
        * max(
            0.04,
            1.0 - view.hunger * 0.90,
        )
    )
    rest = _clamp(
        view.fatigue
        * (
            0.82
            - outputs.escape * 0.32
        )
    )
    explore = _clamp(
        outputs.forward
        * (
            1.0
            - max(
                food_signal,
                wall_signal,
                mate_signal,
                game_signal,
            )
        )
        * 0.82
        + learned_motion * 0.18
    )

    scores = {
        "避痛": avoid,
        "进食": feed,
        "繁衍": reproduce,
        "娱乐": play,
        "休息": rest,
        "探索": explore,
    }
    dominant = max(
        scores,
        key=scores.get,
    )
    total = sum(
        scores.values()
    )
    confidence = (
        scores[dominant] / total
        if total > 1e-6
        else 0.0
    )

    combined_escape = _clamp(
        outputs.escape
        + bias.escape
    )
    combined_forward = _clamp(
        outputs.forward
        + bias.forward
    )
    combined_backward = _clamp(
        outputs.backward
        + bias.backward
    )
    combined_turn = max(
        -1.0,
        min(
            1.0,
            outputs.turn
            + bias.turn,
        ),
    )

    if combined_escape > 0.45:
        action = "逃离"
    elif combined_backward > 0.42:
        action = "后退"
    elif abs(combined_turn) > 0.30:
        action = (
            "右转"
            if combined_turn > 0
            else "左转"
        )
    elif combined_forward > 0.22:
        action = "前进"
    else:
        action = "停留"

    raw = {
        "饥饿": _clamp(view.hunger),
        "疼痛": _clamp(view.pain),
        "食物感觉": _clamp(food_signal),
        "边界感觉": _clamp(wall_signal),
        "异性感觉": _clamp(mate_signal),
        "游戏感觉": _clamp(game_signal),
        "前进神经": _clamp(outputs.forward),
        "逃逸神经": _clamp(outputs.escape),
        "求偶神经": _clamp(outputs.courtship),
        "策略置信": _clamp(bias.confidence),
    }

    return NeuralIntent(
        dominant=dominant,
        confidence=_clamp(confidence),
        action=action,
        scores=scores,
        raw=raw,
    )
