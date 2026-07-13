# SoundBox Pallet Optimizer

Solução web para o problema de **Manufacturing Pallet Loading (MPL)** — otimização do arranjo de caixas em paletes com restrições de estabilidade, peso e resistência.

## Arquitetura

```
project/
├── backend/          # API Python (Flask)
│   ├── app.py        # Servidor Flask + rotas da API
│   ├── models/       # Modelos de dados (Case, Pallet)
│   ├── algorithms/   # Algoritmos de empacotamento
│   ├── utils/        # Utilitários
│   └── requirements.txt
├── frontend/         # Interface Web
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── assets/
└── README.md
```

## Funcionalidades

- Visualização 3D interativa do palete carregado (Three.js)
- Algoritmo DubePacker com verificação de estabilidade e resistência
- Suporte a múltiplas caixas com diferentes dimensões
- Restrições de peso máximo e altura máxima do palete
- Sistema de unidades customizável (cm/kg ou inches/lbs)
- Exportação de coordenadas (CSV)
- Responsivo (desktop e mobile)

## Como Rodar

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Acesso
Abra o navegador em `http://localhost:5000`

## Algoritmo

Baseado no DubePacker (Dube, Kanavathy & Woodview, 2006) com modificações para:
- Verificação de estabilidade (superfície mínima de suporte de 70%)
- Verificação de resistência (quantas caixas cada caixa aguenta em cima)
- Verificação de obstrução física (a caixa pode ser colocada sem remover outras)
- Rotação automática de caixas no plano horizontal

## Referências

- Dube, E., Kanavathy, L. R., & Woodview, P. (2006). Optimizing Three-Dimensional Bin Packing Through Simulation.
- R.Morabito and S.Morales (1998). A simple and effective recursive procedure for the manufacturer's pallet loading problem.
