# Microservicio TC3005B — La Comer (@lacomer1)

Microservicio con **un solo parser en la capa de APIs** (`Main.py`) que controla
tres servicios independientes, cada uno en su carpeta:

| Servicio | Carpeta | Patrón / técnica |
|---|---|---|
| Crawler | `crawler/` | yt-dlp 2026.03.17 + bs4 + ffmpeg (256h) |
| Indexamiento | `indexamiento/` | **Tubería (pipe-filter)** + SQLite + dashboard Streamlit |
| Búsqueda | `busqueda/` | **Matriz de probabilidad** + **matriz de adyacencia** |

Canal asignado por terminación de matrícula **(1)**: `https://www.youtube.com/@lacomer1/videos`.

## Instalación (entorno virtual)
```powershell
# Crear y activar el entorno virtual (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1            # Git Bash: source .venv/Scripts/activate

# Instalar dependencias (incluye ffmpeg estático imageio-ffmpeg)
pip install -r requirements.txt
python -m playwright install chromium   # solo si vas a regenerar capturas

# Opcional (mejor calidad de resumen/categoría con Gemini):
#   1) Copy-Item .env.example .env   2) pega tu clave en  GEMINI_API_KEY=
#   El modelo se fija con  GEMINI_MODEL=  (p.ej. gemini-2.5-flash).
#   Si no defines clave, usa el modo local automáticamente.
```
Con el entorno activado, todos los comandos `python ...` usan el `.venv`.
Si PowerShell bloquea la activación: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Uso (capa de APIs — parser único)
```bash
# Indexamiento (tubería): descarga e indexa >=30 videos, pausa 90 s entre videos
python Main.py Retrieve --URL https://www.youtube.com/@lacomer1/videos --N 30 --Sleep 90 --Path ./data

# Inspección independiente de la tubería: lista las URLs indexadas
python Main.py List --URL https://www.youtube.com/@lacomer1/videos --Path ./data

# Búsqueda probabilística (imprime probabilidad y matriz de adyacencia)
python Main.py Buscar --Query "Likes > 95"
python Main.py Buscar --Query "Likes > 950000"     # advertencia de baja probabilidad

# Re-genera categoría/resumen con Gemini SIN re-descargar (usa la BD existente)
python Main.py Enrich --Path ./data

# Transcribe con Gemini el audio del video 256h (N videos sin transcripción)
python Main.py TranscribeVideo --N 1 --Path ./data

# Probar el crawler de forma aislada (--no_video omite la descarga de video)
python Main.py Crawl --URL https://www.youtube.com/@lacomer1/videos --N 2
python Main.py Crawl --URL https://www.youtube.com/@lacomer1/videos --N 2 --no_video

# Dashboard (Streamlit): 4 pestañas -> preguntas NL + mosaico 1:5, búsqueda
# probabilística + matriz de adyacencia (heatmap), explorador de datos, gráficas
python Main.py Dashboard --Path ./data        # abre http://localhost:8501

# Ayuda integrada
python Main.py            # lista todos los subcomandos
python Main.py Buscar -h  # ayuda de un subcomando
```

## Pruebas independientes de cada microservicio
```bash
python -m crawler      --URL https://www.youtube.com/@lacomer1/videos --N 2
python -m indexamiento List --URL https://www.youtube.com/@lacomer1/videos --Path ./data
python -m busqueda     --Query "Views > 100" --Path ./data
```

## Prueba dinámica automática (IEEE 29119)
```bash
bash tests/auto_test.sh 1000     # genera tests/results.out con >=1000 búsquedas
```

## Documento
`doc/main.tex` se compila en Overleaf (pdflatex). Antes, regenera los recursos:
```bash
python doc/make_figs.py          # figuras vectorizadas (arquitectura, tubería, búsqueda)
python doc/make_evidence.py      # mosaico 1:5, gráfica, terminales y copia del bash
python doc/make_screenshots.py   # capturas del dashboard (requiere dashboard activo en :8501)
```
Luego sube el contenido de `doc/` (main.tex, figs/, evidencia/, auto_test.sh) a
Overleaf y compila con **pdfLaTeX**.
