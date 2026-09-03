"""
Diagnostico de comunicacao com o robo Yaskawa YRC1000 via HSES.

Ferramenta manual para validar a comunicacao com o controlador, testando
escrita/leitura de registrador (M) ou de variavel de posicao (P).
Nenhum destes testes move o robo - apenas gravam/leem valores.

Uso:
    # Testar registrador (escreve e le de volta)
    python diagnose.py register --ip 192.168.0.80 --reg 432 --value 123

    # Testar variavel de posicao P (coordenadas mockadas)
    python diagnose.py position --ip 192.168.0.80 --pvar 110 --x 800 --y -300 --z 520

Pre-requisitos:
    - HSES habilitado no YRC1000.
    - PC na mesma rede do controlador.
    - Firewall liberado para UDP na porta 10040.
"""
import argparse

from hses_client import HSESClient

DEFAULT_IP = "192.168.0.80"


def cmd_register(args):
    """Escreve um valor no registrador e le de volta para confirmar."""
    print("=" * 60)
    print("  TESTE DE REGISTRADOR - YASKAWA YRC1000 (HSES/UDP)")
    print("=" * 60)
    print(f"  Controlador : {args.ip}:10040")
    print(f"  Registrador : M{args.reg}")
    print(f"  Valor       : {args.value}")
    print("=" * 60)

    robot = HSESClient(args.ip)

    print(f"\n[1] Escrevendo {args.value} no registrador M{args.reg}...")
    if not robot.write_register(args.reg, args.value):
        print("    FALHOU - veja o codigo de erro acima.")
        return
    print("    OK - escrita confirmada pelo controlador.")

    print(f"\n[2] Lendo registrador M{args.reg} de volta...")
    lido = robot.read_register(args.reg)
    if lido is None:
        print("    FALHOU ao ler.")
        return
    print(f"    Valor lido: {lido}")
    if lido == args.value:
        print("    OK - valor confere! Comunicacao funcionando.")
    else:
        print("    ATENCAO - valor lido difere do escrito.")

    if args.pendant:
        print("\n[3] Mostrando texto na teach pendant...")
        if robot.show_text(f"SoundBox reg{args.reg}={args.value}"):
            print("    OK - verifique o display do robo.")


def cmd_position(args):
    """Escreve coordenadas em uma variavel P e le de volta para confirmar."""
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

    print(f"\n[1] Escrevendo posicao em P{args.pvar}...")
    ok = robot.write_position(
        args.pvar,
        x_mm=args.x, y_mm=args.y, z_mm=args.z,
        tx_deg=args.rx, ty_deg=args.ry, tz_deg=args.rz,
        data_type=args.coord, tool_no=args.tool,
    )
    if not ok:
        print("    FALHOU - veja o codigo de erro acima.")
        return
    print("    OK - escrita confirmada pelo controlador.")

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

    conferem = (
        abs(pos['x_mm'] - args.x) < 0.01 and
        abs(pos['y_mm'] - args.y) < 0.01 and
        abs(pos['z_mm'] - args.z) < 0.01
    )
    if conferem:
        print("\n    OK - coordenadas conferem! Escrita de P funcionando.")
    else:
        print("\n    ATENCAO - valores lidos diferem dos escritos.")


def build_parser():
    parser = argparse.ArgumentParser(description="Diagnostico HSES do YRC1000.")
    sub = parser.add_subparsers(dest="comando", required=True)

    # register
    p_reg = sub.add_parser("register", help="Testa escrita/leitura de registrador (M)")
    p_reg.add_argument("--ip", default=DEFAULT_IP, help=f"IP do controlador (default: {DEFAULT_IP})")
    p_reg.add_argument("--reg", type=int, default=432, help="Numero do registrador (default: 432)")
    p_reg.add_argument("--value", type=int, default=123, help="Valor a escrever 0-65535 (default: 123)")
    p_reg.add_argument("--pendant", action="store_true", help="Tambem mostra texto na teach pendant")
    p_reg.set_defaults(func=cmd_register)

    # position
    p_pos = sub.add_parser("position", help="Testa escrita/leitura de variavel de posicao (P)")
    p_pos.add_argument("--ip", default=DEFAULT_IP, help=f"IP do controlador (default: {DEFAULT_IP})")
    p_pos.add_argument("--pvar", type=int, default=110, help="Numero da variavel P (default: 110)")
    p_pos.add_argument("--x", type=float, default=800.0, help="X em mm (default: 800)")
    p_pos.add_argument("--y", type=float, default=-300.0, help="Y em mm (default: -300)")
    p_pos.add_argument("--z", type=float, default=520.0, help="Z em mm (default: 520)")
    p_pos.add_argument("--rx", type=float, default=180.0, help="Tx em graus (default: 180)")
    p_pos.add_argument("--ry", type=float, default=0.0, help="Ty em graus (default: 0)")
    p_pos.add_argument("--rz", type=float, default=0.0, help="Tz em graus (default: 0)")
    p_pos.add_argument("--coord", type=int, default=17,
                       help="Sistema de coord: 16=base 17=robo 18=usuario (default: 17)")
    p_pos.add_argument("--tool", type=int, default=0, help="Numero da ferramenta (default: 0)")
    p_pos.set_defaults(func=cmd_position)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
