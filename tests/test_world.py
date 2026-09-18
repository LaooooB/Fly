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
