from __future__ import annotations

import atexit
from collections import deque
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
from .world import CyberFlyWorld, PersonView


WIDTH, HEIGHT = 1180, 760
ARENA_W = 900
PANEL_W = WIDTH - ARENA_W
FPS = 60
AUTOSAVE_SECONDS = 30.0

PANEL_PAD = 18
PICKER_RECT = pygame.Rect(
    ARENA_W + PANEL_PAD,
    530,
    PANEL_W - PANEL_PAD * 2,
    42,
)
PLACE_RECT = pygame.Rect(
    ARENA_W + PANEL_PAD,
    582,
    PANEL_W - PANEL_PAD * 2,
    44,
)
DROPDOWN_TOP = 576
DROPDOWN_ROW_H = 42
DROPDOWN_MAX = 3

BG = (14, 20, 16)
GRASS = (54, 112, 58)
GRASS_DARK = (45, 98, 50)
GRASS_LIGHT = (69, 128, 70)
PANEL_BG = (11, 16, 14)
CARD = (20, 29, 25)
CARD_HOVER = (29, 40, 35)
LINE = (48, 64, 55)
TEXT = (237, 242, 238)
MUTED = (149, 162, 153)
ACCENT = (102, 211, 151)
SELECTED = (255, 222, 101)
HOVER = (242, 249, 228)
DANGER = (231, 101, 101)
WARM = (235, 180, 86)
BLUE = (104, 161, 221)
PURPLE = (177, 126, 220)


def _clamp(
    v: float,
    lo: float = 0.0,
    hi: float = 1.0,
) -> float:
    return max(lo, min(hi, v))


def _marker_path() -> Path:
    root = Path(
        os.environ.get(
            "FLY_DATA",
            r"J:\FLY\male_cns_data",
        )
    )
    return root / "OFFICIAL_MALECNS_BUILD_OK.json"


def _ensure_verified_malecns() -> None:
    marker = _marker_path()
    if not marker.exists():
        raise RuntimeError(
            "未找到 MaleCNS 数据。请先运行 "
            "INSTALL_OFFICIAL_MALECNS.bat。\n"
            f"需要文件：{marker}"
        )


def _font(
    size: int,
    bold: bool = False,
) -> pygame.font.Font:
    for name in (
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    ):
        path = pygame.font.match_font(
            name,
            bold=bold,
        )
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
    width: int,
) -> None:
    value = _clamp(value)
    _text(
        screen,
        font,
        label,
        x,
        y,
        TEXT,
    )
    pct = font.render(
        f"{int(value * 100)}%",
        True,
        MUTED,
    )
    screen.blit(
        pct,
        (
            x + width - pct.get_width(),
            y,
        ),
    )
    track = pygame.Rect(
        x,
        y + 22,
        width,
        7,
    )
    pygame.draw.rect(
        screen,
        (35, 46, 40),
        track,
        border_radius=4,
    )
    if value > 0:
        pygame.draw.rect(
            screen,
            fill,
            (
                track.x,
                track.y,
                max(4, int(track.w * value)),
                track.h,
            ),
            border_radius=4,
        )


def _person_hit_rect(
    view: PersonView,
) -> pygame.Rect:
    return pygame.Rect(
        int(view.x) - 38,
        int(view.y) - 58,
        76,
        116,
    )


def _person_at(
    world: CyberFlyWorld,
    point: tuple[int, int],
) -> str | None:
    candidates: list[
        tuple[float, str]
    ] = []
    for person_id in ("male", "female"):
        view = world.person_view(person_id)
        if _person_hit_rect(view).collidepoint(point):
            distance = math.hypot(
                point[0] - view.x,
                point[1] - view.y,
            )
            candidates.append(
                (distance, person_id)
            )
    if not candidates:
        return None
    candidates.sort(key=lambda row: row[0])
    return candidates[0][1]


def _outline_blit(
    screen: pygame.Surface,
    base: pygame.Surface,
    center: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int,
) -> None:
    mask = pygame.mask.from_surface(base)
    silhouette = mask.to_surface(
        setcolor=(*color, 255),
        unsetcolor=(0, 0, 0, 0),
    )
    rect = base.get_rect(center=center)
    offsets = (
        (-thickness, 0),
        (thickness, 0),
        (0, -thickness),
        (0, thickness),
        (-thickness, -thickness),
        (thickness, -thickness),
        (-thickness, thickness),
        (thickness, thickness),
    )
    for ox, oy in offsets:
        screen.blit(
            silhouette,
            rect.move(ox, oy),
        )


def _person_surface(
    gender: str,
    walk_phase: float,
    moving: bool,
    social: float = 0.0,
) -> pygame.Surface:
    surf = pygame.Surface(
        (92, 126),
        pygame.SRCALPHA,
    )
    c = 46

    skin = (225, 184, 148)
    skin_shadow = (197, 151, 119)
    hair = (
        (48, 38, 31)
        if gender == "male"
        else (52, 38, 34)
    )
    top = (
        (55, 118, 181)
        if gender == "male"
        else (176, 91, 119)
    )
    top_light = (
        (80, 148, 207)
        if gender == "male"
        else (207, 121, 149)
    )
    bottom = (
        (40, 50, 65)
        if gender == "male"
        else (63, 53, 68)
    )
    shoe = (28, 31, 35)

    swing = (
        math.sin(walk_phase) * 10.0
        if moving
        else 0.0
    )
    bob = (
        abs(math.sin(walk_phase)) * 2.0
        if moving
        else 0.0
    )
    yoff = int(bob)

    head_center = (
        c,
        27 - yoff,
    )
    pygame.draw.circle(
        surf,
        hair,
        (
            head_center[0],
            head_center[1] - 3,
        ),
        13,
    )

    if gender == "female":
        pygame.draw.ellipse(
            surf,
            hair,
            (
                c - 14,
                19 - yoff,
                28,
                33,
            ),
        )
        pygame.draw.circle(
            surf,
            hair,
            (
                c + 13,
                31 - yoff,
            ),
            7,
        )

    pygame.draw.circle(
        surf,
        skin,
        (
            head_center[0],
            head_center[1] + 2,
        ),
        11,
    )

    pygame.draw.circle(
        surf,
        (48, 43, 40),
        (
            c - 4,
            30 - yoff,
        ),
        1,
    )
    pygame.draw.circle(
        surf,
        (48, 43, 40),
        (
            c + 4,
            30 - yoff,
        ),
        1,
    )
    pygame.draw.line(
        surf,
        skin_shadow,
        (
            c - 3,
            36 - yoff,
        ),
        (
            c + 3,
            36 - yoff,
        ),
        1,
    )

    shoulder_y = 48 - yoff
    hip_y = 77 - yoff

    torso_width = (
        25
        if gender == "male"
        else 21
    )
    torso = pygame.Rect(
        c - torso_width // 2,
        shoulder_y,
        torso_width,
        31,
    )
    pygame.draw.rect(
        surf,
        top,
        torso,
        border_radius=8,
    )
    pygame.draw.line(
        surf,
        top_light,
        (
            torso.x + 5,
            torso.y + 5,
        ),
        (
            torso.x + 5,
            torso.bottom - 5,
        ),
        2,
    )

    social_open = int(
        8 * _clamp(social)
    )
    arm_swing = int(
        swing * 0.70
    )
    left_hand = (
        c - 22 - social_open,
        70 - yoff - arm_swing,
    )
    right_hand = (
        c + 22 + social_open,
        70 - yoff + arm_swing,
    )

    pygame.draw.line(
        surf,
        skin,
        (
            c - torso_width // 2 + 2,
            shoulder_y + 7,
        ),
        left_hand,
        6,
    )
    pygame.draw.line(
        surf,
        skin,
        (
            c + torso_width // 2 - 2,
            shoulder_y + 7,
        ),
        right_hand,
        6,
    )

    leg_swing = int(swing)
    left_knee = (
        c - 8 - leg_swing // 3,
        96 - yoff,
    )
    right_knee = (
        c + 8 + leg_swing // 3,
        96 - yoff,
    )
    left_foot = (
        c - 11 - leg_swing,
        118 - yoff,
    )
    right_foot = (
        c + 11 + leg_swing,
        118 - yoff,
    )

    pygame.draw.line(
        surf,
        bottom,
        (
            c - 6,
            hip_y,
        ),
        left_knee,
        8,
    )
    pygame.draw.line(
        surf,
        bottom,
        left_knee,
        left_foot,
        7,
    )
    pygame.draw.line(
        surf,
        bottom,
        (
            c + 6,
            hip_y,
        ),
        right_knee,
        8,
    )
    pygame.draw.line(
        surf,
        bottom,
        right_knee,
        right_foot,
        7,
    )

    pygame.draw.line(
        surf,
        shoe,
        left_foot,
        (
            left_foot[0] - 7,
            left_foot[1],
        ),
        5,
    )
    pygame.draw.line(
        surf,
        shoe,
        right_foot,
        (
            right_foot[0] + 7,
            right_foot[1],
        ),
        5,
    )

    return surf


def _draw_person(
    screen: pygame.Surface,
    view: PersonView,
    gender: str,
    walk_phase: float,
    speed: float,
    selected: bool,
    hovered: bool,
    social: float = 0.0,
) -> None:
    moving = speed > 4.0
    base = _person_surface(
        gender,
        walk_phase,
        moving,
        social=social,
    )

    facing_left = (
        math.cos(view.heading) < 0.0
    )
    if facing_left:
        base = pygame.transform.flip(
            base,
            True,
            False,
        )

    shadow_w = 46 if moving else 42
    shadow = pygame.Surface(
        (shadow_w, 14),
        pygame.SRCALPHA,
    )
    pygame.draw.ellipse(
        shadow,
        (0, 0, 0, 68),
        shadow.get_rect(),
    )
    screen.blit(
        shadow,
        shadow.get_rect(
            center=(
                int(view.x),
                int(view.y) + 45,
            )
        ),
    )

    center = (
        int(view.x),
        int(view.y),
    )
    if hovered:
        _outline_blit(
            screen,
            base,
            center,
            HOVER,
            5,
        )
    if selected:
        _outline_blit(
            screen,
            base,
            center,
            SELECTED,
            3,
        )

    screen.blit(
        base,
        base.get_rect(center=center),
    )


def _bread_surface(
    alpha: int = 255,
) -> pygame.Surface:
    surf = pygame.Surface(
        (38, 32),
        pygame.SRCALPHA,
    )
    pygame.draw.ellipse(
        surf,
        (0, 0, 0, min(alpha, 75)),
        (7, 22, 25, 7),
    )
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
    surf = _bread_surface(
        145 if ghost else 255
    )
    screen.blit(
        surf,
        surf.get_rect(
            center=(int(x), int(y))
        ),
    )


def _draw_heart(
    screen: pygame.Surface,
    x: int,
    y: int,
) -> None:
    color = (226, 109, 137)
    pygame.draw.circle(
        screen,
        color,
        (x - 4, y - 2),
        5,
    )
    pygame.draw.circle(
        screen,
        color,
        (x + 4, y - 2),
        5,
    )
    pygame.draw.polygon(
        screen,
        color,
        [
            (x - 9, y),
            (x + 9, y),
            (x, y + 11),
        ],
    )


def _draw_grass(
    screen: pygame.Surface,
) -> None:
    pygame.draw.rect(
        screen,
        GRASS,
        (0, 0, ARENA_W, HEIGHT),
    )

    for gx in range(24, ARENA_W, 64):
        pygame.draw.line(
            screen,
            GRASS_DARK,
            (gx, 12),
            (gx, HEIGHT - 12),
            1,
        )
    for gy in range(28, HEIGHT, 64):
        pygame.draw.line(
            screen,
            GRASS_DARK,
            (12, gy),
            (ARENA_W - 12, gy),
            1,
        )

    for y in range(36, HEIGHT, 96):
        shift = 34 if (y // 96) % 2 else 0
        for x in range(
            40 + shift,
            ARENA_W,
            96,
        ):
            pygame.draw.line(
                screen,
                GRASS_LIGHT,
                (x, y + 3),
                (x - 3, y - 2),
                1,
            )
            pygame.draw.line(
                screen,
                GRASS_LIGHT,
                (x, y + 3),
                (x + 3, y - 3),
                1,
            )


def _draw_arena(
    screen: pygame.Surface,
    world: CyberFlyWorld,
    outputs: BrainOutputs,
    selected_person: str,
    hovered_person: str | None,
    placing_item_id: str | None,
    mouse_pos: tuple[int, int],
    font_small: pygame.font.Font,
) -> None:
    _draw_grass(screen)

    border_color = (
        DANGER
        if world.state.pain > 0.72
        else (37, 78, 42)
    )
    pygame.draw.rect(
        screen,
        border_color,
        (10, 10, ARENA_W - 20, HEIGHT - 20),
        3,
        border_radius=16,
    )

    for x, y in world.food:
        _draw_bread(
            screen,
            x,
            y,
        )

    male = world.person_view("male")
    female = world.person_view("female")

    _draw_person(
        screen,
        female,
        "female",
        world.female_walk_phase,
        world.female_speed,
        selected_person == "female",
        hovered_person == "female",
    )
    _draw_person(
        screen,
        male,
        "male",
        world.male_walk_phase,
        world.male_speed,
        selected_person == "male",
        hovered_person == "male",
        social=outputs.courtship,
    )

    if outputs.courtship > 0.28:
        _draw_heart(
            screen,
            int(male.x) + 28,
            int(male.y) - 46,
        )

    if placing_item_id:
        mx, my = mouse_pos
        if (
            10 <= mx < ARENA_W - 10
            and 10 <= my < HEIGHT - 10
        ):
            pygame.draw.circle(
                screen,
                HOVER,
                (mx, my),
                24,
                2,
            )
            if placing_item_id == "bread":
                _draw_bread(
                    screen,
                    mx,
                    my,
                    ghost=True,
                )

        item = get_item(placing_item_id)
        label = (
            f"点击地面放置 "
            f"{item.name if item else '物品'}"
        )
        pill = pygame.Rect(
            20,
            20,
            190,
            34,
        )
        pygame.draw.rect(
            screen,
            (37, 80, 45),
            pill,
            border_radius=17,
        )
        pygame.draw.rect(
            screen,
            HOVER,
            pill,
            1,
            border_radius=17,
        )
        img = font_small.render(
            label,
            True,
            TEXT,
        )
        screen.blit(
            img,
            (
                pill.x + 14,
                pill.centery
                - img.get_height() // 2,
            ),
        )


def _dropdown_rows(
    query: str,
) -> list[tuple[object, pygame.Rect]]:
    items = search_items(query)[
        :DROPDOWN_MAX
    ]
    rows: list[
        tuple[object, pygame.Rect]
    ] = []
    for index, item in enumerate(items):
        rows.append(
            (
                item,
                pygame.Rect(
                    PICKER_RECT.x,
                    DROPDOWN_TOP
                    + index * DROPDOWN_ROW_H,
                    PICKER_RECT.w,
                    DROPDOWN_ROW_H,
                ),
            )
        )
    return rows


def _learning_values(
    selected_person: str,
    total: int,
    session: int,
    recent: int,
) -> tuple[str, str, str]:
    if selected_person == "male":
        return (
            str(total),
            str(session),
            str(recent),
        )
    return ("—", "—", "—")


def _draw_three_stats(
    screen: pygame.Surface,
    rect: pygame.Rect,
    stats: tuple[
        tuple[str, str],
        tuple[str, str],
        tuple[str, str],
    ],
    font_small: pygame.font.Font,
    font: pygame.font.Font,
) -> None:
    col_w = rect.w // 3
    for i, (label, value) in enumerate(stats):
        cx = rect.x + i * col_w
        val = font.render(
            value,
            True,
            TEXT,
        )
        lab = font_small.render(
            label,
            True,
            MUTED,
        )
        screen.blit(
            val,
            (
                cx
                + (col_w - val.get_width())
                // 2,
                rect.y + 12,
            ),
        )
        screen.blit(
            lab,
            (
                cx
                + (col_w - lab.get_width())
                // 2,
                rect.y + 42,
            ),
        )
        if i:
            pygame.draw.line(
                screen,
                LINE,
                (
                    cx,
                    rect.y + 12,
                ),
                (
                    cx,
                    rect.bottom - 12,
                ),
                1,
            )


def _draw_panel(
    screen: pygame.Surface,
    world: CyberFlyWorld,
    selected_person: str,
    male_sleeping: bool,
    total_learning: int,
    session_learning: int,
    recent_learning: int,
    selected_item_id: str,
    placing_item_id: str | None,
    dropdown_open: bool,
    search_active: bool,
    search_text: str,
    last_event_text: str,
    mouse_pos: tuple[int, int],
    font_small: pygame.font.Font,
    font: pygame.font.Font,
    font_big: pygame.font.Font,
) -> None:
    pygame.draw.rect(
        screen,
        PANEL_BG,
        (ARENA_W, 0, PANEL_W, HEIGHT),
    )
    pygame.draw.line(
        screen,
        LINE,
        (ARENA_W, 0),
        (ARENA_W, HEIGHT),
        1,
    )

    view = world.person_view(
        selected_person
    )
    x = ARENA_W + PANEL_PAD

    title = (
        "男性"
        if selected_person == "male"
        else "女性"
    )
    _text(
        screen,
        font_big,
        title,
        x,
        22,
    )

    if selected_person == "male":
        status = (
            "睡眠"
            if male_sleeping
            else "清醒"
        )
    else:
        status = (
            "疲惫"
            if view.fatigue > 0.86
            else "清醒"
        )

    chip = pygame.Rect(
        WIDTH - 78,
        23,
        58,
        28,
    )
    pygame.draw.rect(
        screen,
        CARD,
        chip,
        border_radius=14,
    )
    pygame.draw.circle(
        screen,
        BLUE if status == "睡眠" else ACCENT,
        (
            chip.x + 12,
            chip.centery,
        ),
        4,
    )
    status_img = font_small.render(
        status,
        True,
        TEXT,
    )
    screen.blit(
        status_img,
        (
            chip.x + 22,
            chip.centery
            - status_img.get_height() // 2,
        ),
    )

    state_card = pygame.Rect(
        x,
        68,
        PANEL_W - PANEL_PAD * 2,
        214,
    )
    pygame.draw.rect(
        screen,
        CARD,
        state_card,
        border_radius=14,
    )
    _text(
        screen,
        font_small,
        "状态",
        state_card.x + 14,
        state_card.y + 10,
        MUTED,
    )

    bx = state_card.x + 14
    bw = state_card.w - 28
    _meter(
        screen,
        font_small,
        bx,
        101,
        "饥饿",
        view.hunger,
        WARM,
        bw,
    )
    _meter(
        screen,
        font_small,
        bx,
        137,
        "疲劳",
        view.fatigue,
        BLUE,
        bw,
    )
    _meter(
        screen,
        font_small,
        bx,
        173,
        "社交",
        view.social_drive,
        PURPLE,
        bw,
    )
    _meter(
        screen,
        font_small,
        bx,
        209,
        "奖励",
        view.dopamine,
        ACCENT,
        bw,
    )
    _meter(
        screen,
        font_small,
        bx,
        245,
        "疼痛",
        view.pain,
        DANGER,
        bw,
    )

    stats_card = pygame.Rect(
        x,
        296,
        PANEL_W - PANEL_PAD * 2,
        68,
    )
    pygame.draw.rect(
        screen,
        CARD,
        stats_card,
        border_radius=13,
    )
    _draw_three_stats(
        screen,
        stats_card,
        (
            (
                "年龄",
                f"{view.age_seconds / 60.0:.1f}分",
            ),
            (
                "面包",
                str(view.food_eaten),
            ),
            (
                "位置",
                f"{int(view.x)},{int(view.y)}",
            ),
        ),
        font_small,
        font,
    )

    learning_card = pygame.Rect(
        x,
        378,
        PANEL_W - PANEL_PAD * 2,
        96,
    )
    pygame.draw.rect(
        screen,
        CARD,
        learning_card,
        border_radius=13,
    )
    _text(
        screen,
        font_small,
        "学习",
        learning_card.x + 14,
        learning_card.y + 9,
        MUTED,
    )
    lv = _learning_values(
        selected_person,
        total_learning,
        session_learning,
        recent_learning,
    )
    learn_stats_rect = pygame.Rect(
        learning_card.x,
        learning_card.y + 24,
        learning_card.w,
        learning_card.h - 24,
    )
    _draw_three_stats(
        screen,
        learn_stats_rect,
        (
            ("总量", lv[0]),
            ("本局", lv[1]),
            ("10秒", lv[2]),
        ),
        font_small,
        font,
    )

    _text(
        screen,
        font_small,
        "物品",
        x,
        500,
        MUTED,
    )

    picker_hover = (
        PICKER_RECT.collidepoint(
            mouse_pos
        )
    )
    picker_fill = (
        CARD_HOVER
        if picker_hover or search_active
        else CARD
    )
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

    selected_item = get_item(
        selected_item_id
    )
    if search_active:
        picker_text = (
            search_text
            or "输入关键词"
        )
        picker_color = (
            TEXT
            if search_text
            else MUTED
        )
    else:
        picker_text = (
            selected_item.name
            if selected_item
            else "选择物品"
        )
        picker_color = TEXT

    img = font.render(
        picker_text,
        True,
        picker_color,
    )
    screen.blit(
        img,
        (
            PICKER_RECT.x + 14,
            PICKER_RECT.centery
            - img.get_height() // 2,
        ),
    )

    pygame.draw.polygon(
        screen,
        MUTED,
        [
            (
                PICKER_RECT.right - 23,
                PICKER_RECT.centery - 3,
            ),
            (
                PICKER_RECT.right - 13,
                PICKER_RECT.centery - 3,
            ),
            (
                PICKER_RECT.right - 18,
                PICKER_RECT.centery + 3,
            ),
        ],
    )

    if (
        search_active
        and int(time.monotonic() * 2) % 2
        == 0
    ):
        caret_x = min(
            PICKER_RECT.right - 34,
            PICKER_RECT.x
            + 14
            + img.get_width()
            + 2,
        )
        pygame.draw.line(
            screen,
            TEXT,
            (
                caret_x,
                PICKER_RECT.y + 11,
            ),
            (
                caret_x,
                PICKER_RECT.bottom - 11,
            ),
            1,
        )

    place_hover = (
        PLACE_RECT.collidepoint(
            mouse_pos
        )
    )
    if placing_item_id:
        button_fill = (105, 70, 67)
        button_text = "取消放置"
    else:
        button_fill = (
            (53, 139, 92)
            if place_hover
            else (45, 119, 80)
        )
        button_text = "放置"

    pygame.draw.rect(
        screen,
        button_fill,
        PLACE_RECT,
        border_radius=11,
    )
    button_img = font.render(
        button_text,
        True,
        TEXT,
    )
    screen.blit(
        button_img,
        (
            PLACE_RECT.centerx
            - button_img.get_width() // 2,
            PLACE_RECT.centery
            - button_img.get_height() // 2,
        ),
    )

    event_card = pygame.Rect(
        x,
        644,
        PANEL_W - PANEL_PAD * 2,
        52,
    )
    pygame.draw.rect(
        screen,
        CARD,
        event_card,
        border_radius=12,
    )
    pygame.draw.circle(
        screen,
        ACCENT,
        (
            event_card.x + 16,
            event_card.centery,
        ),
        4,
    )
    event_img = font_small.render(
        last_event_text,
        True,
        TEXT,
    )
    screen.blit(
        event_img,
        (
            event_card.x + 28,
            event_card.centery
            - event_img.get_height() // 2,
        ),
    )

    footer = "点击人物切换  ·  Q 退出"
    if placing_item_id or dropdown_open:
        footer = "Esc 取消  ·  Q 退出"

    footer_img = font_small.render(
        footer,
        True,
        MUTED,
    )
    screen.blit(
        footer_img,
        (
            x,
            HEIGHT - 32,
        ),
    )

    if dropdown_open:
        rows = _dropdown_rows(
            search_text
        )
        if rows:
            box = pygame.Rect(
                PICKER_RECT.x,
                DROPDOWN_TOP,
                PICKER_RECT.w,
                len(rows)
                * DROPDOWN_ROW_H,
            )
            pygame.draw.rect(
                screen,
                (18, 27, 23),
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
                if rect.collidepoint(
                    mouse_pos
                ):
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
                category = (
                    font_small.render(
                        item.category,
                        True,
                        MUTED,
                    )
                )
                screen.blit(
                    category,
                    (
                        rect.right
                        - category.get_width()
                        - 14,
                        rect.centery
                        - category.get_height()
                        // 2,
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
                (18, 27, 23),
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
                    empty.centery
                    - msg.get_height() // 2,
                ),
            )


def run() -> int:
    _ensure_verified_malecns()

    pygame.init()
    pygame.display.set_caption(
        "赛博宠物"
    )
    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT)
    )
    clock = pygame.time.Clock()

    font_small = _font(14)
    font = _font(18)
    font_big = _font(
        27,
        bold=True,
    )

    store = MemoryStore()
    snapshot = store.load_snapshot()

    world = CyberFlyWorld(
        width=ARENA_W,
        height=HEIGHT,
        snapshot=snapshot,
    )
    brain = MaleCNSBrain()
    learner = FastValenceLearner(
        q_table=world.state.policy_q
    )

    prior_learning_updates = (
        world.state.learning_updates
    )
    outputs = BrainOutputs(
        forward=0.1
    )
    bias = LearningBias()

    selected_person = "male"
    selected_item_id = "bread"
    placing_item_id: str | None = None
    dropdown_open = False
    search_active = False
    search_text = ""

    learning_history: deque[
        tuple[float, int]
    ] = deque()
    last_seen_learner_updates = 0

    running = True
    shutdown_saved = False
    last_save = time.monotonic()
    brain_acc = 0.0

    last_event_text = (
        "已读取存档"
        if snapshot
        else "新生命"
    )
    courtship_cooldown = 0.0
    escape_cooldown = 0.0
    collision_log_cooldown = 0.0
    sleeping = False
    hunger_pain_active = False

    def sync_learning_state() -> None:
        world.state.policy_q = (
            learner.export()
        )
        world.state.learning_updates = (
            prior_learning_updates
            + learner.updates
        )

    def update_learning_history() -> None:
        nonlocal last_seen_learner_updates
        delta = (
            learner.updates
            - last_seen_learner_updates
        )
        now = time.monotonic()
        if delta > 0:
            learning_history.append(
                (now, delta)
            )
            last_seen_learner_updates = (
                learner.updates
            )
        while (
            learning_history
            and now
            - learning_history[0][0]
            > 10.0
        ):
            learning_history.popleft()

    def learning_recent() -> int:
        now = time.monotonic()
        while (
            learning_history
            and now
            - learning_history[0][0]
            > 10.0
        ):
            learning_history.popleft()
        return sum(
            delta
            for _, delta
            in learning_history
        )

    def close_search() -> None:
        nonlocal search_active
        nonlocal dropdown_open
        search_active = False
        dropdown_open = False
        pygame.key.stop_text_input()

    def choose_first_search_result() -> bool:
        nonlocal selected_item_id
        nonlocal search_text
        results = search_items(
            search_text
        )
        if not results:
            return False
        selected_item_id = (
            results[0].item_id
        )
        search_text = ""
        close_search()
        return True

    def save(
        reason: str = "shutdown",
    ) -> None:
        nonlocal shutdown_saved
        try:
            sync_learning_state()
            store.save_snapshot(
                world.state
            )
            if (
                reason == "shutdown"
                and not shutdown_saved
            ):
                store.append_episode(
                    "session_end",
                    0.15,
                    {
                        "age_seconds": round(
                            world.state.age_seconds,
                            2,
                        ),
                        "learning_updates": (
                            world.state.learning_updates
                        ),
                    },
                )
                shutdown_saved = True
        except Exception as exc:
            print(
                f"存档失败：{exc}"
            )

    atexit.register(save)

    def stop_signal(
        signum,
        frame,
    ):
        nonlocal running
        running = False

    for sig in (
        signal.SIGINT,
        signal.SIGTERM,
    ):
        try:
            signal.signal(
                sig,
                stop_signal,
            )
        except (
            ValueError,
            OSError,
        ):
            pass

    try:
        while running:
            dt = min(
                clock.tick(FPS) / 1000.0,
                0.08,
            )

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    continue

                if (
                    event.type
                    == pygame.TEXTINPUT
                    and search_active
                ):
                    search_text += event.text
                    dropdown_open = True
                    continue

                if event.type == pygame.KEYDOWN:
                    if search_active:
                        if (
                            event.key
                            == pygame.K_BACKSPACE
                        ):
                            search_text = (
                                search_text[:-1]
                            )
                        elif (
                            event.key
                            == pygame.K_RETURN
                        ):
                            choose_first_search_result()
                        elif (
                            event.key
                            == pygame.K_ESCAPE
                        ):
                            search_text = ""
                            close_search()
                        continue

                    if event.key == pygame.K_q:
                        running = False
                    elif (
                        event.key
                        == pygame.K_ESCAPE
                    ):
                        if placing_item_id:
                            placing_item_id = None
                            last_event_text = (
                                "已取消放置"
                            )
                        elif dropdown_open:
                            close_search()
                        else:
                            running = False
                    continue

                if (
                    event.type
                    == pygame.MOUSEBUTTONDOWN
                ):
                    mx, my = event.pos

                    if (
                        event.button == 3
                        and placing_item_id
                    ):
                        placing_item_id = None
                        last_event_text = (
                            "已取消放置"
                        )
                        continue

                    if event.button != 1:
                        continue

                    if PICKER_RECT.collidepoint(
                        event.pos
                    ):
                        placing_item_id = None
                        search_text = ""
                        search_active = True
                        dropdown_open = True
                        pygame.key.start_text_input()
                        continue

                    if dropdown_open:
                        picked = None
                        for item, rect in (
                            _dropdown_rows(
                                search_text
                            )
                        ):
                            if rect.collidepoint(
                                event.pos
                            ):
                                picked = item
                                break
                        if picked:
                            selected_item_id = (
                                picked.item_id
                            )
                            search_text = ""
                            close_search()
                        else:
                            close_search()
                        continue

                    if PLACE_RECT.collidepoint(
                        event.pos
                    ):
                        if placing_item_id:
                            placing_item_id = None
                            last_event_text = (
                                "已取消放置"
                            )
                        else:
                            placing_item_id = (
                                selected_item_id
                            )
                            item = get_item(
                                selected_item_id
                            )
                            last_event_text = (
                                f"选择"
                                f"{item.name if item else '物品'}"
                                f"位置"
                            )
                        continue

                    if (
                        placing_item_id
                        and mx < ARENA_W
                    ):
                        item = get_item(
                            placing_item_id
                        )
                        if (
                            placing_item_id
                            == "bread"
                        ):
                            px, py = (
                                world.place_food(
                                    mx,
                                    my,
                                )
                            )
                            store.append_episode(
                                "place_item",
                                0.1,
                                {
                                    "item": "bread",
                                    "x": round(
                                        px,
                                        2,
                                    ),
                                    "y": round(
                                        py,
                                        2,
                                    ),
                                },
                            )
                            last_event_text = (
                                "已放置面包"
                            )
                        elif item:
                            last_event_text = (
                                f"暂不支持放置"
                                f"{item.name}"
                            )
                        placing_item_id = None
                        continue

                    if mx < ARENA_W:
                        person = _person_at(
                            world,
                            event.pos,
                        )
                        if person:
                            selected_person = person
                            last_event_text = (
                                "已选择男性"
                                if person == "male"
                                else "已选择女性"
                            )
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
            body_event = world.update_body(
                dt
            )

            if body_event == "male_ate":
                store.append_episode(
                    "ate_bread",
                    1.0,
                    {
                        "person": "male",
                        "hunger_after": round(
                            world.state.hunger,
                            3,
                        ),
                        "satiety_gain": 0.15,
                    },
                )
                last_event_text = (
                    "男性吃到面包"
                )
            elif body_event == "female_ate":
                store.append_episode(
                    "ate_bread",
                    0.8,
                    {
                        "person": "female",
                        "hunger_after": round(
                            world.state.female_hunger,
                            3,
                        ),
                        "satiety_gain": 0.15,
                    },
                )
                last_event_text = (
                    "女性吃到面包"
                )

            hunger_pain_level = _clamp(
                (
                    world.state.hunger
                    - 0.50
                )
                / 0.50
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
                    },
                )
                last_event_text = (
                    "男性饥饿"
                )
            elif (
                hunger_pain_level < 0.10
            ):
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
                getattr(
                    brain.brain,
                    "dt",
                    0.02,
                )
            )
            steps = 0
            while (
                brain_acc >= neural_dt
                and steps < 3
            ):
                outputs = brain.step(
                    sensors,
                    hunger=world.state.hunger,
                    fatigue=world.state.fatigue,
                    social_drive=(
                        world.state.social_drive
                    ),
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
                    last_event_text = (
                        "男性睡眠"
                    )
                sleeping = True
            elif (
                sleeping
                and world.state.fatigue < 0.42
            ):
                sleeping = False
                store.append_episode(
                    "wake",
                    0.25,
                    {},
                )
                last_event_text = (
                    "男性醒来"
                )

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
                    outputs.forward
                    + bias.forward
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
                    outputs.backward
                    + bias.backward
                )
                applied_escape = _clamp(
                    outputs.escape
                    + bias.escape
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
                    and collision_log_cooldown
                    <= 0.0
                ):
                    collision_log_cooldown = 0.8
                    store.append_episode(
                        "boundary_pain",
                        1.0,
                        {
                            "person": "male",
                            "pain": 1.0,
                        },
                    )
                    last_event_text = (
                        "男性撞到边界"
                    )

            mate_dist = math.hypot(
                world.state.female_x
                - world.state.x,
                world.state.female_y
                - world.state.y,
            )
            if (
                not sleeping
                and outputs.courtship > 0.22
                and mate_dist < 58
                and courtship_cooldown
                <= 0
            ):
                courtship_cooldown = 8.0
                world.state.courtship_events += 1
                world.state.social_drive = _clamp(
                    world.state.social_drive
                    - 0.22
                )
                world.state.female_social_drive = (
                    _clamp(
                        world.state.female_social_drive
                        - 0.16
                    )
                )
                world.state.female_dopamine = max(
                    world.state.female_dopamine,
                    0.65,
                )
                world.state.female_reward_events += 1

                world.pulse_dopamine(
                    0.65,
                    "social_contact",
                    count_event=True,
                )
                store.append_episode(
                    "social_contact",
                    0.7,
                    {
                        "distance": round(
                            mate_dist,
                            2,
                        ),
                    },
                )
                last_event_text = (
                    "社交奖励"
                )

            if (
                outputs.escape > 0.55
                and escape_cooldown <= 0
            ):
                escape_cooldown = 5.0
                store.append_episode(
                    "escape",
                    0.8,
                    {
                        "person": "male",
                    },
                )
                last_event_text = "逃逸"

            if not sleeping:
                next_sensors = world.sense()
                (
                    dopamine_signal,
                    pain_signal,
                    _,
                ) = (
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

            update_learning_history()
            sync_learning_state()

            if (
                time.monotonic() - last_save
                >= AUTOSAVE_SECONDS
            ):
                save("autosave")
                last_save = time.monotonic()

            screen.fill(BG)
            mouse_pos = pygame.mouse.get_pos()

            hovered_person = None
            if (
                mouse_pos[0] < ARENA_W
                and not placing_item_id
            ):
                hovered_person = _person_at(
                    world,
                    mouse_pos,
                )

            _draw_arena(
                screen,
                world,
                outputs,
                selected_person,
                hovered_person,
                placing_item_id,
                mouse_pos,
                font_small,
            )

            _draw_panel(
                screen,
                world,
                selected_person,
                sleeping,
                prior_learning_updates
                + learner.updates,
                learner.updates,
                learning_recent(),
                selected_item_id,
                placing_item_id,
                dropdown_open,
                search_active,
                search_text,
                last_event_text,
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
