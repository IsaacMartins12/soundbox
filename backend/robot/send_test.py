"""
Script de exemplo para enviar valores a um registrador do robô Yaskawa via socket.

Objetivo desta primeira versão: validar a COMUNICAÇÃO.
Manda uma string de valores (ex.: "99 99 50 30 64") para o controlador,
que roda um job em INFORM escutando o socket e faz o parse dos valores
para variáveis de posição / registradores.

O formato da string e o protocolo (UDP ou TCP) dependem de como o job do
robô foi escrito. Por isso os dois estão disponíveis aqui e são
selecionáveis por parâmetro.

Uso:
    python send_test.py                      # usa os valores default
    python send_test.py --ip 192.168.1.31 --port 10040 --proto udp
    python send_test.py --values "99 99 50 30 64"

Referências de configuração típicas do Yaskawa:
    - Controladores: YRC1000, DX200, FS100
    - O robô trabalha em MILÍMETROS e milésimos de grau.
    - Portas de socket são definidas no job (SKOPEN) — ajuste conforme o seu.
"""
import argparse
import socket


# ---------------------------------------------------------------------------
# Configuração default (ajuste para o seu controlador)
# ---------------------------------------------------------------------------
DEFAULT_IP = "192.168.1.31"   # IP do controlador Yaskawa
DEFAULT_PORT = 10040          # porta que o job abre com SKOPEN
DEFAULT_PROTO = "udp"         # "udp" ou "tcp"
DEFAULT_VALUES = "99 99 50 30 64"  # string de exemplo (X Y Z ... )
TIMEOUT_S = 5.0               # timeout de resposta em segundos
ENCODING = "ascii"           # o INFORM costuma tratar bytes ASCII


def send_udp(ip, port, message, timeout=TIMEOUT_S):
    """Envia a mensagem via UDP e tenta ler uma resposta (se o job responder)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        payload = message.encode(ENCODING)
        print(f"[UDP] Enviando para {ip}:{port} -> {message!r} ({len(payload)} bytes)")
        sock.sendto(payload, (ip, port))

        try:
            data, addr = sock.recvfrom(1024)
            print(f"[UDP] Resposta de {addr}: {data.decode(ENCODING, errors='replace')!r}")
        except socket.timeout:
            print("[UDP] Sem resposta (normal se o job apenas recebe e não responde).")
    finally:
        sock.close()


def send_tcp(ip, port, message, timeout=TIMEOUT_S):
    """Abre conexão TCP, envia a mensagem e tenta ler uma resposta."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        print(f"[TCP] Conectando em {ip}:{port}...")
        sock.connect((ip, port))
        payload = message.encode(ENCODING)
        print(f"[TCP] Enviando -> {message!r} ({len(payload)} bytes)")
        sock.sendall(payload)

        try:
            data = sock.recv(1024)
            if data:
                print(f"[TCP] Resposta: {data.decode(ENCODING, errors='replace')!r}")
            else:
                print("[TCP] Conexão fechada pelo robô sem resposta.")
        except socket.timeout:
            print("[TCP] Sem resposta (timeout).")
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(description="Envia valores de teste ao robô Yaskawa via socket.")
    parser.add_argument("--ip", default=DEFAULT_IP, help=f"IP do controlador (default: {DEFAULT_IP})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Porta do socket (default: {DEFAULT_PORT})")
    parser.add_argument("--proto", choices=["udp", "tcp"], default=DEFAULT_PROTO,
                        help=f"Protocolo (default: {DEFAULT_PROTO})")
    parser.add_argument("--values", default=DEFAULT_VALUES,
                        help=f"String de valores a enviar (default: {DEFAULT_VALUES!r})")
    args = parser.parse_args()

    print("=" * 60)
    print("  TESTE DE COMUNICAÇÃO COM ROBÔ YASKAWA")
    print("=" * 60)
    print(f"  Destino : {args.ip}:{args.port}")
    print(f"  Protocolo: {args.proto.upper()}")
    print(f"  Valores : {args.values!r}")
    print("=" * 60)

    try:
        if args.proto == "udp":
            send_udp(args.ip, args.port, args.values)
        else:
            send_tcp(args.ip, args.port, args.values)
        print("\n[OK] Mensagem enviada.")
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f"\n[ERRO] Falha na comunicação: {e}")
        print("       Verifique: IP/porta corretos, robô ligado, job de socket rodando,")
        print("       e se o PC está na mesma rede do controlador.")


if __name__ == "__main__":
    main()
