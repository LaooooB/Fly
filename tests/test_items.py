from cyberfly.items import get_item, search_items


def test_catalog_contains_bread():
    bread = get_item("bread")
    assert bread is not None
    assert bread.name == "面包"


def test_search_supports_chinese_and_english_keywords():
    assert [item.item_id for item in search_items("面包")] == ["bread"]
    assert [item.item_id for item in search_items("bread")] == ["bread"]
    assert [item.item_id for item in search_items("食物")] == ["bread"]


def test_game_item_is_searchable():
    assert [item.item_id for item in search_items("游戏")] == ["game"]
    assert [item.item_id for item in search_items("game")] == ["game"]
    assert get_item("game").category == "娱乐"


def test_unknown_search_returns_empty_list():
    assert search_items("不存在") == []
