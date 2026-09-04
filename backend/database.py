"""
Banco de dados SQLite para modelos de caixas.
"""
import sqlite3
import os
import json

# Caminho do banco: usa DB_PATH do ambiente (util no Docker, com volume) ou
# um arquivo local por padrao.
DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "soundbox.db"),
)

# Garante que a pasta do banco exista (ex.: /app/backend/data no container)
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria as tabelas se não existirem."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS box_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            type TEXT NOT NULL DEFAULT 'regular',
            sizex REAL,
            sizey REAL,
            sizez REAL,
            weight REAL DEFAULT 0,
            strength INTEGER DEFAULT 10,
            quantity INTEGER DEFAULT 10,
            comp_total REAL,
            largura REAL,
            alt_vertical REAL,
            alt_perpendicular REAL,
            comp_braco REAL,
            l_orientation TEXT DEFAULT 'vertical',
            pallet_face TEXT DEFAULT 'xy',
            pallet_sizex REAL DEFAULT 100,
            pallet_sizey REAL DEFAULT 120,
            pallet_sizez REAL DEFAULT 200,
            pallet_max_weight REAL DEFAULT 1200,
            overhang REAL DEFAULT 5,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migração: adiciona coluna pallet_face se não existir.
    # OperationalError e esperado quando a coluna ja existe; outros erros sobem.
    try:
        conn.execute("ALTER TABLE box_models ADD COLUMN pallet_face TEXT DEFAULT 'xy'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Coluna já existe

    # Migração: adiciona coluna interlocking_type se não existir
    try:
        conn.execute("ALTER TABLE box_models ADD COLUMN interlocking_type TEXT DEFAULT 'mirror'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Coluna já existe
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pallet_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sizex REAL NOT NULL,
            sizey REAL NOT NULL,
            sizez REAL NOT NULL,
            max_weight REAL DEFAULT 1200,
            overhang REAL DEFAULT 5,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # Inserir dados padrão se tabelas vazias
    if conn.execute("SELECT COUNT(*) FROM box_models").fetchone()[0] == 0:
        _insert_defaults(conn)

    conn.close()


def _insert_defaults(conn):
    """Insere modelos padrão."""
    # Colunas: name, code, type, sizex, sizey, sizez, weight, strength, quantity,
    #          comp_total, largura, alt_vertical, alt_perpendicular, comp_braco,
    #          l_orientation, pallet_face, interlocking_type,
    #          pallet_sizex, pallet_sizey, pallet_sizez,
    #          pallet_max_weight, overhang, notes
    defaults = [
        ("S60TR Caixa L (em pé)", "S60TR-L", "l-shape", None, None, None, 8, 10, 20, 91.4, 26.3, 43.5, 14.1, 45.7, "vertical", "xy", "mirror", 100, 120, 200, 1200, 12, "Caixa formato L em pé"),
        ("S60T Caixa L (deitada)", "S60T-L", "l-shape", None, None, None, 8, 10, 24, 92.4, 27.6, 44.5, 14.1, 46.2, "horizontal", "xy", "mirror", 100, 120, 200, 1200, 12, "Caixa formato L deitada"),
        ("CL87", "CL87", "regular", 91.9, 45.3, 52.0, 16, 5, 9, None, None, None, None, None, "vertical", "xy", "mirror", 100, 120, 200, 1200, 18, ""),
        ("SH5A", "SH5A", "regular", 110.9, 26.6, 51.5, 2, 10, 12, None, None, None, None, None, "vertical", "xy", "mirror", 100, 120, 200, 1200, 10, ""),
        ("RNC7", "RNC7", "regular", 86.1, 39.6, 43.6, 10, 10, 12, None, None, None, None, None, "vertical", "xy", "mirror", 100, 120, 200, 1200, 20, ""),
        ("S90TY", "S90TY", "regular", 134.5, 57.2, 26.1, 5, 10, 12, None, None, None, None, None, "vertical", "xz", "mirror", 100, 120, 200, 1200, 15, ""),
        ("RNC9", "RNC9", "regular", 114.0, 39.6, 48.7, 10, 10, 9, None, None, None, None, None, "vertical", "xy", "alternate", 100, 120, 200, 1200, 20, ""),
        ("S40T", "S40T", "regular", 77.6, 41.9, 22.3, 10, 10, 24, None, None, None, None, None, "horizontal", "xz", "mirror", 100, 120, 200, 1200, 10, ""),
    ]
    conn.executemany("""
        INSERT INTO box_models (name, code, type, sizex, sizey, sizez, weight, strength, quantity,
                                comp_total, largura, alt_vertical, alt_perpendicular, comp_braco,
                                l_orientation, pallet_face, interlocking_type,
                                pallet_sizex, pallet_sizey, pallet_sizez, pallet_max_weight, overhang, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, defaults)

    pallet_defaults = [
        ("Pallet Americano (GMA)", 100, 120, 200, 1200, 5, "Padrão 40x48 polegadas"),
        ("Pallet EUR", 80, 120, 200, 1200, 5, "Europallet 800x1200mm"),
    ]
    conn.executemany("""
        INSERT INTO pallet_models (name, sizex, sizey, sizez, max_weight, overhang, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, pallet_defaults)

    conn.commit()


# ============================================================
# CRUD - Box Models
# ============================================================

def get_all_boxes():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM box_models ORDER BY name").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_box(box_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM box_models WHERE id = ?", (box_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_box(data):
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO box_models (name, code, type, sizex, sizey, sizez, weight, strength, quantity,
                                comp_total, largura, alt_vertical, alt_perpendicular, comp_braco,
                                l_orientation, pallet_face, interlocking_type,
                                pallet_sizex, pallet_sizey, pallet_sizez,
                                pallet_max_weight, overhang, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["name"], data.get("code"), data.get("type", "regular"),
        data.get("sizex"), data.get("sizey"), data.get("sizez"),
        data.get("weight", 0), data.get("strength", 10), data.get("quantity", 10),
        data.get("comp_total"), data.get("largura"),
        data.get("alt_vertical"), data.get("alt_perpendicular"),
        data.get("comp_braco"), data.get("l_orientation", "vertical"),
        data.get("pallet_face", "xy"), data.get("interlocking_type", "mirror"),
        data.get("pallet_sizex", 100), data.get("pallet_sizey", 120),
        data.get("pallet_sizez", 200), data.get("pallet_max_weight", 1200),
        data.get("overhang", 5), data.get("notes"),
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def update_box(box_id, data):
    conn = get_connection()
    conn.execute("""
        UPDATE box_models SET
            name=?, code=?, type=?, sizex=?, sizey=?, sizez=?, weight=?, strength=?, quantity=?,
            comp_total=?, largura=?, alt_vertical=?, alt_perpendicular=?, comp_braco=?,
            l_orientation=?, pallet_face=?, interlocking_type=?,
            pallet_sizex=?, pallet_sizey=?, pallet_sizez=?,
            pallet_max_weight=?, overhang=?, notes=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (
        data["name"], data.get("code"), data.get("type", "regular"),
        data.get("sizex"), data.get("sizey"), data.get("sizez"),
        data.get("weight", 0), data.get("strength", 10), data.get("quantity", 10),
        data.get("comp_total"), data.get("largura"),
        data.get("alt_vertical"), data.get("alt_perpendicular"),
        data.get("comp_braco"), data.get("l_orientation", "vertical"),
        data.get("pallet_face", "xy"), data.get("interlocking_type", "mirror"),
        data.get("pallet_sizex", 100), data.get("pallet_sizey", 120),
        data.get("pallet_sizez", 200), data.get("pallet_max_weight", 1200),
        data.get("overhang", 5), data.get("notes"), box_id,
    ))
    conn.commit()
    conn.close()


def delete_box(box_id):
    conn = get_connection()
    conn.execute("DELETE FROM box_models WHERE id = ?", (box_id,))
    conn.commit()
    conn.close()


# ============================================================
# CRUD - Pallet Models
# ============================================================

def get_all_pallets():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM pallet_models ORDER BY name").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_pallet(data):
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO pallet_models (name, sizex, sizey, sizez, max_weight, overhang, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["name"], data["sizex"], data["sizey"], data["sizez"],
        data.get("max_weight", 1200), data.get("overhang", 5), data.get("notes"),
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def delete_pallet(pallet_id):
    conn = get_connection()
    conn.execute("DELETE FROM pallet_models WHERE id = ?", (pallet_id,))
    conn.commit()
    conn.close()
