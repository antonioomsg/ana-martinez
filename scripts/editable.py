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


def campo(etiqueta, valor, ruta, opciones=None):
    """Dato sin texto propio en la página (fecha, precio…): se cambia con una casilla que solo admite ese dato.
    Con `opciones` es un selector y solo se edita pulsando su elemento en la página (no sale en el formulario general)."""
    tipo = "num" if isinstance(valor, (int, float)) and not isinstance(valor, bool) else "txt"
    extra = f' data-e-opciones="{e("|".join(opciones))}"' if opciones else ""
    return (f'<span hidden{ed(ruta)} data-e-etq="{e(etiqueta)}" data-e-tipo="{tipo}"{extra} '
            f'data-v="{e(str(valor if valor is not None else ""))}"></span>')


TEXTOS = {}  # data/sitio.json › textos (los carga build.py)


def tx(clave):
    """Texto fijo de la web (menú, títulos, botones) tal cual, para atributos o <title>."""
    return TEXTOS[clave]


def t(clave, lapiz=False, mayus=False):
    """Texto fijo editable. `lapiz`: dentro de enlaces o botones, se edita con ✎ y pulsar sigue navegando."""
    v = TEXTOS[clave]
    marca = ed(["sitio.json", "textos", clave], raw=v if mayus else None)
    return f'<span{marca}{" data-e-lapiz" if lapiz else ""}>{e(v.upper() if mayus else v)}</span>'


def foto(**datos):
    """Atributos de una foto editable: data-e-<clave> (listas y rutas en JSON)."""
    return "".join(f' data-e-{k.replace("_", "-")}="{e(json.dumps(v, ensure_ascii=False) if isinstance(v, list) else str(v))}"'
                   for k, v in datos.items() if v is not None)


def cargar_lotes(carpeta):
    """Une los JSON de data/<carpeta>/ recordando en `_f` de qué fichero sale cada entrada."""
    out = {}
    for f in sorted(carpeta.glob("*.json")):
        for k, v in json.loads(f.read_text()).items():
            out[k] = dict(v, _f=f"{carpeta.name}/{f.name}", _k=k)
    return out
