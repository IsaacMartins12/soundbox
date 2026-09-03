"""
Simulador (mock) do robô Yaskawa para testar o envio LOCALMENTE, sem o robô real.

Fica escutando num socket e imprime tudo que recebe, simulando o job em INFORM
que faria o parse da string. Útil para validar o formato da mensagem antes de
apontar para o controlador de verdade.

Uso (em um terminal separado):
    python mock_robot.py                 # UDP na porta 10040
    python mock_robot.py --proto tcp     # TCP na porta 10040
    python mock_robot.py --port 11000

Depois, em outro terminal, rode o send_test.py apontando para localhost:
    python send_test.py --ip 127.0.0.1 --port 10040 --proto udp
"""
import argparse
import socket

DEFAULT_PORT = 10040
ENCODING = "ascii"


def parse_valores(texto):
    """Simula o que o job faria: separar a string por espaços em números."""
    partes = texto.strip().split()
    try:
        numeros = [float(p) for p in partes]
        return numeros
    except ValueError:
        return None


def run_udp(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    print(f"[MOCK-UDP] Escutando na porta {port}... (Ctrl+C para parar)")
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            texto = data.decode(ENCODING, errors="replace")
            print(f"\n[MOCK-UDP] Recebido de {addr}: {texto!r}")
            numeros = parse_valores(texto)
            if numeros is not None:
                print(f"           Parse OK -> {numeros}")
                # devolve um ACK simples, como um job poderia fazer
                sock.sendto(b"ACK", addr)
            else:
                print("           Parse FALHOU (nao sao numeros separados por espaco)")
                sock.sendto(b"ERR", addr)
    except KeyboardInterrupt:
        print("\n[MOCK-UDP] Encerrado.")
    finally:
        sock.close()


def run_tcp(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen(1)
    print(f"[MOCK-TCP] Escutando na porta {port}... (Ctrl+C para parar)")
    try:
        while True:
            conn, addr = sock.accept()
            print(f"\n[MOCK-TCP] Conexao de {addr}")
            with conn:
                data = conn.recv(1024)
                if not data:
                    continue
                texto = data.decode(ENCODING, errors="replace")
                print(f"[MOCK-TCP] Recebido: {texto!r}")
                numeros = parse_valores(texto)
                if numeros is not None:
                    print(f"           Parse OK -> {numeros}")
                    conn.sendall(b"ACK")
                else:
                    print("           Parse FALHOU")
                    conn.sendall(b"ERR")
    except KeyboardInterrupt:
        print("\n[MOCK-TCP] Encerrado.")
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(description="Mock do robô Yaskawa (escuta socket).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--proto", choices=["udp", "tcp"], default="udp")
    args = parser.parse_args()

    if args.proto == "udp":
        run_udp(args.port)
    else:
        run_tcp(args.port)


if __name__ == "__main__":
    main()
