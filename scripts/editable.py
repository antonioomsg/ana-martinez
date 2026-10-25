"""Marcas del modo edición: cada texto lleva el fichero de data/ y la ruta dentro del JSON.

assets/editor.js las convierte en zonas editables y Apps Script guarda el cambio en ese punto.
"""
import html
import json

e = html.escape


def ed(ruta, raw=None):
    """Atributos para un texto editable en su sitio. `raw`: valor guardado si se muestra transformado (p. ej. en mayúsculas)."""
    if not ruta:
        return ""
    attr = f' data-e="{e(json.dumps(list(ruta), ensure_ascii=False))}"'
    return attr + (f' data-raw="{e(raw)}"' if raw is not None else "")


def campo(etiqueta, valor, ruta):
    """Dato sin texto propio en la página (fecha, precio…): sale en el panel «Otros datos» del modo edición."""
    tipo = "num" if isinstance(valor, (int, float)) and not isinstance(valor, bool) else "txt"
    return (f'<span hidden{ed(ruta)} data-e-etq="{e(etiqueta)}" data-e-tipo="{tipo}" '
            f'data-v="{e(str(valor if valor is not None else ""))}"></span>')


def cargar_lotes(carpeta):
    """Une los JSON de data/<carpeta>/ recordando en `_f` de qué fichero sale cada entrada."""
    out = {}
    for f in sorted(carpeta.glob("*.json")):
        for k, v in json.loads(f.read_text()).items():
            out[k] = dict(v, _f=f"{carpeta.name}/{f.name}", _k=k)
    return out
