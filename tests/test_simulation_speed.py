from cyberfly.game import (
    SIM_SPEED_MAX,
    SIM_SPEED_MIN,
    _snap_simulation_speed,
)


def test_speed_slider_clamps_to_bounds():
    assert _snap_simulation_speed(0.0) == SIM_SPEED_MIN
    assert _snap_simulation_speed(99.0) == SIM_SPEED_MAX


def test_speed_slider_uses_half_step_increments():
    assert _snap_simulation_speed(1.24) == 1.0
    assert _snap_simulation_speed(1.26) == 1.5
    assert _snap_simulation_speed(4.74) == 4.5
    assert _snap_simulation_speed(4.76) == 5.0
