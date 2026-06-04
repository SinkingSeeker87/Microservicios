"""crawler.crawler — Servicio 1: Crawler (perspectiva de Contexto, caja negra).

Recupera de YouTube (@lacomer1) la información pedida por la actividad usando
yt-dlp 2026.03.17. Cada video se transforma en un registro `dict`. Las
funciones públicas son los *filtros* que consume la tubería de Indexamiento:

    discover(url, n)      -> [urls]            (descubrimiento)
    fetch(url, path, ...) -> rec               (descarga de datos y media)
    run(Options)          -> prueba aislada del crawler
"""
import os
import glob
import shutil
import base64
import datetime
import subprocess
import urllib.request

import yt_dlp

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Binario de ffmpeg para el escalado a 256h. Se prefiere el binario estático de
# imageio-ffmpeg (robusto en Windows); si no, se usa el del PATH.
def _resolve_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


FFMPEG = _resolve_ffmpeg()


def discover(url, n):
    """Filtro de descubrimiento: URLs de los primeros n videos del canal."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "playlistend": int(n),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    urls = []
    for e in (info.get("entries") or [])[:int(n)]:
        if not e:
            continue
        u = e.get("url") or e.get("id")
        if u and not str(u).startswith("http"):
            u = f"https://www.youtube.com/watch?v={u}"
        if u:
            urls.append(u)
    return urls


def fetch(url, path, download_video=True):
    """Filtro de descarga: metadatos, comentarios, thumbnail y video 256h."""
    thumb_dir = os.path.join(path, "thumbnails")
    video_dir = os.path.join(path, "videos")
    for d in (thumb_dir, video_dir):
        os.makedirs(d, exist_ok=True)

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "getcomments": True,
        "extractor_args": {"youtube": {"max_comments": ["40", "all", "0"]}},
        "http_headers": {"User-Agent": UA},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    vid = info.get("id")
    rec = {
        "url": info.get("webpage_url") or url,
        "video_id": vid,
        "titulo": info.get("title"),
        "captura_ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_pub": info.get("upload_date"),
        "duracion": info.get("duration"),
        "views": info.get("view_count"),
        "likes": info.get("like_count"),
    }

    comments = info.get("comments") or []
    rec["comentarios"] = [
        {"author": c.get("author"), "text": c.get("text"),
         "likes": c.get("like_count")}
        for c in comments
    ]
    rec["n_comentarios"] = info.get("comment_count") or len(comments)

    rec["thumbnail_b64"] = _download_thumbnail(info, thumb_dir, vid)
    rec["_subs_text"] = _extract_subs_text(info)
    rec["_description"] = info.get("description") or ""

    rec["_video_path"] = None
    if download_video:
        rec["_video_path"] = _download_scaled_video(url, video_dir, vid)

    return rec


def run(Options):
    """Prueba el crawler de forma totalmente aislada (subcomando Crawl)."""
    from . import enrich
    urls = discover(Options.URL, Options.N)
    print(f"[crawler] {len(urls)} URLs descubiertas en {Options.URL}")
    no_video = getattr(Options, "no_video", False)
    for i, u in enumerate(urls, 1):
        print(f"[crawler] ({i}/{len(urls)}) {u}")
        try:
            rec = fetch(u, Options.Path, download_video=not no_video)
            enrich.enrich_record(rec)
        except Exception as exc:  # robustez ante fallos puntuales de red
            print(f"    ERROR: {exc}")
            continue
        print(f"    titulo   = {rec.get('titulo')!r}")
        print(f"    fecha    = {rec.get('fecha_pub')}  dur={rec.get('duracion')}s")
        print(f"    social   = views={rec.get('views')} likes={rec.get('likes')} "
              f"comentarios={rec.get('n_comentarios')}")
        print(f"    categoria= {rec.get('categoria')}")
        thumb = rec.get("thumbnail_b64") or ""
        print(f"    thumbnail= {len(thumb)} bytes base64; video={rec.get('_video_path')}")
        print(f"    resumen  = {(rec.get('resumen') or '')[:140]}")


# --------------------------------------------------------------------------- #
# Helpers internos
# --------------------------------------------------------------------------- #
def _download_thumbnail(info, thumb_dir, vid):
    url = info.get("thumbnail")
    if not url:
        thumbs = info.get("thumbnails") or []
        if thumbs:
            url = thumbs[-1].get("url")
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=30).read()
        with open(os.path.join(thumb_dir, f"{vid}.jpg"), "wb") as fh:
            fh.write(data)
        return base64.b64encode(data).decode("ascii")
    except Exception:
        return None


def _extract_subs_text(info):
    """Transcripción base a partir de subtítulos (auto o manuales)."""
    for key in ("subtitles", "automatic_captions"):
        subs = info.get(key) or {}
        for lang in ("es", "es-orig", "es-MX", "es-419", "en", "en-orig"):
            fmts = subs.get(lang)
            if not fmts:
                continue
            url = chosen = None
            for f in fmts:
                if f.get("ext") in ("json3", "srv3", "vtt"):
                    url, chosen = f.get("url"), f.get("ext")
                    break
            if not url and fmts:
                url, chosen = fmts[0].get("url"), fmts[0].get("ext")
            if not url:
                continue
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
                text = _parse_subs(raw, chosen)
                if text:
                    return text
            except Exception:
                continue
    return ""


def _parse_subs(raw, ext):
    import re
    import json as _json
    if ext == "json3" or raw.lstrip().startswith("{"):
        try:
            data = _json.loads(raw)
            parts = []
            for ev in data.get("events", []):
                for seg in (ev.get("segs") or []):
                    t = seg.get("utf8")
                    if t:
                        parts.append(t)
            return re.sub(r"\s+", " ", "".join(parts)).strip()
        except Exception:
            pass
    lines = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("WEBVTT") or "-->" in ln or ln.isdigit():
            continue
        lines.append(re.sub(r"<[^>]+>", "", ln))
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def _download_scaled_video(url, video_dir, vid):
    """Descarga la mínima resolución y la escala a 256 px de alto (256h)."""
    out = os.path.join(video_dir, f"{vid}.mp4")
    if os.path.exists(out):
        return out
    # Formato progresivo (un solo archivo: video+audio) -> no requiere merge.
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": ("worst[vcodec!=none][acodec!=none][ext=mp4]/"
                   "worst[vcodec!=none][acodec!=none]/worst"),
        "outtmpl": os.path.join(video_dir, f"{vid}.src.%(ext)s"),
        "http_headers": {"User-Agent": UA},
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception:
        return None
    srcs = glob.glob(os.path.join(video_dir, f"{vid}.src.*"))
    if not srcs:
        return None
    src = srcs[0]
    try:
        subprocess.run(
            [FFMPEG, "-y", "-i", src, "-vf", "scale=-2:256",
             "-loglevel", "error", out],
            check=True,
        )
        os.remove(src)
        return out
    except Exception:
        return src
