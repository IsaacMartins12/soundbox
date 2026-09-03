"""
Testes do modelo Case (geometria da caixa).
"""
from models.case import Case, rotate


def make_case():
    return Case(code="BOX", sizex=40, sizey=30, sizez=20, weight=5, strength=10)


def test_case_volume():
    c = make_case()
    assert c.volume == 40 * 30 * 20


def test_case_posicao_inicial_na_origem():
    c = make_case()
    assert c.position == (0, 0, 0)


def test_case_set_position():
    c = make_case()
    c.set_position((10, 20, 30))
    assert c.position == (10, 20, 30)
    assert c.x == 10 and c.y == 20 and c.z == 30


def test_case_limites_geometricos():
    c = make_case()
    c.set_position((10, 20, 30))
    # left/front/bottom = origem; right/back/top = origem + tamanho
    assert c.left == 10
    assert c.right == 10 + 40
    assert c.front == 20
    assert c.back == 20 + 30
    assert c.bottom == 30
    assert c.top == 30 + 20


def test_case_can_hold_inicia_igual_strength():
    c = make_case()
    assert c.can_hold == c.strength == 10


def test_rotate_troca_x_e_y():
    c = make_case()
    assert not c.rotated
    rotate(c)
    assert c.rotated
    assert c.sizex == 30 and c.sizey == 40
    # altura nao muda com rotacao horizontal
    assert c.sizez == 20


def test_rotate_duas_vezes_volta_ao_original():
    c = make_case()
    rotate(c)
    rotate(c)
    assert not c.rotated
    assert c.sizex == 40 and c.sizey == 30


def test_case_copy_e_independente():
    c = make_case()
    c.set_position((1, 2, 3))
    d = c.copy()
    d.set_position((9, 9, 9))
    # alterar a copia nao afeta o original
    assert c.position == (1, 2, 3)
    assert d.position == (9, 9, 9)
