"""Inspección/ejecución independiente del servicio de Indexamiento:

    python -m indexamiento Retrieve --URL <url> --N 30 --Sleep 90 --Path ./data
    python -m indexamiento List     --URL <url> --Path ./data
"""
import sys
import argparse
from . import pipeline

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser("indexamiento", description="Tubería (pipe-filter)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("Retrieve", description="Ejecuta la tubería completa")
    r.add_argument("--URL", required=True, type=str)
    r.add_argument("--N", default=30, type=int)
    r.add_argument("--Sleep", default=90, type=float)
    r.add_argument("--Path", default="./data", type=str)
    r.add_argument("--no_video", action="store_true")
    r.set_defaults(func=pipeline.Retrieve)

    l = sub.add_parser("List", description="Lista las URLs indexadas")
    l.add_argument("--URL", required=True, type=str)
    l.add_argument("--Path", default="./data", type=str)
    l.add_argument("--N", default=30, type=int)
    l.set_defaults(func=pipeline.List)

    opts = p.parse_args()
    opts.func(opts)


if __name__ == "__main__":
    main()
