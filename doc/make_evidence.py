"""Genera la EVIDENCIA del documento a partir de la base de datos ya poblada.

Produce:
  doc/figs/mosaico.png      mosaico 1:5 desde los thumbnails
  doc/figs/grafica.png      reaccion social por categoria
  doc/evidencia/list.txt    salida real de  Main.py List
  doc/evidencia/buscar_ok.txt   busqueda valida
  doc/evidencia/buscar_low.txt  busqueda de baja probabilidad
  doc/auto_test.sh          copia del script para el apendice LaTeX

    python doc/make_evidence.py
"""
import os
import io
import re
import sys
import base64
import shutil
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from busqueda import search  # noqa: E402

DOC = os.path.join(ROOT, "doc")
FIGS = os.path.join(DOC, "figs")
EV = os.path.join(DOC, "evidencia")
DATA = os.path.join(ROOT, "data")
CHANNEL = "https://www.youtube.com/@lacomer1/videos"
for d in (FIGS, EV):
    os.makedirs(d, exist_ok=True)


def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "Main.py"] + args, cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    out = (r.stdout or "") + (r.stderr or "")
    return re.sub(r"\x1b\[[0-9;]*m", "", out).strip() + "\n"


def build_mosaic(b64_list, cols=5, thumb_w=240):
    imgs = []
    for b in b64_list:
        if not b:
            continue
        try:
            im = Image.open(io.BytesIO(base64.b64decode(b))).convert("RGB")
            h = int(im.height * thumb_w / im.width)
            imgs.append(im.resize((thumb_w, h)))
        except Exception:
            continue
    if not imgs:
        return None
    rows = (len(imgs) + cols - 1) // cols
    cw, ch = thumb_w, max(i.height for i in imgs)
    canvas = Image.new("RGB", (cols * cw, rows * ch), (255, 255, 255))
    for idx, im in enumerate(imgs):
        r, c = divmod(idx, cols)
        canvas.paste(im, (c * cw, r * ch))
    return canvas


def main():
    df = search.load_df(DATA)
    if df.empty:
        print("La base de datos esta vacia; ejecuta primero Retrieve.")
        return

    # --- Mosaico 1:5 (hasta 10 videos -> 2 filas x 5 columnas) ---
    mosaic = build_mosaic(list(df["thumbnail_b64"].head(10)))
    if mosaic is not None:
        mosaic.save(os.path.join(FIGS, "mosaico.png"))
        print("OK figs/mosaico.png")

    # --- Grafica: reaccion social por categoria ---
    g = df.groupby("categoria")[["views", "likes"]].sum().sort_values("views", ascending=False)
    fig, ax = plt.subplots(figsize=(7, 4))
    g.plot(kind="bar", ax=ax)
    ax.set_ylabel("Reaccion social"); ax.set_xlabel("Categoria")
    plt.xticks(rotation=20, ha="right"); plt.tight_layout()
    fig.savefig(os.path.join(FIGS, "grafica.png"), dpi=150)
    plt.close(fig)
    print("OK figs/grafica.png")

    # --- Evidencias de terminal (salidas reales) ---
    with open(os.path.join(EV, "list.txt"), "w", encoding="utf-8") as fh:
        fh.write(run_cli(["List", "--URL", CHANNEL, "--Path", "./data"]))

    # Busqueda valida: umbral = percentil 25 de views (alta probabilidad)
    thr = int(df["views"].quantile(0.25))
    with open(os.path.join(EV, "buscar_ok.txt"), "w", encoding="utf-8") as fh:
        fh.write(run_cli(["Buscar", "--Query", f"Views > {thr}", "--Path", "./data"]))

    with open(os.path.join(EV, "buscar_low.txt"), "w", encoding="utf-8") as fh:
        fh.write(run_cli(["Buscar", "--Query", "Likes > 950000", "--Path", "./data"]))
    print("OK evidencia/*.txt")

    # --- Copia del script bash para el apendice (Overleaf no admite '..') ---
    shutil.copyfile(os.path.join(ROOT, "tests", "auto_test.sh"),
                    os.path.join(DOC, "auto_test.sh"))
    print("OK doc/auto_test.sh")


if __name__ == "__main__":
    main()
