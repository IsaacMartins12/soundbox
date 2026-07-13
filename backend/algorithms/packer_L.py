"""
Algoritmo de Paletização de Caixas em Formato L
================================================
A caixa L fica EM PÉ no pallet. Duas caixas L encaixadas formam um retângulo.

Orientação no pallet:
- Face no chão: comp_total × largura (91.4 × 26.3 cm)
- Altura do par encaixado: alt_vertical + alt_perpendicular (43.5 + 14.1 = 57.6 cm)

Como 2 caixas L encaixadas = 1 retângulo, a paletização usa a mesma
lógica de caixas retangulares. A única diferença é que a quantidade
de caixas L é dividida por 2 para obter o número de retângulos.

Dimensões do par encaixado (retângulo):
- Comprimento: comp_total (ex: 91.4 cm)
- Largura: largura (ex: 26.3 cm)  
- Altura: alt_vertical + alt_perpendicular (ex: 43.5 + 14.1 = 57.6 cm)
"""
import math


def pack_pallet_L(pallet_size, l_dims, quantidade, peso_caixa=0, max_weight=float("inf"), overhang=0):
    """
    Empacota caixas em L no pallet.
    
    O par encaixado forma um retângulo com:
    - comp = l_dims["comp_total"]
    - larg = l_dims["largura"]
    - alt = l_dims["alt_vertical"] + l_dims["alt_perpendicular"]

    :param pallet_size: (comp, larg, alt) do pallet em cm
    :param l_dims: dict com {comp_total, largura, alt_vertical, alt_perpendicular}
    :param quantidade: Número de caixas L desejado
    :param peso_caixa: Peso de cada caixa L em kg
    :param max_weight: Peso máximo do pallet
    :param overhang: Saliência permitida para fora do pallet (cm) em X e Y
    :return: dict com resultado
    """
    comp_pallet, larg_pallet, alt_pallet = pallet_size

    # Espaço efetivo com overhang
    comp_efetivo = comp_pallet + overhang
    larg_efetivo = larg_pallet + overhang

    # Dimensões do par encaixado dependem da orientação
    l_orientation = l_dims.get("l_orientation", "vertical")

    if l_orientation == "vertical":
        # Em pé: face no chão = comp_total × largura, altura = alt_v + alt_p
        par_comp = l_dims["comp_total"]
        par_larg = l_dims["largura"]
        par_alt = l_dims["alt_vertical"] + l_dims["alt_perpendicular"]
    else:
        # Deitada: face no chão = comp_total × (alt_v + alt_p), altura = largura
        par_comp = l_dims["comp_total"]
        par_larg = l_dims["alt_vertical"] + l_dims["alt_perpendicular"]
        par_alt = l_dims["largura"]

    # Quantos pares precisamos (2 caixas L por par)
    num_pares_necessarios = math.ceil(quantidade / 2)

    # Testar as 2 orientações do par no pallet (rotação horizontal)
    # Orientação A: comp × larg
    nx_a = int(comp_efetivo // par_comp)
    ny_a = int(larg_efetivo // par_larg)
    pares_a = nx_a * ny_a

    # Orientação B: larg × comp (rotacionado 90°)
    nx_b = int(comp_efetivo // par_larg)
    ny_b = int(larg_efetivo // par_comp)
    pares_b = nx_b * ny_b

    # Escolher a melhor orientação
    if pares_a >= pares_b:
        pares_por_camada = pares_a
        nx, ny = nx_a, ny_a
        bloco_x, bloco_y = par_comp, par_larg
        eixo_comp = "x"  # comprimento total está no eixo X
    else:
        pares_por_camada = pares_b
        nx, ny = nx_b, ny_b
        bloco_x, bloco_y = par_larg, par_comp
        eixo_comp = "y"  # comprimento total está no eixo Y

    if pares_por_camada == 0:
        return {
            "success": False,
            "error": f"O par de caixas L ({par_comp}×{par_larg}×{par_alt} cm) não cabe no pallet ({comp_efetivo}×{larg_efetivo} cm com overhang).",
            "caixas": [],
            "caixas_por_camada": 0,
            "num_camadas": 0,
            "total": 0,
        }

    caixas_por_camada = pares_por_camada * 2

    # Limites de camadas
    camadas_por_altura = int(alt_pallet // par_alt)
    peso_camada = peso_caixa * caixas_por_camada
    camadas_por_peso = int(max_weight // peso_camada) if peso_camada > 0 else camadas_por_altura
    camadas_max = min(camadas_por_altura, camadas_por_peso)

    camadas_necessarias = math.ceil(num_pares_necessarios / pares_por_camada)
    num_camadas = min(camadas_necessarias, camadas_max)

    # Centralizar no pallet REAL (overhang distribuído igualmente para os dois lados)
    largura_total_usada_x = nx * bloco_x
    largura_total_usada_y = ny * bloco_y
    offset_x = (comp_pallet - largura_total_usada_x) / 2
    offset_y = (larg_pallet - largura_total_usada_y) / 2

    # Gerar blocos retangulares
    blocos = []
    caixas_colocadas = 0

    for camada in range(num_camadas):
        z = camada * par_alt

        for i in range(nx):
            for j in range(ny):
                if caixas_colocadas >= quantidade:
                    break

                x = offset_x + i * bloco_x
                y = offset_y + j * bloco_y

                # Intertravamento 180°: camadas ímpares espelham
                if camada % 2 == 1:
                    x = comp_pallet - x - bloco_x
                    y = larg_pallet - y - bloco_y

                caixas_neste_bloco = min(2, quantidade - caixas_colocadas)

                if caixas_neste_bloco == 2 and l_orientation == "horizontal":
                    # Deitada: mesma decomposição do L mas com eixos trocados
                    # O L está deitado: a "altura" do L vira uma dimensão horizontal (Y)
                    # Base = faixa larga no Y, Braço = faixa estreita no Y
                    alt_v = l_dims["alt_vertical"]
                    alt_p = l_dims["alt_perpendicular"]
                    comp_braco = l_dims.get("comp_braco", l_dims["comp_total"] / 2)
                    
                    # No modo deitado: par_larg = alt_v + alt_p, par_alt = largura
                    # A decomposição é no eixo Y (onde ficava a altura vertical)
                    base_sizey = round(alt_p, 2)  # faixa estreita
                    braco_sizey = round(alt_v - alt_p, 2)  # faixa do meio
                    
                    if eixo_comp == "x":
                        braco_sizex = round(comp_braco, 2)
                    else:
                        braco_sizex = round(bloco_x, 2)
                    
                    # Base caixa 1 (frente, faixa estreita no Y)
                    blocos.append({
                        "code": "L-base",
                        "x": round(x, 2),
                        "y": round(y, 2),
                        "z": round(z, 2),
                        "sizex": round(bloco_x, 2),
                        "sizey": base_sizey,
                        "sizez": round(par_alt, 2),
                        "weight": peso_caixa * 0.3,
                        "rotated": False,
                        "camada": camada,
                        "num_caixas_l": 1,
                    })
                    # Braço caixa 1 (meio-esquerda)
                    blocos.append({
                        "code": "L-braco1",
                        "x": round(x, 2),
                        "y": round(y + alt_p, 2),
                        "z": round(z, 2),
                        "sizex": braco_sizex,
                        "sizey": braco_sizey,
                        "sizez": round(par_alt, 2),
                        "weight": peso_caixa * 0.4,
                        "rotated": False,
                        "camada": camada,
                        "num_caixas_l": 0,
                    })
                    # Braço caixa 2 (meio-direita)
                    blocos.append({
                        "code": "L-braco2",
                        "x": round(x + bloco_x - comp_braco, 2) if eixo_comp == "x" else round(x, 2),
                        "y": round(y + alt_p, 2),
                        "z": round(z, 2),
                        "sizex": braco_sizex,
                        "sizey": braco_sizey,
                        "sizez": round(par_alt, 2),
                        "weight": peso_caixa * 0.4,
                        "rotated": True,
                        "camada": camada,
                        "num_caixas_l": 0,
                    })
                    # Base caixa 2 (fundo, faixa estreita no Y)
                    blocos.append({
                        "code": "L-base",
                        "x": round(x, 2),
                        "y": round(y + alt_p + braco_sizey, 2),
                        "z": round(z, 2),
                        "sizex": round(bloco_x, 2),
                        "sizey": base_sizey,
                        "sizez": round(par_alt, 2),
                        "weight": peso_caixa * 0.3,
                        "rotated": True,
                        "camada": camada,
                        "num_caixas_l": 1,
                    })
                elif caixas_neste_bloco == 2:
                    # Par completo: 2 caixas L encaixadas (uma invertida 180° em cima)
                    # Estrutura vertical:
                    #   Topo:   Base da caixa 2 (invertida)     z = alt_v
                    #   Meio:   Braço1 (esq) + Braço2 (dir)    z = alt_p
                    #   Base:   Base da caixa 1                 z = 0
                    # Altura total = alt_p + alt_v = par_alt (57.6)
                    
                    alt_v = l_dims["alt_vertical"]
                    alt_p = l_dims["alt_perpendicular"]
                    comp_braco = l_dims.get("comp_braco", par_comp / 2)
                    
                    if eixo_comp == "x":
                        braco_sizex = round(comp_braco, 2)
                        braco_sizey = round(bloco_y, 2)
                        braco1_x = round(x, 2)
                        braco1_y = round(y, 2)
                        braco2_x = round(x + bloco_x - comp_braco, 2)
                        braco2_y = round(y, 2)
                    else:
                        braco_sizex = round(bloco_x, 2)
                        braco_sizey = round(comp_braco, 2)
                        braco1_x = round(x, 2)
                        braco1_y = round(y, 2)
                        braco2_x = round(x, 2)
                        braco2_y = round(y + bloco_y - comp_braco, 2)
                    
                    # Base caixa 1 (embaixo, comprimento total)
                    blocos.append({
                        "code": "L-base",
                        "x": round(x, 2),
                        "y": round(y, 2),
                        "z": round(z, 2),
                        "sizex": round(bloco_x, 2),
                        "sizey": round(bloco_y, 2),
                        "sizez": round(alt_p, 2),
                        "weight": peso_caixa * 0.3,
                        "rotated": False,
                        "camada": camada,
                        "num_caixas_l": 1,
                    })
                    # Braço caixa 1 (metade esquerda/inferior, acima da base)
                    blocos.append({
                        "code": "L-braco1",
                        "x": braco1_x,
                        "y": braco1_y,
                        "z": round(z + alt_p, 2),
                        "sizex": braco_sizex,
                        "sizey": braco_sizey,
                        "sizez": round(alt_v - alt_p, 2),
                        "weight": peso_caixa * 0.4,
                        "rotated": False,
                        "camada": camada,
                        "num_caixas_l": 0,
                    })
                    # Braço caixa 2 invertida (metade direita/superior, acima da base)
                    blocos.append({
                        "code": "L-braco2",
                        "x": braco2_x,
                        "y": braco2_y,
                        "z": round(z + alt_p, 2),
                        "sizex": braco_sizex,
                        "sizey": braco_sizey,
                        "sizez": round(alt_v - alt_p, 2),
                        "weight": peso_caixa * 0.4,
                        "rotated": True,
                        "camada": camada,
                        "num_caixas_l": 0,
                    })
                    # Base caixa 2 invertida (em cima, comprimento total)
                    blocos.append({
                        "code": "L-base",
                        "x": round(x, 2),
                        "y": round(y, 2),
                        "z": round(z + alt_v, 2),
                        "sizex": round(bloco_x, 2),
                        "sizey": round(bloco_y, 2),
                        "sizez": round(alt_p, 2),
                        "weight": peso_caixa * 0.3,
                        "rotated": True,
                        "camada": camada,
                        "num_caixas_l": 1,
                    })
                else:
                    # Caixa L sozinha
                    if l_orientation == "horizontal":
                        # Deitada: bloco sólido com metade da altura
                        blocos.append({
                            "code": "PAR-L",
                            "x": round(x, 2),
                            "y": round(y, 2),
                            "z": round(z, 2),
                            "sizex": round(bloco_x, 2),
                            "sizey": round(bloco_y, 2),
                            "sizez": round(par_alt / 2, 2),
                            "weight": peso_caixa,
                            "rotated": False,
                            "camada": camada,
                            "num_caixas_l": 1,
                        })
                    else:
                        # Em pé: gera 2 blocos formando o L
                        alt_v = l_dims["alt_vertical"]
                        alt_p = l_dims["alt_perpendicular"]
                    comp_braco = l_dims.get("comp_braco", par_comp / 2)
                    
                    # O braço tem comp_braco no eixo do comprimento total
                    if eixo_comp == "x":
                        braco_sizex = round(comp_braco, 2)
                        braco_sizey = round(bloco_y, 2)
                    else:
                        braco_sizex = round(bloco_x, 2)
                        braco_sizey = round(comp_braco, 2)
                    
                    # Bloco base (comprimento total × largura total, altura menor)
                    blocos.append({
                        "code": "PAR-L",
                        "x": round(x, 2),
                        "y": round(y, 2),
                        "z": round(z, 2),
                        "sizex": round(bloco_x, 2),
                        "sizey": round(bloco_y, 2),
                        "sizez": round(alt_p, 2),
                        "weight": peso_caixa * 0.3,
                        "rotated": False,
                        "camada": camada,
                        "num_caixas_l": 1,
                    })
                    # Bloco braço (metade do comprimento, mesma largura, altura vertical)
                    blocos.append({
                        "code": "PAR-L",
                        "x": round(x, 2),
                        "y": round(y, 2),
                        "z": round(z + alt_p, 2),
                        "sizex": braco_sizex,
                        "sizey": braco_sizey,
                        "sizez": round(alt_v, 2),
                        "weight": peso_caixa * 0.7,
                        "rotated": False,
                        "camada": camada,
                        "num_caixas_l": 0,
                    })

                caixas_colocadas += caixas_neste_bloco

            if caixas_colocadas >= quantidade:
                break
        if caixas_colocadas >= quantidade:
            break

    cabe_tudo = caixas_colocadas >= quantidade

    return {
        "success": True,
        "caixas": blocos,
        "caixas_por_camada": caixas_por_camada,
        "pares_por_camada": pares_por_camada,
        "num_camadas": num_camadas,
        "total": caixas_colocadas,
        "total_blocos": len(blocos),
        "cabe_tudo": cabe_tudo,
        "capacidade_max": caixas_por_camada * camadas_max,
        "altura_total": round(num_camadas * par_alt, 2),
        "peso_total": round(caixas_colocadas * peso_caixa, 2),
        "par_dimensions": {
            "sizex": round(bloco_x, 2),
            "sizey": round(bloco_y, 2),
            "sizez": round(par_alt, 2),
        },
    }

