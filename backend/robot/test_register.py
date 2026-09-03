"""
Teste de escrita/leitura de registrador no YRC1000 via HSES (socket puro).

Uso:
    python test_register.py --ip 192.168.1.31 --reg 0 --value 123

O que faz:
    1. Escreve `value` no registrador `reg`.
    2. Lê o registrador de volta para confirmar.
    3. (Opcional) mostra um texto na teach pendant.

Pre-requisitos no controlador YRC1000:
    - HSES habilitado (padrao no YRC1000).
    - PC na mesma rede do controlador.
    - Firewall liberado para UDP na porta 10040.
"""
import argparse

from hses_client import HSESClient


def main():
    parser = argparse.ArgumentParser(description="Teste de registrador HSES (YRC1000).")
    parser.add_argument("--ip", required=True, help="IP do controlador YRC1000")
    parser.add_argument("--reg", type=int, default=0, help="Numero do registrador (default: 0)")
    parser.add_argument("--value", type=int, default=123, help="Valor a escrever 0-65535 (default: 123)")
    parser.add_argument("--pendant", action="store_true", help="Tambem mostra texto na teach pendant")
    args = parser.parse_args()

    print("=" * 60)
    print("  TESTE DE REGISTRADOR - YASKAWA YRC1000 (HSES/UDP)")
    print("=" * 60)
    print(f"  Controlador : {args.ip}:10040")
    print(f"  Registrador : M{args.reg}")
    print(f"  Valor       : {args.value}")
    print("=" * 60)

    robot = HSESClient(args.ip)

    # 1. Escrever
    print(f"\n[1] Escrevendo {args.value} no registrador M{args.reg}...")
    if robot.write_register(args.reg, args.value):
        print("    OK - escrita confirmada pelo controlador.")
    else:
        print("    FALHOU - veja o codigo de erro acima.")
        return

    # 2. Ler de volta
    print(f"\n[2] Lendo registrador M{args.reg} de volta...")
    lido = robot.read_register(args.reg)
    if lido is not None:
        print(f"    Valor lido: {lido}")
        if lido == args.value:
            print("    OK - valor confere! Comunicacao funcionando.")
        else:
            print("    ATENCAO - valor lido difere do escrito.")
    else:
        print("    FALHOU ao ler.")

    # 3. Pendant (opcional)
    if args.pendant:
        print("\n[3] Mostrando texto na teach pendant...")
        if robot.show_text(f"SoundBox reg{args.reg}={args.value}"):
            print("    OK - verifique o display do robo.")


if __name__ == "__main__":
    main()
