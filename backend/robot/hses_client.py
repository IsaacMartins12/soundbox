"""
Cliente HSES (High-Speed Ethernet Server) para robôs Yaskawa YRC1000.

Comunicação direta por UDP na porta 10040, usando o protocolo nativo do
controlador. NÃO precisa de SDK pago nem de escrever job de recepção no robô
para ler/escrever variáveis e registradores.

Este módulo implementa o mínimo necessário para o nosso caso:
    - escrever registrador (write_register)
    - ler registrador (read_register)
    - mostrar texto na teach pendant (show_text)  [útil para teste visual]

Protocolo de referência (livre, MIT): https://github.com/hsinkoyu/fs100
O YRC1000 usa o mesmo formato de pacote HSES do FS100/DX200.

Unidades importantes do Yaskawa:
    - Registrador (M-var): inteiro de 2 bytes, 0 a 65535.
    - Posições cartesianas: X,Y,Z em 0.000001 m (micrometros); Rx,Ry,Rz em 0.0001 grau.
"""
import socket
import struct


class HSESClient:
    """Cliente UDP para o High-Speed Ethernet Server do YRC1000."""

    HEADER_ID = b"YERC"
    HEADER_SIZE = 0x20            # 32 bytes de cabeçalho
    RESERVED_1 = 3
    DIVISION_ROBOT = 1           # controle de robô
    ACK_REQUEST = 0
    BLOCK_NUMBER_REQ = 0
    RESERVED_2 = b"99999999"     # 8 bytes
    PADDING = 0

    PORT_ROBOT_CONTROL = 10040

    # Tipos de variável (comando HSES)
    CMD_REGISTER = 0x79          # registrador
    CMD_POSITION = 0x7F          # variável de posição robô (P)

    # Data type (sistema de coordenadas) para variável P
    COORD_PULSE = 0
    COORD_BASE = 16
    COORD_ROBOT = 17
    COORD_USER = 18
    COORD_TOOL = 19

    ERROR_SUCCESS = 0

    def __init__(self, ip, timeout=2.0, port=None):
        self.ip = ip
        self.timeout = timeout
        self.port = port if port is not None else self.PORT_ROBOT_CONTROL
        self.errno = 0

    # ------------------------------------------------------------------
    # Montagem do pacote de requisição
    # ------------------------------------------------------------------
    def _build_request(self, cmd_no, inst, attr, service, data):
        """Monta o pacote HSES completo (cabeçalho YERC + sub-header + dados)."""
        data_size = len(data)

        header = self.HEADER_ID
        header += struct.pack("<H", self.HEADER_SIZE)   # tamanho do header
        header += struct.pack("<H", data_size)          # tamanho dos dados
        header += struct.pack("B", self.RESERVED_1)
        header += struct.pack("B", self.DIVISION_ROBOT)
        header += struct.pack("B", self.ACK_REQUEST)
        header += struct.pack("B", 0)                   # req_id
        header += struct.pack("<I", self.BLOCK_NUMBER_REQ)
        header += self.RESERVED_2

        # sub-header
        sub = struct.pack("<H", cmd_no)                 # numero do comando
        sub += struct.pack("<H", inst)                  # instancia (num. da var)
        sub += struct.pack("B", attr)                   # atributo
        sub += struct.pack("B", service)                # servico (0x10=write,0x0e=read)
        sub += struct.pack("<H", self.PADDING)

        return header + sub + data

    # Status interno para falha de comunicacao (nao vem do protocolo)
    ERROR_COMMUNICATION = 0xFFFF

    def _transmit(self, packet):
        """Envia o pacote e retorna (status, added_status, data) da resposta.

        Em caso de falha de rede (timeout, conexao recusada), retorna um status
        de erro em vez de levantar excecao, para nao interromper envios em lote.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.ip, self.port))
            sock.sendall(packet)
            ans, _ = sock.recvfrom(512)
        except (socket.timeout, OSError) as e:
            print(f"[HSES] Falha de comunicacao com {self.ip}: {e}")
            return self.ERROR_COMMUNICATION, self.ERROR_COMMUNICATION, b""
        finally:
            sock.close()

        # Parse da resposta HSES
        # data_size fica nos bytes 6:8; sub-header de resposta comeca em 24
        data_size = struct.unpack("<H", ans[6:8])[0]
        status = struct.unpack("B", ans[25:26])[0]
        added_status = struct.unpack("<H", ans[28:30])[0]
        data = ans[self.HEADER_SIZE:self.HEADER_SIZE + data_size]
        return status, added_status, data

    # ------------------------------------------------------------------
    # Registradores
    # ------------------------------------------------------------------
    def write_register(self, num, value):
        """Escreve um valor no registrador `num`.

        Segundo o manual do YRC1000 (secao 3.3.3.10), o dado do registrador e
        um inteiro de 32 bits (4 bytes). Registradores escreviveis: 0 a 559.

        Retorna True em caso de sucesso.
        """
        if not (0 <= num <= 999):
            raise ValueError("Numero do registrador deve estar entre 0 e 999")
        # O registrador armazena 16 bits uteis (0-65535), mas o pacote
        # transporta um campo de 32 bits.
        if not (0 <= value <= 65535):
            raise ValueError("Valor do registrador deve estar entre 0 e 65535")

        data = struct.pack("<I", value)
        packet = self._build_request(
            cmd_no=self.CMD_REGISTER, inst=num, attr=1, service=0x10, data=data
        )
        status, added, _ = self._transmit(packet)
        self.errno = added
        if status != self.ERROR_SUCCESS:
            print(f"[HSES] Falha ao escrever registrador {num}, erro={hex(added)}")
            return False
        return True

    def read_register(self, num):
        """Lê o valor do registrador `num`. Retorna o inteiro ou None em erro.

        O dado retornado e um inteiro de 32 bits (4 bytes).
        """
        if not (0 <= num <= 999):
            raise ValueError("Numero do registrador deve estar entre 0 e 999")
        packet = self._build_request(
            cmd_no=self.CMD_REGISTER, inst=num, attr=1, service=0x0e, data=b""
        )
        status, added, data = self._transmit(packet)
        self.errno = added
        if status != self.ERROR_SUCCESS:
            print(f"[HSES] Falha ao ler registrador {num}, erro={hex(added)}")
            return None
        # O YRC1000 devolve o valor do registrador em 2 bytes na leitura
        # (mesmo o manual citando 32 bits para a escrita). Tratamos os dois casos.
        if len(data) >= 4:
            return struct.unpack("<I", data[0:4])[0]
        elif len(data) >= 2:
            return struct.unpack("<H", data[0:2])[0]
        else:
            print(f"[HSES] Resposta de leitura inesperada: {data.hex()}")
            return None

    # ------------------------------------------------------------------
    # Variavel de posicao robô (P)
    # ------------------------------------------------------------------
    def write_position(self, num, x_mm, y_mm, z_mm, tx_deg=0.0, ty_deg=0.0, tz_deg=0.0,
                       data_type=COORD_ROBOT, figure=0, tool_no=0, user_coord_no=0,
                       extended_figure=0):
        """Escreve uma posicao cartesiana na variavel P[`num`].

        Segundo o manual do YRC1000 (secao 3.3.3.16), a escrita usa
        Set_Attribute_All (attribute=0, service=0x02). O bloco de dados sao
        13 inteiros de 32 bits, nesta ordem.

        Unidades (conforme manual):
            - x, y, z em MICROMETROS (μm). Recebemos em mm e convertemos.
            - tx, ty, tz em 0.0001 grau. Recebemos em graus e convertemos.

        :param num: numero da variavel P (0 a 127 no padrao)
        :param x_mm, y_mm, z_mm: coordenadas em milimetros
        :param tx_deg, ty_deg, tz_deg: orientacao em graus
        :param data_type: sistema de coordenadas (17=robo, 18=usuario, 16=base)
        :param figure: form/pose do robo
        :param tool_no: numero da ferramenta (0 a 63)
        :param user_coord_no: numero do frame de usuario
        Retorna True em caso de sucesso.
        """
        if not (0 <= num <= 127):
            raise ValueError("Numero da variavel P deve estar entre 0 e 127")

        # Conversao de unidades: mm -> μm ; graus -> 0.0001 grau
        x = int(round(x_mm * 1000))
        y = int(round(y_mm * 1000))
        z = int(round(z_mm * 1000))
        tx = int(round(tx_deg * 10000))
        ty = int(round(ty_deg * 10000))
        tz = int(round(tz_deg * 10000))

        # 13 inteiros de 32 bits com sinal (little-endian).
        # Coordenadas podem ser negativas, por isso usamos '<i' (signed).
        data = struct.pack(
            "<iiiiiiiiiiiii",
            data_type,        # 1  Data type
            figure,           # 2  Figure
            tool_no,          # 3  Tool number
            user_coord_no,    # 4  User coordinate number
            extended_figure,  # 5  Extended figure
            x,                # 6  X (μm)
            y,                # 7  Y (μm)
            z,                # 8  Z (μm)
            tx,               # 9  Tx (0.0001 grau)
            ty,               # 10 Ty (0.0001 grau)
            tz,               # 11 Tz (0.0001 grau)
            0,                # 12 Reserva
            0,                # 13 Reserva
        )

        packet = self._build_request(
            cmd_no=self.CMD_POSITION, inst=num, attr=0, service=0x02, data=data
        )
        status, added, _ = self._transmit(packet)
        self.errno = added
        if status != self.ERROR_SUCCESS:
            print(f"[HSES] Falha ao escrever P[{num}], erro={hex(added)}")
            return False
        return True

    def read_position(self, num):
        """Le a variavel P[`num`]. Retorna dict com dados em mm/graus ou None.

        Usa Get_Attribute_All (attribute=0, service=0x01).
        """
        if not (0 <= num <= 127):
            raise ValueError("Numero da variavel P deve estar entre 0 e 127")

        packet = self._build_request(
            cmd_no=self.CMD_POSITION, inst=num, attr=0, service=0x01, data=b""
        )
        status, added, data = self._transmit(packet)
        self.errno = added
        if status != self.ERROR_SUCCESS:
            print(f"[HSES] Falha ao ler P[{num}], erro={hex(added)}")
            return None

        # Desempacota os campos que interessam (pode vir com mais campos).
        vals = struct.unpack("<iiiiiiiiiii", data[0:44])
        return {
            "data_type": vals[0],
            "figure": vals[1],
            "tool_no": vals[2],
            "user_coord_no": vals[3],
            "extended_figure": vals[4],
            "x_mm": vals[5] / 1000.0,
            "y_mm": vals[6] / 1000.0,
            "z_mm": vals[7] / 1000.0,
            "tx_deg": vals[8] / 10000.0,
            "ty_deg": vals[9] / 10000.0,
            "tz_deg": vals[10] / 10000.0,
        }

    # ------------------------------------------------------------------
    # Teach pendant (util para confirmar comunicacao visualmente)
    # ------------------------------------------------------------------
    def show_text(self, text):
        """Mostra um texto (max 30 chars) no display da teach pendant."""
        raw = text.encode("utf-8")[:30]
        raw += bytes(32 - len(raw))
        packet = self._build_request(
            cmd_no=0x85, inst=1, attr=1, service=0x10, data=raw
        )
        status, added, _ = self._transmit(packet)
        self.errno = added
        if status != self.ERROR_SUCCESS:
            print(f"[HSES] Falha ao mostrar texto, erro={hex(added)}")
            return False
        return True
