"""indexamiento.pipeline — Patrón arquitectónico de TUBERÍA (pipe-filter).

La información fluye por una secuencia de filtros independientes; cada filtro
recibe un registro de video, lo transforma y lo entrega al siguiente. Esto
desacopla descubrimiento → descarga → enriquecimiento → persistencia y
favorece la reusabilidad, cohesión y bajo acoplamiento (RL_2026: Patrones).

    Descubrir → Descargar(media+meta) → Enriquecer(cat/resumen/transcripción)
              → Persistir(SQLite)

Funciones de la capa de APIs:
    Retrieve(Options)  -> ejecuta la tubería completa (pausa 90 s entre videos)
    List(Options)      -> inspecciona la tubería (lista las URLs)
"""
import os
import time

from crawler import crawler, enrich
from . import db


def Retrieve(Options):
    url = Options.URL
    n = int(Options.N)
    sleep = float(getattr(Options, "Sleep", 90))
    path = getattr(Options, "Path", "./data")
    no_video = getattr(Options, "no_video", False)

    con = db.connect(path)
    urls = crawler.discover(url, n)                       # filtro 1: descubrir
    print(f"[pipeline] {len(urls)} videos a procesar | sleep={sleep:g}s | path={path}")

    ok = 0
    for i, u in enumerate(urls, 1):
        print(f"[pipeline] ({i}/{len(urls)}) {u}")
        try:
            rec = crawler.fetch(u, path, download_video=not no_video)  # filtro 2
            enrich.enrich_record(rec)                                  # filtro 3
            db.upsert_video(con, rec)                                  # filtro 4
            ok += 1
            print(f"    OK | cat={rec.get('categoria')} "
                  f"views={rec.get('views')} likes={rec.get('likes')} "
                  f"coment={rec.get('n_comentarios')}")
        except Exception as exc:
            print(f"    ERROR: {exc}")
        if i < len(urls):
            time.sleep(sleep)                            # pausa de 90 s requerida

    print(f"[pipeline] procesados={ok}/{len(urls)} | total en BD={db.count(con)}")
    con.close()


def Reenrich(Options):
    """Re-genera categoría y resumen (p.ej. con Gemini) sobre la BD existente,
    SIN re-descargar videos ni esperar pausas. Reutiliza la transcripción y los
    metadatos ya almacenados."""
    path = getattr(Options, "Path", "./data")
    con = db.connect(path)
    rows = db.all_rows(con)
    if not rows:
        print("[enrich] No hay datos. Ejecuta primero Retrieve.")
        con.close()
        return

    ok, msg = enrich.check_gemini()
    print(f"[enrich] {msg}")
    print(f"[enrich] re-enriqueciendo {len(rows)} registros...")
    for i, row in enumerate(rows, 1):
        rec = dict(row)                              # conserva todos los campos
        rec["_subs_text"] = row.get("transcripcion") or ""
        rec["_description"] = ""
        enrich.enrich_record(rec)                    # actualiza categoria y resumen
        db.upsert_video(con, rec)
        print(f"  ({i}/{len(rows)}) cat={rec.get('categoria')} :: "
              f"{str(rec.get('resumen'))[:80]}")
    print(f"[enrich] listo | total en BD={db.count(con)}")
    con.close()


def List(Options):
    """Inspección independiente de la tubería: imprime las URLs indexadas."""
    path = getattr(Options, "Path", "./data")
    if os.path.exists(db.db_path(path)):
        con = db.connect(path)
        urls = db.list_urls(con)
        con.close()
        if urls:
            for u in urls:
                print(u)
            return
    # Si la BD está vacía, descubre desde el canal (inspección previa).
    for u in crawler.discover(Options.URL, int(getattr(Options, "N", 30) or 30)):
        print(u)
