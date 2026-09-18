from __future__ import annotations

from dataclasses import dataclass
import math
import random

from .memory import PetSnapshot


TAU = math.tau


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _wrap_angle(a: float) -> float:
    return (a + math.pi) % TAU - math.pi


@dataclass
class Sensors:
    food_odor: float = 0.0
    food_left: float = 0.0
    food_right: float = 0.0
    mate_visual: float = 0.0
    mate_left: float = 0.0
    mate_right: float = 0.0
    loom_left: float = 0.0
    loom_right: float = 0.0
    memory_food_left: float = 0.0
    memory_food_right: float = 0.0


class CyberFlyWorld:
    """2D body/world around the fixed MaleCNS controller.

    The public class name is kept for save/package compatibility. The rendered avatar can be human.
    """

    def __init__(
        self,
        width: int = 1100,
        height: int = 700,
        rng: random.Random | None = None,
        snapshot: PetSnapshot | None = None,
    ):
        self.width = width
        self.height = height
        self.rng = rng or random.Random()
        self.state = snapshot or PetSnapshot(x=width * 0.5, y=height * 0.5)
        self.food: list[tuple[float, float]] = []
        self.mate = [width * 0.75, height * 0.5]
        self.mate_heading = math.pi
        self._mate_turn_timer = 0.0
        self._dopamine_signal = 0.0
        self._pain_signal = 0.0
        self._signal_reasons: list[str] = []
        self._last_food_distance: float | None = None
        self._spawn_food(7)

    def _spawn_food(self, count: int = 1) -> None:
        margin = 55
        for _ in range(count):
            self.food.append(
                (
                    self.rng.uniform(margin, self.width - margin),
                    self.rng.uniform(margin, self.height - margin),
                )
            )

    def _relative_side(self, tx: float, ty: float) -> tuple[float, float, float]:
        dx = tx - self.state.x
        dy = ty - self.state.y
        distance = max(1e-6, math.hypot(dx, dy))
        target_angle = math.atan2(dy, dx)
        rel = _wrap_angle(target_angle - self.state.heading)
        left = (
            _clamp((-rel / math.pi + 1.0) * 0.5)
            if rel < 0
            else _clamp(0.5 - rel / math.pi)
        )
        right = (
            _clamp((rel / math.pi + 1.0) * 0.5)
            if rel > 0
            else _clamp(0.5 + rel / math.pi)
        )
        if abs(rel) < 0.05:
            left = right = 0.5
        return distance, left, right

    def _nearest(
        self, points: list[tuple[float, float]] | list[list[float]]
    ) -> tuple[float, float] | None:
        if not points:
            return None
        return min(
            points,
            key=lambda p: (p[0] - self.state.x) ** 2 + (p[1] - self.state.y) ** 2,
        )

    def nearest_food_distance(self) -> float | None:
        nearest = self._nearest(self.food)
        if nearest is None:
            return None
        return math.hypot(nearest[0] - self.state.x, nearest[1] - self.state.y)

    def pulse_dopamine(
        self, amount: float, reason: str, count_event: bool = False
    ) -> None:
        amount = max(0.0, float(amount))
        if amount <= 0.0:
            return
        self._dopamine_signal = min(1.5, self._dopamine_signal + amount)
        self.state.dopamine = max(self.state.dopamine, _clamp(amount * 7.0))
        if reason:
            self._signal_reasons.append(f"dopamine:{reason}")
        if count_event:
            self.state.reward_events += 1

    def pulse_pain(self, amount: float, reason: str, count_event: bool = False) -> None:
        amount = max(0.0, float(amount))
        if amount <= 0.0:
            return
        self._pain_signal = min(1.5, self._pain_signal + amount)
        self.state.pain = max(self.state.pain, _clamp(amount * 5.0))
        if reason:
            self._signal_reasons.append(f"pain:{reason}")
        if count_event:
            self.state.pain_events += 1

    def consume_learning_signal(self) -> tuple[float, float, tuple[str, ...]]:
        dopamine = self._dopamine_signal
        pain = self._pain_signal
        reasons = tuple(self._signal_reasons)
        self._dopamine_signal = 0.0
        self._pain_signal = 0.0
        self._signal_reasons.clear()
        return dopamine, pain, reasons

    def sense(self) -> Sensors:
        s = Sensors()
        nearest_food = self._nearest(self.food)
        if nearest_food:
            dist, left, right = self._relative_side(nearest_food[0], nearest_food[1])
            s.food_odor = _clamp(
                (1.0 - dist / 420.0) * (0.35 + 0.65 * self.state.hunger)
            )
            s.food_left = s.food_odor * left
            s.food_right = s.food_odor * right

        dist, left, right = self._relative_side(self.mate[0], self.mate[1])
        s.mate_visual = _clamp(
            (1.0 - dist / 500.0) * (0.35 + 0.65 * self.state.social_drive)
        )
        s.mate_left = s.mate_visual * left
        s.mate_right = s.mate_visual * right

        wall_margin = 90.0
        left_wall = self.state.x
        right_wall = self.width - self.state.x
        top_wall = self.state.y
        bottom_wall = self.height - self.state.y
        for sign, attr in [(-1.0, "loom_left"), (1.0, "loom_right")]:
            a = self.state.heading + sign * 0.55
            ray_dx, ray_dy = math.cos(a), math.sin(a)
            candidates: list[float] = []
            if ray_dx < -1e-5:
                candidates.append(left_wall / -ray_dx)
            if ray_dx > 1e-5:
                candidates.append(right_wall / ray_dx)
            if ray_dy < -1e-5:
                candidates.append(top_wall / -ray_dy)
            if ray_dy > 1e-5:
                candidates.append(bottom_wall / ray_dy)
            ray_dist = min((d for d in candidates if d >= 0), default=9999.0)
            setattr(s, attr, _clamp(1.0 - ray_dist / wall_margin))

        if s.food_odor < 0.08 and self.state.known_food_spots:
            remembered = self._nearest(self.state.known_food_spots)
            if remembered:
                _, left, right = self._relative_side(remembered[0], remembered[1])
                memory_strength = 0.18 * self.state.hunger
                s.memory_food_left = left * memory_strength
                s.memory_food_right = right * memory_strength
        return s

    def update_mate(self, dt: float) -> None:
        self._mate_turn_timer -= dt
        if self._mate_turn_timer <= 0:
            self._mate_turn_timer = self.rng.uniform(0.8, 2.8)
            self.mate_heading += self.rng.uniform(-1.2, 1.2)
        speed = 28.0
        self.mate[0] += math.cos(self.mate_heading) * speed * dt
        self.mate[1] += math.sin(self.mate_heading) * speed * dt
        if self.mate[0] < 35 or self.mate[0] > self.width - 35:
            self.mate_heading = math.pi - self.mate_heading
        if self.mate[1] < 35 or self.mate[1] > self.height - 35:
            self.mate_heading = -self.mate_heading
        self.mate[0] = max(35, min(self.width - 35, self.mate[0]))
        self.mate[1] = max(35, min(self.height - 35, self.mate[1]))

    def update_body(self, dt: float) -> str | None:
        st = self.state
        self._dopamine_signal = 0.0
        self._pain_signal = 0.0
        self._signal_reasons.clear()

        st.age_seconds += dt
        st.hunger = _clamp(st.hunger + 0.0032 * dt)
        st.fatigue = _clamp(st.fatigue + 0.0018 * dt)
        st.social_drive = _clamp(st.social_drive + 0.0008 * dt)
        st.dopamine = _clamp(st.dopamine - 0.85 * dt)
        st.pain = _clamp(st.pain - 0.70 * dt)

        current_food_distance = self.nearest_food_distance()
        if current_food_distance is not None and self._last_food_distance is not None:
            progress = self._last_food_distance - current_food_distance
            if progress > 0.25 and st.hunger > 0.32:
                shaping = min(0.028, progress * 0.0075) * (
                    0.35 + 0.65 * st.hunger
                )
                self.pulse_dopamine(shaping, "approach_bread")
        self._last_food_distance = current_food_distance

        hunger_pain = _clamp((st.hunger - 0.50) / 0.50)
        if hunger_pain > 0.0:
            self._pain_signal += hunger_pain * dt * 0.60
            st.pain = max(st.pain, hunger_pain)
            self._signal_reasons.append("pain:hunger")

        eaten_index = None
        for i, (fx, fy) in enumerate(self.food):
            if math.hypot(fx - st.x, fy - st.y) <= 24.0 and st.hunger > 0.18:
                eaten_index = i
                spot = [round(fx, 2), round(fy, 2)]
                if spot not in st.known_food_spots:
                    st.known_food_spots.append(spot)
                    st.known_food_spots = st.known_food_spots[-32:]
                st.hunger = _clamp(st.hunger - 0.52)
                st.food_eaten += 1
                self.pulse_dopamine(1.0, "ate_bread", count_event=True)
                break
        if eaten_index is not None:
            self.food.pop(eaten_index)
            self._spawn_food(1)
            self._last_food_distance = self.nearest_food_distance()
            return "ate"
        return None

    def apply_motor(
        self,
        dt: float,
        forward: float,
        turn: float,
        backward: float,
        escape: float,
    ) -> bool:
        st = self.state
        energy_scale = 1.0 - 0.58 * st.fatigue
        speed = (
            18.0 + 92.0 * _clamp(forward) - 70.0 * _clamp(backward)
        ) * energy_scale
        speed += 150.0 * _clamp(escape)
        turn_rate = math.radians(125.0) * max(-1.0, min(1.0, turn))
        st.heading = _wrap_angle(st.heading + turn_rate * dt)
        st.x += math.cos(st.heading) * speed * dt
        st.y += math.sin(st.heading) * speed * dt
        bounced = False
        margin = 18.0
        if st.x < margin or st.x > self.width - margin:
            st.x = max(margin, min(self.width - margin, st.x))
            st.heading = math.pi - st.heading
            bounced = True
        if st.y < margin or st.y > self.height - margin:
            st.y = max(margin, min(self.height - margin, st.y))
            st.heading = -st.heading
            bounced = True
        if bounced:
            st.fatigue = _clamp(st.fatigue + 0.018)
            self.pulse_pain(1.0, "boundary_collision", count_event=True)
        return bounced

    def rest(self, dt: float) -> None:
        self.state.fatigue = _clamp(self.state.fatigue - 0.06 * dt)
