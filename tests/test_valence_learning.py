import random

from cyberfly.learning import ACTIONS, FastValenceLearner
from cyberfly.world import CyberFlyWorld, Sensors


def test_eating_bread_emits_dopamine():
    world = CyberFlyWorld(width=400, height=300, rng=random.Random(1))
    world.food = [(200.0, 150.0)]
    world.state.x = 200.0
    world.state.y = 150.0
    world.state.hunger = 0.9
    event = world.update_body(0.1)
    dopamine, pain, reasons = world.consume_learning_signal()

    assert event == "ate"
    assert dopamine >= 1.0
    assert pain >= 0.0
    assert "dopamine:ate_bread" in reasons
    assert world.state.reward_events == 1


def test_boundary_collision_emits_pain():
    world = CyberFlyWorld(width=400, height=300, rng=random.Random(2))
    world.state.x = 382.0
    world.state.y = 150.0
    world.state.heading = 0.0
    world.update_body(0.02)
    bounced = world.apply_motor(
        dt=0.5,
        forward=1.0,
        turn=0.0,
        backward=0.0,
        escape=0.0,
    )
    _, pain, reasons = world.consume_learning_signal()

    assert bounced is True
    assert pain >= 1.0
    assert "pain:boundary_collision" in reasons
    assert world.state.pain_events == 1


def test_hunger_emits_continuous_pain():
    world = CyberFlyWorld(width=400, height=300, rng=random.Random(3))
    world.state.hunger = 0.9
    world.update_body(0.5)
    _, pain, reasons = world.consume_learning_signal()

    assert pain > 0.0
    assert "pain:hunger" in reasons
    assert world.state.pain > 0.5


def test_dopamine_strengthens_selected_action():
    learner = FastValenceLearner(rng=random.Random(4), epsilon=0.0)
    sensors = Sensors(
        food_odor=0.8,
        food_left=0.8,
        food_right=0.1,
    )
    state = learner.state_key(sensors, hunger=0.8)
    learner.q_table[state] = [0.0, 0.5, 0.0, 0.0, 0.0]
    bias = learner.choose_bias(sensors, hunger=0.8, dt=1.0)
    idx = ACTIONS.index(bias.action)
    before = learner.q_table[state][idx]
    learner.learn(1.0, 0.0, sensors, hunger=0.8)
    after = learner.q_table[state][idx]

    assert bias.action == "left"
    assert after > before


def test_pain_weakens_selected_action():
    learner = FastValenceLearner(rng=random.Random(5), epsilon=0.0)
    sensors = Sensors(loom_left=0.9, loom_right=0.9)
    state = learner.state_key(sensors, hunger=0.3)
    learner.q_table[state] = [0.0, 0.0, 0.0, 0.7, 0.0]
    bias = learner.choose_bias(sensors, hunger=0.3, dt=1.0)
    idx = ACTIONS.index(bias.action)
    before = learner.q_table[state][idx]
    learner.learn(0.0, 1.0, sensors, hunger=0.3)
    after = learner.q_table[state][idx]

    assert bias.action == "forward"
    assert after < before
