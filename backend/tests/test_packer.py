"""
Testes do algoritmo de empacotamento (pack_pallet).

Focam em propriedades verificaveis: caixas dentro dos limites, respeito a
quantidade solicitada, coordenadas de place e casos-limite.
"""
from models.pallet import Pallet
from algorithms.packer import pack_pallet


def build_case(sizex, sizey, sizez, quantity, **extra):
    base = {
        "code": "BOX",
        "sizex": sizex,
        "sizey": sizey,
        "sizez": sizez,
        "weight": 1,
        "quantity": quantity,
        "strength": 100,
    }
    base.update(extra)
    return base


def test_empacota_caixas_simples():
    pallet = Pallet((100, 120, 200), max_weight=10000)
    result = pack_pallet(pallet, [build_case(50, 40, 30, quantity=4)], overhang=0)
    assert result.total_cases if hasattr(result, "total_cases") else len(result.cases) > 0
    assert len(result.cases) > 0


def test_respeita_quantidade_solicitada():
    pallet = Pallet((100, 120, 200), max_weight=100000)
    # Pede 5 caixas pequenas; o resultado nao deve exceder o pedido
    result = pack_pallet(pallet, [build_case(20, 20, 20, quantity=5)], overhang=0)
    assert len(result.cases) <= 5


def test_caixas_dentro_dos_limites_sem_overhang():
    X, Y, Z = 100, 120, 200
    pallet = Pallet((X, Y, Z), max_weight=100000)
    result = pack_pallet(pallet, [build_case(50, 40, 30, quantity=8)], overhang=0)
    assert len(result.cases) > 0
    for c in result.cases:
        # sem overhang, nenhuma caixa ultrapassa o pallet
        assert c.right <= X + 1e-9
        assert c.back <= Y + 1e-9
        assert c.top <= Z + 1e-9
        # nada abaixo da base
        assert c.z >= 0


def test_caixa_maior_que_pallet_nao_posiciona():
    pallet = Pallet((100, 120, 200), max_weight=100000)
    # Caixa maior que o pallet em X e Y, sem overhang -> nao cabe
    result = pack_pallet(pallet, [build_case(150, 150, 30, quantity=1)], overhang=0)
    assert len(result.cases) == 0


def test_coordenadas_de_place_sao_centro_da_face_superior():
    pallet = Pallet((100, 120, 200), max_weight=100000)
    result = pack_pallet(pallet, [build_case(50, 40, 30, quantity=2)], overhang=0)
    data = result.to_dict()
    assert data["total_cases"] > 0
    for case in data["cases"]:
        # place_x/y = centro horizontal; place_z = topo
        esperado_x = round(case["x"] + case["sizex"] / 2, 2)
        esperado_y = round(case["y"] + case["sizey"] / 2, 2)
        esperado_z = round(case["z"] + case["sizez"], 2)
        assert case["place_x"] == esperado_x
        assert case["place_y"] == esperado_y
        assert case["place_z"] == esperado_z


def test_index_sequencial_no_to_dict():
    pallet = Pallet((100, 120, 200), max_weight=100000)
    result = pack_pallet(pallet, [build_case(30, 30, 30, quantity=6)], overhang=0)
    data = result.to_dict()
    indices = [c["index"] for c in data["cases"]]
    # index comeca em 1 e e sequencial
    assert indices == list(range(1, len(indices) + 1))


def test_empilha_em_camadas_quando_ha_altura():
    # Caixa que cabe varias vezes por camada e o pallet e alto -> deve empilhar
    pallet = Pallet((100, 100, 200), max_weight=100000)
    result = pack_pallet(pallet, [build_case(50, 50, 50, quantity=8)], overhang=0)
    zs = {round(c.z, 2) for c in result.cases}
    # deve haver mais de uma altura distinta (mais de uma camada)
    assert len(zs) > 1


def test_peso_total_bate_com_numero_de_caixas():
    pallet = Pallet((100, 120, 200), max_weight=100000)
    result = pack_pallet(pallet, [build_case(40, 40, 40, quantity=6, weight=2.5)], overhang=0)
    assert result.weight == len(result.cases) * 2.5
