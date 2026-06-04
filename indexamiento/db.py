"""indexamiento.db — Perspectiva de Información (SDD, IEEE 1016-2009).

Define el esquema SQLite y el acceso a datos. Es el filtro de persistencia
de la tubería (pipe-filter) y la fuente de datos de los servicios de
Búsqueda y del Dashboard. Se eligió SQLite por ser un motor embebido, sin
servidor, fácil de inspeccionar y de documentar.
"""
import os
import json
import sqlite3

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "data")

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    url            TEXT PRIMARY KEY,
    video_id       TEXT,
    titulo         TEXT,
    captura_ts     TEXT,      -- estampa de captura (fecha y hora)
    fecha_pub      TEXT,      -- fecha de publicacion (YYYYMMDD)
    duracion       INTEGER,   -- segundos
    views          INTEGER,   -- reaccion social: vistas
    likes          INTEGER,   -- reaccion social: likes
    n_comentarios  INTEGER,
    comentarios    TEXT,      -- JSON con los comentarios
    thumbnail_b64  TEXT,      -- miniatura en base64 (hex64)
    categoria      TEXT,
    resumen        TEXT,
    transcripcion  TEXT
);
"""

# Orden canonico de columnas
FIELDS = ["url", "video_id", "titulo", "captura_ts", "fecha_pub", "duracion",
          "views", "likes", "n_comentarios", "comentarios", "thumbnail_b64",
          "categoria", "resumen", "transcripcion"]

# Campos numericos expuestos al servicio de Busqueda probabilistica
NUMERIC_FIELDS = ["views", "likes", "duracion", "n_comentarios"]


def db_path(path=None):
    """Devuelve la ruta absoluta del archivo SQLite a partir de un directorio."""
    base = path or DEFAULT_PATH
    base = os.path.abspath(base)
    if base.endswith(".db"):
        return base
    return os.path.join(base, "videos.db")


def connect(path=None):
    p = db_path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    con = sqlite3.connect(p)
    con.execute(SCHEMA)
    return con


def upsert_video(con, rec):
    """Filtro de persistencia: inserta/actualiza un registro de video."""
    row = {k: rec.get(k) for k in FIELDS}
    if isinstance(row.get("comentarios"), (list, dict)):
        row["comentarios"] = json.dumps(row["comentarios"], ensure_ascii=False)
    cols = ",".join(FIELDS)
    placeholders = ",".join(["?"] * len(FIELDS))
    updates = ",".join(f"{f}=excluded.{f}" for f in FIELDS if f != "url")
    con.execute(
        f"INSERT INTO videos ({cols}) VALUES ({placeholders}) "
        f"ON CONFLICT(url) DO UPDATE SET {updates}",
        [row[f] for f in FIELDS],
    )
    con.commit()


def list_urls(con):
    return [r[0] for r in con.execute("SELECT url FROM videos ORDER BY captura_ts")]


def count(con):
    return con.execute("SELECT COUNT(*) FROM videos").fetchone()[0]


def all_rows(con):
    cur = con.execute(f"SELECT {','.join(FIELDS)} FROM videos")
    return [dict(zip(FIELDS, r)) for r in cur.fetchall()]
