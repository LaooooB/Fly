from pathlib import Path

from cyberfly.memory import MemoryStore, PetSnapshot


def test_memory_store_round_trip(tmp_path: Path):
    store = MemoryStore(tmp_path)
    snap = PetSnapshot(x=12.5, y=44.0, heading=1.2, hunger=0.7, fatigue=0.3,
                       social_drive=0.8, age_seconds=123.0, food_eaten=4,
                       courtship_events=2, known_food_spots=[[10.0, 20.0]])
    store.save_snapshot(snap)
    loaded = store.load_snapshot()
    assert loaded == snap


def test_memory_store_appends_episodes(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append_episode("ate", 0.8, {"x": 10, "y": 20})
    store.append_episode("escape", 1.0, {"x": 30, "y": 40})
    episodes = store.load_recent_episodes(limit=10)
    assert [e["kind"] for e in episodes] == ["ate", "escape"]
    assert episodes[0]["details"]["x"] == 10
