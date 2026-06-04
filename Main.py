# Main.py — Capa de APIs: parser ÚNICO que controla todo el microservicio.
#
# Sigue el patrón de "ejemplo de parser.py": argparse + subparsers +
# set_defaults(func=...). Cada subcomando delega en su microservicio, que vive
# en una carpeta independiente y es probable de forma aislada:
#
#   python Main.py Retrieve --URL <url> --N 30 --Sleep 90 --Path ./data
#   python Main.py List     --URL <url> --Path ./data
#   python Main.py Buscar   --Query "Likes > 95"
#   python Main.py Crawl    --URL <url> --N 2 --no_video      (prueba el crawler)
#   python Main.py Dashboard                                  (lanza Streamlit)
import os
import sys
import argparse
import datetime
import subprocess

# La consola de Windows usa cp1252 por defecto; forzamos UTF-8 para los acentos.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

from crawler import crawler           # Servicio 1
from indexamiento import pipeline     # Servicio 2
from busqueda import search           # Servicio 3


def Dashboard(Options):
    app = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "indexamiento", "dashboard.py")
    env = dict(os.environ, MS_PATH=getattr(Options, "Path", "./data"))
    subprocess.run([sys.executable, "-m", "streamlit", "run", app], env=env)


def main():
    parser = argparse.ArgumentParser(
        "LaComerMS",
        description="Microservicio: Crawler, Indexamiento y Busqueda (@lacomer1)")
    subparsers = parser.add_subparsers(dest="cmd")

    sp = subparsers.add_parser("Retrieve", description="Tuberia: descarga e indexa videos")
    sp.add_argument("--URL", required=True, type=str)
    sp.add_argument("--N", default=30, type=int)
    sp.add_argument("--Sleep", default=90, type=float)
    sp.add_argument("--Path", default="./data", type=str)
    sp.add_argument("--no_video", action="store_true")
    sp.set_defaults(func=pipeline.Retrieve)

    sp = subparsers.add_parser("List", description="Inspecciona la tuberia: lista las URLs")
    sp.add_argument("--URL", required=True, type=str)
    sp.add_argument("--Path", default="./data", type=str)
    sp.add_argument("--N", default=30, type=int)
    sp.set_defaults(func=pipeline.List)

    sp = subparsers.add_parser("Enrich", description="Re-genera categoria/resumen (Gemini) sin re-descargar")
    sp.add_argument("--Path", default="./data", type=str)
    sp.set_defaults(func=pipeline.Reenrich)

    sp = subparsers.add_parser("TranscribeVideo", description="Transcribe con Gemini el video 256h (N sin transcripcion)")
    sp.add_argument("--N", default=1, type=int)
    sp.add_argument("--Path", default="./data", type=str)
    sp.set_defaults(func=pipeline.TranscribeVideos)

    sp = subparsers.add_parser("Buscar", description="Busqueda probabilistica de campos")
    sp.add_argument("--Query", type=str, help='Ej: "Likes > 95"')
    sp.add_argument("--Likes", type=str)
    sp.add_argument("--Views", type=str)
    sp.add_argument("--Duracion", type=str)
    sp.add_argument("--Comentarios", type=str)
    sp.add_argument("--Path", default="./data", type=str)
    sp.set_defaults(func=search.Buscar)

    sp = subparsers.add_parser("Crawl", description="Prueba el crawler de forma aislada")
    sp.add_argument("--URL", required=True, type=str)
    sp.add_argument("--N", default=2, type=int)
    sp.add_argument("--Path", default="./data", type=str)
    sp.add_argument("--no_video", action="store_true")
    sp.set_defaults(func=crawler.run)

    sp = subparsers.add_parser("Dashboard", description="Lanza el dashboard Streamlit")
    sp.add_argument("--Path", default="./data", type=str)
    sp.set_defaults(func=Dashboard)

    Options = parser.parse_args()
    if not getattr(Options, "func", None):
        parser.print_help()
        return

    print(str(Options) + "\n")
    Options.func(Options)


if __name__ == "__main__":
    print("\n" + "\033[0;32m" + "[start] " + str(datetime.datetime.now()) + "\033[0m" + "\n")
    main()
    print("\n" + "\033[0;32m" + "[end] " + str(datetime.datetime.now()) + "\033[0m" + "\n")
