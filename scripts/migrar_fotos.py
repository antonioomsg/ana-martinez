"""Copia al repo las fotos y PDF que la web enlaza del WordPress antiguo y reescribe los JSON.

  python3 scripts/migrar_fotos.py            # descarga lo que falte y reescribe data/
  python3 scripts/migrar_fotos.py --solo-bajar

Cada URL https://www.ana-martinez.com/wp-content/uploads/AAAA/MM/x.jpg pasa a
assets/wp/AAAA/MM/x.jpg (también cuando es clave, como en data/cuadros).
"""
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FICHEROS = ["content.json", "panuelos.json", "laminas.json", "documentos.json",
            "ediciones.json", "bio.json", "translations_en.json", "cuadros/*.json", "textos_curador/*.json"]
URL_RE = re.compile(r"https?://(?:www\.)?ana-martinez\.com/wp-content/uploads/([^\"'\s?#]+\.(?:jpe?g|png|gif|webp|pdf))", re.I)


def local(m):
    """Ruta en el repo, sin tildes ni espacios para no depender de cómo normaliza cada sistema."""
    ruta = unicodedata.normalize("NFKD", urllib.parse.unquote(m.group(1))).encode("ascii", "ignore").decode()
    return "assets/wp/" + ruta.replace(" ", "-")


def ficheros():
    for patron in FICHEROS:
        yield from sorted((ROOT / "data").glob(patron))


def bajar(item):
    url, destino = item
    if destino.exists() and destino.stat().st_size:
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    url = urllib.parse.quote(url.replace("http://", "https://"), safe=":/%")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            destino.write_bytes(r.read())
    except Exception as ex:  # noqa: BLE001
        return f"{url}: {ex}"
    return None


def main():
    urls = {}
    for f in ficheros():
        for m in URL_RE.finditer(f.read_text()):
            urls[m.group(0)] = ROOT / local(m)
    errores = [x for x in ThreadPoolExecutor(8).map(bajar, urls.items()) if x]
    print(f"{len(urls)} enlaces, {len(errores)} errores")
    for x in errores:
        print("  ", x)
    if errores or "--solo-bajar" in sys.argv:
        sys.exit(1 if errores else 0)
    origen = ROOT / "data" / "fotos_origen.json"  # foto del repo -> URL del WordPress (sorteo de «vendido», archivo)
    previo = json.loads(origen.read_text()) if origen.exists() else {}
    for f in ficheros():
        for m in URL_RE.finditer(f.read_text()):
            previo[local(m)] = m.group(0)
    origen.write_text(json.dumps(dict(sorted(previo.items())), ensure_ascii=False, indent=1) + "\n")
    for f in ficheros():
        s = f.read_text()
        nuevo = URL_RE.sub(local, s)
        if nuevo != s:
            f.write_text(nuevo)
            print("reescrito", f.relative_to(ROOT))


if __name__ == "__main__":
    main()
