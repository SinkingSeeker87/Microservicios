"""Permite probar el crawler de forma aislada:

    python -m crawler --URL https://www.youtube.com/@lacomer1/videos --N 2
"""
import sys
import argparse
from . import crawler

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser("crawler",
                                description="Servicio Crawler (independiente)")
    p.add_argument("--URL", required=True, type=str)
    p.add_argument("--N", default=2, type=int)
    p.add_argument("--Path", default="./data", type=str)
    p.add_argument("--no_video", action="store_true")
    crawler.run(p.parse_args())


if __name__ == "__main__":
    main()
