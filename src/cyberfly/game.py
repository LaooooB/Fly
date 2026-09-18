from __future__ import annotations

import atexit
import math
import os
from pathlib import Path
import signal
import time

import pygame

from .brain_adapter import BrainOutputs, MaleCNSBrain
from .memory import MemoryStore, PetSnapshot
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
    pygame.draw.rect(screen, (45, 48, 55), (x, y + 21, width, 12), border_radius=4)
    pygame.draw.rect(screen, (170, 194, 148), (x, y + 21, int(width * value), 12), border_radius=4)
    txt = font.render(f"{label}  {value:0.2f}", True, (225, 228, 235))
    screen.blit(txt, (x, y))


def _insect_surface(scale: float, male: bool = True, courtship: float = 0.0) -> pygame.Surface:
    size = int(84 * scale)
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    s = scale
    body = (58, 54, 49) if male else (90, 79, 70)
    wing = (205, 220, 226, 115)
    leg = (65, 60, 55, 230)

    # legs
    for dy in (-10, 0, 10):
        pygame.draw.line(surf, leg, (c - 7*s, c + dy*s), (c - 25*s, c + (dy - 11)*s), max(1, int(2*s)))
        pygame.draw.line(surf, leg, (c + 7*s, c + dy*s), (c + 25*s, c + (dy + 11)*s), max(1, int(2*s)))
    # wings, exaggerated while courting
    wing_open = 8 + 10 * courtship
    pygame.draw.ellipse(surf, wing, (c - int(30*s), c - int((27+wing_open)*s), int(30*s), int(38*s)))
    pygame.draw.ellipse(surf, wing, (c, c - int((27+wing_open)*s), int(30*s), int(38*s)))
    # abdomen/thorax/head
    pygame.draw.ellipse(surf, body, (c - int(8*s), c - int(2*s), int(16*s), int(27*s)))
    pygame.draw.circle(surf, (73, 68, 61), (c, c - int(7*s)), int(9*s))
    pygame.draw.circle(surf, (75, 40, 36), (c - int(5*s), c - int(13*s)), max(2, int(4*s)))
    pygame.draw.circle(surf, (75, 40, 36), (c + int(5*s), c - int(13*s)), max(2, int(4*s)))
    return surf


def _draw_fly(screen, x, y, heading, scale=0.75, male=True, courtship=0.0):
    base = _insect_surface(scale, male=male, courtship=courtship)
    # source insect points upward; pygame/world heading 0 points right
    rotated = pygame.transform.rotozoom(base, -math.degrees(heading) - 90.0, 1.0)
    rect = rotated.get_rect(center=(int(x), int(y)))
    screen.blit(rotated, rect)


def _draw_arena(screen, world: CyberFlyWorld, outputs: BrainOutputs, font_small):
    pygame.draw.rect(screen, (23, 27, 31), (0, 0, ARENA_W, HEIGHT))
    pygame.draw.rect(screen, (70, 76, 80), (10, 10, ARENA_W - 20, HEIGHT - 20), 2, border_radius=12)

    for x, y in world.food:
        pygame.draw.circle(screen, (121, 157, 91), (int(x), int(y)), 8)
        pygame.draw.circle(screen, (190, 213, 130), (int(x), int(y)), 3)

    # passive mate target
    _draw_fly(screen, world.mate[0], world.mate[1], world.mate_heading,
              scale=0.63, male=False, courtship=0.0)
    _draw_fly(screen, world.state.x, world.state.y, world.state.heading,
              scale=0.82, male=True, courtship=outputs.courtship)

    if outputs.courtship > 0.28:
        text = font_small.render("courtship", True, (220, 190, 200))
        screen.blit(text, (int(world.state.x) + 20, int(world.state.y) - 35))


def run() -> int:
    _ensure_verified_malecns()
    pygame.init()
    pygame.display.set_caption("MaleCNS CyberPet v0.1")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Segoe UI", 19)
    font_small = pygame.font.SysFont("Segoe UI", 15)
    font_big = pygame.font.SysFont("Segoe UI", 26, bold=True)

    store = MemoryStore()
    snapshot = store.load_snapshot()
    world = CyberFlyWorld(width=ARENA_W, height=HEIGHT, snapshot=snapshot)
    brain = MaleCNSBrain()
    outputs = BrainOutputs(forward=0.1)

    running = True
    shutdown_saved = False
    last_save = time.monotonic()
    brain_acc = 0.0
    last_event_text = "restored memory" if snapshot else "new life"
    event_display_until = time.monotonic() + 4.0
    courtship_cooldown = 0.0
    escape_cooldown = 0.0
    sleeping = False

    def save(reason: str = "shutdown"):
        nonlocal shutdown_saved, last_event_text
        try:
            store.save_snapshot(world.state)
            if reason == "shutdown" and not shutdown_saved:
                store.append_episode("session_end", 0.15, {
                    "age_seconds": round(world.state.age_seconds, 2),
                    "x": round(world.state.x, 2),
                    "y": round(world.state.y, 2),
                })
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
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False

            world.update_mate(dt)
            body_event = world.update_body(dt)
            if body_event == "ate":
                store.append_episode("ate", 0.75, {
                    "x": round(world.state.x, 2), "y": round(world.state.y, 2),
                    "hunger_after": round(world.state.hunger, 3),
                })
                last_event_text = "ATE / food location remembered"
                event_display_until = time.monotonic() + 4.0

            sensors = world.sense()
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

            if world.state.fatigue > 0.88 and world.state.hunger < 0.78 and outputs.escape < 0.3:
                if not sleeping:
                    store.append_episode("sleep", 0.35, {"fatigue": round(world.state.fatigue, 3)})
                    last_event_text = "SLEEP"
                    event_display_until = time.monotonic() + 3.0
                sleeping = True
            elif sleeping and world.state.fatigue < 0.42:
                sleeping = False
                store.append_episode("wake", 0.25, {})
                last_event_text = "WAKE"
                event_display_until = time.monotonic() + 3.0

            if sleeping:
                world.rest(dt)
            else:
                # A remembered-food asymmetry is a weak cognitive bias layered on the MaleCNS readout.
                memory_turn = (sensors.memory_food_right - sensors.memory_food_left) * 0.55
                world.apply_motor(dt, outputs.forward, outputs.turn + memory_turn,
                                  outputs.backward, outputs.escape)

            courtship_cooldown = max(0.0, courtship_cooldown - dt)
            mate_dist = math.hypot(world.mate[0] - world.state.x, world.mate[1] - world.state.y)
            if outputs.courtship > 0.22 and mate_dist < 58 and courtship_cooldown <= 0:
                courtship_cooldown = 8.0
                world.state.courtship_events += 1
                world.state.social_drive = _clamp(world.state.social_drive - 0.22)
                store.append_episode("courtship", 0.7, {
                    "male_cns_pIP1_readout": round(outputs.courtship, 3),
                    "distance": round(mate_dist, 2),
                })
                last_event_text = "COURTSHIP / pIP1 activity"
                event_display_until = time.monotonic() + 4.0

            escape_cooldown = max(0.0, escape_cooldown - dt)
            if outputs.escape > 0.55 and escape_cooldown <= 0:
                escape_cooldown = 5.0
                store.append_episode("escape", 0.8, {
                    "dn_p01": round(outputs.escape, 3),
                    "x": round(world.state.x, 2), "y": round(world.state.y, 2),
                })
                last_event_text = "ESCAPE / DNp01"
                event_display_until = time.monotonic() + 3.5

            if time.monotonic() - last_save >= AUTOSAVE_SECONDS:
                save("autosave")
                last_save = time.monotonic()

            screen.fill((17, 19, 23))
            _draw_arena(screen, world, outputs, font_small)
            panel_x = ARENA_W + 22
            title = font_big.render("MaleCNS CyberPet", True, (235, 238, 242))
            screen.blit(title, (panel_x, 24))
            subtitle = font_small.render("full male-cns:v1.0 controller", True, (150, 158, 167))
            screen.blit(subtitle, (panel_x, 58))

            _bar(screen, font_small, panel_x, 96, "HUNGER", world.state.hunger)
            _bar(screen, font_small, panel_x, 142, "FATIGUE", world.state.fatigue)
            _bar(screen, font_small, panel_x, 188, "SOCIAL", world.state.social_drive)
            _bar(screen, font_small, panel_x, 254, "FORWARD / DNg100", outputs.forward)
            turn_norm = (outputs.turn + 1.0) * 0.5
            _bar(screen, font_small, panel_x, 300, "TURN / DNa02 L-R", turn_norm)
            _bar(screen, font_small, panel_x, 346, "ESCAPE / DNp01", outputs.escape)
            _bar(screen, font_small, panel_x, 392, "COURTSHIP / pIP1", outputs.courtship)

            facts = [
                f"spikes/tick: {outputs.spike_count}",
                f"age: {world.state.age_seconds/60.0:0.1f} min",
                f"food eaten: {world.state.food_eaten}",
                f"courtship events: {world.state.courtship_events}",
                f"food memories: {len(world.state.known_food_spots)}",
                f"save: {store.snapshot_path}",
            ]
            yy = 458
            for line in facts:
                img = font_small.render(line, True, (196, 202, 210))
                screen.blit(img, (panel_x, yy))
                yy += 24

            status = "SLEEPING" if sleeping else "AWAKE"
            screen.blit(font.render(status, True, (207, 214, 188)), (panel_x, 628))
            if time.monotonic() < event_display_until:
                evt = font_small.render(last_event_text, True, (225, 198, 161))
                screen.blit(evt, (panel_x, 664))
            hint = font_small.render("Q / ESC: save + quit", True, (128, 136, 145))
            screen.blit(hint, (panel_x, 716))
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
