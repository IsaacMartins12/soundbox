# SoundBox Pallet Optimizer

Solução web para otimização do arranjo de caixas em paletes (Pallet Loading),
com restrições de estabilidade, peso e resistência. Calcula o melhor
empilhamento, mostra o resultado em 3D e envia as coordenadas de cada caixa
para um robô **Yaskawa YRC1000** executar a paletização.

## Arquitetura

```
project/
├── backend/                  # API Python (Flask)
│   ├── app.py                # Cria o app, serve o frontend e registra os blueprints
│   ├── database.py           # SQLite (modelos de caixa e pallet)
│   ├── models/               # Modelos de dados (Case, Pallet)
│   ├── algorithms/           # Algoritmos de empacotamento (retangular e formato L)
│   ├── routes/               # Rotas da API organizadas em blueprints por domínio
│   ├── robot/                # Comunicação com o robô Yaskawa (HSES)
│   ├── scripts/              # Ferramentas de diagnóstico (não são testes)
│   ├── requirements.txt      # Dependências de produção
│   └── requirements-dev.txt  # Dependências de desenvolvimento
├── frontend/                 # Interface Web (HTML + Three.js)
│   ├── index.html
│   ├── css/
│   └── js/
└── README.md
```

## Funcionalidades

- Cálculo de empacotamento para caixas retangulares e em formato L
- Visualização 3D interativa do palete carregado (Three.js)
- Cadastro de modelos de caixa e pallet (SQLite)
- Restrições de peso máximo, resistência e overhang (saliência)
- Exportação de coordenadas (CSV)
- **Envio das coordenadas de cada caixa para o robô Yaskawa YRC1000**

## Como Rodar

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```

Abra o navegador em `http://localhost:5000` (o Flask serve o frontend na
mesma porta da API).

### Com Docker (recomendado para rodar em outra máquina)

Basta clonar o repositório e subir com Docker Compose — não precisa instalar
Python nem dependências na máquina:

```bash
git clone https://github.com/IsaacMartins12/soundbox.git
cd soundbox/project
docker compose up --build
```

Acesse `http://localhost:5000`. O banco SQLite é persistido em um volume
(`soundbox-data`), então os dados sobrevivem entre reinícios do container.

Para ajustar o IP do robô ou outras configurações, edite as variáveis em
`docker-compose.yml` (ex.: `ROBOT_IP`) ou o arquivo `backend/config.py`.

Para parar: `docker compose down`.

### Configuração

Os valores importantes (IP do robô, porta, faixa de variáveis P, orientação da
garra, etc.) ficam centralizados em `backend/config.py`. Basta editar lá para
mudar o comportamento, sem mexer no resto do código. Cada valor também pode ser
sobrescrito por variável de ambiente:

| Variável             | Default        | Descrição                                              |
|----------------------|----------------|--------------------------------------------------------|
| `FLASK_DEBUG`        | desligado      | `1`/`true` liga o modo debug do Flask                  |
| `HOST`               | `0.0.0.0`      | Host de bind                                           |
| `PORT`               | `5000`         | Porta do servidor                                      |
| `CORS_ORIGINS`       | (vazio)        | Origens permitidas (separadas por vírgula). Sem valor, CORS não é habilitado |
| `ROBOT_IP`           | `192.168.0.80` | IP do controlador YRC1000                              |
| `ROBOT_PORT`         | `10040`        | Porta HSES (robot control)                             |
| `ROBOT_TIMEOUT`      | `2.0`          | Timeout de resposta do robô (s)                        |
| `ROBOT_START_PVAR`   | `110`          | Primeira variável P usada no envio                     |
| `ROBOT_MAX_PVAR`     | `127`          | Última variável P disponível                           |
| `ROBOT_COORD_SYSTEM` | `17`           | Sistema de coordenadas (16=base 17=robô 18=usuário)    |
| `ROBOT_TOOL_NO`      | `0`            | Número da ferramenta                                   |
| `ROBOT_RX/RY/RZ`     | `180/0/0`      | Orientação padrão da garra (graus)                     |

## Fluxo de uso

1. O operador informa as dimensões do pallet e das caixas (ou carrega um modelo salvo).
2. Clica em **Calcular Empacotamento** — o backend calcula o arranjo e mostra o 3D.
3. Clica em **Enviar ao Robô** — as coordenadas de place de cada caixa são
   escritas nas variáveis de posição do robô (P110, P111, ...), prontas para o
   job do robô consumir.

As coordenadas de place são o **centro da face superior** de cada caixa, com
referencial no canto do pallet. O cálculo trabalha em centímetros; o envio
converte para milímetros (unidade do robô).

## Comunicação com o robô (Yaskawa YRC1000)

A comunicação usa o protocolo **HSES (High-Speed Ethernet Server)** nativo do
YRC1000, por socket UDP na porta 10040. Não requer SDK pago nem escrita de job
de recepção no robô para gravar variáveis.

- `robot/hses_client.py` — cliente HSES (escrita/leitura de registrador M e de
  variável de posição P, e mensagem na teach pendant).
- `robot/pallet_sender.py` — converte as coordenadas e escreve cada caixa em uma
  variável P sequencial (início configurável, default P110).
- Rota da API: `POST /api/send-to-robot`.

### Diagnóstico da comunicação

O script `robot/diagnose.py` valida a comunicação com o controlador sem mover o
robô (apenas grava/lê valores):

```bash
cd backend/robot

# Testar registrador (escreve e lê de volta)
python diagnose.py register --ip 192.168.0.80 --reg 432 --value 123

# Testar variável de posição P (coordenadas mockadas)
python diagnose.py position --ip 192.168.0.80 --pvar 110 --x 800 --y -300 --z 520
```

O formato dos pacotes HSES foi validado contra o manual oficial do YRC1000
(documento 178942-1CD).

## Ferramentas de diagnóstico

Em `backend/scripts/` há ferramentas manuais de apoio (exigem o backend rodando):

- `check_rnc7.py` — consulta as coordenadas de place do modelo RNC7.
- `plot_coordinates.py` — plota as camadas de paletização em plano cartesiano
  (requer `matplotlib`/`numpy`, instaláveis via `requirements-dev.txt`).

## Testes

Testes automatizados cobrem o núcleo do sistema (geometria da caixa, algoritmo
de empacotamento e conversão de coordenadas para o robô). Não dependem do robô
nem da rede.

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

## Algoritmo

O empacotamento usa uma estratégia de grid que testa múltiplos arranjos
(orientações puras e mistas) e escolhe o de maior aproveitamento, com:

- Centralização das caixas no pallet
- Intertravamento entre camadas para estabilidade (espelho ou alternância)
- Verificação de resistência (quantas caixas cada modelo aguenta empilhadas)
- Overhang configurável (saliência simétrica além da borda do pallet)

Caixas em formato L têm tratamento próprio (`algorithms/packer_L.py`): duas
caixas complementares (uma girada 180°) se encaixam formando um retângulo.

## Referências

- Dube, E., Kanavathy, L. R., & Woodview, P. (2006). Optimizing Three-Dimensional Bin Packing Through Simulation.
- Morabito, R., & Morales, S. (1998). A simple and effective recursive procedure for the manufacturer's pallet loading problem.
