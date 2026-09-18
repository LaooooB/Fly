import random

from cyberfly.brain_adapter import BrainOutputs
from cyberfly.introspection import interpret_neural_intent
from cyberfly.learning import LearningBias
from cyberfly.world import CyberFlyWorld, Sensors


def _view():
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(50),
    )
    male = world.people[
        world._resolve_person_id("male")
    ]
    male.hunger = 0.2
    male.pain = 0.0
    male.fatigue = 0.1
    male.mood = 0.5
    male.reproduction_drive = 0.8
    return world, male


def test_neural_intent_changes_with_live_hunger_and_food_signal():
    world, male = _view()
    male.hunger = 0.95
    view = world.person_view(male.person_id)

    intent = interpret_neural_intent(
        view,
        Sensors(
            food_odor=0.95,
            food_left=0.8,
            food_right=0.2,
        ),
        BrainOutputs(
            forward=0.7,
            escape=0.0,
            courtship=0.0,
        ),
        LearningBias(
            forward=0.2,
            confidence=0.7,
        ),
    )

    assert intent.dominant == "进食"
    assert intent.raw["饥饿"] > 0.9
    assert intent.scores["进食"] > intent.scores["繁衍"]


def test_neural_intent_changes_to_avoidance_with_pain_and_looming():
    world, male = _view()
    male.pain = 0.9
    view = world.person_view(male.person_id)

    intent = interpret_neural_intent(
        view,
        Sensors(
            loom_left=0.95,
            loom_right=0.8,
        ),
        BrainOutputs(
            forward=0.1,
            escape=0.9,
            courtship=0.0,
        ),
        LearningBias(
            escape=0.1,
            confidence=0.8,
        ),
    )

    assert intent.dominant == "避痛"
    assert intent.action == "逃离"
    assert intent.raw["边界感觉"] > 0.9


def test_neural_intent_can_be_reproduction_driven():
    world, male = _view()
    male.reproduction_drive = 1.0
    male.hunger = 0.1
    male.pain = 0.0
    view = world.person_view(male.person_id)

    intent = interpret_neural_intent(
        view,
        Sensors(
            mate_visual=0.95,
            mate_left=0.1,
            mate_right=0.9,
        ),
        BrainOutputs(
            forward=0.35,
            escape=0.0,
            courtship=1.0,
        ),
        LearningBias(
            turn=0.2,
            confidence=0.6,
        ),
    )

    assert intent.dominant == "繁衍"
    assert intent.scores["繁衍"] > intent.scores["进食"]



def test_user_command_changes_interpreted_intent_without_hardcoded_event_text():
    world, male = _view()
    male.hunger = 0.35
    male.pain = 0.0
    male.mood = 0.4
    view = world.person_view(
        male.person_id
    )

    no_command = interpret_neural_intent(
        view,
        Sensors(
            game_odor=0.55,
            game_left=0.4,
            game_right=0.5,
        ),
        BrainOutputs(
            forward=0.25,
            escape=0.0,
            courtship=0.0,
        ),
        LearningBias(),
    )
    with_command = interpret_neural_intent(
        view,
        Sensors(
            game_odor=0.55,
            game_left=0.4,
            game_right=0.5,
        ),
        BrainOutputs(
            forward=0.25,
            escape=0.0,
            courtship=0.0,
        ),
        LearningBias(),
        command_goal="game",
        command_strength=0.9,
    )

    assert (
        with_command.scores["娱乐"]
        > no_command.scores["娱乐"]
    )
    assert (
        with_command.raw["指令影响"]
        == 0.9
    )
