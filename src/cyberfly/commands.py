from __future__ import annotations

from dataclasses import dataclass
import re

from .learning import LearningBias
from .world import PersonView, Sensors


GOAL_LABELS = {
    "food": "去吃面包",
    "game": "去玩游戏",
    "mate": "去找异性",
    "avoid": "远离墙边",
    "rest": "休息",
    "explore": "探索",
}


@dataclass(frozen=True)
class ParsedCommand:
    scope: str
    goal: str | None
    label: str
    original: str


@dataclass
class ActiveCommand:
    goal: str
    label: str
    baseline_food: int = 0
    baseline_games: int = 0
    baseline_sex: int = 0
    elapsed: float = 0.0


def _normalize(text: str) -> str:
    value = text.strip().casefold()
    value = re.sub(r"[\s，。！？、,.!?；;：:]+", "", value)
    return value


def parse_command(text: str) -> ParsedCommand | None:
    original = text.strip()
    value = _normalize(original)
    if not value:
        return None

    scope = "selected"
    for prefix in (
        "所有人",
        "全部人",
        "全体",
        "大家",
        "所有角色",
    ):
        if value.startswith(prefix):
            scope = "all"
            value = value[len(prefix):]
            break

    if value in {
        "停止",
        "停下",
        "取消",
        "取消指令",
        "停止指令",
        "自由活动",
        "自己决定",
    }:
        return ParsedCommand(
            scope=scope,
            goal=None,
            label="取消指令",
            original=original,
        )

    groups = (
        (
            "food",
            (
                "吃面包",
                "去吃面包",
                "找面包",
                "找面包吃",
                "吃东西",
                "去吃东西",
                "找吃的",
                "进食",
                "去进食",
            ),
        ),
        (
            "game",
            (
                "玩游戏",
                "去玩游戏",
                "打游戏",
                "去打游戏",
                "娱乐",
                "去娱乐",
                "玩游戏机",
                "去玩游戏机",
            ),
        ),
        (
            "mate",
            (
                "找异性",
                "去找异性",
                "找对象",
                "去找对象",
                "找伴侣",
                "去找伴侣",
                "繁衍",
                "去繁衍",
                "交配",
            ),
        ),
        (
            "avoid",
            (
                "离开墙边",
                "远离墙",
                "远离墙边",
                "别撞墙",
                "不要撞墙",
                "避开墙",
                "躲开墙",
            ),
        ),
        (
            "rest",
            (
                "休息",
                "去休息",
                "睡觉",
                "去睡觉",
                "停下来休息",
            ),
        ),
        (
            "explore",
            (
                "探索",
                "去探索",
                "随便走走",
                "四处走走",
                "到处看看",
                "走走",
            ),
        ),
    )

    for goal, phrases in groups:
        if any(
            phrase in value
            for phrase in phrases
        ):
            return ParsedCommand(
                scope=scope,
                goal=goal,
                label=GOAL_LABELS[goal],
                original=original,
            )

    return None


def make_active_command(
    goal: str,
    view: PersonView,
) -> ActiveCommand:
    return ActiveCommand(
        goal=goal,
        label=GOAL_LABELS[goal],
        baseline_food=view.food_eaten,
        baseline_games=view.games_played,
        baseline_sex=view.sex_events,
    )


def command_is_complete(
    command: ActiveCommand,
    view: PersonView,
    sensors: Sensors,
) -> bool:
    if command.goal == "food":
        return (
            view.food_eaten
            > command.baseline_food
        )
    if command.goal == "game":
        return (
            view.games_played
            > command.baseline_games
        )
    if command.goal == "mate":
        return (
            view.sex_events
            > command.baseline_sex
        )
    if command.goal == "rest":
        return (
            view.fatigue < 0.34
            and command.elapsed > 0.5
        )
    if command.goal == "avoid":
        return (
            max(
                sensors.loom_left,
                sensors.loom_right,
            )
            < 0.10
            and command.elapsed > 0.8
        )
    return False


def _target_bias(
    left: float,
    right: float,
    strength: float,
    action: str,
) -> LearningBias:
    delta = right - left
    return LearningBias(
        forward=0.34 * strength,
        turn=max(
            -0.62,
            min(
                0.62,
                delta * 1.15,
            ),
        )
        * strength,
        action=action,
        confidence=strength,
    )


def command_bias(
    command: ActiveCommand | None,
    view: PersonView,
    sensors: Sensors,
) -> LearningBias:
    if (
        command is None
        or not view.alive
    ):
        return LearningBias()

    wall = max(
        sensors.loom_left,
        sensors.loom_right,
    )

    danger = max(
        view.pain,
        wall,
        max(
            0.0,
            (view.hunger - 0.88)
            / 0.12,
        ),
    )

    survival_override = max(
        0.0,
        min(1.0, danger),
    )

    if command.goal in {
        "food",
        "avoid",
    }:
        command_gate = 1.0
    else:
        command_gate = max(
            0.05,
            1.0
            - survival_override * 0.94,
        )

    if command.goal == "food":
        signal = max(
            sensors.food_odor,
            sensors.memory_food_left,
            sensors.memory_food_right,
        )
        if signal < 0.04:
            return LearningBias(
                forward=0.16,
                action="cmd_food_search",
                confidence=0.28,
            )
        return _target_bias(
            sensors.food_left
            + sensors.memory_food_left,
            sensors.food_right
            + sensors.memory_food_right,
            max(
                0.38,
                min(
                    1.0,
                    0.52
                    + view.hunger * 0.48,
                ),
            ),
            "cmd_food",
        )

    if command.goal == "game":
        if sensors.game_odor < 0.04:
            return LearningBias(
                forward=0.10
                * command_gate,
                action="cmd_game_search",
                confidence=0.18
                * command_gate,
            )
        return _target_bias(
            sensors.game_left,
            sensors.game_right,
            0.72 * command_gate,
            "cmd_game",
        )

    if command.goal == "mate":
        if sensors.mate_visual < 0.04:
            return LearningBias(
                forward=0.10
                * command_gate,
                action="cmd_mate_search",
                confidence=0.18
                * command_gate,
            )
        return _target_bias(
            sensors.mate_left,
            sensors.mate_right,
            0.70 * command_gate,
            "cmd_mate",
        )

    if command.goal == "avoid":
        delta = (
            sensors.loom_left
            - sensors.loom_right
        )
        if wall < 0.10:
            return LearningBias(
                action="cmd_avoid",
                confidence=0.15,
            )
        return LearningBias(
            forward=0.04,
            turn=max(
                -0.85,
                min(
                    0.85,
                    delta * 1.30,
                ),
            ),
            backward=0.14 * wall,
            escape=0.30 * wall,
            action="cmd_avoid",
            confidence=min(
                1.0,
                0.45 + wall * 0.55,
            ),
        )

    if command.goal == "rest":
        return LearningBias(
            backward=0.08
            * command_gate,
            action="cmd_rest",
            confidence=0.62
            * command_gate,
        )

    if command.goal == "explore":
        return LearningBias(
            forward=0.20
            * command_gate,
            action="cmd_explore",
            confidence=0.45
            * command_gate,
        )

    return LearningBias()


def command_strength(
    command: ActiveCommand | None,
    view: PersonView,
    sensors: Sensors,
) -> float:
    if command is None:
        return 0.0
    return command_bias(
        command,
        view,
        sensors,
    ).confidence
