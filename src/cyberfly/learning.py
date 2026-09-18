from __future__ import annotations

from dataclasses import dataclass
import random

from .world import Sensors


ACTIONS = ("none", "left", "right", "forward", "back")


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


@dataclass(frozen=True)
class LearningBias:
    forward: float = 0.0
    turn: float = 0.0
    backward: float = 0.0
    escape: float = 0.0
    action: str = "none"
    confidence: float = 0.0


@dataclass
class _AgentTrace:
    last_state: str | None = None
    last_action: int | None = None
    held_action: int = 0
    hold_remaining: float = 0.0


class FastValenceLearner:
    """One shared Q table fed by many simulated bodies."""

    def __init__(
        self,
        q_table: dict[str, list[float]] | None = None,
        rng: random.Random | None = None,
        alpha: float = 0.38,
        gamma: float = 0.35,
        epsilon: float = 0.22,
        decision_seconds: float = 0.22,
    ):
        self.rng = rng or random.Random()
        self.alpha = float(alpha)
        self.gamma = float(gamma)
        self.epsilon = float(epsilon)
        self.decision_seconds = float(decision_seconds)
        self.q_table: dict[str, list[float]] = {}
        for key, values in (q_table or {}).items():
            if (
                not isinstance(key, str)
                or not isinstance(values, list)
                or len(values) != len(ACTIONS)
            ):
                continue
            self.q_table[key] = [
                _clamp(v, -2.0, 2.0)
                for v in values
            ]

        self._traces: dict[str, _AgentTrace] = {}
        self.updates = 0

    def _trace(self, agent_id: str) -> _AgentTrace:
        return self._traces.setdefault(
            str(agent_id),
            _AgentTrace(),
        )

    @property
    def last_state(self) -> str | None:
        return self._trace("default").last_state

    @property
    def last_action(self) -> int | None:
        return self._trace("default").last_action

    def _q(self, state: str) -> list[float]:
        return self.q_table.setdefault(
            state,
            [0.0] * len(ACTIONS),
        )

    @staticmethod
    def state_key(
        sensors: Sensors,
        hunger: float,
    ) -> str:
        food_left = (
            sensors.food_left
            + sensors.memory_food_left
        )
        food_right = (
            sensors.food_right
            + sensors.memory_food_right
        )
        food_strength = max(
            food_left,
            food_right,
            sensors.food_odor,
        )
        food_delta = (
            food_right - food_left
        )

        if food_strength < 0.07:
            food = "F0"
        elif food_delta > 0.06:
            food = "FR"
        elif food_delta < -0.06:
            food = "FL"
        else:
            food = "FC"

        wall_strength = max(
            sensors.loom_left,
            sensors.loom_right,
        )
        if wall_strength < 0.12:
            wall = "W0"
        elif (
            sensors.loom_left
            - sensors.loom_right
            > 0.08
        ):
            wall = "WL"
        elif (
            sensors.loom_right
            - sensors.loom_left
            > 0.08
        ):
            wall = "WR"
        else:
            wall = "WB"

        if hunger > 0.72:
            need = "H2"
        elif hunger > 0.40:
            need = "H1"
        else:
            need = "H0"

        return f"{food}|{wall}|{need}"

    def _pick_action(self, state: str) -> int:
        q = self._q(state)
        if self.rng.random() < self.epsilon:
            return self.rng.randrange(
                len(ACTIONS)
            )
        best = max(q)
        if abs(best) < 1e-6:
            return 0
        candidates = [
            i
            for i, value in enumerate(q)
            if abs(value - best) < 1e-9
        ]
        return candidates[
            self.rng.randrange(
                len(candidates)
            )
        ]

    def choose_bias(
        self,
        sensors: Sensors,
        hunger: float,
        dt: float,
        agent_id: str = "default",
    ) -> LearningBias:
        trace = self._trace(agent_id)
        state = self.state_key(
            sensors,
            hunger,
        )
        trace.hold_remaining -= max(
            0.0,
            dt,
        )

        if trace.hold_remaining <= 0.0:
            trace.held_action = (
                self._pick_action(state)
            )
            trace.hold_remaining = (
                self.decision_seconds
            )

        action_idx = trace.held_action
        trace.last_state = state
        trace.last_action = action_idx

        q = self._q(state)
        confidence = _clamp(
            abs(q[action_idx]) / 1.5,
            0.0,
            1.0,
        )
        strength = (
            0.72 + 0.28 * confidence
        )
        action = ACTIONS[action_idx]

        if action == "left":
            return LearningBias(
                turn=-0.42 * strength,
                action=action,
                confidence=confidence,
            )
        if action == "right":
            return LearningBias(
                turn=0.42 * strength,
                action=action,
                confidence=confidence,
            )
        if action == "forward":
            return LearningBias(
                forward=0.30 * strength,
                action=action,
                confidence=confidence,
            )
        if action == "back":
            return LearningBias(
                backward=0.26 * strength,
                escape=0.08 * strength,
                action=action,
                confidence=confidence,
            )

        return LearningBias(
            action="none",
            confidence=confidence,
        )

    def learn(
        self,
        dopamine: float,
        pain: float,
        next_sensors: Sensors,
        hunger: float,
        agent_id: str = "default",
    ) -> float:
        trace = self._trace(agent_id)

        if (
            trace.last_state is None
            or trace.last_action is None
        ):
            return 0.0

        valence = _clamp(
            float(dopamine)
            - float(pain),
            -1.0,
            1.0,
        )
        if abs(valence) < 1e-6:
            return 0.0

        q = self._q(
            trace.last_state
        )
        next_q = self._q(
            self.state_key(
                next_sensors,
                hunger,
            )
        )
        old = q[trace.last_action]
        target = (
            valence
            + self.gamma * max(next_q)
        )
        event_alpha = min(
            0.75,
            self.alpha
            * (
                1.0
                + 0.55 * abs(valence)
            ),
        )

        q[trace.last_action] = _clamp(
            old
            + event_alpha
            * (target - old),
            -2.0,
            2.0,
        )
        self.updates += 1
        return valence

    def pause(
        self,
        agent_id: str = "default",
    ) -> None:
        trace = self._trace(agent_id)
        trace.last_state = None
        trace.last_action = None
        trace.held_action = 0
        trace.hold_remaining = 0.0

    def forget_agent(
        self,
        agent_id: str,
    ) -> None:
        self._traces.pop(
            str(agent_id),
            None,
        )

    def export(self) -> dict[str, list[float]]:
        return {
            key: [
                round(float(v), 6)
                for v in values
            ]
            for key, values
            in self.q_table.items()
        }

    @property
    def known_states(self) -> int:
        return len(self.q_table)

    @property
    def active_agents(self) -> int:
        return len(self._traces)
