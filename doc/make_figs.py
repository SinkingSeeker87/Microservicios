"""Genera las figuras VECTORIZADAS (PDF) del documento LaTeX.

Las figuras usan un lienzo normalizado 0..100 en ambos ejes y sin márgenes,
para un encuadre limpio al insertarlas con \\includegraphics en main.tex.

    python doc/make_figs.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figs")
os.makedirs(OUT, exist_ok=True)

BLUE = "#2c6fbb"
GREEN = "#2e8b57"
GRAY = "#555555"


def _canvas(w=10, h=6):
    fig = plt.figure(figsize=(w, h))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, color=BLUE, fc="white"):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0.6,rounding_size=2",
                                linewidth=1.6, edgecolor=color, facecolor=fc))
    ax.text(x, y, text, ha="center", va="center", fontsize=11, color="black")


def arrow(ax, x1, y1, x2, y2, color=GRAY, style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=14, linewidth=1.4, color=color))


# --------------------------------------------------------------------------- #
# Figura 1: Arquitectura general (diagrama de componentes).
# --------------------------------------------------------------------------- #
def fig_arquitectura():
    fig, ax = _canvas()
    box(ax, 12, 50, 16, 14, "Usuario", color=GRAY)
    box(ax, 35, 50, 18, 16, "Main.py\n(parser único\ncapa de APIs)", color=BLUE)
    box(ax, 62, 80, 22, 14, "Crawler\n(yt-dlp · 256h)", color=GREEN)
    box(ax, 62, 50, 24, 16, "Indexamiento\nTubería + SQLite", color=GREEN)
    box(ax, 62, 20, 22, 14, "Búsqueda\n(prob. + adyacencia)", color=GREEN)
    box(ax, 89, 50, 16, 16, "Dashboard\n(Streamlit)", color=BLUE)

    arrow(ax, 20, 50, 26, 50)
    arrow(ax, 44, 56, 53, 74)
    arrow(ax, 44, 50, 50, 50)
    arrow(ax, 44, 44, 53, 26)
    arrow(ax, 62, 73, 62, 58)               # Crawler -> Indexamiento
    arrow(ax, 62, 42, 62, 27)               # Indexamiento -> Búsqueda (datos)
    arrow(ax, 74, 50, 81, 50)               # Indexamiento -> Dashboard
    fig.savefig(os.path.join(OUT, "arquitectura.pdf"))
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Figura 2: Tubería (pipe-filter) del Indexamiento.
# --------------------------------------------------------------------------- #
def fig_tuberia():
    fig, ax = _canvas(11, 4)
    etapas = ["Descubrir\nURLs", "Descargar\nmeta+media", "Transcribir\n(subs/Gemini)",
              "Resumir /\nCategorizar", "Persistir\nSQLite"]
    xs = [11, 31, 51, 71, 91]
    for x, t in zip(xs, etapas):
        box(ax, x, 55, 16, 26, t, color=GREEN)
    for i in range(len(xs) - 1):
        arrow(ax, xs[i] + 8, 55, xs[i + 1] - 8, 55)
    ax.text(50, 18, "pausa de 90 s entre videos  ·  parámetros --N y --Path",
            ha="center", va="center", fontsize=10, color=GRAY, style="italic")
    fig.savefig(os.path.join(OUT, "tuberia.pdf"))
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Figura 3: Arquitectura del servicio de Búsqueda probabilística.
# --------------------------------------------------------------------------- #
def fig_busqueda():
    fig, ax = _canvas(11, 4.5)
    box(ax, 12, 55, 16, 22, "SQLite\n(videos)", color=GREEN)
    box(ax, 36, 55, 20, 22, "Matriz de\nprobabilidad\n(histograma)", color=BLUE)
    box(ax, 62, 55, 18, 22, "P(consulta)\ncampo op valor", color=BLUE)
    box(ax, 87, 78, 20, 22, "Resultados\n+ p por video", color=GREEN)
    box(ax, 87, 30, 20, 22, "Advertencia\n+ rango sugerido", color="#b5651d")
    arrow(ax, 20, 55, 26, 55)
    arrow(ax, 46, 55, 53, 55)
    arrow(ax, 71, 60, 78, 72)
    arrow(ax, 71, 50, 78, 36)
    ax.text(62, 22, "matriz de adyacencia = correlación de parejas de campos",
            ha="center", va="center", fontsize=9, color=GRAY, style="italic")
    fig.savefig(os.path.join(OUT, "busqueda.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    fig_arquitectura()
    fig_tuberia()
    fig_busqueda()
    print("Figuras generadas en", OUT)
