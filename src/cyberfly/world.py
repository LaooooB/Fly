from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Any

from .memory import PetSnapshot


TAU = math.tau


def _clamp(
    v: float,
    lo: float = 0.0,
    hi: float = 1.0,
) -> float:
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
    game_odor: float = 0.0
    game_left: float = 0.0
    game_right: float = 0.0


@dataclass
class PersonState:
    person_id: str
    gender: str
    x: float
    y: float
    heading: float
    hunger: float = 0.35
    fatigue: float = 0.15
    social_drive: float = 0.30
    dopamine: float = 0.0
    pain: float = 0.0
    age_seconds: float = 0.0
    food_eaten: int = 0
    reward_events: int = 0
    pain_events: int = 0
    mood: float = 0.50
    games_played: int = 0
    starvation_seconds: float = 0.0
    alive: bool = True
    walk_phase: float = 0.0
    speed: float = 0.0
    last_food_distance: float | None = None
    game_cooldown: float = 0.0
    reproduction_drive: float = 0.35
    sex_events: int = 0
    offspring_count: int = 0
    sex_cooldown: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "gender": self.gender,
            "x": round(float(self.x), 4),
            "y": round(float(self.y), 4),
            "heading": round(float(self.heading), 6),
            "hunger": round(float(self.hunger), 6),
            "fatigue": round(float(self.fatigue), 6),
            "social_drive": round(float(self.social_drive), 6),
            "dopamine": round(float(self.dopamine), 6),
            "pain": round(float(self.pain), 6),
            "age_seconds": round(float(self.age_seconds), 4),
            "food_eaten": int(self.food_eaten),
            "reward_events": int(self.reward_events),
            "pain_events": int(self.pain_events),
            "mood": round(float(self.mood), 6),
            "games_played": int(self.games_played),
            "starvation_seconds": round(float(self.starvation_seconds), 4),
            "alive": bool(self.alive),
            "reproduction_drive": round(float(self.reproduction_drive), 6),
            "sex_events": int(self.sex_events),
            "offspring_count": int(self.offspring_count),
        }

    @classmethod
    def from_dict(
        cls,
        raw: dict[str, Any],
        fallback_id: str,
        fallback_gender: str,
        fallback_x: float,
        fallback_y: float,
    ) -> "PersonState":
        gender = str(
            raw.get("gender", fallback_gender)
        ).lower()
        if gender not in {"male", "female"}:
            gender = fallback_gender

        return cls(
            person_id=str(
                raw.get(
                    "person_id",
                    fallback_id,
                )
            ),
            gender=gender,
            x=float(
                raw.get("x", fallback_x)
            ),
            y=float(
                raw.get("y", fallback_y)
            ),
            heading=float(
                raw.get(
                    "heading",
                    0.0,
                )
            ),
            hunger=_clamp(
                float(
                    raw.get(
                        "hunger",
                        0.35,
                    )
                )
            ),
            fatigue=_clamp(
                float(
                    raw.get(
                        "fatigue",
                        0.15,
                    )
                )
            ),
            social_drive=_clamp(
                float(
                    raw.get(
                        "social_drive",
                        0.30,
                    )
                )
            ),
            dopamine=_clamp(
                float(
                    raw.get(
                        "dopamine",
                        0.0,
                    )
                )
            ),
            pain=_clamp(
                float(
                    raw.get(
                        "pain",
                        0.0,
                    )
                )
            ),
            age_seconds=max(
                0.0,
                float(
                    raw.get(
                        "age_seconds",
                        0.0,
                    )
                ),
            ),
            food_eaten=max(
                0,
                int(
                    raw.get(
                        "food_eaten",
                        0,
                    )
                ),
            ),
            reward_events=max(
                0,
                int(
                    raw.get(
                        "reward_events",
                        0,
                    )
                ),
            ),
            pain_events=max(
                0,
                int(
                    raw.get(
                        "pain_events",
                        0,
                    )
                ),
            ),
            mood=_clamp(
                float(
                    raw.get(
                        "mood",
                        0.50,
                    )
                )
            ),
            games_played=max(
                0,
                int(
                    raw.get(
                        "games_played",
                        0,
                    )
                ),
            ),
            starvation_seconds=max(
                0.0,
                float(
                    raw.get(
                        "starvation_seconds",
                        0.0,
                    )
                ),
            ),
            alive=bool(
                raw.get(
                    "alive",
                    True,
                )
            ),
            reproduction_drive=_clamp(
                float(
                    raw.get(
                        "reproduction_drive",
                        0.35,
                    )
                )
            ),
            sex_events=max(
                0,
                int(raw.get("sex_events", 0)),
            ),
            offspring_count=max(
                0,
                int(raw.get("offspring_count", 0)),
            ),
        )


@dataclass(frozen=True)
class PersonView:
    person_id: str
    gender: str
    name: str
    x: float
    y: float
    heading: float
    hunger: float
    fatigue: float
    social_drive: float
    dopamine: float
    pain: float
    age_seconds: float
    food_eaten: int
    reward_events: int
    pain_events: int
    mood: float
    games_played: int
    starvation_seconds: float
    starvation_remaining: float
    alive: bool
    reproduction_drive: float
    sex_events: int
    offspring_count: int
    walk_phase: float
    speed: float


class CyberFlyWorld:
    FEMALE_SPEED_MULTIPLIER = 1.30

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
        self.state = snapshot or PetSnapshot()

        self.food: list[
            tuple[float, float]
        ] = []
        self.games: list[
            tuple[float, float]
        ] = []
        self.people: dict[
            str, PersonState
        ] = {}
        self._signals: dict[
            str,
            dict[str, Any],
        ] = {}

        self._load_people()
        self.sync_snapshot()

    def _load_people(self) -> None:
        raw_people = self.state.people

        if raw_people:
            for index, raw in enumerate(
                raw_people,
                start=1,
            ):
                if not isinstance(raw, dict):
                    continue
                fallback_gender = (
                    "male"
                    if index % 2
                    else "female"
                )
                person = PersonState.from_dict(
                    raw,
                    fallback_id=(
                        f"{fallback_gender}_{index}"
                    ),
                    fallback_gender=(
                        fallback_gender
                    ),
                    fallback_x=(
                        self.width * 0.45
                    ),
                    fallback_y=(
                        self.height * 0.50
                    ),
                )
                person.person_id = (
                    self._unique_id(
                        person.person_id,
                        person.gender,
                    )
                )
                self.people[
                    person.person_id
                ] = person

        if not self.people:
            male = PersonState(
                person_id="male_1",
                gender="male",
                x=float(self.state.x),
                y=float(self.state.y),
                heading=float(
                    self.state.heading
                ),
                hunger=float(
                    self.state.hunger
                ),
                fatigue=float(
                    self.state.fatigue
                ),
                social_drive=float(
                    self.state.social_drive
                ),
                dopamine=float(
                    self.state.dopamine
                ),
                pain=float(
                    self.state.pain
                ),
                age_seconds=float(
                    self.state.age_seconds
                ),
                food_eaten=int(
                    self.state.food_eaten
                ),
                reward_events=int(
                    self.state.reward_events
                ),
                pain_events=int(
                    self.state.pain_events
                ),
            )
            female = PersonState(
                person_id="female_1",
                gender="female",
                x=float(
                    self.state.female_x
                ),
                y=float(
                    self.state.female_y
                ),
                heading=float(
                    self.state.female_heading
                ),
                hunger=float(
                    self.state.female_hunger
                ),
                fatigue=float(
                    self.state.female_fatigue
                ),
                social_drive=float(
                    self.state.female_social_drive
                ),
                dopamine=float(
                    self.state.female_dopamine
                ),
                pain=float(
                    self.state.female_pain
                ),
                age_seconds=float(
                    self.state.female_age_seconds
                ),
                food_eaten=int(
                    self.state.female_food_eaten
                ),
                reward_events=int(
                    self.state.female_reward_events
                ),
                pain_events=int(
                    self.state.female_pain_events
                ),
            )
            self.people[male.person_id] = male
            self.people[female.person_id] = female

    def _unique_id(
        self,
        requested: str,
        gender: str,
    ) -> str:
        if requested not in self.people:
            return requested
        n = 1
        while (
            f"{gender}_{n}"
            in self.people
        ):
            n += 1
        return f"{gender}_{n}"

    def _next_id(
        self,
        gender: str,
    ) -> str:
        n = 1
        while (
            f"{gender}_{n}"
            in self.people
        ):
            n += 1
        return f"{gender}_{n}"

    def _spawn_position(
        self,
    ) -> tuple[float, float]:
        margin = 70.0

        for _ in range(30):
            x = self.rng.uniform(
                margin,
                self.width - margin,
            )
            y = self.rng.uniform(
                margin,
                self.height - margin,
            )
            if all(
                math.hypot(
                    x - p.x,
                    y - p.y,
                )
                >= 85.0
                for p in self.people.values()
                if p.alive
            ):
                return x, y

        return (
            self.rng.uniform(
                margin,
                self.width - margin,
            ),
            self.rng.uniform(
                margin,
                self.height - margin,
            ),
        )

    def add_person(
        self,
        gender: str,
    ) -> str:
        gender = str(gender).lower()
        if gender not in {
            "male",
            "female",
        }:
            raise ValueError(
                "gender must be male or female"
            )

        person_id = self._next_id(
            gender
        )
        x, y = self._spawn_position()

        person = PersonState(
            person_id=person_id,
            gender=gender,
            x=x,
            y=y,
            heading=self.rng.uniform(
                -math.pi,
                math.pi,
            ),
            hunger=(
                0.33
                if gender == "male"
                else 0.30
            ),
            fatigue=0.14,
            social_drive=0.30,
        )
        self.people[
            person_id
        ] = person
        self.sync_snapshot()
        return person_id

    def remove_person(
        self,
        gender: str,
        preferred_id: str | None = None,
    ) -> str | None:
        gender = str(gender).lower()
        if gender not in {
            "male",
            "female",
        }:
            raise ValueError(
                "gender must be male or female"
            )

        living = self.living_ids()
        if len(living) <= 1:
            return None

        candidates = [
            pid
            for pid in living
            if self.people[pid].gender
            == gender
        ]
        if not candidates:
            return None

        if (
            preferred_id in candidates
        ):
            target_id = str(
                preferred_id
            )
        else:
            target_id = candidates[-1]

        self.people.pop(
            target_id,
            None,
        )
        self._signals.pop(
            target_id,
            None,
        )
        self.sync_snapshot()
        return target_id

    def person_ids(
        self,
    ) -> list[str]:
        return list(
            self.people.keys()
        )

    def population_counts(
        self,
    ) -> tuple[int, int]:
        living = [
            p
            for p in self.people.values()
            if p.alive
        ]
        males = sum(
            p.gender == "male"
            for p in living
        )
        females = len(living) - males
        return males, females

    def _resolve_person_id(
        self,
        person_id: str | None,
    ) -> str:
        if person_id in {
            "male",
            "female",
        }:
            target = str(person_id)
            for pid, person in (
                self.people.items()
            ):
                if (
                    person.gender
                    == target
                ):
                    return pid

        if (
            person_id
            and person_id
            in self.people
        ):
            return person_id

        for pid, person in (
            self.people.items()
        ):
            if person.gender == "male":
                return pid

        return next(
            iter(self.people)
        )

    def person_view(
        self,
        person_id: str,
    ) -> PersonView:
        pid = self._resolve_person_id(
            person_id
        )
        person = self.people[pid]

        same_gender = [
            p.person_id
            for p in self.people.values()
            if p.gender == person.gender
        ]
        number = (
            same_gender.index(pid) + 1
        )
        name = (
            f"男 {number}"
            if person.gender == "male"
            else f"女 {number}"
        )

        return PersonView(
            person_id=pid,
            gender=person.gender,
            name=name,
            x=person.x,
            y=person.y,
            heading=person.heading,
            hunger=person.hunger,
            fatigue=person.fatigue,
            social_drive=(
                person.social_drive
            ),
            dopamine=person.dopamine,
            pain=person.pain,
            age_seconds=(
                person.age_seconds
            ),
            food_eaten=person.food_eaten,
            reward_events=(
                person.reward_events
            ),
            pain_events=(
                person.pain_events
            ),
            mood=person.mood,
            games_played=(
                person.games_played
            ),
            starvation_seconds=(
                person.starvation_seconds
            ),
            starvation_remaining=max(
                0.0,
                60.0
                - person.starvation_seconds,
            ),
            alive=person.alive,
            reproduction_drive=(
                person.reproduction_drive
            ),
            sex_events=person.sex_events,
            offspring_count=(
                person.offspring_count
            ),
            walk_phase=(
                person.walk_phase
            ),
            speed=person.speed,
        )

    def living_ids(
        self,
    ) -> list[str]:
        return [
            pid
            for pid, person
            in self.people.items()
            if person.alive
        ]

    def living_count(
        self,
    ) -> int:
        return len(
            self.living_ids()
        )

    def place_food(
        self,
        x: float,
        y: float,
    ) -> tuple[float, float]:
        margin = 28.0
        px = max(
            margin,
            min(
                self.width - margin,
                float(x),
            ),
        )
        py = max(
            margin,
            min(
                self.height - margin,
                float(y),
            ),
        )
        point = (px, py)
        self.food.append(point)

        for person in (
            self.people.values()
        ):
            person.last_food_distance = (
                self.nearest_food_distance(
                    person.person_id
                )
            )

        return point

    def place_game(
        self,
        x: float,
        y: float,
    ) -> tuple[float, float]:
        margin = 34.0
        px = max(
            margin,
            min(
                self.width - margin,
                float(x),
            ),
        )
        py = max(
            margin,
            min(
                self.height - margin,
                float(y),
            ),
        )
        point = (px, py)
        self.games.append(point)
        return point

    def _nearest_game(
        self,
        person: PersonState,
    ) -> tuple[float, float] | None:
        if not self.games:
            return None
        return min(
            self.games,
            key=lambda point: (
                point[0] - person.x
            ) ** 2
            + (
                point[1] - person.y
            ) ** 2,
        )

    def nearest_game_distance(
        self,
        person_id: str | None = None,
    ) -> float | None:
        pid = self._resolve_person_id(
            person_id
        )
        person = self.people[pid]
        nearest = self._nearest_game(
            person
        )
        if nearest is None:
            return None
        return math.hypot(
            nearest[0] - person.x,
            nearest[1] - person.y,
        )

    def _nearest_food(
        self,
        person: PersonState,
    ) -> tuple[float, float] | None:
        if not self.food:
            return None
        return min(
            self.food,
            key=lambda point: (
                point[0] - person.x
            ) ** 2
            + (
                point[1] - person.y
            ) ** 2,
        )

    def nearest_food_distance(
        self,
        person_id: str | None = None,
    ) -> float | None:
        pid = self._resolve_person_id(
            person_id
        )
        person = self.people[pid]
        nearest = self._nearest_food(
            person
        )
        if nearest is None:
            return None
        return math.hypot(
            nearest[0] - person.x,
            nearest[1] - person.y,
        )

    def _relative_side(
        self,
        person: PersonState,
        tx: float,
        ty: float,
    ) -> tuple[float, float, float]:
        dx = tx - person.x
        dy = ty - person.y
        distance = max(
            1e-6,
            math.hypot(dx, dy),
        )
        target_angle = math.atan2(
            dy,
            dx,
        )
        rel = _wrap_angle(
            target_angle
            - person.heading
        )

        left = (
            _clamp(
                (
                    -rel / math.pi
                    + 1.0
                )
                * 0.5
            )
            if rel < 0
            else _clamp(
                0.5
                - rel / math.pi
            )
        )
        right = (
            _clamp(
                (
                    rel / math.pi
                    + 1.0
                )
                * 0.5
            )
            if rel > 0
            else _clamp(
                0.5
                + rel / math.pi
            )
        )

        if abs(rel) < 0.05:
            left = right = 0.5

        return (
            distance,
            left,
            right,
        )

    def _nearest_other(
        self,
        person: PersonState,
    ) -> PersonState | None:
        others = [
            other
            for other
            in self.people.values()
            if (
                other.person_id
                != person.person_id
                and other.alive
                and other.gender
                != person.gender
            )
        ]
        if not others:
            return None
        return min(
            others,
            key=lambda other: (
                other.x - person.x
            ) ** 2
            + (
                other.y - person.y
            ) ** 2,
        )

    def sense(
        self,
        person_id: str | None = None,
    ) -> Sensors:
        pid = self._resolve_person_id(
            person_id
        )
        person = self.people[pid]
        sensors = Sensors()

        nearest_food = self._nearest_food(
            person
        )
        if nearest_food:
            dist, left, right = (
                self._relative_side(
                    person,
                    nearest_food[0],
                    nearest_food[1],
                )
            )
            sensors.food_odor = _clamp(
                (
                    1.0
                    - dist / 420.0
                )
                * (
                    0.35
                    + 0.65
                    * person.hunger
                )
            )
            sensors.food_left = (
                sensors.food_odor
                * left
            )
            sensors.food_right = (
                sensors.food_odor
                * right
            )

        other = self._nearest_other(
            person
        )
        if other:
            dist, left, right = (
                self._relative_side(
                    person,
                    other.x,
                    other.y,
                )
            )
            survival_gate = _clamp(
                1.0
                - person.hunger * 0.78
                - person.pain * 0.35,
                0.05,
                1.0,
            )
            attraction_gain = (
                0.20
                + 0.80
                * person.reproduction_drive
            )
            sensors.mate_visual = _clamp(
                (
                    1.0
                    - dist / 520.0
                )
                * attraction_gain
                * survival_gate
            )
            sensors.mate_left = (
                sensors.mate_visual
                * left
            )
            sensors.mate_right = (
                sensors.mate_visual
                * right
            )

        wall_margin = 90.0
        left_wall = person.x
        right_wall = (
            self.width - person.x
        )
        top_wall = person.y
        bottom_wall = (
            self.height - person.y
        )

        for sign, attr in [
            (-1.0, "loom_left"),
            (1.0, "loom_right"),
        ]:
            a = (
                person.heading
                + sign * 0.55
            )
            ray_dx = math.cos(a)
            ray_dy = math.sin(a)
            candidates: list[
                float
            ] = []

            if ray_dx < -1e-5:
                candidates.append(
                    left_wall / -ray_dx
                )
            if ray_dx > 1e-5:
                candidates.append(
                    right_wall / ray_dx
                )
            if ray_dy < -1e-5:
                candidates.append(
                    top_wall / -ray_dy
                )
            if ray_dy > 1e-5:
                candidates.append(
                    bottom_wall / ray_dy
                )

            ray_dist = min(
                (
                    d
                    for d in candidates
                    if d >= 0
                ),
                default=9999.0,
            )
            setattr(
                sensors,
                attr,
                _clamp(
                    1.0
                    - ray_dist
                    / wall_margin
                ),
            )

        nearest_game = self._nearest_game(
            person
        )
        if (
            nearest_game
            and person.alive
        ):
            dist, left, right = (
                self._relative_side(
                    person,
                    nearest_game[0],
                    nearest_game[1],
                )
            )
            survival_gate = max(
                0.12,
                1.0
                - person.hunger * 0.85,
            )
            mood_need = (
                0.40
                + 0.60
                * (1.0 - person.mood)
            )
            sensors.game_odor = _clamp(
                (
                    1.0
                    - dist / 380.0
                )
                * survival_gate
                * mood_need
            )
            sensors.game_left = (
                sensors.game_odor
                * left
            )
            sensors.game_right = (
                sensors.game_odor
                * right
            )

        if (
            sensors.food_odor < 0.08
            and self.state.known_food_spots
        ):
            remembered = min(
                self.state.known_food_spots,
                key=lambda point: (
                    point[0] - person.x
                ) ** 2
                + (
                    point[1] - person.y
                ) ** 2,
            )
            _, left, right = (
                self._relative_side(
                    person,
                    remembered[0],
                    remembered[1],
                )
            )
            memory_strength = (
                0.18
                * person.hunger
            )
            sensors.memory_food_left = (
                left
                * memory_strength
            )
            sensors.memory_food_right = (
                right
                * memory_strength
            )

        return sensors

    @staticmethod
    def aggregate_sensors(
        sensors_list: list[Sensors],
    ) -> Sensors:
        if not sensors_list:
            return Sensors()

        fields = (
            "food_odor",
            "food_left",
            "food_right",
            "mate_visual",
            "mate_left",
            "mate_right",
            "loom_left",
            "loom_right",
            "memory_food_left",
            "memory_food_right",
            "game_odor",
            "game_left",
            "game_right",
        )
        result = Sensors()

        for field_name in fields:
            setattr(
                result,
                field_name,
                max(
                    getattr(
                        sensors,
                        field_name,
                    )
                    for sensors
                    in sensors_list
                ),
            )

        return result

    def _signal(
        self,
        person_id: str,
    ) -> dict[str, Any]:
        return self._signals.setdefault(
            person_id,
            {
                "dopamine": 0.0,
                "pain": 0.0,
                "reasons": [],
            },
        )

    def pulse_dopamine(
        self,
        person_id: str,
        amount: float,
        reason: str,
        count_event: bool = False,
    ) -> None:
        pid = self._resolve_person_id(
            person_id
        )
        person = self.people[pid]
        amount = max(
            0.0,
            float(amount),
        )
        if amount <= 0.0:
            return

        signal = self._signal(pid)
        signal["dopamine"] = min(
            1.5,
            signal["dopamine"]
            + amount,
        )
        person.dopamine = max(
            person.dopamine,
            _clamp(amount * 7.0),
        )
        if reason:
            signal["reasons"].append(
                f"dopamine:{reason}"
            )
        if count_event:
            person.reward_events += 1

    def pulse_pain(
        self,
        person_id: str,
        amount: float,
        reason: str,
        count_event: bool = False,
    ) -> None:
        pid = self._resolve_person_id(
            person_id
        )
        person = self.people[pid]
        amount = max(
            0.0,
            float(amount),
        )
        if amount <= 0.0:
            return

        signal = self._signal(pid)
        signal["pain"] = min(
            2.0,
            signal["pain"]
            + amount,
        )
        person.pain = max(
            person.pain,
            _clamp(amount * 5.0),
        )
        if reason:
            signal["reasons"].append(
                f"pain:{reason}"
            )
        if count_event:
            person.pain_events += 1

    def consume_learning_signal(
        self,
        person_id: str | None = None,
    ) -> tuple[
        float,
        float,
        tuple[str, ...],
    ]:
        pid = self._resolve_person_id(
            person_id
        )
        signal = self._signals.pop(
            pid,
            None,
        )
        if not signal:
            return (
                0.0,
                0.0,
                (),
            )
        return (
            float(
                signal["dopamine"]
            ),
            float(
                signal["pain"]
            ),
            tuple(
                signal["reasons"]
            ),
        )

    def _remember_food(
        self,
        x: float,
        y: float,
    ) -> None:
        spot = [
            round(x, 2),
            round(y, 2),
        ]
        if (
            spot
            not in self.state.known_food_spots
        ):
            self.state.known_food_spots.append(
                spot
            )
            self.state.known_food_spots = (
                self.state.known_food_spots[
                    -64:
                ]
            )

    def update_people(
        self,
        dt: float,
    ) -> list[dict[str, Any]]:
        events: list[
            dict[str, Any]
        ] = []

        for person in (
            self.people.values()
        ):
            if not person.alive:
                person.speed = 0.0
                continue

            person.age_seconds += dt
            person.hunger = _clamp(
                person.hunger
                + (
                    0.0032
                    if person.gender
                    == "male"
                    else 0.0030
                )
                * dt
            )
            person.fatigue = _clamp(
                person.fatigue
                + 0.0017 * dt
            )
            person.social_drive = _clamp(
                person.social_drive
                + 0.0008 * dt
            )
            person.dopamine = _clamp(
                person.dopamine
                - 0.85 * dt
            )
            person.pain = _clamp(
                person.pain
                - 0.70 * dt
            )
            person.mood = _clamp(
                person.mood
                - 0.0012 * dt
            )
            person.game_cooldown = max(
                0.0,
                person.game_cooldown
                - dt,
            )
            person.sex_cooldown = max(
                0.0,
                person.sex_cooldown - dt,
            )
            person.reproduction_drive = _clamp(
                person.reproduction_drive
                + 0.0014 * dt
            )

            if person.hunger >= 0.999:
                person.starvation_seconds += dt
            else:
                person.starvation_seconds = 0.0

            current_distance = (
                self.nearest_food_distance(
                    person.person_id
                )
            )
            if (
                current_distance
                is not None
                and person.last_food_distance
                is not None
            ):
                progress = (
                    person.last_food_distance
                    - current_distance
                )
                if (
                    progress > 0.25
                    and person.hunger
                    > 0.30
                ):
                    shaping = (
                        min(
                            0.032,
                            progress * 0.0085,
                        )
                        * (
                            0.35
                            + 0.65
                            * person.hunger
                        )
                    )
                    self.pulse_dopamine(
                        person.person_id,
                        shaping,
                        "approach_bread",
                    )
            person.last_food_distance = (
                current_distance
            )

            hunger_pain = _clamp(
                (
                    person.hunger
                    - 0.50
                )
                / 0.50
            )
            critical = _clamp(
                (
                    person.hunger
                    - 0.85
                )
                / 0.15
            )
            if hunger_pain > 0.0:
                signal = self._signal(
                    person.person_id
                )
                pressure = (
                    hunger_pain * 0.60
                    + critical * 1.80
                )
                if (
                    person.starvation_seconds
                    > 0.0
                ):
                    starvation_progress = _clamp(
                        person.starvation_seconds
                        / 60.0
                    )
                    pressure += (
                        2.20
                        * (
                            0.45
                            + 0.55
                            * starvation_progress
                        )
                    )
                signal["pain"] = min(
                    2.0,
                    signal["pain"]
                    + pressure * dt,
                )
                person.pain = max(
                    person.pain,
                    hunger_pain,
                    critical,
                )
                signal["reasons"].append(
                    "pain:hunger"
                )
                if (
                    person.starvation_seconds
                    > 0.0
                ):
                    signal["reasons"].append(
                        "pain:starvation"
                    )

            if (
                person.reproduction_drive > 0.82
                and person.hunger < 0.72
                and person.pain < 0.45
                and self._nearest_other(person)
                is not None
            ):
                reproduction_pressure = (
                    (
                        person.reproduction_drive
                        - 0.82
                    )
                    / 0.18
                )
                signal = self._signal(
                    person.person_id
                )
                signal["pain"] = min(
                    2.0,
                    signal["pain"]
                    + 0.10
                    * reproduction_pressure
                    * dt,
                )
                signal["reasons"].append(
                    "pain:reproduction_pressure"
                )

        for person in list(
            self.people.values()
        ):
            if (
                not person.alive
                or person.hunger <= 0.18
            ):
                continue

            for i, (fx, fy) in enumerate(
                list(self.food)
            ):
                if (
                    math.hypot(
                        fx - person.x,
                        fy - person.y,
                    )
                    > 25.0
                ):
                    continue

                self.food.pop(i)
                person.hunger = _clamp(
                    person.hunger - 0.15
                )
                person.food_eaten += 1
                self._remember_food(
                    fx,
                    fy,
                )
                rescue = (
                    person.starvation_seconds
                    > 0.0
                    or person.hunger
                    >= 0.95
                )
                person.starvation_seconds = 0.0
                self.pulse_dopamine(
                    person.person_id,
                    (
                        1.45
                        if rescue
                        else 1.0
                    ),
                    (
                        "survival_food"
                        if rescue
                        else "ate_bread"
                    ),
                    count_event=True,
                )
                events.append(
                    {
                        "kind": "ate_bread",
                        "person_id": (
                            person.person_id
                        ),
                        "gender": (
                            person.gender
                        ),
                        "hunger_after": (
                            person.hunger
                        ),
                    }
                )

                for other in (
                    self.people.values()
                ):
                    other.last_food_distance = (
                        self.nearest_food_distance(
                            other.person_id
                        )
                    )
                break

        for person in list(
            self.people.values()
        ):
            if (
                not person.alive
                or person.game_cooldown
                > 0.0
            ):
                continue

            nearest_game = self._nearest_game(
                person
            )
            if (
                nearest_game is None
                or math.hypot(
                    nearest_game[0]
                    - person.x,
                    nearest_game[1]
                    - person.y,
                )
                > 34.0
            ):
                continue

            person.game_cooldown = 4.0
            person.games_played += 1
            person.mood = _clamp(
                person.mood + 0.42
            )
            self.pulse_dopamine(
                person.person_id,
                1.15,
                "played_game",
                count_event=True,
            )
            events.append(
                {
                    "kind": "played_game",
                    "person_id": (
                        person.person_id
                    ),
                    "gender": (
                        person.gender
                    ),
                    "mood_after": (
                        person.mood
                    ),
                }
            )

        for person in (
            self.people.values()
        ):
            if (
                not person.alive
                or person.hunger < 0.999
                or person.starvation_seconds
                < 60.0
            ):
                continue

            person.alive = False
            person.speed = 0.0
            person.pain = 1.0
            person.dopamine = 0.0
            self.pulse_pain(
                person.person_id,
                2.0,
                "death_starvation",
                count_event=True,
            )
            events.append(
                {
                    "kind": "died",
                    "person_id": (
                        person.person_id
                    ),
                    "gender": (
                        person.gender
                    ),
                    "reason": "starvation",
                }
            )

        self.sync_snapshot()
        return events

    def update_body(
        self,
        dt: float,
    ) -> str | None:
        events = self.update_people(dt)
        if not events:
            return None
        event = events[0]
        if event["gender"] == "female":
            return "female_ate"
        return "male_ate"

    def apply_motor(
        self,
        dt: float,
        forward: float,
        turn: float,
        backward: float,
        escape: float,
        person_id: str | None = None,
    ) -> bool:
        pid = self._resolve_person_id(
            person_id
        )
        person = self.people[pid]
        if not person.alive:
            person.speed = 0.0
            return False

        energy_scale = (
            1.0
            - 0.58
            * person.fatigue
        )
        gender_speed = (
            self.FEMALE_SPEED_MULTIPLIER
            if person.gender
            == "female"
            else 1.0
        )

        speed = (
            (
                10.0
                + 58.0
                * _clamp(forward)
                - 38.0
                * _clamp(backward)
            )
            * energy_scale
            * gender_speed
        )
        speed += (
            78.0
            * _clamp(escape)
            * gender_speed
        )

        turn_rate = (
            math.radians(110.0)
            * max(
                -1.0,
                min(1.0, turn),
            )
        )
        person.heading = _wrap_angle(
            person.heading
            + turn_rate * dt
        )

        old_x = person.x
        old_y = person.y

        person.x += (
            math.cos(person.heading)
            * speed
            * dt
        )
        person.y += (
            math.sin(person.heading)
            * speed
            * dt
        )

        bounced = False
        margin = 22.0

        if (
            person.x < margin
            or person.x
            > self.width - margin
        ):
            person.x = max(
                margin,
                min(
                    self.width - margin,
                    person.x,
                ),
            )
            person.heading = (
                math.pi
                - person.heading
            )
            bounced = True

        if (
            person.y < margin
            or person.y
            > self.height - margin
        ):
            person.y = max(
                margin,
                min(
                    self.height - margin,
                    person.y,
                ),
            )
            person.heading = (
                -person.heading
            )
            bounced = True

        if bounced:
            person.fatigue = _clamp(
                person.fatigue
                + 0.018
            )
            self.pulse_pain(
                pid,
                2.0,
                "boundary_collision",
                count_event=True,
            )

        moved = math.hypot(
            person.x - old_x,
            person.y - old_y,
        )
        person.speed = (
            moved
            / max(dt, 1e-6)
        )
        person.walk_phase += (
            moved * 0.24
        )

        self.sync_snapshot()
        return bounced

    def rest(
        self,
        dt: float,
        person_id: str | None = None,
    ) -> None:
        pid = self._resolve_person_id(
            person_id
        )
        person = self.people[pid]
        if not person.alive:
            person.speed = 0.0
            return
        person.fatigue = _clamp(
            person.fatigue
            - 0.06 * dt
        )
        person.speed = 0.0
        self.sync_snapshot()

    def try_sex(
        self,
        courtship_signal: float,
        max_people: int = 12,
    ) -> list[dict[str, Any]]:
        if courtship_signal < 0.18:
            return []

        candidates: list[
            tuple[float, PersonState, PersonState]
        ] = []
        people = [
            p
            for p in self.people.values()
            if p.alive
        ]

        for i, a in enumerate(people):
            if (
                a.sex_cooldown > 0.0
                or a.reproduction_drive < 0.45
                or a.hunger > 0.88
                or a.pain > 0.72
            ):
                continue
            for b in people[i + 1:]:
                if (
                    a.gender == b.gender
                    or b.sex_cooldown > 0.0
                    or b.reproduction_drive < 0.45
                    or b.hunger > 0.88
                    or b.pain > 0.72
                ):
                    continue
                distance = math.hypot(
                    a.x - b.x,
                    a.y - b.y,
                )
                if distance <= 42.0:
                    candidates.append(
                        (distance, a, b)
                    )

        if not candidates:
            return []

        candidates.sort(
            key=lambda row: row[0]
        )
        _, a, b = candidates[0]

        for person in (a, b):
            person.sex_cooldown = 28.0
            person.reproduction_drive = _clamp(
                person.reproduction_drive
                - 0.72
            )
            person.sex_events += 1
            person.mood = _clamp(
                person.mood + 0.55
            )
            person.fatigue = _clamp(
                person.fatigue + 0.055
            )
            self.pulse_dopamine(
                person.person_id,
                1.5,
                "sex",
                count_event=True,
            )

        events: list[dict[str, Any]] = [
            {
                "kind": "sex",
                "person_a": a.person_id,
                "person_b": b.person_id,
                "distance": math.hypot(
                    a.x - b.x,
                    a.y - b.y,
                ),
            }
        ]

        health = _clamp(
            1.0
            - (
                a.hunger
                + b.hunger
                + a.fatigue
                + b.fatigue
            )
            / 4.0
        )
        mood = (
            a.mood + b.mood
        ) * 0.5
        fertility = _clamp(
            0.15
            + 0.55 * health
            + 0.30 * mood
        )

        if (
            self.living_count() < max_people
            and self.rng.random()
            < fertility * 0.45
        ):
            gender = (
                "male"
                if self.rng.random() < 0.5
                else "female"
            )
            child_id = self.add_person(gender)
            child = self.people[child_id]
            child.x = _clamp(
                (a.x + b.x) * 0.5
                + self.rng.uniform(-22.0, 22.0),
                30.0,
                self.width - 30.0,
            )
            child.y = _clamp(
                (a.y + b.y) * 0.5
                + self.rng.uniform(-22.0, 22.0),
                30.0,
                self.height - 30.0,
            )
            child.hunger = 0.20
            child.fatigue = 0.08
            child.mood = 0.70
            a.offspring_count += 1
            b.offspring_count += 1

            for person in (a, b):
                self.pulse_dopamine(
                    person.person_id,
                    1.5,
                    "reproduction_success",
                    count_event=True,
                )

            events.append(
                {
                    "kind": "offspring",
                    "child_id": child_id,
                    "gender": gender,
                    "parent_a": a.person_id,
                    "parent_b": b.person_id,
                }
            )

        self.sync_snapshot()
        return events

    def closest_pair(
        self,
    ) -> tuple[
        str,
        str,
        float,
    ] | None:
        ids = self.living_ids()
        if len(ids) < 2:
            return None

        best: tuple[
            str,
            str,
            float,
        ] | None = None

        for i, pid_a in enumerate(ids):
            a = self.people[pid_a]
            for pid_b in ids[
                i + 1:
            ]:
                b = self.people[pid_b]
                distance = math.hypot(
                    a.x - b.x,
                    a.y - b.y,
                )
                if (
                    best is None
                    or distance
                    < best[2]
                ):
                    best = (
                        pid_a,
                        pid_b,
                        distance,
                    )

        return best

    def population_averages(
        self,
    ) -> tuple[
        float,
        float,
        float,
    ]:
        people = [
            person
            for person
            in self.people.values()
            if person.alive
        ]
        n = max(
            1,
            len(people),
        )
        return (
            sum(
                p.hunger
                for p in people
            )
            / n,
            sum(
                p.fatigue
                for p in people
            )
            / n,
            sum(
                p.social_drive
                for p in people
            )
            / n,
        )

    def sync_snapshot(self) -> None:
        self.state.people = [
            person.to_dict()
            for person
            in self.people.values()
        ]

        first_male = next(
            (
                p
                for p in self.people.values()
                if p.gender == "male"
            ),
            None,
        )
        first_female = next(
            (
                p
                for p in self.people.values()
                if p.gender == "female"
            ),
            None,
        )

        if first_male:
            self.state.x = first_male.x
            self.state.y = first_male.y
            self.state.heading = (
                first_male.heading
            )
            self.state.hunger = (
                first_male.hunger
            )
            self.state.fatigue = (
                first_male.fatigue
            )
            self.state.social_drive = (
                first_male.social_drive
            )
            self.state.age_seconds = (
                first_male.age_seconds
            )
            self.state.food_eaten = (
                first_male.food_eaten
            )
            self.state.dopamine = (
                first_male.dopamine
            )
            self.state.pain = (
                first_male.pain
            )
            self.state.reward_events = (
                first_male.reward_events
            )
            self.state.pain_events = (
                first_male.pain_events
            )

        if first_female:
            self.state.female_x = (
                first_female.x
            )
            self.state.female_y = (
                first_female.y
            )
            self.state.female_heading = (
                first_female.heading
            )
            self.state.female_hunger = (
                first_female.hunger
            )
            self.state.female_fatigue = (
                first_female.fatigue
            )
            self.state.female_social_drive = (
                first_female.social_drive
            )
            self.state.female_age_seconds = (
                first_female.age_seconds
            )
            self.state.female_food_eaten = (
                first_female.food_eaten
            )
            self.state.female_dopamine = (
                first_female.dopamine
            )
            self.state.female_pain = (
                first_female.pain
            )
            self.state.female_reward_events = (
                first_female.reward_events
            )
            self.state.female_pain_events = (
                first_female.pain_events
            )
