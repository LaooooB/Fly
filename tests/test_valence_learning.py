import random

from cyberfly.learning import ACTIONS, FastValenceLearner
from cyberfly.world import CyberFlyWorld, Sensors


def _male(world):
    return world.people[
        world._resolve_person_id("male")
    ]


def test_eating_bread_emits_dopamine():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(1),
    )
    male = _male(world)
    male.x = 200.0
    male.y = 150.0
    male.hunger = 0.9
    world.food = [(200.0, 150.0)]

    events = world.update_people(0.1)
    dopamine, pain, reasons = (
        world.consume_learning_signal(
            male.person_id
        )
    )

    assert events[0]["person_id"] == male.person_id
    assert dopamine >= 1.0
    assert pain >= 0.0
    assert "dopamine:ate_bread" in reasons
    assert male.reward_events == 1


def test_boundary_collision_emits_pain():
    world = CyberFlyWorld(
        width=400,
        height=300,
        rng=random.Random(2),
    )
    male = _male(world)
    male.x = 382.0
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
    _, pain, reasons = (
        world.consume_learning_signal(
            male.person_id
        )
    )

    assert bounced is True
    assert pain >= 1.0
    assert "pain:boundary_collision" in reasons
    assert male.pain_events == 1


def test_hunger_emits_continuous_pain():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(3),
    )
    male = _male(world)
    male.hunger = 0.9

    world.update_people(0.5)
    _, pain, reasons = (
        world.consume_learning_signal(
            male.person_id
        )
    )

    assert pain > 0.0
    assert "pain:hunger" in reasons
    assert male.pain > 0.5


def test_dopamine_strengthens_selected_action():
    learner = FastValenceLearner(
        rng=random.Random(4),
        epsilon=0.0,
    )
    sensors = Sensors(
        food_odor=0.8,
        food_left=0.8,
        food_right=0.1,
    )
    state = learner.state_key(
        sensors,
        hunger=0.8,
    )
    learner.q_table[state] = [
        0.0,
        0.5,
        0.0,
        0.0,
        0.0,
    ]

    bias = learner.choose_bias(
        sensors,
        hunger=0.8,
        dt=1.0,
    )
    idx = ACTIONS.index(
        bias.action
    )
    before = learner.q_table[
        state
    ][idx]

    learner.learn(
        1.0,
        0.0,
        sensors,
        hunger=0.8,
    )
    after = learner.q_table[
        state
    ][idx]

    assert bias.action == "left"
    assert after > before


def test_pain_weakens_selected_action():
    learner = FastValenceLearner(
        rng=random.Random(5),
        epsilon=0.0,
    )
    sensors = Sensors(
        loom_left=0.9,
        loom_right=0.9,
    )
    state = learner.state_key(
        sensors,
        hunger=0.3,
    )
    learner.q_table[state] = [
        0.0,
        0.0,
        0.0,
        0.7,
        0.0,
    ]

    bias = learner.choose_bias(
        sensors,
        hunger=0.3,
        dt=1.0,
    )
    idx = ACTIONS.index(
        bias.action
    )
    before = learner.q_table[
        state
    ][idx]

    learner.learn(
        0.0,
        1.0,
        sensors,
        hunger=0.3,
    )
    after = learner.q_table[
        state
    ][idx]

    assert bias.action == "forward"
    assert after < before


def test_two_people_train_one_shared_q_table_twice():
    learner = FastValenceLearner(
        rng=random.Random(6),
        epsilon=0.0,
    )
    sensors = Sensors(
        food_odor=0.8,
        food_left=0.9,
        food_right=0.1,
    )
    state = learner.state_key(
        sensors,
        hunger=0.8,
    )
    learner.q_table[state] = [
        0.0,
        0.5,
        0.0,
        0.0,
        0.0,
    ]

    learner.choose_bias(
        sensors,
        hunger=0.8,
        dt=1.0,
        agent_id="male_1",
    )
    learner.choose_bias(
        sensors,
        hunger=0.8,
        dt=1.0,
        agent_id="female_1",
    )

    before = learner.q_table[
        state
    ][1]

    learner.learn(
        1.0,
        0.0,
        sensors,
        hunger=0.8,
        agent_id="male_1",
    )
    middle = learner.q_table[
        state
    ][1]

    learner.learn(
        1.0,
        0.0,
        sensors,
        hunger=0.8,
        agent_id="female_1",
    )
    after = learner.q_table[
        state
    ][1]

    assert learner.updates == 2
    assert middle > before
    assert after > middle
    assert learner.active_agents == 2


def test_terminal_death_penalty_is_stronger_and_does_not_bootstrap():
    learner = FastValenceLearner(
        rng=random.Random(30),
        epsilon=0.0,
    )
    sensors = Sensors(
        food_odor=0.8,
        food_left=0.8,
        food_right=0.1,
    )
    state = learner.state_key(
        sensors,
        hunger=1.0,
    )
    learner.q_table[state] = [
        0.0,
        0.7,
        0.0,
        0.0,
        0.0,
    ]
    bias = learner.choose_bias(
        sensors,
        hunger=1.0,
        dt=1.0,
        agent_id="male_1",
    )
    idx = ACTIONS.index(bias.action)
    before = learner.q_table[state][idx]

    valence = learner.learn(
        0.0,
        2.0,
        sensors,
        hunger=1.0,
        agent_id="male_1",
        terminal=True,
    )
    after = learner.q_table[state][idx]

    assert valence == -2.0
    assert after < before
