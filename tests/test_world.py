import math
import random

from cyberfly.world import CyberFlyWorld


def _person(world, alias):
    pid = world._resolve_person_id(alias)
    return world.people[pid]


def test_world_starts_without_food():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(0),
    )
    assert world.food == []
    assert world.population_counts() == (1, 1)


def test_place_food_uses_selected_position_and_clamps_margin():
    world = CyberFlyWorld(
        width=400,
        height=300,
        rng=random.Random(1),
    )
    placed = world.place_food(
        5.0,
        295.0,
    )
    assert placed == (28.0, 272.0)
    assert world.food == [placed]


def test_male_eating_restores_only_fifteen_percent_satiety():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(2),
    )
    male = _person(world, "male")
    male.x = 200.0
    male.y = 150.0
    male.hunger = 0.9
    world.food = [(200.0, 150.0)]

    before = male.hunger
    events = world.update_people(0.1)
    restored = before - male.hunger

    assert events[0]["person_id"] == male.person_id
    assert 0.149 < restored < 0.151
    assert [200.0, 150.0] in world.state.known_food_spots
    assert world.food == []


def test_female_eats_and_emits_reward_signal():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(3),
    )
    female = _person(world, "female")
    female.x = 260.0
    female.y = 180.0
    female.hunger = 0.9
    world.food = [(260.0, 180.0)]

    events = world.update_people(0.1)
    dopamine, pain, reasons = world.consume_learning_signal(
        female.person_id
    )

    assert events[0]["gender"] == "female"
    assert female.food_eaten == 1
    assert dopamine >= 1.0
    assert pain >= 0.0
    assert "dopamine:ate_bread" in reasons


def test_add_people_keeps_one_shared_population_snapshot():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(4),
    )
    male_2 = world.add_person("male")
    female_2 = world.add_person("female")

    assert world.population_counts() == (2, 2)
    assert male_2 in world.people
    assert female_2 in world.people
    assert len(world.state.people) == 4


def test_female_moves_faster_than_male_for_same_command():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(5),
    )
    male = _person(world, "male")
    female = _person(world, "female")

    male.x = 300.0
    male.y = 300.0
    female.x = 300.0
    female.y = 450.0
    male.heading = 0.0
    female.heading = 0.0
    male.fatigue = 0.0
    female.fatigue = 0.0

    male_x0 = male.x
    female_x0 = female.x

    world.apply_motor(
        dt=0.5,
        forward=1.0,
        turn=0.0,
        backward=0.0,
        escape=0.0,
        person_id=male.person_id,
    )
    world.apply_motor(
        dt=0.5,
        forward=1.0,
        turn=0.0,
        backward=0.0,
        escape=0.0,
        person_id=female.person_id,
    )

    male_distance = male.x - male_x0
    female_distance = female.x - female_x0

    assert male_distance > 1.0
    assert female_distance > male_distance * 1.25


def test_sensors_split_food_odor_by_side():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(6),
    )
    male = _person(world, "male")
    male.x = 200.0
    male.y = 150.0
    male.heading = 0.0
    world.food = [(240.0, 110.0)]

    sensors = world.sense(male.person_id)

    assert sensors.food_odor > 0
    assert sensors.food_left != sensors.food_right


def test_apply_motor_moves_person_and_advances_walk_phase():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(7),
    )
    male = _person(world, "male")
    x0 = male.x
    y0 = male.y
    phase0 = male.walk_phase

    world.apply_motor(
        dt=0.5,
        forward=1.0,
        turn=0.0,
        backward=0.0,
        escape=0.0,
        person_id=male.person_id,
    )

    assert math.hypot(
        male.x - x0,
        male.y - y0,
    ) > 1.0
    assert male.walk_phase > phase0


def test_starvation_at_full_hunger_kills_after_sixty_simulated_seconds():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(20),
    )
    male = _person(world, "male")
    male.hunger = 1.0

    events = world.update_people(59.0)
    assert male.alive is True
    assert not any(e["kind"] == "died" for e in events)

    events = world.update_people(1.1)
    assert male.alive is False
    assert any(
        e["kind"] == "died"
        and e["person_id"] == male.person_id
        for e in events
    )


def test_eating_at_last_moment_resets_starvation_and_prevents_death():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(21),
    )
    male = _person(world, "male")
    male.x = 220.0
    male.y = 180.0
    male.hunger = 1.0
    male.starvation_seconds = 59.5
    world.food = [(220.0, 180.0)]

    events = world.update_people(0.6)

    assert male.alive is True
    assert male.starvation_seconds == 0.0
    assert male.hunger < 1.0
    assert any(e["kind"] == "ate_bread" for e in events)
    assert not any(e["kind"] == "died" for e in events)


def test_game_improves_mood_and_dopamine_without_feeding():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(22),
    )
    female = _person(world, "female")
    female.x = 300.0
    female.y = 240.0
    female.hunger = 0.72
    female.mood = 0.20
    world.place_game(300.0, 240.0)

    hunger_before = female.hunger
    mood_before = female.mood
    events = world.update_people(0.1)
    dopamine, _, reasons = world.consume_learning_signal(
        female.person_id
    )

    assert female.hunger >= hunger_before
    assert female.mood > mood_before
    assert female.games_played == 1
    assert dopamine >= 1.0
    assert "dopamine:played_game" in reasons
    assert any(e["kind"] == "played_game" for e in events)


def test_dead_person_cannot_move():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(23),
    )
    male = _person(world, "male")
    male.alive = False
    x0, y0 = male.x, male.y

    bounced = world.apply_motor(
        dt=1.0,
        forward=1.0,
        turn=0.0,
        backward=0.0,
        escape=0.0,
        person_id=male.person_id,
    )

    assert bounced is False
    assert male.x == x0
    assert male.y == y0


def test_mate_sensor_targets_opposite_sex_only():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(40),
    )
    male_1 = _person(world, "male")
    male_2_id = world.add_person("male")
    male_2 = world.people[male_2_id]
    female = _person(world, "female")

    male_1.x = 200.0
    male_1.y = 200.0
    male_1.heading = 0.0
    male_2.x = 215.0
    male_2.y = 200.0
    female.x = 260.0
    female.y = 200.0
    male_1.reproduction_drive = 1.0
    male_1.hunger = 0.2
    male_1.pain = 0.0

    nearest = world._nearest_other(male_1)
    sensors = world.sense(male_1.person_id)

    assert nearest is not None
    assert nearest.gender == "female"
    assert sensors.mate_visual > 0.0


def test_sex_gives_max_dopamine_and_reduces_reproduction_drive():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(41),
    )
    male = _person(world, "male")
    female = _person(world, "female")

    male.x = 300.0
    male.y = 300.0
    female.x = 320.0
    female.y = 300.0

    for person in (male, female):
        person.hunger = 0.2
        person.pain = 0.0
        person.mood = 0.8
        person.reproduction_drive = 1.0
        person.sex_cooldown = 0.0

    events = world.try_sex(
        courtship_signal=1.0,
        max_people=12,
    )
    male_signal, _, male_reasons = world.consume_learning_signal(
        male.person_id
    )
    female_signal, _, female_reasons = world.consume_learning_signal(
        female.person_id
    )

    assert any(e["kind"] == "sex" for e in events)
    assert male.sex_events == 1
    assert female.sex_events == 1
    assert male.dopamine == 1.0
    assert female.dopamine == 1.0
    assert male_signal >= 1.5
    assert female_signal >= 1.5
    assert "dopamine:sex" in male_reasons
    assert "dopamine:sex" in female_reasons
    assert male.reproduction_drive < 0.4
    assert female.reproduction_drive < 0.4


def test_dead_people_do_not_count_as_population_or_block_spawn_checks():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(42),
    )
    male = _person(world, "male")
    male.alive = False

    assert male.person_id not in world.living_ids()
    assert world.population_counts() == (0, 1)
    assert world.living_count() == 1


def test_collision_pain_is_strong():
    world = CyberFlyWorld(
        width=400,
        height=300,
        rng=random.Random(43),
    )
    male = _person(world, "male")
    male.x = 378.0
    male.y = 150.0
    male.heading = 0.0

    bounced = world.apply_motor(
        dt=0.5,
        forward=1.0,
        turn=0.0,
        backward=0.0,
        escape=0.0,
        person_id=male.person_id,
    )
    _, pain, reasons = world.consume_learning_signal(
        male.person_id
    )

    assert bounced is True
    assert pain >= 2.0
    assert "pain:boundary_collision" in reasons



def test_remove_person_prefers_selected_same_gender_and_keeps_shared_world():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(60),
    )
    male_2 = world.add_person("male")
    male_3 = world.add_person("male")

    removed = world.remove_person(
        "male",
        preferred_id=male_2,
    )

    assert removed == male_2
    assert male_2 not in world.people
    assert male_3 in world.people
    assert world.population_counts() == (2, 1)


def test_remove_gender_can_reach_zero_and_persist_in_population_snapshot():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(61),
    )

    removed = world.remove_person("female")

    assert removed is not None
    assert world.population_counts() == (1, 0)
    assert all(
        person["gender"] != "female"
        for person in world.state.people
    )

    restored = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(62),
        snapshot=world.state,
    )
    assert restored.population_counts() == (1, 0)


def test_remove_person_never_removes_last_living_person():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(63),
    )
    world.remove_person("female")

    only_male = world._resolve_person_id("male")
    removed = world.remove_person(
        "male",
        preferred_id=only_male,
    )

    assert removed is None
    assert world.living_count() == 1
    assert only_male in world.people
