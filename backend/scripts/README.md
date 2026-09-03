# Scripts de diagnóstico

Ferramentas manuais de apoio ao desenvolvimento. **Não são testes automatizados.**
Todos exigem o backend Flask rodando em `localhost:5000`.

| Script | O que faz | Dependências |
|--------|-----------|--------------|
| `check_rnc7.py` | Consulta e imprime as coordenadas de place do modelo RNC7 | stdlib (urllib) |
| `plot_coordinates.py` | Plota as camadas de paletização em plano cartesiano | matplotlib, numpy |

## Como rodar

```bash
# a partir da pasta backend/, com o servidor rodando em outro terminal
python scripts/check_rnc7.py
python scripts/plot_coordinates.py
```

Para os scripts que usam matplotlib/numpy, instale as dependências de dev:

```bash
pip install -r requirements-dev.txt
```

> Os scripts de comunicação com o robô ficam em `backend/robot/`
> (`test_register.py`, `test_position.py`) por dependerem do `hses_client.py`.
