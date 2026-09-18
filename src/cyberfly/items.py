from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlaceableItem:
    item_id: str
    name: str
    category: str
    keywords: tuple[str, ...] = ()


ITEM_CATALOG: tuple[PlaceableItem, ...] = (
    PlaceableItem(
        item_id="bread",
        name="面包",
        category="食物",
        keywords=("bread", "food", "吃", "食物"),
    ),
    PlaceableItem(
        item_id="game",
        name="游戏机",
        category="娱乐",
        keywords=("game", "游戏", "玩", "娱乐", "快乐", "多巴胺"),
    ),
)


def get_item(item_id: str) -> PlaceableItem | None:
    for item in ITEM_CATALOG:
        if item.item_id == item_id:
            return item
    return None


def search_items(query: str) -> list[PlaceableItem]:
    needle = query.strip().casefold()
    if not needle:
        return list(ITEM_CATALOG)

    ranked: list[tuple[int, str, PlaceableItem]] = []
    for item in ITEM_CATALOG:
        fields = (
            item.name,
            item.item_id,
            item.category,
            *item.keywords,
        )
        normalized = [field.casefold() for field in fields]
        if not any(needle in field for field in normalized):
            continue

        if item.name.casefold().startswith(needle):
            score = 0
        elif item.item_id.casefold().startswith(needle):
            score = 1
        elif any(field.startswith(needle) for field in normalized):
            score = 2
        else:
            score = 3
        ranked.append((score, item.name, item))

    ranked.sort(key=lambda row: (row[0], row[1]))
    return [item for _, _, item in ranked]
