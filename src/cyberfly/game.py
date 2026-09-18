from __future__ import annotations

import atexit
import math
import os
from pathlib import Path
import signal
import time

import pygame

from .brain_adapter import BrainOutputs, MaleCNSBrain
from .learning import FastValenceLearner, LearningBias
from .memory import MemoryStore
from .world import CyberFlyWorld


WIDTH, HEIGHT = 1180, 760
ARENA_W = 900
FPS = 60
AUTOSAVE_SECONDS = 30.0


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _marker_path() -> Path:
    root = Path(os.environ.get("FLY_DATA", r"J:\FLY\male_cns_data"))
    return root / "OFFICIAL_MALECNS_BUILD_OK.json"


def _ensure_verified_malecns() -> None:
    marker = _marker_path()
    if not marker.exists():
        raise RuntimeError(
            "Official MaleCNS build marker is missing. Run INSTALL_OFFICIAL_MALECNS.bat first.\n"
            f"Expected: {marker}"
        )


def _bar(screen, font, x, y, label, value, width=190):
    value = _clamp(value)
    pygame.draw.rect(screen, (45, 48, 55), (x, y + 19, width, 11), border_radius=4)
    pygame.draw.rect(
        screen,
        (170, 194, 148),
        (x, y + 19, int(width * value), 11),
        border_radius=4,
    )
    txt = font.render(f"{label}  {value:0.2f}", True, (225, 228, 235))
    screen.blit(txt, (x, y))


def _person_surface(
    scale: float, primary: bool = True, social: float = 0.0
) -> pygame.Surface:
    size = max(44, int(82 * scale))
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    s = scale
    skin = (222, 185, 154)
    shirt = (68, 115, 166) if primary else (150, 92, 121)
    pants = (48, 55, 68)
    outline = (31, 35, 42)

    head_r = max(5, int(8 * s))
    head_y = c - int(19 * s)
    pygame.draw.circle(surf, outline, (c, head_y), head_r + 2)
    pygame.draw.circle(surf, skin, (c, head_y), head_r)

    torso = pygame.Rect(
        c - int(9 * s), c - int(10 * s), int(18 * s), int(25 * s)
    )
    pygame.draw.rect(
        surf, outline, torso.inflate(3, 3), border_radius=max(2, int(5 * s))
    )
    pygame.draw.rect(surf, shirt, torso, border_radius=max(2, int(5 * s)))

    arm_open = int((13 + 8 * _clamp(social)) * s)
    arm_y = c - int(3 * s)
    pygame.draw.line(
        surf,
        skin,
        (c - int(7 * s), arm_y),
        (c - arm_open, arm_y - int(5 * social * s)),
        max(2, int(4 * s)),
    )
    pygame.draw.line(
        surf,
        skin,
        (c + int(7 * s), arm_y),
        (c + arm_open, arm_y - int(5 * social * s)),
        max(2, int(4 * s)),
    )

    hip_y = c + int(13 * s)
    leg_end = c + int(30 * s)
    pygame.draw.line(
        surf,
        pants,
        (c - int(4 * s), hip_y),
        (c - int(9 * s), leg_end),
        max(3, int(5 * s)),
    )
    pygame.draw.line(
        surf,
        pants,
        (c + int(4 * s), hip_y),
        (c + int(9 * s), leg_end),
        max(3, int(5 * s)),
    )
    return surf


def _draw_person(
    screen,
    x,
    y,
    heading,
    scale=0.75,
    primary=True,
    social=0.0,
):
    base = _person_surface(scale, primary=primary, social=social)
    rotated = pygame.transform.rotozoom(
        base, -math.degrees(heading) - 90.0, 1.0
    )
    rect = rotated.get_rect(center=(int(x), int(y)))
    screen.blit(rotated, rect)


def _draw_bread(screen, x: float, y: float) -> None:
    cx, cy = int(x), int(y)
    outer = pygame.Rect(cx - 11, cy - 8, 22, 16)
    inner = pygame.Rect(cx - 9, cy - 6, 18, 12)
    pygame.draw.rect(screen, (139, 91, 49), outer, border_radius=6)
    pygame.draw.rect(screen, (226, 177, 101), inner, border_radius=5)
    for dx in (-5, 1, 6):
        pygame.draw.line(
            screen,
            (245, 213, 151),
            (cx + dx - 2, cy - 4),
            (cx + dx, cy + 1),
            2,
        )


def _draw_arena(
    screen,
    world: CyberFlyWorld,
    outputs: BrainOutputs,
    font_small,
):
    pygame.draw.rect(screen, (23, 27, 31), (0, 0, ARENA_W, HEIGHT))
    pygame.draw.rect(
        screen,
        (70, 76, 80),
        (10, 10, ARENA_W - 20, HEIGHT - 20),
        2,
        border_radius=12,
    )

    for x, y in world.food:
        _draw_bread(screen, x, y)

    _draw_person(
        screen,
        world.mate[0],
        world.mate[1],
        world.mate_heading,
        scale=0.70,
        primary=False,
        social=0.0,
    )
    _draw_person(
        screen,
        world.state.x,
        world.state.y,
        world.state.heading,
        scale=0.82,
        primary=True,
        social=outputs.courtship,
    )

    if outputs.courtship > 0.28:
        text = font_small.render("social / pIP1", True, (220, 190, 200))
        screen.blit(
            text,
            (int(world.state.x) + 20, int(world.state.y) - 35),
        )


def run() -> int:
    _ensure_verified_malecns()
    pygame.init()
    pygame.display.set_caption("MaleCNS Human Avatar CyberPet v0.2")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Segoe UI", 19)
    font_small = pygame.font.SysFont("Segoe UI", 15)
    font_big = pygame.font.SysFont("Segoe UI", 25, bold=True)

    store = MemoryStore()
    snapshot = store.load_snapshot()
    world = CyberFlyWorld(
        width=ARENA_W,
        height=HEIGHT,
        snapshot=snapshot,
    )
    brain = MaleCNSBrain()
    learner = FastValenceLearner(q_table=world.state.policy_q)
    prior_learning_updates = world.state.learning_updates
    outputs = BrainOutputs(forward=0.1)
    bias = LearningBias()

    running = True
    shutdown_saved = False
    last_save = time.monotonic()
    brain_acc = 0.0
    last_event_text = "restored memory" if snapshot else "new life"
    event_display_until = time.monotonic() + 4.0
    courtship_cooldown = 0.0
    escape_cooldown = 0.0
    collision_log_cooldown = 0.0
    sleeping = False
    hunger_pain_active = False

    def sync_learning_state() -> None:
        world.state.policy_q = learner.export()
        world.state.learning_updates = prior_learning_updates + learner.updates

    def save(reason: str = "shutdown"):
        nonlocal shutdown_saved
        try:
            sync_learning_state()
            store.save_snapshot(world.state)
            if reason == "shutdown" and not shutdown_saved:
                store.append_episode(
                    "session_end",
                    0.15,
                    {
                        "age_seconds": round(world.state.age_seconds, 2),
                        "x": round(world.state.x, 2),
                        "y": round(world.state.y, 2),
                        "learning_updates": world.state.learning_updates,
                    },
                )
                shutdown_saved = True
        except Exception as exc:
            print(f"SAVE ERROR: {exc}")

    atexit.register(save)

    def stop_signal(signum, frame):
        nonlocal running
        running = False

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, stop_signal)
        except (ValueError, OSError):
            pass

    try:
        while running:
            dt = min(clock.tick(FPS) / 1000.0, 0.08)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif (
                    event.type == pygame.KEYDOWN
                    and event.key in (pygame.K_ESCAPE, pygame.K_q)
                ):
                    running = False

            courtship_cooldown = max(0.0, courtship_cooldown - dt)
            escape_cooldown = max(0.0, escape_cooldown - dt)
            collision_log_cooldown = max(0.0, collision_log_cooldown - dt)

            world.update_mate(dt)
            body_event = world.update_body(dt)
            if body_event == "ate":
                store.append_episode(
                    "ate_bread",
                    1.0,
                    {
                        "x": round(world.state.x, 2),
                        "y": round(world.state.y, 2),
                        "hunger_after": round(world.state.hunger, 3),
                        "dopamine": 1.0,
                    },
                )
                last_event_text = "ATE BREAD / dopamine +1.0"
                event_display_until = time.monotonic() + 4.0

            hunger_pain_level = _clamp(
                (world.state.hunger - 0.50) / 0.50
            )
            if hunger_pain_level > 0.25 and not hunger_pain_active:
                hunger_pain_active = True
                world.state.pain_events += 1
                store.append_episode(
                    "hunger_pain",
                    hunger_pain_level,
                    {
                        "hunger": round(world.state.hunger, 3),
                        "pain": round(hunger_pain_level, 3),
                    },
                )
                last_event_text = "PAIN / hunger"
                event_display_until = time.monotonic() + 3.0
            elif hunger_pain_level < 0.10:
                hunger_pain_active = False

            sensors = world.sense()
            dopamine_signal, pain_signal, _ = world.consume_learning_signal()
            learner.learn(
                dopamine_signal,
                pain_signal,
                sensors,
                world.state.hunger,
            )

            brain_acc += dt
            neural_dt = float(getattr(brain.brain, "dt", 0.02))
            steps = 0
            while brain_acc >= neural_dt and steps < 3:
                outputs = brain.step(
                    sensors,
                    hunger=world.state.hunger,
                    fatigue=world.state.fatigue,
                    social_drive=world.state.social_drive,
                )
                brain_acc -= neural_dt
                steps += 1

            if (
                world.state.fatigue > 0.88
                and world.state.hunger < 0.78
                and outputs.escape < 0.3
            ):
                if not sleeping:
                    store.append_episode(
                        "sleep",
                        0.35,
                        {"fatigue": round(world.state.fatigue, 3)},
                    )
                    last_event_text = "SLEEP"
                    event_display_until = time.monotonic() + 3.0
                sleeping = True
            elif sleeping and world.state.fatigue < 0.42:
                sleeping = False
                store.append_episode("wake", 0.25, {})
                last_event_text = "WAKE"
                event_display_until = time.monotonic() + 3.0

            if sleeping:
                learner.pause()
                bias = LearningBias()
                world.rest(dt)
            else:
                bias = learner.choose_bias(
                    sensors,
                    world.state.hunger,
                    dt,
                )
                memory_turn = (
                    sensors.memory_food_right - sensors.memory_food_left
                ) * 0.55
                applied_forward = _clamp(
                    outputs.forward + bias.forward
                )
                applied_turn = max(
                    -1.0,
                    min(
                        1.0,
                        outputs.turn + memory_turn + bias.turn,
                    ),
                )
                applied_backward = _clamp(
                    outputs.backward + bias.backward
                )
                applied_escape = _clamp(
                    outputs.escape + bias.escape
                )
                bounced = world.apply_motor(
                    dt,
                    applied_forward,
                    applied_turn,
                    applied_backward,
                    applied_escape,
                )
                if bounced and collision_log_cooldown <= 0.0:
                    collision_log_cooldown = 0.8
                    store.append_episode(
                        "boundary_pain",
                        1.0,
                        {
                            "x": round(world.state.x, 2),
                            "y": round(world.state.y, 2),
                            "pain": 1.0,
                            "learning_action": bias.action,
                        },
                    )
                    last_event_text = "PAIN / boundary collision"
                    event_display_until = time.monotonic() + 3.5

            mate_dist = math.hypot(
                world.mate[0] - world.state.x,
                world.mate[1] - world.state.y,
            )
            if (
                not sleeping
                and outputs.courtship > 0.22
                and mate_dist < 58
                and courtship_cooldown <= 0
            ):
                courtship_cooldown = 8.0
                world.state.courtship_events += 1
                world.state.social_drive = _clamp(
                    world.state.social_drive - 0.22
                )
                world.pulse_dopamine(
                    0.65,
                    "social_contact",
                    count_event=True,
                )
                store.append_episode(
                    "social_contact",
                    0.7,
                    {
                        "male_cns_pIP1_readout": round(
                            outputs.courtship, 3
                        ),
                        "distance": round(mate_dist, 2),
                        "dopamine": 0.65,
                    },
                )
                last_event_text = "SOCIAL CONTACT / dopamine +0.65"
                event_display_until = time.monotonic() + 4.0

            if outputs.escape > 0.55 and escape_cooldown <= 0:
                escape_cooldown = 5.0
                store.append_episode(
                    "escape",
                    0.8,
                    {
                        "dn_p01": round(outputs.escape, 3),
                        "x": round(world.state.x, 2),
                        "y": round(world.state.y, 2),
                    },
                )
                last_event_text = "ESCAPE / DNp01"
                event_display_until = time.monotonic() + 3.5

            if not sleeping:
                next_sensors = world.sense()
                dopamine_signal, pain_signal, _ = (
                    world.consume_learning_signal()
                )
                learner.learn(
                    dopamine_signal,
                    pain_signal,
                    next_sensors,
                    world.state.hunger,
                )
            else:
                world.consume_learning_signal()

            sync_learning_state()
            if time.monotonic() - last_save >= AUTOSAVE_SECONDS:
                save("autosave")
                last_save = time.monotonic()

            screen.fill((17, 19, 23))
            _draw_arena(
                screen,
                world,
                outputs,
                font_small,
            )
            panel_x = ARENA_W + 18
            title = font_big.render(
                "MaleCNS HumanPet",
                True,
                (235, 238, 242),
            )
            screen.blit(title, (panel_x, 22))
            subtitle = font_small.render(
                "human avatar / male-cns:v1.0",
                True,
                (150, 158, 167),
            )
            screen.blit(subtitle, (panel_x, 54))

            _bar(
                screen,
                font_small,
                panel_x,
                86,
                "HUNGER",
                world.state.hunger,
            )
            _bar(
                screen,
                font_small,
                panel_x,
                121,
                "FATIGUE",
                world.state.fatigue,
            )
            _bar(
                screen,
                font_small,
                panel_x,
                156,
                "SOCIAL",
                world.state.social_drive,
            )
            _bar(
                screen,
                font_small,
                panel_x,
                202,
                "DOPAMINE",
                world.state.dopamine,
            )
            _bar(
                screen,
                font_small,
                panel_x,
                237,
                "PAIN",
                world.state.pain,
            )
            _bar(
                screen,
                font_small,
                panel_x,
                292,
                "FORWARD / DNg100",
                outputs.forward,
            )
            turn_norm = (outputs.turn + 1.0) * 0.5
            _bar(
                screen,
                font_small,
                panel_x,
                327,
                "TURN / DNa02",
                turn_norm,
            )
            _bar(
                screen,
                font_small,
                panel_x,
                362,
                "ESCAPE / DNp01",
                outputs.escape,
            )
            _bar(
                screen,
                font_small,
                panel_x,
                397,
                "SOCIAL / pIP1",
                outputs.courtship,
            )

            facts = [
                f"spikes/tick: {outputs.spike_count}",
                f"age: {world.state.age_seconds / 60.0:0.1f} min",
                f"bread eaten: {world.state.food_eaten}",
                f"reward events: {world.state.reward_events}",
                f"pain events: {world.state.pain_events}",
                f"bread memories: {len(world.state.known_food_spots)}",
                f"RL states: {learner.known_states}",
                f"RL updates: {world.state.learning_updates}",
                f"learn bias: {bias.action}",
            ]
            yy = 451
            for line in facts:
                img = font_small.render(
                    line,
                    True,
                    (196, 202, 210),
                )
                screen.blit(img, (panel_x, yy))
                yy += 21

            status = "SLEEPING" if sleeping else "AWAKE"
            screen.blit(
                font.render(
                    status,
                    True,
                    (207, 214, 188),
                ),
                (panel_x, 650),
            )
            if time.monotonic() < event_display_until:
                evt = font_small.render(
                    last_event_text,
                    True,
                    (225, 198, 161),
                )
                screen.blit(evt, (panel_x, 684))
            hint = font_small.render(
                "Q / ESC: save + quit",
                True,
                (128, 136, 145),
            )
            screen.blit(hint, (panel_x, 721))
            pygame.display.flip()
    except KeyboardInterrupt:
        pass
    finally:
        save("shutdown")
        try:
            atexit.unregister(save)
        except Exception:
            pass
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
