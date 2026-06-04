"""busqueda.search — Servicio 3: Búsqueda probabilística.

Construye la **matriz de probabilidad** (distribución empírica) de cada campo
numérico y la **matriz de adyacencia** (correlación) de las parejas de campos,
para validar consultas del tipo `Likes > 95` y advertir búsquedas improbables.

    P(consulta)  = fracción de videos que satisfacen el predicado
    p(video)     = probabilidad empírica del valor del campo (por bin)
    adyacencia   = matriz de correlación de Pearson entre campos numéricos
"""
import os
import re

import numpy as np
import pandas as pd

from indexamiento import db

NUMERIC = db.NUMERIC_FIELDS  # views, likes, duracion, n_comentarios

ALIASES = {
    "likes": "likes", "like": "likes",
    "views": "views", "vistas": "views", "reacciones": "views",
    "duracion": "duracion", "duración": "duracion", "dur": "duracion",
    "comentarios": "n_comentarios", "comments": "n_comentarios",
    "n_comentarios": "n_comentarios",
}

OPS = {
    ">": lambda s, v: s > v, "<": lambda s, v: s < v,
    ">=": lambda s, v: s >= v, "<=": lambda s, v: s <= v,
    "=": lambda s, v: s == v, "==": lambda s, v: s == v,
}

LOW_P = 0.01  # umbral de advertencia de baja probabilidad


def load_df(path="./data"):
    con = db.connect(path)
    rows = db.all_rows(con)
    con.close()
    df = pd.DataFrame(rows)
    for f in NUMERIC:
        if f in df:
            df[f] = pd.to_numeric(df[f], errors="coerce").fillna(0)
    return df


def parse_query(q):
    m = re.match(r"\s*([A-Za-zÁÉÍÓÚáéíóúñ_]+)\s*(>=|<=|==|>|<|=)\s*([0-9]+(?:\.[0-9]+)?)\s*$", q)
    if not m:
        raise ValueError(f"Consulta inválida: {q!r}. Ejemplo válido: 'Likes > 95'")
    field = ALIASES.get(m.group(1).lower())
    if field is None:
        raise ValueError(f"Campo desconocido: {m.group(1)}. Usa: "
                         f"{', '.join(sorted(set(ALIASES)))}")
    return field, m.group(2), float(m.group(3))


def field_distribution(df, field, bins=10):
    """Matriz de probabilidad de un campo: histograma normalizado."""
    vals = df[field].to_numpy(dtype=float)
    nb = max(1, min(bins, len(np.unique(vals))))
    counts, edges = np.histogram(vals, bins=nb)
    probs = counts / max(1, counts.sum())
    return edges, probs


def per_video_prob(df, field, bins=10):
    edges, probs = field_distribution(df, field, bins)
    idx = np.clip(np.digitize(df[field].to_numpy(dtype=float), edges[1:-1]),
                  0, len(probs) - 1)
    return probs[idx]


def adjacency_matrix(df):
    """Matriz de adyacencia: correlación de Pearson entre campos numéricos."""
    present = [f for f in NUMERIC if f in df]
    return df[present].corr().fillna(0.0)


def Buscar(Options):
    path = getattr(Options, "Path", "./data")
    df = load_df(path)
    if df.empty:
        print("No hay datos indexados. Ejecuta primero: Main.py Retrieve ...")
        return

    query = _resolve_query(Options)
    field, op, val = parse_query(query)

    mask = OPS[op](df[field], val)
    P = float(np.asarray(mask, dtype=float).mean())   # probabilidad de la consulta
    lo, hi = int(df[field].min()), int(df[field].max())

    print(f"\nConsulta: {field} {op} {val:g}")
    if P < LOW_P:
        print(f"La probabilidad de tu búsqueda es {P:.6f} "
              f"utiliza el siguiente rango {lo} - {hi}")
    else:
        res = df[mask].copy()
        res["p"] = per_video_prob(df, field)[np.asarray(mask)]
        res = res.sort_values("p", ascending=False)
        print(f"Probabilidad de la búsqueda: p = {P:.4f}  "
              f"({len(res)} de {len(df)} videos)\n")
        print(f"{'URL':55s} {'p':>6s}  {field}")
        for _, r in res.iterrows():
            print(f"{str(r['url'])[:55]:55s} p = {r['p']:.2f}  {field} = {int(r[field])}")

    print("\nMatriz de adyacencia (correlación) de parejas de campos:")
    print(adjacency_matrix(df).round(2).to_string())
    print()


def _resolve_query(Options):
    if getattr(Options, "Query", None):
        return Options.Query
    for flag in ("Likes", "Views", "Duracion", "Comentarios"):
        v = getattr(Options, flag, None)
        if v:
            v = str(v).strip()
            return f"{flag} {v}" if re.match(r"^[<>=]", v) else f"{flag} > {v}"
    raise ValueError("Especifica --Query \"Likes > 95\" o un flag de campo "
                     "(--Likes, --Views, --Duracion, --Comentarios)")
