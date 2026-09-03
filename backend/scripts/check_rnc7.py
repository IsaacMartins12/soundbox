"""
Script de diagnostico: consulta as coordenadas de place do modelo RNC7.

Nao e um teste automatizado (pytest) - e uma ferramenta manual.
Roda com: python scripts/check_rnc7.py
Requer: backend Flask rodando em localhost:5000 (usa urllib, sem dependencias).
"""
import json
import urllib.request
import urllib.error


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

# Buscar modelo RNC7 do banco
models = api_get('/api/boxes')
rnc7 = next(m for m in models if 'RNC7' in m['name'])

print("=" * 60)
print(f"  MODELO: {rnc7['name']}")
print(f"  Dimensões: {rnc7['sizex']} x {rnc7['sizey']} x {rnc7['sizez']} cm")
print(f"  Quantidade: {rnc7['quantity']}")
print(f"  Overhang: {rnc7['overhang']} cm")
print(f"  Intertravamento: {rnc7.get('interlocking_type', 'mirror')}")
print(f"  Face no chão: {rnc7.get('pallet_face', 'xy')}")
print("=" * 60)

# Calcular paletização
payload = {
    "pallet": {
        "sizex": rnc7.get("pallet_sizex", 100),
        "sizey": rnc7.get("pallet_sizey", 120),
        "sizez": rnc7.get("pallet_sizez", 200),
        "max_weight": rnc7.get("pallet_max_weight", 1200),
    },
    "cases": [{
        "code": rnc7.get("code", "RNC7"),
        "sizex": rnc7["sizex"],
        "sizey": rnc7["sizey"],
        "sizez": rnc7["sizez"],
        "weight": rnc7.get("weight", 10),
        "quantity": rnc7.get("quantity", 12),
        "strength": rnc7.get("strength", 10),
        "pallet_face": rnc7.get("pallet_face", "xy"),
        "interlocking_type": rnc7.get("interlocking_type", "mirror"),
    }],
    "overhang": rnc7.get("overhang", 20),
}

resp = api_post('/api/calculate', payload)
result = resp

print(f"\n  Total de caixas: {result['total_cases']}")
print(f"  Utilização volume: {result['volume_utilization']}%")
print(f"  Peso total: {result['total_weight']} kg")
print()

# Mostrar coordenadas de place (o que vai pro robô)
print("-" * 60)
print(f"  {'#':<4} {'place_x':>8} {'place_y':>8} {'place_z':>8} {'rotated':>8}")
print("-" * 60)

for case in result['cases']:
    print(f"  {case['index']:<4} {case['place_x']:>8.1f} {case['place_y']:>8.1f} {case['place_z']:>8.1f} {str(case['rotated']):>8}")

print("-" * 60)
print()
print("  Referencial: (0,0,0) = canto do pallet")
print("  Unidade: cm")
print("  place_x, place_y = centro da face superior")
print("  place_z = altura do topo da caixa")
print()

# Exportar JSON limpo (só as coordenadas de place)
place_coords = [{
    "index": c["index"],
    "place_x": c["place_x"],
    "place_y": c["place_y"],
    "place_z": c["place_z"],
    "rotated": c["rotated"],
} for c in result["cases"]]

with open("rnc7_coordinates.json", "w") as f:
    json.dump({
        "model": rnc7["name"],
        "pallet_size": {"x": 100, "y": 120},
        "unit": "cm",
        "reference": "canto do pallet (0,0,0)",
        "description": "Centro da face superior de cada caixa",
        "coordinates": place_coords,
    }, f, indent=2)

print("  Arquivo salvo: rnc7_coordinates.json")
