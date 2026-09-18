import random

from cyberfly.commands import (
    command_bias,
    command_is_complete,
    make_active_command,
    parse_command,
)
from cyberfly.world import CyberFlyWorld, Sensors


def _view_and_person(seed=70):
    world = CyberFlyWorld(
        width=900,
        height=700,
        rng=random.Random(seed),
    )
    pid = world._resolve_person_id(
        "male"
    )
    return (
        world,
        pid,
        world.people[pid],
    )


def test_parse_common_food_command():
    parsed = parse_command(
        "去吃面包"
    )
    assert parsed is not None
    assert parsed.scope == "selected"
    assert parsed.goal == "food"
    assert parsed.label == "去吃面包"


def test_parse_all_people_command():
    parsed = parse_command(
        "所有人 去玩游戏"
    )
    assert parsed is not None
    assert parsed.scope == "all"
    assert parsed.goal == "game"


def test_parse_cancel_command():
    parsed = parse_command(
        "取消指令"
    )
    assert parsed is not None
    assert parsed.goal is None


def test_food_command_steers_toward_food():
    world, pid, person = (
        _view_and_person()
    )
    person.hunger = 0.5
    view = world.person_view(pid)
    command = make_active_command(
        "food",
        view,
    )
    bias = command_bias(
        command,
        view,
        Sensors(
            food_odor=0.8,
            food_left=0.1,
            food_right=0.9,
        ),
    )

    assert bias.forward > 0.2
    assert bias.turn > 0.0
    assert bias.confidence > 0.5


def test_survival_pressure_suppresses_game_command():
    world, pid, person = (
        _view_and_person(71)
    )
    person.hunger = 0.99
    person.pain = 0.2
    view = world.person_view(pid)
    command = make_active_command(
        "game",
        view,
    )
    bias = command_bias(
        command,
        view,
        Sensors(
            game_odor=0.9,
            game_left=0.1,
            game_right=0.9,
        ),
    )

    assert bias.confidence < 0.15
    assert bias.forward < 0.1


def test_food_command_completes_after_eating():
    world, pid, person = (
        _view_and_person(72)
    )
    command = make_active_command(
        "food",
        world.person_view(pid),
    )
    person.food_eaten += 1

    assert command_is_complete(
        command,
        world.person_view(pid),
        Sensors(),
    ) is True


def test_explore_command_does_not_auto_complete():
    world, pid, _ = (
        _view_and_person(73)
    )
    command = make_active_command(
        "explore",
        world.person_view(pid),
    )
    command.elapsed = 100.0

    assert command_is_complete(
        command,
        world.person_view(pid),
        Sensors(),
    ) is False
