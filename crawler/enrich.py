"""crawler.enrich — Categoría, Resumen y Transcripción (estrategia híbrida).

Si existe GEMINI_API_KEY se usa Gemini (google-generativeai); de lo contrario
se degrada a una solución local: la transcripción son los subtítulos
descargados, el resumen es extractivo (frecuencia de términos) y la categoría
se obtiene por palabras clave (Figura 1 de la actividad).
"""
import os
import re
from collections import Counter

# Categorías inspiradas en la Figura 1 (resumen de video) y el giro comercial.
CATEGORIAS = {
    "Promociones": ["oferta", "promoci", "descuento", "precio", "barat",
                    "temporada", "regalado", "fin de semana", "cupon"],
    "Productos": ["producto", "celular", "smart", "telefono", "teléfono",
                  "pantalla", "laptop", "electro", "cobia", "gadget"],
    "Recetas": ["receta", "cocina", "ingredient", "prepara", "sabor",
                "comida", "platillo"],
    "Institucional": ["comer", "tienda", "sucursal", "servicio", "cliente",
                       "aniversario", "app", "compromiso"],
    "Temporada": ["navidad", "verano", "posada", "regalo", "fiestas",
                  "escolar", "regreso a clases", "buen fin"],
}

STOP = set((
    "de la que el en y a los del se las por un para con no una su al lo como "
    "mas más pero sus le ya o este si esta esto esa ese muy nos te mi un una "
    "porque cuando donde sobre entre todo toda hay han ser son fue era"
).split())

GEMINI_MODEL = "gemini-1.5-flash"


def enrich_record(rec):
    """Rellena `categoria`, `resumen` y `transcripcion` en el registro."""
    text = (rec.get("_subs_text") or "").strip()
    desc = (rec.get("_description") or "").strip()
    title = rec.get("titulo") or ""
    base = " ".join([title, desc, text]).strip()

    model = _gemini_client()
    if model is not None:
        try:
            rec["transcripcion"] = text or ""
            rec["resumen"] = _gemini_summary(model, base)
            rec["categoria"] = _gemini_category(model, base)
            return rec
        except Exception:
            pass  # cae a la solución local

    rec["transcripcion"] = text
    rec["resumen"] = _local_summary(base)
    rec["categoria"] = _local_category(base)
    return rec


# --------------------------------------------------------------------------- #
# Gemini (opcional)
# --------------------------------------------------------------------------- #
def _load_dotenv():
    """Carga variables desde un archivo .env en la raíz del proyecto (si existe)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, ".env")
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass


def _gemini_client():
    _load_dotenv()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None
    model = os.environ.get("GEMINI_MODEL", GEMINI_MODEL)
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        return genai.GenerativeModel(model)
    except Exception:
        return None


def check_gemini():
    """Verifica clave + modelo con una llamada mínima. Devuelve (ok, mensaje)."""
    _load_dotenv()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return False, "No hay GEMINI_API_KEY en .env -> modo LOCAL."
    model_name = os.environ.get("GEMINI_MODEL", GEMINI_MODEL)
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        r = genai.GenerativeModel(model_name).generate_content("responde: ok")
        _ = r.text
        return True, f"Gemini ACTIVO (modelo {model_name})."
    except Exception as exc:
        return False, (f"Gemini NO disponible (modelo {model_name}): {exc}. "
                       f"Se usará modo LOCAL. Ajusta GEMINI_MODEL en .env.")


def _gemini_summary(model, text):
    r = model.generate_content(
        "Resume en máximo 80 palabras, en español, el siguiente contenido de "
        f"un video:\n{text[:6000]}")
    return (r.text or "").strip()


def _gemini_category(model, text):
    cats = ", ".join(CATEGORIAS.keys())
    r = model.generate_content(
        f"Clasifica el video en UNA categoría de [{cats}]. Responde solo la "
        f"categoría, sin explicación.\n{text[:3000]}")
    out = (r.text or "").strip().splitlines()[0].strip()
    return out if out in CATEGORIAS else _local_category(text)


# --------------------------------------------------------------------------- #
# Local (fallback)
# --------------------------------------------------------------------------- #
def _local_summary(text, max_sentences=3):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) <= max_sentences:
        return text[:600]
    words = re.findall(r"[a-záéíóúñ]+", text.lower())
    freq = Counter(w for w in words if w not in STOP and len(w) > 3)

    def score(s):
        ws = re.findall(r"[a-záéíóúñ]+", s.lower())
        return sum(freq.get(w, 0) for w in ws) / (len(ws) + 1)

    top = sorted(range(len(sentences)), key=lambda i: score(sentences[i]),
                 reverse=True)[:max_sentences]
    chosen = [sentences[i] for i in sorted(top)]
    return " ".join(chosen)[:600]


def _local_category(text):
    t = text.lower()
    best, best_n = "Institucional", 0
    for cat, kws in CATEGORIAS.items():
        n = sum(t.count(k) for k in kws)
        if n > best_n:
            best, best_n = cat, n
    return best
