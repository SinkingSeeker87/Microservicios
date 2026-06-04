"""Captura pantallas reales del dashboard (Streamlit) con Playwright.

Requiere el dashboard sirviendo en http://localhost:8501 y:
    pip install playwright && python -m playwright install chromium

    python doc/make_screenshots.py
"""
import os
import time
from playwright.sync_api import sync_playwright

URL = os.environ.get("DASH_URL", "http://localhost:8501")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figs")
os.makedirs(OUT, exist_ok=True)

TABS = [
    ("Preguntas", "dash_preguntas.png"),            # pestaña por defecto
    ("Búsqueda probabilística", "dash_busqueda.png"),
    ("Explorador de datos", "dash_explorador.png"),
    ("Gráficas", "dash_graficas.png"),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000},
                                device_scale_factor=2)
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_selector("h1", timeout=60000)
        time.sleep(4)  # deja que se rendericen widgets y mosaico

        # Pestaña 1 (por defecto)
        page.screenshot(path=os.path.join(OUT, TABS[0][1]), full_page=True)
        print("OK", TABS[0][1])

        # Pestañas 2-4: click y captura
        for name, fname in TABS[1:]:
            try:
                page.get_by_role("tab", name=name).first.click()
                time.sleep(3.5)
                page.screenshot(path=os.path.join(OUT, fname), full_page=True)
                print("OK", fname)
            except Exception as exc:
                print("ERROR", fname, exc)

        browser.close()


if __name__ == "__main__":
    main()
