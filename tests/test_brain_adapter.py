import numpy as np

from cyberfly.brain_adapter import MaleCNSBrain
from cyberfly.world import Sensors


class FakeBrain:
    dt = 0.02

    def __init__(self):
        self.mapping = {
            ("ORN_DM1", "L"): np.array([1, 2]),
            ("ORN_DM1", "R"): np.array([3, 4]),
            ("LC10a", "L"): np.array([5]),
            ("LC10a", "R"): np.array([6]),
            ("LC4", "L"): np.array([7]),
            ("LC4", "R"): np.array([8]),
            ("LPLC2", "L"): np.array([9]),
            ("LPLC2", "R"): np.array([10]),
            ("DNa02", "L"): np.array([11]),
            ("DNa02", "R"): np.array([12]),
            ("DNg100", None): np.array([13]),
            ("MDN", None): np.array([14]),
            ("DNp01", None): np.array([15]),
            ("pIP1", None): np.array([16]),
        }
        self.last_inject = []

    def cells(self, types, side=None):
        chunks = [self.mapping.get((t, side), np.array([], dtype=int)) for t in types]
        return np.unique(np.concatenate(chunks)) if chunks else np.array([], dtype=int)

    def step(self, inject=None):
        self.last_inject = inject or []
        # DNa02-L, DNg100, pIP1 fired -> left turn, forward, courtship
        return np.array([11, 13, 16])


def test_adapter_injects_real_named_populations_and_decodes_outputs():
    fake = FakeBrain()
    adapter = MaleCNSBrain(brain=fake)
    sensors = Sensors(food_odor=0.8, food_left=1.0, food_right=0.2,
                      mate_visual=0.7, mate_left=0.1, mate_right=1.0,
                      loom_left=0.0, loom_right=0.6)
    out = adapter.step(sensors, hunger=0.8, fatigue=0.2, social_drive=0.9)
    injected_ids = {int(i) for cells, amount in fake.last_inject for i in cells if amount > 0}
    assert {1, 2, 3, 4, 5, 6, 8, 10}.issubset(injected_ids)
    assert out.forward > 0
    assert out.turn < 0  # left DNa02 -> negative/left turn in game coordinates
    assert out.courtship > 0
