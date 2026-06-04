"""Inspección/ejecución independiente del servicio de Búsqueda:

    python -m busqueda --Query "Likes > 95"
    python -m busqueda --Likes ">95"
"""
import sys
import argparse
from . import search

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser("busqueda", description="Búsqueda probabilística")
    p.add_argument("--Query", type=str)
    p.add_argument("--Likes", type=str)
    p.add_argument("--Views", type=str)
    p.add_argument("--Duracion", type=str)
    p.add_argument("--Comentarios", type=str)
    p.add_argument("--Path", default="./data", type=str)
    search.Buscar(p.parse_args())


if __name__ == "__main__":
    main()
