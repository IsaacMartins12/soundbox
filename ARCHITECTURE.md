# Arquitetura do Sistema — SoundBox Pallet Optimizer

Guia completo da estrutura, lógica e pontos de manutenção do sistema.

---

## Estrutura de Arquivos

```
project/
├── backend/
│   ├── app.py                        # API Flask (endpoints REST)
│   ├── database.py                   # Banco SQLite (CRUD modelos)
│   ├── requirements.txt              # Dependências Python
│   ├── soundbox.db                   # Banco de dados (gerado automaticamente)
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── packer.py                 # Algoritmo principal (caixas retangulares)
│   │   ├── packer_L.py              # Algoritmo para caixas formato L
│   │   └── trajectory_generator.py   # Gerador de coordenadas para o robô
│   └── models/
│       ├── __init__.py
│       ├── case.py                   # Classe Case (caixa individual)
│       └── pallet.py                 # Classe Pallet
├── frontend/
│   ├── index.html                    # Interface web principal
│   ├── css/
│   │   └── styles.css                # Estilos visuais
│   └── js/
│       ├── app.js                    # Lógica do frontend (formulários, API calls, modelos)
│       └── visualization.js          # Renderização 3D com Three.js
└── README.md
```

---

## Fluxo de Dados

```
[Frontend HTML] → (JSON) → [Flask API] → [Algoritmo Packer] → (resultado) → [Frontend 3D]
                                ↕
                        [SQLite Database]
```

1. O usuário seleciona um modelo de caixa no frontend
2. O frontend envia as dimensões via POST para `/api/calculate`
3. O backend executa o algoritmo de paletização
4. O resultado (posições XYZ de cada caixa) retorna ao frontend
5. O Three.js renderiza as caixas em 3D

---

## Backend — Detalhamento

### `backend/app.py` — API REST

Arquivo principal do servidor. Define todos os endpoints.

#### Endpoints:

| Rota | Método | Função | Descrição |
|------|--------|--------|-----------|
| `/` | GET | `index()` | Serve o frontend |
| `/api/calculate` | POST | `calculate()` | Calcula paletização retangular |
| `/api/calculate-l` | POST | `calculate_l()` | Calcula paletização formato L |
| `/api/boxes` | GET | `list_boxes()` | Lista modelos do banco |
| `/api/boxes` | POST | `add_box()` | Cadastra novo modelo |
| `/api/boxes/<id>` | PUT | `edit_box()` | Atualiza modelo existente |
| `/api/boxes/<id>` | DELETE | `remove_box()` | Remove modelo |
| `/api/trajectory` | POST | `get_trajectory()` | Gera waypoints para robô (JSON) |
| `/api/trajectory/csv` | POST | `get_trajectory_csv()` | Exporta trajetória (CSV) |
| `/api/export-csv` | POST | `export_csv()` | Exporta coordenadas das caixas |

#### Payload do `/api/calculate`:
```json
{
    "pallet": {"sizex": 100, "sizey": 120, "sizez": 200, "max_weight": 1200},
    "cases": [{
        "code": "CL87",
        "sizex": 91.9,
        "sizey": 45.3,
        "sizez": 52.0,
        "weight": 10,
        "quantity": 9,
        "strength": 10,
        "pallet_face": "xy",
        "interlocking_type": "alternate"
    }],
    "overhang": 18
}
```

#### Resposta:
```json
{
    "pallet": {"sizex": 100, "sizey": 120, "sizez": 200},
    "cases": [
        {"code": "CL87", "x": 4.3, "y": 7.4, "z": 0, "sizex": 91.9, "sizey": 45.3, "sizez": 52, "rotated": false},
        ...
    ],
    "total_cases": 9,
    "volume_utilization": 81.18,
    "total_weight": 90,
    "weight_utilization": 7.5
}
```

---

### `backend/algorithms/packer.py` — Algoritmo Principal

Este é o arquivo mais crítico do sistema. Contém toda a lógica de posicionamento de caixas retangulares.

#### Fluxo do Algoritmo:

```
1. Recebe dimensões (sizex, sizey, sizez)
2. Aplica pallet_face (troca eixos se caixa "em pé")
3. Gera 4 estratégias de layout por camada
4. Seleciona a melhor (mais caixas, prioriza mix)
5. Centraliza no pallet (overhang simétrico)
6. Aplica intertravamento entre camadas
7. Retorna posições de todas as caixas
```

#### Etapa 2 — Orientação de Paletização (`pallet_face`):

```python
if pallet_face == "xy":
    sizex, sizey, sizez = raw_sizex, raw_sizey, raw_sizez  # Deitada (padrão)
elif pallet_face == "xz":
    sizex, sizey, sizez = raw_sizex, raw_sizez, raw_sizey  # Em pé (Y vira altura)
elif pallet_face == "yz":
    sizex, sizey, sizez = raw_sizey, raw_sizez, raw_sizex  # Em pé (X vira altura)
```

**Onde:** Linhas ~175-190

**Quando mexer:** Quando uma caixa precisa ser paletizada em orientação diferente da cadastrada.

#### Etapa 3 — Estratégias de Camada:

O algoritmo testa 4 famílias de arranjo:

| Estratégia | Descrição | Exemplo |
|------------|-----------|---------|
| A pura | Todas na mesma orientação (sizex×sizey) | 3 caixas iguais |
| B pura | Todas rotacionadas 90° (sizey×sizex) | 3 caixas giradas |
| MixX | Faixas no eixo X com orientações diferentes | 2 normais + 1 girada |
| MixY | Faixas no eixo Y com orientações diferentes | 2 normais + 1 girada |

**Onde:** Linhas ~195-310

**Quando mexer:** Para adicionar uma nova estratégia (ex: arranjo em espiral, offset por camada).

#### Etapa 4 — Seleção do Melhor Layout:

```python
# Prioriza: 1° mais caixas, 2° layout misto (se empata)
if total > melhor_por_camada:
    melhor_layout = layout
elif total == melhor_por_camada and layout é mix real (na>0 e nb>0):
    melhor_layout = layout  # Mix tem melhor intertravamento
```

**Onde:** Linhas ~215-235

**Quando mexer:** Para mudar o critério de seleção (ex: priorizar menor overhang).

#### Etapa 5 — Centralização:

```python
offset_x = (X - max_x_usado) / 2  # Distribui overhang igualmente
offset_y = (Y - max_y_usado) / 2
```

**Onde:** Linhas ~310-320

**Quando mexer:** Se o pallet estiver deslocado ou se quiser alinhamento diferente.

#### Etapa 6 — Intertravamento:

```python
if interlocking_type == "alternate":
    # Camadas ímpares: orientação trocada (horizontal↔vertical)
    layout_atual = posicoes_camada_alt
elif interlocking_type == "mirror":
    # Camadas ímpares: mesmo layout espelhado 180°
    final_x = (max_x_usado - px - sx) + offset_x
    final_y = (max_y_usado - py - sy) + offset_y
```

**Onde:** Linhas ~325-395

**Quando mexer:** Para adicionar novo tipo de intertravamento (ex: rotação 90° por camada).

---

### `backend/algorithms/packer_L.py` — Caixas Formato L

#### Princípio:
Duas caixas L encaixadas (uma rotacionada 180°) formam um retângulo.
O algoritmo trata **pares** como retângulos e paletiza normalmente.

#### Dimensões do par:

| Orientação | Face no chão | Altura |
|------------|-------------|--------|
| `vertical` (em pé) | comp_total × largura | alt_vertical + alt_perpendicular |
| `horizontal` (deitada) | comp_total × (alt_v + alt_p) | largura |

#### Decomposição visual:
Cada par é decomposto em 4 sub-blocos para visualização:
- Base caixa 1 (embaixo)
- Braço caixa 1 (lado esquerdo)
- Braço caixa 2 (lado direito, invertida)
- Base caixa 2 (em cima)

**Onde mexer:**
- Dimensões do par: linhas ~45-58
- Decomposição visual: linhas ~135-260
- Comprimento do braço: usa o campo `comp_braco` do banco

---

### `backend/database.py` — Banco de Dados

#### Tabela `box_models`:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | INTEGER | ID automático |
| name | TEXT | Nome do modelo (ex: "CL87") |
| code | TEXT | Código curto |
| type | TEXT | "regular" ou "l-shape" |
| sizex, sizey, sizez | REAL | Dimensões em cm |
| weight | REAL | Peso em kg |
| strength | INTEGER | Resistência ao empilhamento |
| quantity | INTEGER | Quantidade padrão por pallet |
| pallet_face | TEXT | "xy", "xz" ou "yz" |
| interlocking_type | TEXT | "mirror" ou "alternate" |
| overhang | REAL | Saliência permitida (cm) |
| pallet_sizex/y/z | REAL | Dimensões do pallet (cm) |
| pallet_max_weight | REAL | Peso máximo do pallet (kg) |
| comp_total, largura, alt_vertical, alt_perpendicular, comp_braco | REAL | Campos L |
| l_orientation | TEXT | "vertical" ou "horizontal" |
| notes | TEXT | Observações livres |

#### Migrações:
O `init_db()` usa `ALTER TABLE ... ADD COLUMN` com try/except para adicionar campos novos sem recriar o banco.

**Onde mexer:** Para adicionar campo novo, editar `init_db()`, `create_box()`, `update_box()` e o frontend.

---

### `backend/algorithms/trajectory_generator.py` — Coordenadas para o Robô

Gera sequência de waypoints (pontos no espaço) para cada caixa:

```
HOME → PICK_APPROACH → PICK (gripper close) → PICK_LIFT → PLACE_APPROACH → PLACE (gripper open) → PLACE_RETREAT → HOME
```

Cada waypoint contém: `x, y, z` (mm), `rx, ry, rz` (graus), `speed` (%), `motion` (JOINT/LINEAR), `gripper` (CLOSE/OPEN).

**Onde mexer:**
- Posição da esteira: `PICK_POSITION`
- Posição do pallet: `PALLET_OFFSET`
- Alturas de segurança: `APPROACH_HEIGHT`, `SAFE_HEIGHT`
- Velocidades: `SPEED_FAST`, `SPEED_MEDIUM`, `SPEED_SLOW`

---

## Frontend — Detalhamento

### `frontend/index.html`

Estrutura da interface:
1. Seção "Modelos de Caixas" (dropdown + botões Carregar/Gerenciar)
2. Formulário de configuração (pallet, caixa, tipo L)
3. Botão "Calcular Empacotamento"
4. Resultados (stats + visualização 3D)

### `frontend/js/app.js`

| Função | O que faz |
|--------|-----------|
| `loadBoxModel()` | Carrega modelo do banco → preenche formulário |
| `calculate()` | Chama API → exibe resultados |
| `calculateRegular()` | POST `/api/calculate` |
| `calculateLShape()` | POST `/api/calculate-l` |
| `saveBoxModel()` | Salva modelo no banco |
| `setupBoxTypeToggle()` | Alterna entre retangular/L |
| `buildPayload()` | Monta JSON para enviar à API |

### `frontend/js/visualization.js`

| Função | O que faz |
|--------|-----------|
| `drawResult(data)` | Renderiza todas as caixas em 3D |
| `drawLJointLines(box)` | Desenha contorno verde do L |
| `resetCamera()` | Posiciona câmera para ver o pallet |
| `BOX_COLORS` | Array de cores para diferenciar tipos |

---

## Como Executar

```bash
cd project/backend
pip install flask flask-cors
python app.py
# Acesse http://localhost:5000
```

---

## Cenários de Manutenção

| Preciso... | Arquivo | Função/Seção |
|------------|---------|--------------|
| Cadastrar novo modelo | Frontend ou SQLite direto | `loadBoxModel` / tabela `box_models` |
| Mudar orientação de caixa | Banco: campo `pallet_face` | "xy"/"xz"/"yz" |
| Ajustar overhang | Banco: campo `overhang` | Valor em cm |
| Trocar intertravamento | Banco: campo `interlocking_type` | "mirror"/"alternate" |
| Mudar como caixas são posicionadas | `algorithms/packer.py` | Etapas 3-6 |
| Ajustar visual 3D | `js/visualization.js` | `drawResult()` |
| Mudar posição da esteira/pallet pro robô | `algorithms/trajectory_generator.py` | Constantes no topo |
| Exportar coordenadas | API `/api/trajectory/csv` | POST com payload |
| Adicionar campo novo no modelo | `database.py` + `app.py` + `app.js` + `index.html` | CRUD completo |
| Debug do algoritmo | `packer.py` | Prints nas etapas |

---

## Limites e Restrições Conhecidas

1. **Caixas homogêneas:** O sistema otimiza para um único tipo de caixa por pallet (não mistura tipos)
2. **Altura:** O algoritmo assume que todas as caixas da mesma camada têm a mesma altura
3. **Overhang simétrico:** A saliência é distribuída igualmente para ambos os lados
4. **Intertravamento fixo:** Cada modelo tem um tipo fixo (não alterna estratégias por camada)
5. **Peso:** Verificação de peso é por camada total, não por caixa individual
6. **Formato L:** Sempre emparelha (quantidade ímpar = última caixa sozinha desenhada como L)
