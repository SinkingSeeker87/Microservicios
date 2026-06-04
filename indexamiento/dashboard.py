"""indexamiento.dashboard — Front-end (Streamlit) del microservicio.

Integra los tres servicios en un panel con cuatro pestañas:
  1. Preguntas en lenguaje natural  -> mosaico 1:5 desde thumbnails.
  2. Búsqueda probabilística         -> servicio Buscar: probabilidad + heatmap
                                        de la matriz de adyacencia.
  3. Explorador de datos             -> tabla de los 30 videos + descarga CSV.
  4. Gráficas                        -> reacción social por categoría.

Ejecutar:  python Main.py Dashboard      (o)  streamlit run indexamiento/dashboard.py
"""
import os
import io
import re
import sys
import json
import base64

# Permite los imports del proyecto cuando Streamlit ejecuta este script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image
import matplotlib.pyplot as plt

from busqueda import search

DATA = os.environ.get("MS_PATH", "./data")
POS_WORDS = ["bueno", "buena", "excelente", "genial", "me gusta", "encanta",
             "gracias", "increible", "increíble", "delicioso", "recomiendo", "❤", "👍"]
QWORDS = set((
    "en que qué video videos hablan habla del de la el los las cuanto cuánto "
    "cuesta precio vale sobre cuales cuáles cuál tienen tiene mas más tratan "
    "se un una con para por y a hay donde dónde como cómo es son"
).split())


@st.cache_data(show_spinner=False)
def load():
    return search.load_df(DATA)


def keywords(q):
    toks = re.findall(r"[a-záéíóúñ0-9]+", q.lower())
    return [t for t in toks if t not in QWORDS and len(t) > 3]


def text_of(row):
    return " ".join(str(row.get(c, "")) for c in ("titulo", "resumen", "transcripcion")).lower()


def build_mosaic(b64_list, cols=5, thumb_w=240):
    """Mosaico 1:5 (cinco columnas por fila) desde los thumbnails."""
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


def positive_score(row):
    try:
        coms = json.loads(row.get("comentarios") or "[]")
    except Exception:
        coms = []
    text = " ".join((c.get("text") or "") for c in coms).lower()
    return sum(text.count(w) for w in POS_WORDS)


def answer(question, df):
    """Devuelve (subconjunto_df, nota_textual) según la intención detectada."""
    q = question.lower()
    kws = keywords(q)
    if any(k in q for k in ["cuanto", "cuánto", "cuesta", "precio", "vale"]):
        hits = df[df.apply(lambda r: any(k in text_of(r) for k in kws), axis=1)] if kws else df
        precios = []
        for _, r in hits.iterrows():
            for m in re.findall(r"\$\s?\d[\d,\.]*", str(r.get("transcripcion", "")) + " " + str(r.get("resumen", ""))):
                precios.append(f"{m}  ·  {r['url']}")
        nota = ("Precios detectados:\n- " + "\n- ".join(precios)) if precios \
            else "No se detectaron precios explícitos ($) en los videos coincidentes."
        return hits, nota
    if "reacciones" in q or "reaccion" in q:
        return df.sort_values("views", ascending=False).head(10), "Videos con más reacciones sociales (vistas)."
    if "likes" in q or "tratan" in q:
        top = df.sort_values("likes", ascending=False).head(10)
        resumenes = "\n".join(f"- {r['titulo']}: {str(r['resumen'])[:120]}" for _, r in top.head(5).iterrows())
        return top, "Videos con más likes y de qué tratan:\n" + resumenes
    if "positiv" in q or "comentarios" in q:
        tmp = df.copy()
        tmp["pos"] = tmp.apply(positive_score, axis=1)
        top = tmp[tmp["pos"] > 0].sort_values("pos", ascending=False)
        return (top if not top.empty else df.head(5)), "Videos con comentarios positivos."
    hits = df[df.apply(lambda r: any(k in text_of(r) for k in kws), axis=1)] if kws else df.head(0)
    nota = (f"{len(hits)} video(s) mencionan: {', '.join(kws)}." if kws
            else "Escribe una pregunta con un término a buscar.")
    return hits, nota


@st.cache_data(show_spinner=False)
def thumb_uri(b64, w=130):
    """Miniatura reducida como data-URI para la tabla del explorador."""
    if not b64:
        return None
    try:
        im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        h = int(im.height * w / im.width)
        im = im.resize((w, h))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=70)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def adjacency_heatmap(df):
    A = search.adjacency_matrix(df)
    fig, ax = plt.subplots(figsize=(4.6, 4))
    im = ax.imshow(A.values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(A.columns))); ax.set_xticklabels(A.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(A.index))); ax.set_yticklabels(A.index)
    for i in range(len(A.index)):
        for j in range(len(A.columns)):
            ax.text(j, i, f"{A.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title("Matriz de adyacencia (correlación)")
    plt.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="La Comer · Microservicio", layout="wide")
st.title("La Comer (@lacomer1) — Microservicio: Indexamiento + Búsqueda")

df = load()
if df.empty:
    st.warning("No hay datos. Ejecuta primero:  python Main.py Retrieve --URL "
               "https://www.youtube.com/@lacomer1/videos --N 30 --Sleep 90")
    st.stop()

st.caption(f"{len(df)} videos indexados en {os.path.abspath(search.db.db_path(DATA))}")

tab1, tab2, tab3, tab4 = st.tabs([
    "🔎 Preguntas (NL)", "📊 Búsqueda probabilística",
    "🗂️ Explorador de datos", "📈 Gráficas"])

# --- Pestaña 1: preguntas en lenguaje natural ----------------------------- #
with tab1:
    st.subheader("Pregunta sobre el canal")
    ejemplos = [
        "¿En qué video hablan del Cobia smart phone?",
        "¿Cuánto cuesta un Cobia smart phone?",
        "¿Qué videos tienen más reacciones sociales?",
        "¿Sobre qué tratan los videos que más likes tienen?",
        "¿Qué videos tienen comentarios positivos?",
    ]
    col_q, col_e = st.columns([3, 2])
    with col_e:
        ejemplo = st.selectbox("Ejemplos", ejemplos)
    with col_q:
        pregunta = st.text_input("Tu pregunta", value=ejemplo)
    if pregunta:
        hits, nota = answer(pregunta, df)
        st.info(nota)
        if hits is not None and not hits.empty:
            st.markdown(f"**Mosaico 1:5 — {len(hits)} video(s)**")
            mosaic = build_mosaic(list(hits["thumbnail_b64"]))
            if mosaic is not None:
                st.image(mosaic, width="stretch")
            st.dataframe(hits[["titulo", "url", "views", "likes", "categoria"]],
                         width="stretch")

# --- Pestaña 2: búsqueda probabilística (servicio Buscar) ----------------- #
with tab2:
    st.subheader("Búsqueda probabilística (servicio Buscar)")
    c1, c2, c3 = st.columns(3)
    field = c1.selectbox("Campo", search.NUMERIC, index=1)
    op = c2.selectbox("Operador", [">", "<", ">=", "<=", "="])
    val = c3.number_input("Valor", value=float(int(df[field].median())), step=1.0)

    mask = np.asarray(search.OPS[op](df[field], val))
    P = float(mask.mean())
    lo, hi = int(df[field].min()), int(df[field].max())

    if P < search.LOW_P:
        st.error(f"La probabilidad de tu búsqueda es {P:.6f}. "
                 f"Utiliza el siguiente rango {lo} – {hi}.")
    else:
        st.success(f"Probabilidad de la búsqueda: p = {P:.4f}  "
                   f"({int(mask.sum())} de {len(df)} videos)")
        res = df[mask].copy()
        res["p"] = search.per_video_prob(df, field)[mask]
        res = res.sort_values("p", ascending=False)
        st.dataframe(res[["url", "p", field, "titulo", "categoria"]],
                     width="stretch")

    st.markdown("**Matriz de adyacencia de parejas de campos**")
    st.pyplot(adjacency_heatmap(df))

# --- Pestaña 3: explorador de datos --------------------------------------- #
with tab3:
    st.subheader(f"Explorador de datos ({len(df)} videos)")
    disp = df.copy()
    disp["thumbnail"] = disp["thumbnail_b64"].apply(thumb_uri)
    cols = ["thumbnail", "titulo", "categoria", "views", "likes",
            "n_comentarios", "duracion", "fecha_pub", "url"]
    st.dataframe(
        disp[cols], width="stretch", hide_index=True,
        column_config={
            "thumbnail": st.column_config.ImageColumn("Thumbnail"),
            "url": st.column_config.LinkColumn("URL"),
        })
    with st.expander("Ver resúmenes y transcripciones"):
        for _, r in disp.iterrows():
            st.markdown(f"**{r['titulo']}**  ·  _{r['categoria']}_")
            st.caption("Resumen: " + (str(r["resumen"])[:300] or "—"))
            st.caption("Transcripción: " + (str(r["transcripcion"])[:300] or "—"))
            st.divider()
    csv = df.drop(columns=["thumbnail_b64"]).to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Descargar CSV", csv, "videos.csv", "text/csv")

# --- Pestaña 4: gráficas de reacciones sociales --------------------------- #
with tab4:
    st.subheader("Gráficas de reacciones sociales")
    g = df.groupby("categoria")[["views", "likes"]].sum().sort_values("views", ascending=False)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Reacción social por categoría**")
        fig, ax = plt.subplots(figsize=(6, 4))
        g.plot(kind="bar", ax=ax)
        ax.set_ylabel("Reacción social"); ax.set_xlabel("Categoría")
        plt.tight_layout()
        st.pyplot(fig)
    with c2:
        st.markdown("**Top 10 videos por vistas**")
        top = df.sort_values("views", ascending=False).head(10)
        st.bar_chart(top.set_index("titulo")[["views", "likes"]])
