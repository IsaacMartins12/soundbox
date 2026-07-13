"""
Modelo do palete onde as caixas são posicionadas.
"""
import functools
import operator
from collections import deque


class Pallet:
    """Representa um palete com dimensões e restrições."""

    def __init__(self, size, max_weight=float("inf")):
        """
        :param size: Tuple (largura_x, largura_y, altura_z)
        :param max_weight: Peso máximo suportado pelo palete
        """
        self.size = size
        self.max_weight = max_weight
        self.max_volume = functools.reduce(operator.mul, size, 1)
        self.cases = deque()
        self.weight = 0
        self.volume = 0

    @property
    def sizex(self):
        return self.size[0]

    @property
    def sizey(self):
        return self.size[1]

    @property
    def sizez(self):
        return self.size[2]

    @property
    def utilization(self):
        """Retorna a porcentagem de utilização volumétrica."""
        if self.max_volume == 0:
            return 0
        return self.volume / self.max_volume

    def to_dict(self):
        """Serializa o palete e as caixas posicionadas para JSON."""
        cases_list = []
        for case in self.cases:
            cases_list.append({
                "code": case.code,
                "x": case.x,
                "y": case.y,
                "z": case.z,
                "sizex": case.sizex,
                "sizey": case.sizey,
                "sizez": case.sizez,
                "weight": case.weight,
                "rotated": case.rotated,
            })

        return {
            "pallet": {
                "sizex": self.sizex,
                "sizey": self.sizey,
                "sizez": self.sizez,
                "max_weight": self.max_weight if self.max_weight != float("inf") else None,
            },
            "cases": cases_list,
            "total_cases": len(cases_list),
            "total_weight": self.weight,
            "volume_utilization": round(self.utilization * 100, 2),
            "weight_utilization": round(
                (self.weight / self.max_weight * 100) if self.max_weight != float("inf") else 0, 2
            ),
        }
