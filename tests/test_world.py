import math
import random

from cyberfly.memory import PetSnapshot
from cyberfly.world import CyberFlyWorld


def test_eating_reduces_hunger_and_remembers_food():
    world = CyberFlyWorld(width=400, height=300, rng=random.Random(1))
    world.food = [(200.0, 150.0)]
    world.state.x = 200.0
    world.state.y = 150.0
    world.state.hunger = 0.9
    event = world.update_body(0.1)
    assert event == "ate"
    assert world.state.hunger < 0.9
    assert [200.0, 150.0] in world.state.known_food_spots


def test_sensors_split_food_odor_by_side():
    world = CyberFlyWorld(width=400, height=300, rng=random.Random(2))
    world.state.x = 200.0
    world.state.y = 150.0
    world.state.heading = 0.0  # faces right
    world.food = [(240.0, 110.0)]  # screen-up is left of heading in our convention
    s = world.sense()
    assert s.food_odor > 0
    assert s.food_left != s.food_right


def test_apply_motor_moves_fly():
    world = CyberFlyWorld(width=400, height=300, rng=random.Random(3))
    x0, y0 = world.state.x, world.state.y
    world.apply_motor(dt=0.5, forward=1.0, turn=0.0, backward=0.0, escape=0.0)
    assert math.hypot(world.state.x - x0, world.state.y - y0) > 1.0
