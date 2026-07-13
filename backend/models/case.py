"""
Modelo de uma caixa (case) a ser posicionada no palete.
"""


class Case:
    """Representa uma caixa individual a ser empacotada."""

    def __init__(self, code, sizex, sizey, sizez, weight, strength=100):
        """
        :param code: Identificador do tipo de caixa
        :param sizex: Comprimento (eixo X)
        :param sizey: Largura (eixo Y)
        :param sizez: Altura (eixo Z)
        :param weight: Peso da caixa
        :param strength: Quantas caixas esta caixa aguenta empilhadas em cima
        """
        self.code = code
        self.x = 0
        self.y = 0
        self.z = 0
        self.rotated = False
        self.sizex = sizex
        self.sizey = sizey
        self.sizez = sizez
        self.volume = sizex * sizey * sizez
        self.weight = weight
        self.strength = strength
        self.can_hold = strength
        self.busy_corners = [False, False, False]

    def __repr__(self):
        return (
            f"Case(code={self.code}, pos=({self.x}, {self.y}, {self.z}), "
            f"size=({self.sizex}, {self.sizey}, {self.sizez}), weight={self.weight})"
        )

    def __copy__(self):
        obj = Case.__new__(self.__class__)
        obj.__dict__.update(self.__dict__)
        obj.busy_corners = list(self.busy_corners)
        return obj

    def copy(self):
        return self.__copy__()

    @property
    def position(self):
        return (self.x, self.y, self.z)

    def set_position(self, pos):
        self.x, self.y, self.z = pos

    @property
    def top(self):
        return self.z + self.sizez

    @property
    def bottom(self):
        return self.z

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.sizex

    @property
    def front(self):
        return self.y

    @property
    def back(self):
        return self.y + self.sizey


def rotate(case):
    """Rotaciona a caixa em 90 graus no plano horizontal (troca X com Y)."""
    case.rotated = not case.rotated
    case.sizex, case.sizey = case.sizey, case.sizex
