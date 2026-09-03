"""
Funcoes auxiliares compartilhadas entre as rotas.

Concentra a validacao de pallet e caixas usada pelos endpoints de calculo.
"""


class ValidationError(Exception):
    """Erro de validacao de entrada. Carrega a mensagem para o cliente."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def parse_pallet(pallet_data, default_max_weight="inf"):
    """Valida e converte as dimensoes do pallet.

    :return: (pallet_size tuple, max_weight float)
    :raises ValidationError: se as dimensoes forem invalidas
    """
    if not pallet_data:
        raise ValidationError("Campo 'pallet' é obrigatório")
    try:
        pallet_size = (
            float(pallet_data["sizex"]),
            float(pallet_data["sizey"]),
            float(pallet_data["sizez"]),
        )
        max_weight = float(pallet_data.get("max_weight") or default_max_weight)
    except (KeyError, ValueError, TypeError) as e:
        raise ValidationError(f"Dimensões do palete inválidas: {str(e)}")
    return pallet_size, max_weight


def parse_cases(cases_data):
    """Valida e normaliza a lista de caixas retangulares.

    :return: lista de dicts de caixas validadas
    :raises ValidationError: se alguma caixa for invalida
    """
    if not cases_data:
        raise ValidationError("Campo 'cases' é obrigatório")

    validated = []
    for i, case in enumerate(cases_data):
        try:
            validated.append({
                "code": case.get("code", f"BOX-{i+1}"),
                "sizex": float(case["sizex"]),
                "sizey": float(case["sizey"]),
                "sizez": float(case["sizez"]),
                "weight": float(case.get("weight", 0)),
                "quantity": int(case.get("quantity", 1)),
                "strength": int(case.get("strength", 100)),
                "pallet_face": case.get("pallet_face", "xy"),
                "interlocking_type": case.get("interlocking_type", "mirror"),
            })
        except (KeyError, ValueError, TypeError) as e:
            raise ValidationError(f"Caixa {i+1} inválida: {str(e)}")
    return validated
