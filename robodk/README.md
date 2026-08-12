# SoundBox → RoboDK Integration

Simulação realista do Yaskawa GP88 paletizando caixas usando o RoboDK.

## Pré-requisitos

1. **RoboDK** instalado: https://robodk.com/download
2. **Python packages:**
   ```bash
   pip install robodk requests
   ```
3. **Backend Flask rodando:**
   ```bash
   cd project/backend
   python app.py
   ```

## Setup no RoboDK

1. Abra o RoboDK
2. Vá em **File → Open Online Library**
3. Pesquise **"Motoman GP88"** ou **"Yaskawa GP88"**
4. Download e adicione à cena
5. Posicione o robô na origem

## Como rodar

```bash
cd project/robodk
python palletize_robodk.py
```

O script vai:
1. Conectar ao RoboDK (que deve estar aberto)
2. Buscar as coordenadas calculadas do backend SoundBox
3. Mostrar os modelos de caixa disponíveis
4. Executar a simulação de pick-and-place no RoboDK

## Configurações

No início do script `palletize_robodk.py`, ajuste:

- `PICK_POSITION`: posição da esteira onde o robô pega as caixas
- `PALLET_OFFSET_*`: onde o pallet está em relação ao robô
- `SPEED_*`: velocidades de movimentação
- `APPROACH_HEIGHT`: altura de segurança acima dos pontos

## Output

Após a simulação, o RoboDK pode gerar:
- Programa **INFORM** (linguagem nativa Yaskawa) para upload no controlador real
- Simulação em vídeo
- Análise de tempo de ciclo
- Verificação de alcance e singularidades
