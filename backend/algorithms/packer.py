"""
Algoritmo de empacotamento 3D baseado no DubePacker.

Referência:
    Dube, E., Kanavathy, L. R., & Woodview, P. (2006).
    Optimizing Three-Dimensional Bin Packing Through Simulation.

Modificações:
    - Verificação de estabilidade (superfície mínima de suporte)
    - Verificação de resistência (strength)
    - Verificação de obstrução física
    - Rotação automática no plano horizontal
"""
from collections import deque

from models.case import Case, rotate

# Parâmetros de estabilidade
MIN_STABLE_SURFACE = 0.7  # 70% da superfície deve estar apoiada
MIN_STABLE_CORNERS = 3    # Mínimo de cantos com suporte


def get_position(index, item):
    """Retorna a posição candidata adjacente a um item já posicionado."""
    positions = {
        0: (item.x + item.sizex, item.y, item.z),       # Direita
        1: (item.x, item.y + item.sizey, item.z),       # Trás
        2: (item.x, item.y, item.z + item.sizez),       # Acima
    }
    return positions.get(index)


def check_obstruction(toplace, obstructor, obstruction_risk, possible_inserts, inserts_sum):
    """
    Verifica se a posição de uma caixa é bloqueada por outra já posicionada.
    Também verifica se é fisicamente possível inserir a caixa naquela posição.
    """
    overlap_x = min(obstructor.right, toplace.right) > max(obstructor.left, toplace.left)
    overlap_y = min(obstructor.back, toplace.back) > max(obstructor.front, toplace.front)
    overlap_z = min(obstructor.top, toplace.top) > max(obstructor.bottom, toplace.bottom)

    # Interseção detectada
    if overlap_x and overlap_y and overlap_z:
        return True, inserts_sum

    if not obstruction_risk:
        return False, inserts_sum

    # Verifica obstrução ao longo de X
    if overlap_y and overlap_z:
        if possible_inserts[0] == 1 and obstructor.x < toplace.x:
            possible_inserts[0] = 0
            return False, inserts_sum - 1
        elif possible_inserts[1] == 1 and obstructor.x > toplace.x:
            possible_inserts[1] = 0
            return False, inserts_sum - 1

    # Verifica obstrução ao longo de Y
    if overlap_x and overlap_z:
        if possible_inserts[2] == 1 and obstructor.y < toplace.y:
            possible_inserts[2] = 0
            return False, inserts_sum - 1
        elif possible_inserts[3] == 1 and obstructor.y > toplace.y:
            possible_inserts[3] = 0
            return False, inserts_sum - 1

    # Verifica obstrução ao longo de Z (por cima)
    if overlap_x and overlap_y and obstructor.z > toplace.z:
        possible_inserts[4] = 0
        return False, inserts_sum - 1

    return False, inserts_sum


def fit(current_item, pallet_size, packed, overhang=5.0):
    """
    Verifica se é possível posicionar current_item na posição atual.
    Checa: limites do palete, interseções, estabilidade e resistência.

    :param overhang: Tolerância de saliência permitida para fora do palete (cm) nos eixos X e Y.
    """
    X, Y, Z = pallet_size

    # Verifica limites do palete (com tolerância de overhang nos lados, mas não na altura)
    if current_item.right > X + overhang or current_item.back > Y + overhang or current_item.top > Z:
        return False

    left, right = current_item.left, current_item.right
    front, back = current_item.front, current_item.back

    # Inicializa variáveis de estabilidade
    stable_surface = 0
    stable_corners = [0, 0, 0, 0]
    sum_stables = 0
    stable = False
    item_surface = current_item.sizex * current_item.sizey

    # Verifica risco de obstrução (usa limites expandidos)
    possible_inserts = [1, 1, 1, 1, 1]
    inserts_sum = 5
    obstruct_risk = not (left == 0 or right >= X + overhang or front == 0 or back >= Y + overhang)

    # Cantos que precisam de suporte
    footholds = [
        current_item.position,
        (left, back),
        (right, back),
        (right, front),
    ]

    for packed_item in packed:
        # Verifica interseção e obstrução
        intersection, inserts_sum = check_obstruction(
            current_item, packed_item, obstruct_risk, possible_inserts, inserts_sum
        )
        if intersection or inserts_sum == 0:
            return False

        # Verifica estabilidade
        if not stable and current_item.z == 0:
            stable_surface = item_surface
            stable_corners = [1, 1, 1, 1]
            sum_stables = 4
            stable = True

        elif current_item.z == packed_item.top:
            x1 = min(right, packed_item.right)
            x2 = max(left, packed_item.left)
            y1 = min(back, packed_item.back)
            y2 = max(front, packed_item.front)

            if x1 > x2 and y1 > y2:
                # Verifica resistência
                if packed_item.can_hold == 0:
                    return False

                current_item.can_hold = max(0, min(current_item.strength, packed_item.can_hold - 1))

                if not stable:
                    stable_surface += (x1 - x2) * (y1 - y2)

                    for idx, point in enumerate(footholds):
                        if not stable_corners[idx] and x2 <= point[0] <= x1 and y2 <= point[1] <= y1:
                            stable_corners[idx] = 1
                            sum_stables += 1

                    if (stable_surface / item_surface >= MIN_STABLE_SURFACE or
                            sum_stables >= MIN_STABLE_CORNERS):
                        stable = True

    return stable


def pack_pallet(pallet, cases_input, overhang=5.0):
    """
    Empacota uma lista de caixas em um palete.
    Usa um algoritmo de grid otimizado que testa orientações mistas por camada,
    com centralização e intertravamento 180°.

    :param pallet: Instância de Pallet
    :param cases_input: Lista de dicts com {code, sizex, sizey, sizez, weight, quantity, strength}
    :param overhang: Tolerância de saliência (cm) permitida para fora do palete nos eixos X e Y
    :return: Pallet com as caixas posicionadas
    """
    import math

    X, Y, Z = pallet.size
    comp_efetivo = X + overhang
    larg_efetivo = Y + overhang

    # Para simplificar, usa a primeira caixa como referência (caso homogêneo)
    item = cases_input[0]
    raw_sizex = float(item["sizex"])
    raw_sizey = float(item["sizey"])
    raw_sizez = float(item["sizez"])

    # Tipo de intertravamento
    # 'mirror' = espelho 180° (mesmo layout invertido)
    # 'alternate' = orientação alternada (troca horizontal/vertical entre camadas)
    interlocking_type = item.get("interlocking_type", "mirror")

    # Orientação de paletização: qual face fica no chão
    pallet_face = item.get("pallet_face", "xy")
    print(f"[DEBUG PACKER] raw=({raw_sizex},{raw_sizey},{raw_sizez}), pallet_face={pallet_face}, interlocking={interlocking_type}")

    if pallet_face == "xy":
        sizex, sizey, sizez = raw_sizex, raw_sizey, raw_sizez
    elif pallet_face == "xz":
        sizex, sizey, sizez = raw_sizex, raw_sizez, raw_sizey
    elif pallet_face == "yz":
        sizex, sizey, sizez = raw_sizey, raw_sizez, raw_sizex
    else:
        sizex, sizey, sizez = raw_sizex, raw_sizey, raw_sizez

    print(f"[DEBUG PACKER] floor=({sizex},{sizey}), height={sizez}")
    weight = float(item.get("weight", 0))
    code = item.get("code", "BOX")
    strength = int(item.get("strength", 100))
    quantidade = sum(int(c.get("quantity", 1)) for c in cases_input)

    # Testar todas as estratégias de layout para uma camada
    layouts = []

    # Estratégia 1: Orientação A pura (sizex × sizey)
    nx1 = int(comp_efetivo // sizex)
    ny1 = int(larg_efetivo // sizey)
    layouts.append(("A", nx1, ny1, sizex, sizey))

    # Estratégia 2: Orientação B pura (sizey × sizex)
    nx2 = int(comp_efetivo // sizey)
    ny2 = int(larg_efetivo // sizex)
    layouts.append(("B", nx2, ny2, sizey, sizex))

    # Estratégia 3: Mix - faixas no X com orientações diferentes
    for na in range(0, int(comp_efetivo // sizex) + 1):
        espaco_restante_x = comp_efetivo - na * sizex
        nb = int(espaco_restante_x // sizey)
        if na + nb > 0:
            total_a = na * int(larg_efetivo // sizey)
            total_b = nb * int(larg_efetivo // sizex)
            layouts.append(("MixX", na, nb, total_a + total_b, None))

    # Estratégia 4: Mix - faixas no Y com orientações diferentes
    for na in range(0, int(larg_efetivo // sizey) + 1):
        espaco_restante_y = larg_efetivo - na * sizey
        nb = int(espaco_restante_y // sizex)
        if na + nb > 0:
            total_a = int(comp_efetivo // sizex) * na
            total_b = int(comp_efetivo // sizey) * nb
            layouts.append(("MixY", na, nb, total_a + total_b, None))

    # Encontrar o melhor layout (mais caixas por camada, priorizando mix real para intertravamento)
    melhor_por_camada = 0
    melhor_layout = None

    for layout in layouts:
        if layout[0] in ("A", "B"):
            total = layout[1] * layout[2]
        else:
            total = layout[3]
        if total > melhor_por_camada:
            melhor_por_camada = total
            melhor_layout = layout
        elif total == melhor_por_camada and layout[0].startswith("Mix"):
            # Prioriza mix REAL (ambas faixas > 0) para melhor intertravamento
            na_val = layout[1]
            nb_val = layout[2] if layout[0] == "MixX" else int((larg_efetivo - na_val * sizey) // sizex)
            if na_val > 0 and nb_val > 0:
                melhor_layout = layout

    if melhor_por_camada == 0:
        return pallet

    # Calcular camadas
    camadas_por_altura = int(Z // sizez)
    camadas_por_peso = int(pallet.max_weight // (weight * melhor_por_camada)) if weight > 0 else camadas_por_altura
    camadas_max = min(camadas_por_altura, camadas_por_peso)
    camadas_necessarias = math.ceil(quantidade / melhor_por_camada)
    num_camadas = min(camadas_necessarias, camadas_max)

    # Gerar posições da camada base
    posicoes_camada = []

    if melhor_layout[0] == "A":
        nx, ny = melhor_layout[1], melhor_layout[2]
        for i in range(nx):
            for j in range(ny):
                posicoes_camada.append((i * sizex, j * sizey, sizex, sizey))
    elif melhor_layout[0] == "B":
        nx, ny = melhor_layout[1], melhor_layout[2]
        for i in range(nx):
            for j in range(ny):
                posicoes_camada.append((i * sizey, j * sizex, sizey, sizex))
    elif melhor_layout[0] == "MixX":
        na, nb = melhor_layout[1], melhor_layout[2]
        # Faixas A no eixo X
        for i in range(na):
            ny_a = int(larg_efetivo // sizey)
            for j in range(ny_a):
                posicoes_camada.append((i * sizex, j * sizey, sizex, sizey))
        # Faixas B no eixo X (após as A)
        x_offset = na * sizex
        for i in range(nb):
            ny_b = int(larg_efetivo // sizex)
            for j in range(ny_b):
                posicoes_camada.append((x_offset + i * sizey, j * sizex, sizey, sizex))
    elif melhor_layout[0] == "MixY":
        na, nb = melhor_layout[1], melhor_layout[2]
        # Faixas A no eixo Y (orientação sizex × sizey)
        nx_a = int(comp_efetivo // sizex)
        largura_faixa_a = nx_a * sizex
        for j in range(na):
            for i in range(nx_a):
                posicoes_camada.append((i * sizex, j * sizey, sizex, sizey))
        # Faixas B no eixo Y (orientação sizey × sizex) - centralizada no X
        y_offset = na * sizey
        nx_b = int(comp_efetivo // sizey)
        largura_faixa_b = nx_b * sizey
        # Centralizar faixa B em relação à faixa A
        x_shift_b = (largura_faixa_a - largura_faixa_b) / 2 if largura_faixa_a > largura_faixa_b else 0
        x_shift_a_corr = (largura_faixa_b - largura_faixa_a) / 2 if largura_faixa_b > largura_faixa_a else 0
        for j in range(nb):
            for i in range(nx_b):
                posicoes_camada.append((x_shift_b + i * sizey, y_offset + j * sizex, sizey, sizex))
        # Ajustar faixa A se B é mais larga
        if x_shift_a_corr > 0:
            for k in range(len(posicoes_camada) - nx_b * nb):
                px, py, sx, sy = posicoes_camada[k]
                posicoes_camada[k] = (px + x_shift_a_corr, py, sx, sy)

    # Centralizar (distribuir espaço vazio uniformemente em relação ao pallet real)
    if posicoes_camada:
        max_x_usado = max(px + sx for (px, py, sx, sy) in posicoes_camada)
        max_y_usado = max(py + sy for (px, py, sx, sy) in posicoes_camada)
        # Centraliza o bloco inteiro de caixas no centro do pallet
        offset_x = (X - max_x_usado) / 2
        offset_y = (Y - max_y_usado) / 2
    else:
        offset_x = offset_y = 0

    # Gerar layout alternativo (orientação invertida) para camadas ímpares
    posicoes_camada_alt = []

    if interlocking_type == "alternate":
        # Trocar orientação: sizex↔sizey
        sizex_alt, sizey_alt = sizey, sizex

        # Recalcular o melhor layout com orientações trocadas
        layouts_alt = []
        nx1_alt = int(comp_efetivo // sizex_alt)
        ny1_alt = int(larg_efetivo // sizey_alt)
        layouts_alt.append(("A", nx1_alt, ny1_alt, sizex_alt, sizey_alt))

        nx2_alt = int(comp_efetivo // sizey_alt)
        ny2_alt = int(larg_efetivo // sizex_alt)
        layouts_alt.append(("B", nx2_alt, ny2_alt, sizey_alt, sizex_alt))

        # Escolher o melhor layout alternativo
        melhor_alt = max(layouts_alt, key=lambda l: l[1] * l[2])
        nx_alt, ny_alt = melhor_alt[1], melhor_alt[2]
        sx_alt, sy_alt = melhor_alt[3], melhor_alt[4]

        if nx_alt * ny_alt > 0:
            for i in range(nx_alt):
                for j in range(ny_alt):
                    posicoes_camada_alt.append((i * sx_alt, j * sy_alt, sx_alt, sy_alt))

    # Centralizar layout alternativo (ou usar espelho como fallback)
    if posicoes_camada_alt:
        max_x_alt = max(px + sx for (px, py, sx, sy) in posicoes_camada_alt)
        max_y_alt = max(py + sy for (px, py, sx, sy) in posicoes_camada_alt)
        offset_x_alt = (X - max_x_alt) / 2
        offset_y_alt = (Y - max_y_alt) / 2
    else:
        # Modo espelho: usa o mesmo layout
        posicoes_camada_alt = posicoes_camada
        max_x_alt = max_x_usado
        max_y_alt = max_y_usado
        offset_x_alt = offset_x
        offset_y_alt = offset_y

    # Gerar todas as caixas posicionadas
    packed = deque()
    total_weight = 0
    caixas_colocadas = 0

    for camada in range(num_camadas):
        z = camada * sizez

        if camada % 2 == 0:
            # Camada par: layout principal
            layout_atual = posicoes_camada
            off_x = offset_x
            off_y = offset_y
        else:
            if interlocking_type == "alternate":
                # Camada ímpar: layout com orientação trocada
                layout_atual = posicoes_camada_alt
                off_x = offset_x_alt
                off_y = offset_y_alt
            else:
                # Camada ímpar: espelho 180° do layout principal
                layout_atual = posicoes_camada
                off_x = offset_x
                off_y = offset_y

        for idx_pos, (px, py, sx, sy) in enumerate(layout_atual):
            if caixas_colocadas >= quantidade:
                break

            if camada % 2 == 1 and interlocking_type == "mirror":
                # Espelhar 180°
                final_x = (max_x_usado - px - sx) + offset_x
                final_y = (max_y_usado - py - sy) + offset_y
            else:
                final_x = px + off_x
                final_y = py + off_y

            case = Case(
                code=code,
                sizex=sx,
                sizey=sy,
                sizez=sizez,
                weight=weight,
                strength=strength,
            )
            case.set_position((final_x, final_y, z))
            case.rotated = (sx != sizex)
            packed.append(case)
            total_weight += weight
            caixas_colocadas += 1

        if caixas_colocadas >= quantidade:
            break

    pallet.cases = packed
    pallet.weight = total_weight
    pallet.volume = sum(c.volume for c in packed)

    return pallet
