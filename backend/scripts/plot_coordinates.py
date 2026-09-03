"""
Visualização em plano cartesiano das coordenadas de paletização.
Mostra a vista superior (XY) de cada camada da pilha, com as coordenadas
numéricas de place de cada caixa.

Uso: python scripts/plot_coordinates.py
Requer: matplotlib, numpy, backend Flask rodando em localhost:5000
"""
import json
import urllib.request
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


def api_get(path):
    req = urllib.request.Request(f"http://localhost:5000{path}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def api_post(path, data):
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(f"http://localhost:5000{path}", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    # Buscar modelos
    models = api_get('/api/boxes')
    
    print("Modelos disponíveis:")
    for m in models:
        dim = f"{m.get('sizex','?')}x{m.get('sizey','?')}x{m.get('sizez','?')}" if m['type'] == 'regular' else "L-shape"
        print(f"  [{m['id']}] {m['name']} ({dim})")
    
    choice = input("\nID do modelo (Enter = primeiro): ").strip()
    model = next((m for m in models if str(m['id']) == choice), models[0]) if choice else models[0]
    
    print(f"\nCalculando para: {model['name']}...")
    
    # Calcular
    payload = {
        "pallet": {
            "sizex": model.get("pallet_sizex", 100),
            "sizey": model.get("pallet_sizey", 120),
            "sizez": model.get("pallet_sizez", 200),
            "max_weight": model.get("pallet_max_weight", 1200),
        },
        "cases": [{
            "code": model.get("code", "BOX"),
            "sizex": model.get("sizex", 60),
            "sizey": model.get("sizey", 40),
            "sizez": model.get("sizez", 20),
            "weight": model.get("weight", 5),
            "quantity": model.get("quantity", 10),
            "strength": model.get("strength", 10),
            "pallet_face": model.get("pallet_face", "xy"),
            "interlocking_type": model.get("interlocking_type", "mirror"),
        }],
        "overhang": model.get("overhang", 5),
    }
    
    result = api_post('/api/calculate', payload)
    cases = result['cases']
    pallet = result['pallet']
    
    print(f"Total: {result['total_cases']} caixas | Utilização: {result['volume_utilization']}%")
    
    # === PLOT ===
    # Agrupar caixas por camada (Z)
    camadas = {}
    for c in cases:
        z_key = round(c['z'], 1)
        if z_key not in camadas:
            camadas[z_key] = []
        camadas[z_key].append(c)
    
    camadas_ordenadas = sorted(camadas.keys())
    num_camadas = len(camadas_ordenadas)
    
    # Layout: 1 plot por camada + tabela
    cols = min(num_camadas + 1, 4)
    rows = (num_camadas + 1 + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 5 * rows))
    fig.suptitle(f"Coordenadas de Paletização — {model['name']} ({result['total_cases']} caixas)", fontsize=13)
    
    if rows == 1 and cols == 1:
        axes = np.array([[axes]])
    elif rows == 1:
        axes = axes.reshape(1, -1)
    elif cols == 1:
        axes = axes.reshape(-1, 1)
    
    colors = plt.cm.tab20(np.linspace(0, 1, len(cases)))
    
    # --- Vista de cima de cada camada ---
    for cam_idx, z_val in enumerate(camadas_ordenadas):
        row_idx = cam_idx // cols
        col_idx = cam_idx % cols
        ax = axes[row_idx][col_idx]
        
        cam_cases = camadas[z_val]
        cam_num = cam_idx + 1
        
        ax.set_title(f"Camada {cam_num} (Z={z_val:.1f} cm)", fontsize=10)
        ax.set_xlabel("X (cm)")
        ax.set_ylabel("Y (cm)")
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        
        # Desenhar pallet
        pallet_rect = patches.Rectangle((0, 0), pallet['sizex'], pallet['sizey'],
                                         linewidth=2, edgecolor='brown', facecolor='wheat', alpha=0.3)
        ax.add_patch(pallet_rect)
        
        # Desenhar caixas da camada
        for c in cam_cases:
            i = c['index'] - 1
            rect = patches.Rectangle((c['x'], c['y']), c['sizex'], c['sizey'],
                                      linewidth=1.5, edgecolor='black', facecolor=colors[i % len(colors)], alpha=0.6)
            ax.add_patch(rect)
            # Marcar centro (ponto de place)
            ax.plot(c['place_x'], c['place_y'], 'ro', markersize=6)
            ax.annotate(f"#{c['index']}\n({c['place_x']:.1f}, {c['place_y']:.1f}, {c['place_z']:.1f})",
                         (c['place_x'], c['place_y']), fontsize=7, ha='center', va='bottom')
        
        ax.axhline(y=0, color='gray', linewidth=0.5)
        ax.axvline(x=0, color='gray', linewidth=0.5)
        margin = max(pallet['sizex'], pallet['sizey']) * 0.15
        ax.set_xlim(-margin, pallet['sizex'] + margin)
        ax.set_ylim(-margin, pallet['sizey'] + margin)
    
    # --- Tabela de coordenadas (último subplot) ---
    tab_idx = num_camadas
    row_idx = tab_idx // cols
    col_idx = tab_idx % cols
    
    if row_idx < rows and col_idx < cols:
        ax_tab = axes[row_idx][col_idx]
        ax_tab.axis('off')
        ax_tab.set_title("Coordenadas (cm)", fontsize=10)
        
        table_data = [["#", "place_x", "place_y", "place_z", "rot"]]
        for c in cases:
            table_data.append([
                str(c['index']),
                f"{c['place_x']:.1f}",
                f"{c['place_y']:.1f}",
                f"{c['place_z']:.1f}",
                "90°" if c['rotated'] else "0°"
            ])
        
        table = ax_tab.table(cellText=table_data, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.3)
        
        for j in range(5):
            table[0, j].set_facecolor('#4a90d9')
            table[0, j].set_text_props(color='white', fontweight='bold')
    
    # Esconder subplots vazios
    for idx in range(num_camadas + 1, rows * cols):
        r = idx // cols
        c_idx = idx % cols
        if r < rows and c_idx < cols:
            axes[r][c_idx].axis('off')
    
    plt.tight_layout()
    plt.savefig('coordenadas_place.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("\nImagem salva: coordenadas_place.png")


if __name__ == "__main__":
    main()
