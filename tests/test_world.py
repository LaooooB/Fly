import math
import random

from cyberfly.world import CyberFlyWorld


def test_world_starts_without_food():
    world = CyberFlyWorld(width=400, height=300, rng=random.Random(0))
    assert world.food == []


def test_place_food_uses_selected_position_and_clamps_margin():
    world = CyberFlyWorld(width=400, height=300, rng=random.Random(1))
    placed = world.place_food(5.0, 295.0)
    assert placed == (28.0, 272.0)
    assert world.food == [placed]


def test_eating_reduces_hunger_remembers_food_and_does_not_respawn():
    world = CyberFlyWorld(width=400, height=300, rng=random.Random(2))
    world.food = [(200.0, 150.0)]
    world.state.x = 200.0
    world.state.y = 150.0
    world.state.hunger = 0.9
    event = world.update_body(0.1)

    assert event == "ate"
    assert world.state.hunger < 0.9
    assert [200.0, 150.0] in world.state.known_food_spots
    assert world.food == []


def test_sensors_split_food_odor_by_side():
    world = CyberFlyWorld(width=400, height=300, rng=random.Random(3))
    world.state.x = 200.0
    world.state.y = 150.0
    world.state.heading = 0.0
    world.food = [(240.0, 110.0)]
    sensors = world.sense()

    assert sensors.food_odor > 0
    assert sensors.food_left != sensors.food_right


def test_apply_motor_moves_pet():
    world = CyberFlyWorld(width=400, height=300, rng=random.Random(4))
    x0, y0 = world.state.x, world.state.y
    world.apply_motor(
        dt=0.5,
        forward=1.0,
        turn=0.0,
        backward=0.0,
        escape=0.0,
    )
    assert math.hypot(world.state.x - x0, world.state.y - y0) > 1.0
