from __future__ import annotations

import atexit
import math
import os
from pathlib import Path
import signal
import time

import pygame

from .brain_adapter import BrainOutputs, MaleCNSBrain
from .items import get_item, search_items
from .learning import FastValenceLearner, LearningBias
from .memory import MemoryStore
from .world import CyberFlyWorld


WIDTH, HEIGHT = 1180, 760
ARENA_W = 900
PANEL_W = WIDTH - ARENA_W
FPS = 60
AUTOSAVE_SECONDS = 30.0

PANEL_PAD = 18
PICKER_RECT = pygame.Rect(ARENA_W + PANEL_PAD, 440, PANEL_W - PANEL_PAD * 2, 42)
PLACE_RECT = pygame.Rect(ARENA_W + PANEL_PAD, 492, PANEL_W - PANEL_PAD * 2, 44)
DROPDOWN_TOP = 486
DROPDOWN_ROW_H = 42
DROPDOWN_MAX = 4

BG = (8, 11, 16)
ARENA_BG = (14, 19, 26)
PANEL_BG = (11, 15, 21)
CARD = (20, 26, 34)
CARD_HOVER = (28, 36, 46)
LINE = (43, 53, 65)
TEXT = (235, 239, 244)
MUTED = (143, 153, 165)
ACCENT = (95, 190, 160)
DANGER = (225, 98, 98)
WARM = (232, 174, 91)
BLUE = (104, 154, 214)
PURPLE = (169, 124, 215)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _marker_path() -> Path:
    root = Path(os.environ.get("FLY_DATA", r"J:\FLY\male_cns_data"))
    return root / "OFFICIAL_MALECNS_BUILD_OK.json"


def _ensure_verified_malecns() -> None:
    marker = _marker_path()
    if not marker.exists():
        raise RuntimeError(
            "未找到 MaleCNS 数据。请先运行 INSTALL_OFFICIAL_MALECNS.bat。\n"
            f"需要文件：{marker}"
        )


def _font(size: int, bold: bool = False) -> pygame.font.Font:
    for name in (
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    ):
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def _text(
    screen: pygame.Surface,
    font: pygame.font.Font,
    value: str,
    x: int,
    y: int,
    color=TEXT,
) -> pygame.Surface:
    img = font.render(value, True, color)
    screen.blit(img, (x, y))
    return img


def _meter(
    screen: pygame.Surface,
    font: pygame.font.Font,
    x: int,
    y: int,
    label: str,
    value: float,
    fill: tuple[int, int, int],
    width: int = 230,
) -> None:
    value = _clamp(value)
    _text(screen, font, label, x, y, TEXT)
    pct = font.render(f"{int(value * 100)}%", True, MUTED)
    screen.blit(pct, (x + width - pct.get_width(), y))
    track = pygame.Rect(x, y + 24, width, 7)
    pygame.draw.rect(screen, (34, 42, 52), track, border_radius=4)
    if value > 0:
        pygame.draw.rect(
            screen,
            fill,
            (track.x, track.y, max(4, int(track.w * value)), track.h),
            border_radius=4,
        )


def _person_surface(
    scale: float,
    primary: bool = True,
    social: float = 0.0,
) -> pygame.Surface:
    size = max(58, int(98 * scale))
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    s = scale

    skin = (225, 186, 151)
    hair = (42, 35, 31)
    shirt = (58, 128, 186) if primary else (145, 89, 126)
    shirt_light = (79, 151, 209) if primary else (173, 111, 151)
    pants = (42, 50, 64)
    shoe = (24, 29, 36)

    head_y = c - int(23 * s)
    head_r = max(6, int(10 * s))
    pygame.draw.circle(surf, hair, (c, head_y - int(2 * s)), head_r + 2)
    pygame.draw.circle(surf, skin, (c, head_y + int(2 * s)), head_r)
    pygame.draw.arc(
        surf,
        hair,
        pygame.Rect(c - head_r, head_y - head_r, head_r * 2, head_r * 2),
        math.pi,
        math.tau,
        max(2, int(4 * s)),
    )
    eye_y = head_y + int(2 * s)
    pygame.draw.circle(
        surf,
        (49, 45, 43),
        (c - int(4 * s), eye_y),
        max(1, int(1.5 * s)),
    )
    pygame.draw.circle(
        surf,
        (49, 45, 43),
        (c + int(4 * s), eye_y),
        max(1, int(1.5 * s)),
    )

    torso = pygame.Rect(
        c - int(11 * s),
        c - int(10 * s),
        int(22 * s),
        int(29 * s),
    )
    pygame.draw.rect(surf, shirt, torso, border_radius=max(3, int(7 * s)))
    pygame.draw.line(
        surf,
        shirt_light,
        (torso.x + int(4 * s), torso.y + int(5 * s)),
        (torso.x + int(4 * s), torso.bottom - int(6 * s)),
        max(1, int(2 * s)),
    )

    arm_open = int((15 + 9 * _clamp(social)) * s)
    arm_y = c - int(1 * s)
    pygame.draw.line(
        surf,
        skin,
        (c - int(8 * s), arm_y),
        (c - arm_open, arm_y - int(7 * social * s)),
        max(3, int(5 * s)),
    )
    pygame.draw.line(
        surf,
        skin,
        (c + int(8 * s), arm_y),
        (c + arm_open, arm_y - int(7 * social * s)),
        max(3, int(5 * s)),
    )

    hip_y = c + int(17 * s)
    leg_end = c + int(36 * s)
    pygame.draw.line(
        surf,
        pants,
        (c - int(5 * s), hip_y),
        (c - int(10 * s), leg_end),
        max(4, int(7 * s)),
    )
    pygame.draw.line(
        surf,
        pants,
        (c + int(5 * s), hip_y),
        (c + int(10 * s), leg_end),
        max(4, int(7 * s)),
    )
    pygame.draw.line(
        surf,
        shoe,
        (c - int(10 * s), leg_end),
        (c - int(15 * s), leg_end),
        max(3, int(5 * s)),
    )
    pygame.draw.line(
        surf,
        shoe,
        (c + int(10 * s), leg_end),
        (c + int(15 * s), leg_end),
        max(3, int(5 * s)),
    )
    return surf


def _draw_aura(
    screen: pygame.Surface,
    x: float,
    y: float,
    reward: float,
    pain: float,
) -> None:
    strength = max(reward, pain)
    if strength < 0.08:
        return
    color = (88, 208, 158) if reward >= pain else (230, 90, 90)
    radius = int(36 + 22 * _clamp(strength))
    glow = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
    center = glow.get_width() // 2
    for ring in range(3, 0, -1):
        rr = radius - ring * 6
        if rr > 0:
            pygame.draw.circle(
                glow,
                (*color, 16 + ring * 10),
                (center, center),
                rr,
                width=max(2, 5 - ring),
            )
    screen.blit(glow, glow.get_rect(center=(int(x), int(y))))


def _draw_person(
    screen: pygame.Surface,
    x: float,
    y: float,
    heading: float,
    scale: float = 0.75,
    primary: bool = True,
    social: float = 0.0,
    reward: float = 0.0,
    pain: float = 0.0,
) -> None:
    if primary:
        _draw_aura(screen, x, y, reward, pain)

    shadow = pygame.Surface((62, 22), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
    screen.blit(shadow, shadow.get_rect(center=(int(x), int(y) + 23)))

    base = _person_surface(scale, primary=primary, social=social)
    rotated = pygame.transform.rotozoom(
        base,
        -math.degrees(heading) - 90.0,
        1.0,
    )
    screen.blit(rotated, rotated.get_rect(center=(int(x), int(y))))


def _bread_surface(alpha: int = 255) -> pygame.Surface:
    surf = pygame.Surface((38, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (0, 0, 0, min(alpha, 75)), (7, 22, 25, 7))
    pygame.draw.rect(
        surf,
        (132, 79, 39, alpha),
        (5, 7, 28, 18),
        border_radius=8,
    )
    pygame.draw.rect(
        surf,
        (229, 177, 94, alpha),
        (7, 8, 24, 15),
        border_radius=7,
    )
    pygame.draw.rect(
        surf,
        (244, 204, 137, alpha),
        (9, 10, 20, 11),
        border_radius=6,
    )
    for x in (13, 19, 25):
        pygame.draw.line(
            surf,
            (202, 148, 76, alpha),
            (x - 2, 11),
            (x, 17),
            2,
        )
    return surf


def _draw_bread(
    screen: pygame.Surface,
    x: float,
    y: float,
    ghost: bool = False,
) -> None:
    surf = _bread_surface(145 if ghost else 255)
    screen.blit(surf, surf.get_rect(center=(int(x), int(y))))


def _draw_heart(screen: pygame.Surface, x: int, y: int) -> None:
    color = (224, 109, 137)
    pygame.draw.circle(screen, color, (x - 4, y - 2), 5)
    pygame.draw.circle(screen, color, (x + 4, y - 2), 5)
    pygame.draw.polygon(
        screen,
        color,
        [(x - 9, y), (x + 9, y), (x, y + 11)],
    )


def _draw_arena(
    screen: pygame.Surface,
    world: CyberFlyWorld,
    outputs: BrainOutputs,
    placing_item_id: str | None,
    mouse_pos: tuple[int, int],
    font_small: pygame.font.Font,
) -> None:
    pygame.draw.rect(screen, ARENA_BG, (0, 0, ARENA_W, HEIGHT))

    for gx in range(40, ARENA_W, 56):
        pygame.draw.line(
            screen,
            (20, 27, 35),
            (gx, 16),
            (gx, HEIGHT - 16),
            1,
        )
    for gy in range(40, HEIGHT, 56):
        pygame.draw.line(
            screen,
            (20, 27, 35),
            (16, gy),
            (ARENA_W - 16, gy),
            1,
        )

    border_color = DANGER if world.state.pain > 0.72 else LINE
    pygame.draw.rect(
        screen,
        border_color,
        (10, 10, ARENA_W - 20, HEIGHT - 20),
        2,
        border_radius=14,
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
    )
    _draw_person(
        screen,
        world.state.x,
        world.state.y,
        world.state.heading,
        scale=0.84,
        primary=True,
        social=outputs.courtship,
        reward=world.state.dopamine,
        pain=world.state.pain,
    )

    if outputs.courtship > 0.28:
        _draw_heart(
            screen,
            int(world.state.x) + 27,
            int(world.state.y) - 34,
        )

    if placing_item_id:
        mx, my = mouse_pos
        if 10 <= mx < ARENA_W - 10 and 10 <= my < HEIGHT - 10:
            pygame.draw.circle(screen, ACCENT, (mx, my), 24, 1)
            if placing_item_id == "bread":
                _draw_bread(screen, mx, my, ghost=True)

        item = get_item(placing_item_id)
        label = f"点击场地放置 {item.name if item else '物品'}"
        pill = pygame.Rect(20, 20, 196, 34)
        pygame.draw.rect(screen, (20, 31, 36), pill, border_radius=17)
        pygame.draw.rect(screen, ACCENT, pill, 1, border_radius=17)
        img = font_small.render(label, True, TEXT)
        screen.blit(
            img,
            (
                pill.x + 14,
                pill.centery - img.get_height() // 2,
            ),
        )


def _dropdown_rows(query: str) -> list[tuple[object, pygame.Rect]]:
    items = search_items(query)[:DROPDOWN_MAX]
    rows: list[tuple[object, pygame.Rect]] = []
    for index, item in enumerate(items):
        rows.append(
            (
                item,
                pygame.Rect(
                    PICKER_RECT.x,
                    DROPDOWN_TOP + index * DROPDOWN_ROW_H,
                    PICKER_RECT.w,
                    DROPDOWN_ROW_H,
                ),
            )
        )
    return rows


def _draw_panel(
    screen: pygame.Surface,
    world: CyberFlyWorld,
    sleeping: bool,
    selected_item_id: str,
    placing_item_id: str | None,
    dropdown_open: bool,
    search_active: bool,
    search_text: str,
    last_event_text: str,
    learner: FastValenceLearner,
    mouse_pos: tuple[int, int],
    font_small: pygame.font.Font,
    font: pygame.font.Font,
    font_big: pygame.font.Font,
) -> None:
    pygame.draw.rect(screen, PANEL_BG, (ARENA_W, 0, PANEL_W, HEIGHT))
    pygame.draw.line(screen, LINE, (ARENA_W, 0), (ARENA_W, HEIGHT), 1)

    x = ARENA_W + PANEL_PAD
    _text(screen, font_big, "赛博宠物", x, 24)

    status = "睡眠" if sleeping else "清醒"
    status_color = BLUE if sleeping else ACCENT
    chip = pygame.Rect(WIDTH - 78, 25, 58, 28)
    pygame.draw.rect(screen, CARD, chip, border_radius=14)
    pygame.draw.circle(
        screen,
        status_color,
        (chip.x + 12, chip.centery),
        4,
    )
    status_img = font_small.render(status, True, TEXT)
    screen.blit(
        status_img,
        (
            chip.x + 22,
            chip.centery - status_img.get_height() // 2,
        ),
    )

    state_card = pygame.Rect(x, 75, PANEL_W - PANEL_PAD * 2, 220)
    pygame.draw.rect(screen, CARD, state_card, border_radius=14)
    _text(
        screen,
        font_small,
        "状态",
        state_card.x + 14,
        state_card.y + 12,
        MUTED,
    )

    bx = state_card.x + 14
    bw = state_card.w - 28
    _meter(
        screen,
        font_small,
        bx,
        112,
        "饥饿",
        world.state.hunger,
        WARM,
        bw,
    )
    _meter(
        screen,
        font_small,
        bx,
        150,
        "疲劳",
        world.state.fatigue,
        BLUE,
        bw,
    )
    _meter(
        screen,
        font_small,
        bx,
        188,
        "社交",
        world.state.social_drive,
        PURPLE,
        bw,
    )
    _meter(
        screen,
        font_small,
        bx,
        226,
        "奖励",
        world.state.dopamine,
        ACCENT,
        bw,
    )
    _meter(
        screen,
        font_small,
        bx,
        264,
        "疼痛",
        world.state.pain,
        DANGER,
        bw,
    )

    stats_card = pygame.Rect(x, 309, PANEL_W - PANEL_PAD * 2, 92)
    pygame.draw.rect(screen, CARD, stats_card, border_radius=14)
    stats = (
        ("年龄", f"{world.state.age_seconds / 60.0:.1f} 分"),
        ("面包", str(world.state.food_eaten)),
        ("学习", str(world.state.learning_updates)),
    )
    col_w = stats_card.w // 3
    for i, (label, value) in enumerate(stats):
        cx = stats_card.x + i * col_w
        val = font.render(value, True, TEXT)
        lab = font_small.render(label, True, MUTED)
        screen.blit(
            val,
            (
                cx + (col_w - val.get_width()) // 2,
                stats_card.y + 18,
            ),
        )
        screen.blit(
            lab,
            (
                cx + (col_w - lab.get_width()) // 2,
                stats_card.y + 54,
            ),
        )
        if i:
            pygame.draw.line(
                screen,
                LINE,
                (cx, stats_card.y + 16),
                (cx, stats_card.bottom - 16),
                1,
            )

    _text(screen, font_small, "物品", x, 414, MUTED)

    picker_hover = PICKER_RECT.collidepoint(mouse_pos)
    picker_fill = CARD_HOVER if picker_hover or search_active else CARD
    pygame.draw.rect(
        screen,
        picker_fill,
        PICKER_RECT,
        border_radius=10,
    )
    pygame.draw.rect(
        screen,
        ACCENT if search_active else LINE,
        PICKER_RECT,
        1,
        border_radius=10,
    )

    selected = get_item(selected_item_id)
    if search_active:
        picker_text = search_text or "输入关键词"
        picker_color = TEXT if search_text else MUTED
    else:
        picker_text = selected.name if selected else "选择物品"
        picker_color = TEXT
    img = font.render(picker_text, True, picker_color)
    screen.blit(
        img,
        (
            PICKER_RECT.x + 14,
            PICKER_RECT.centery - img.get_height() // 2,
        ),
    )
    pygame.draw.polygon(
        screen,
        MUTED,
        [
            (PICKER_RECT.right - 23, PICKER_RECT.centery - 3),
            (PICKER_RECT.right - 13, PICKER_RECT.centery - 3),
            (PICKER_RECT.right - 18, PICKER_RECT.centery + 3),
        ],
    )

    if search_active and int(time.monotonic() * 2) % 2 == 0:
        caret_x = min(
            PICKER_RECT.right - 34,
            PICKER_RECT.x + 14 + img.get_width() + 2,
        )
        pygame.draw.line(
            screen,
            TEXT,
            (caret_x, PICKER_RECT.y + 11),
            (caret_x, PICKER_RECT.bottom - 11),
            1,
        )

    place_hover = PLACE_RECT.collidepoint(mouse_pos)
    if placing_item_id:
        button_fill = (96, 69, 70)
        button_text = "取消放置"
    else:
        button_fill = (
            (53, 128, 108)
            if place_hover
            else (45, 111, 94)
        )
        button_text = "放置"
    pygame.draw.rect(
        screen,
        button_fill,
        PLACE_RECT,
        border_radius=11,
    )
    button_img = font.render(button_text, True, TEXT)
    screen.blit(
        button_img,
        (
            PLACE_RECT.centerx - button_img.get_width() // 2,
            PLACE_RECT.centery - button_img.get_height() // 2,
        ),
    )

    event_card = pygame.Rect(x, 558, PANEL_W - PANEL_PAD * 2, 56)
    pygame.draw.rect(screen, CARD, event_card, border_radius=12)
    pygame.draw.circle(
        screen,
        ACCENT,
        (event_card.x + 16, event_card.centery),
        4,
    )
    event_img = font_small.render(last_event_text, True, TEXT)
    screen.blit(
        event_img,
        (
            event_card.x + 28,
            event_card.centery - event_img.get_height() // 2,
        ),
    )

    footer = "Q 退出"
    if placing_item_id or dropdown_open:
        footer += "  ·  Esc 取消"
    footer_img = font_small.render(footer, True, MUTED)
    screen.blit(footer_img, (x, HEIGHT - 34))

    core = font_small.render("MaleCNS", True, (96, 108, 122))
    screen.blit(
        core,
        (
            WIDTH - PANEL_PAD - core.get_width(),
            HEIGHT - 34,
        ),
    )

    if dropdown_open:
        rows = _dropdown_rows(search_text)
        if rows:
            box = pygame.Rect(
                PICKER_RECT.x,
                DROPDOWN_TOP,
                PICKER_RECT.w,
                len(rows) * DROPDOWN_ROW_H,
            )
            pygame.draw.rect(
                screen,
                (17, 23, 30),
                box,
                border_radius=10,
            )
            pygame.draw.rect(
                screen,
                LINE,
                box,
                1,
                border_radius=10,
            )
            for item, rect in rows:
                if rect.collidepoint(mouse_pos):
                    pygame.draw.rect(
                        screen,
                        CARD_HOVER,
                        rect.inflate(-2, -2),
                        border_radius=8,
                    )
                _text(
                    screen,
                    font,
                    item.name,
                    rect.x + 14,
                    rect.y + 10,
                )
                category = font_small.render(
                    item.category,
                    True,
                    MUTED,
                )
                screen.blit(
                    category,
                    (
                        rect.right - category.get_width() - 14,
                        rect.centery - category.get_height() // 2,
                    ),
                )
        else:
            empty = pygame.Rect(
                PICKER_RECT.x,
                DROPDOWN_TOP,
                PICKER_RECT.w,
                DROPDOWN_ROW_H,
            )
            pygame.draw.rect(
                screen,
                (17, 23, 30),
                empty,
                border_radius=10,
            )
            pygame.draw.rect(
                screen,
                LINE,
                empty,
                1,
                border_radius=10,
            )
            msg = font_small.render(
                "没有匹配物品",
                True,
                MUTED,
            )
            screen.blit(
                msg,
                (
                    empty.x + 14,
                    empty.centery - msg.get_height() // 2,
                ),
            )


def run() -> int:
    _ensure_verified_malecns()
    pygame.init()
    pygame.display.set_caption("赛博宠物")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font_small = _font(14)
    font = _font(18)
    font_big = _font(26, bold=True)

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

    selected_item_id = "bread"
    placing_item_id: str | None = None
    dropdown_open = False
    search_active = False
    search_text = ""

    running = True
    shutdown_saved = False
    last_save = time.monotonic()
    brain_acc = 0.0
    last_event_text = "已读取存档" if snapshot else "新生命"
    courtship_cooldown = 0.0
    escape_cooldown = 0.0
    collision_log_cooldown = 0.0
    sleeping = False
    hunger_pain_active = False

    def sync_learning_state() -> None:
        world.state.policy_q = learner.export()
        world.state.learning_updates = (
            prior_learning_updates + learner.updates
        )

    def close_search() -> None:
        nonlocal search_active, dropdown_open
        search_active = False
        dropdown_open = False
        pygame.key.stop_text_input()

    def choose_first_search_result() -> bool:
        nonlocal selected_item_id, search_text
        results = search_items(search_text)
        if not results:
            return False
        selected_item_id = results[0].item_id
        search_text = ""
        close_search()
        return True

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
                        "age_seconds": round(
                            world.state.age_seconds,
                            2,
                        ),
                        "x": round(world.state.x, 2),
                        "y": round(world.state.y, 2),
                        "learning_updates": world.state.learning_updates,
                    },
                )
                shutdown_saved = True
        except Exception as exc:
            print(f"存档失败：{exc}")

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
                    continue

                if (
                    event.type == pygame.TEXTINPUT
                    and search_active
                ):
                    search_text += event.text
                    dropdown_open = True
                    continue

                if event.type == pygame.KEYDOWN:
                    if search_active:
                        if event.key == pygame.K_BACKSPACE:
                            search_text = search_text[:-1]
                        elif event.key == pygame.K_RETURN:
                            choose_first_search_result()
                        elif event.key == pygame.K_ESCAPE:
                            search_text = ""
                            close_search()
                        continue

                    if event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_ESCAPE:
                        if placing_item_id:
                            placing_item_id = None
                            last_event_text = "已取消放置"
                        elif dropdown_open:
                            close_search()
                        else:
                            running = False
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos

                    if event.button == 3 and placing_item_id:
                        placing_item_id = None
                        last_event_text = "已取消放置"
                        continue

                    if event.button != 1:
                        continue

                    if PICKER_RECT.collidepoint(event.pos):
                        placing_item_id = None
                        search_text = ""
                        search_active = True
                        dropdown_open = True
                        pygame.key.start_text_input()
                        continue

                    if dropdown_open:
                        picked = None
                        for item, rect in _dropdown_rows(
                            search_text
                        ):
                            if rect.collidepoint(event.pos):
                                picked = item
                                break
                        if picked:
                            selected_item_id = picked.item_id
                            search_text = ""
                            close_search()
                        else:
                            close_search()
                        continue

                    if PLACE_RECT.collidepoint(event.pos):
                        if placing_item_id:
                            placing_item_id = None
                            last_event_text = "已取消放置"
                        else:
                            placing_item_id = selected_item_id
                            item = get_item(selected_item_id)
                            last_event_text = (
                                f"选择{item.name if item else '物品'}位置"
                            )
                        continue

                    if placing_item_id and mx < ARENA_W:
                        item = get_item(placing_item_id)
                        if placing_item_id == "bread":
                            px, py = world.place_food(mx, my)
                            store.append_episode(
                                "place_item",
                                0.1,
                                {
                                    "item": "bread",
                                    "x": round(px, 2),
                                    "y": round(py, 2),
                                },
                            )
                            last_event_text = "已放置面包"
                        elif item:
                            last_event_text = (
                                f"暂不支持放置{item.name}"
                            )
                        placing_item_id = None
                        continue

                    close_search()

            courtship_cooldown = max(
                0.0,
                courtship_cooldown - dt,
            )
            escape_cooldown = max(
                0.0,
                escape_cooldown - dt,
            )
            collision_log_cooldown = max(
                0.0,
                collision_log_cooldown - dt,
            )

            world.update_mate(dt)
            body_event = world.update_body(dt)
            if body_event == "ate":
                store.append_episode(
                    "ate_bread",
                    1.0,
                    {
                        "x": round(world.state.x, 2),
                        "y": round(world.state.y, 2),
                        "hunger_after": round(
                            world.state.hunger,
                            3,
                        ),
                        "dopamine": 1.0,
                    },
                )
                last_event_text = "吃到面包"

            hunger_pain_level = _clamp(
                (world.state.hunger - 0.50) / 0.50
            )
            if (
                hunger_pain_level > 0.25
                and not hunger_pain_active
            ):
                hunger_pain_active = True
                world.state.pain_events += 1
                store.append_episode(
                    "hunger_pain",
                    hunger_pain_level,
                    {
                        "hunger": round(
                            world.state.hunger,
                            3,
                        ),
                        "pain": round(
                            hunger_pain_level,
                            3,
                        ),
                    },
                )
                last_event_text = "饥饿"
            elif hunger_pain_level < 0.10:
                hunger_pain_active = False

            sensors = world.sense()
            dopamine_signal, pain_signal, _ = (
                world.consume_learning_signal()
            )
            learner.learn(
                dopamine_signal,
                pain_signal,
                sensors,
                world.state.hunger,
            )

            brain_acc += dt
            neural_dt = float(
                getattr(brain.brain, "dt", 0.02)
            )
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
                        {
                            "fatigue": round(
                                world.state.fatigue,
                                3,
                            )
                        },
                    )
                    last_event_text = "睡眠"
                sleeping = True
            elif (
                sleeping
                and world.state.fatigue < 0.42
            ):
                sleeping = False
                store.append_episode("wake", 0.25, {})
                last_event_text = "醒来"

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
                    sensors.memory_food_right
                    - sensors.memory_food_left
                ) * 0.55
                applied_forward = _clamp(
                    outputs.forward + bias.forward
                )
                applied_turn = max(
                    -1.0,
                    min(
                        1.0,
                        outputs.turn
                        + memory_turn
                        + bias.turn,
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
                if (
                    bounced
                    and collision_log_cooldown <= 0.0
                ):
                    collision_log_cooldown = 0.8
                    store.append_episode(
                        "boundary_pain",
                        1.0,
                        {
                            "x": round(
                                world.state.x,
                                2,
                            ),
                            "y": round(
                                world.state.y,
                                2,
                            ),
                            "pain": 1.0,
                            "learning_action": bias.action,
                        },
                    )
                    last_event_text = "撞到边界"

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
                            outputs.courtship,
                            3,
                        ),
                        "distance": round(
                            mate_dist,
                            2,
                        ),
                        "dopamine": 0.65,
                    },
                )
                last_event_text = "社交奖励"

            if (
                outputs.escape > 0.55
                and escape_cooldown <= 0
            ):
                escape_cooldown = 5.0
                store.append_episode(
                    "escape",
                    0.8,
                    {
                        "dn_p01": round(
                            outputs.escape,
                            3,
                        ),
                        "x": round(
                            world.state.x,
                            2,
                        ),
                        "y": round(
                            world.state.y,
                            2,
                        ),
                    },
                )
                last_event_text = "逃逸"

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
            if (
                time.monotonic() - last_save
                >= AUTOSAVE_SECONDS
            ):
                save("autosave")
                last_save = time.monotonic()

            screen.fill(BG)
            mouse_pos = pygame.mouse.get_pos()
            _draw_arena(
                screen,
                world,
                outputs,
                placing_item_id,
                mouse_pos,
                font_small,
            )
            _draw_panel(
                screen,
                world,
                sleeping,
                selected_item_id,
                placing_item_id,
                dropdown_open,
                search_active,
                search_text,
                last_event_text,
                learner,
                mouse_pos,
                font_small,
                font,
                font_big,
            )
            pygame.display.flip()
    except KeyboardInterrupt:
        pass
    finally:
        save("shutdown")
        try:
            atexit.unregister(save)
        except Exception:
            pass
        pygame.key.stop_text_input()
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
