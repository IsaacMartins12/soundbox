"""
Teste de escrita de VARIAVEL DE POSICAO (P) no YRC1000 via HSES.

Escreve coordenadas X, Y, Z mockadas diretamente na variavel P120 e le de
volta para confirmar. Este teste NAO move o robo - apenas grava a posicao na
variavel. O movimento so acontece quando um job faz MOVL/MOVJ P120.

Uso:
    python test_position.py --ip 192.168.0.80
    python test_position.py --ip 192.168.0.80 --pvar 120 --x 800 --y -300 --z 520

Unidades: milimetros (o cliente converte para micrometros internamente).
Sistema de coordenadas padrao: robot (17). Pode trocar com --coord.

Pre-requisitos:
    - HSES habilitado no YRC1000 (ja validado no teste de registrador).
    - PC na mesma rede do controlador (192.168.0.80).
"""
import argparse

from hses_client import HSESClient


def main():
    parser = argparse.ArgumentParser(description="Teste de escrita de variavel P (YRC1000).")
    parser.add_argument("--ip", default="192.168.0.80", help="IP do controlador (default: 192.168.0.80)")
    parser.add_argument("--pvar", type=int, default=120, help="Numero da variavel P (default: 120)")
    # Coordenadas mockadas (mm)
    parser.add_argument("--x", type=float, default=800.0, help="X em mm (default: 800)")
    parser.add_argument("--y", type=float, default=-300.0, help="Y em mm (default: -300)")
    parser.add_argument("--z", type=float, default=520.0, help="Z em mm (default: 520)")
    parser.add_argument("--rx", type=float, default=180.0, help="Tx em graus (default: 180)")
    parser.add_argument("--ry", type=float, default=0.0, help="Ty em graus (default: 0)")
    parser.add_argument("--rz", type=float, default=0.0, help="Tz em graus (default: 0)")
    parser.add_argument("--coord", type=int, default=17,
                        help="Sistema de coord: 16=base 17=robo 18=usuario (default: 17)")
    parser.add_argument("--tool", type=int, default=0, help="Numero da ferramenta (default: 0)")
    args = parser.parse_args()

    print("=" * 60)
    print("  TESTE DE VARIAVEL DE POSICAO (P) - YASKAWA YRC1000")
    print("=" * 60)
    print(f"  Controlador : {args.ip}:10040")
    print(f"  Variavel    : P{args.pvar}")
    print(f"  Coordenadas : X={args.x}  Y={args.y}  Z={args.z} (mm)")
    print(f"  Orientacao  : Rx={args.rx}  Ry={args.ry}  Rz={args.rz} (graus)")
    print(f"  Sistema     : {args.coord} (16=base 17=robo 18=usuario)")
    print(f"  Ferramenta  : {args.tool}")
    print("=" * 60)

    robot = HSESClient(args.ip)

    # 1. Escrever a posicao mockada
    print(f"\n[1] Escrevendo posicao em P{args.pvar}...")
    ok = robot.write_position(
        args.pvar,
        x_mm=args.x, y_mm=args.y, z_mm=args.z,
        tx_deg=args.rx, ty_deg=args.ry, tz_deg=args.rz,
        data_type=args.coord, tool_no=args.tool,
    )
    if ok:
        print("    OK - escrita confirmada pelo controlador.")
    else:
        print("    FALHOU - veja o codigo de erro acima.")
        return

    # 2. Ler de volta
    print(f"\n[2] Lendo P{args.pvar} de volta...")
    pos = robot.read_position(args.pvar)
    if pos is None:
        print("    FALHOU ao ler.")
        return

    print(f"    Data type : {pos['data_type']}")
    print(f"    Tool      : {pos['tool_no']}")
    print(f"    X = {pos['x_mm']:.3f} mm")
    print(f"    Y = {pos['y_mm']:.3f} mm")
    print(f"    Z = {pos['z_mm']:.3f} mm")
    print(f"    Rx = {pos['tx_deg']:.4f}  Ry = {pos['ty_deg']:.4f}  Rz = {pos['tz_deg']:.4f} (graus)")

    # 3. Conferir
    conferem = (
        abs(pos['x_mm'] - args.x) < 0.01 and
        abs(pos['y_mm'] - args.y) < 0.01 and
        abs(pos['z_mm'] - args.z) < 0.01
    )
    if conferem:
        print("\n    OK - coordenadas conferem! Escrita de P funcionando.")
    else:
        print("\n    ATENCAO - valores lidos diferem dos escritos.")


if __name__ == "__main__":
    main()
