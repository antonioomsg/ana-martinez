"""Genera la web estática de Ana Martínez en docs/ a partir de data/content.json.

Diseño: Figma "Dream-Team" › página "Pg web ANA" (HOME PAGE, PROYECTOS, MURALES,
FLOTABILIDAD NEUTRA). Las páginas usan rutas relativas para funcionar en GitHub Pages.
"""
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import tienda  # noqa: E402

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT = ROOT / "docs"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
SECCIONES = [
    # (categoría WP, carpeta, título, columnas de la rejilla)
    ("PROYECTOS", "proyectos", "Proyectos", 3),
    ("PINTAMENTO", "murales", "Murales", 2),
    ("TALLERES", "talleres", "Talleres", 3),
]
EMAIL = "ana@ana-martinez.com"
INSTAGRAM = "https://www.instagram.com/anamartinez_studio/"
YOUTUBE = "https://www.youtube.com/user/aninanona"

e = html.escape


def fecha(iso):
    y, m, _ = iso.split("-")
    return f"{MESES[int(m) - 1]}, {y}"


def nav(r, current=""):
    def item(href, label, key):
        cls = ' aria-current="page"' if key == current else ""
        return f'<a href="{r}{href}"{cls}>{label}</a>'

    sub = "".join(item(f"{f}/", t, f) for _, f, t, _ in SECCIONES)
    return f"""<header class="site-header">
  <nav class="nav" aria-label="Principal">
    <a class="nav-brand" href="{r}index.html">ANA MARTINEZ</a>
    <button class="nav-toggle" aria-expanded="false" aria-controls="nav-menu" aria-label="Abrir menú">
      <span></span><span></span><span></span>
    </button>
    <ul class="nav-menu" id="nav-menu">
      <li class="has-sub"><button class="sub-toggle" aria-expanded="false">COLECCIONES</button>
        <div class="sub">{sub}</div></li>
      <li class="has-sub"><button class="sub-toggle" aria-expanded="false"{' aria-current="page"' if current == "ediciones" else ""}>EDICIONES</button>
        <div class="sub">{item("ediciones/", "Todas", "sub-ediciones")}{item("panuelos/", "Pañuelos", "sub-panuelos")}{item("laminas/", "Láminas", "sub-laminas")}</div></li>
      <li>{item("sobre-mi/", "SOBRE MÍ", "sobre-mi")}</li>
      <li>{item("contacto/", "CONTACTO", "contacto")}</li>
    </ul>
    <button class="cart-open" type="button" aria-label="Abrir la cesta">CESTA <span data-cart-count>0</span></button>
  </nav>
</header>
<aside class="cart" aria-label="Cesta" hidden>
  <div class="cart-panel">
    <header><h2>CESTA</h2><button class="cart-close" type="button" aria-label="Cerrar"><svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true" focusable="false"><path d="M.5.5l10 10M10.5.5l-10 10" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button></header>
    <div class="cart-items" data-cart-items></div>
    <footer>
      <p class="cart-total">Total <span data-cart-total>0 €</span></p>
      <button class="btn-dark cart-checkout" type="button">FINALIZAR COMPRA</button>
    </footer>
  </div>
</aside>
<dialog class="demo-note">
  <h2>Tienda en preparación</h2>
  <p>Gracias por tu interés. La tienda online de pañuelos todavía no acepta pedidos: esta es una vista previa.</p>
  <p>Si quieres uno, escríbenos a <a href="mailto:{EMAIL}?subject=Pa%C3%B1uelos">{EMAIL}</a> y te contamos.</p>
  <form method="dialog"><button class="btn-dark">CERRAR</button></form>
</dialog>"""


def footer(r):
    return f"""<footer class="site-footer">
  <img class="firma" src="{r}assets/firma.png" alt="Ana Martínez" width="325" height="89">
  <div class="footer-lead bi">
    <p lang="es">Cada pieza es única. Para recibir más información déjanos tu email y nos pondremos en contacto contigo.</p>
    <p lang="en">Every piece is unique. Leave us your email for more information and we will get in touch.</p>
  </div>
  <form class="footer-form" action="mailto:{EMAIL}" method="post" enctype="text/plain">
    <label class="sr-only" for="f-email">Email</label>
    <input id="f-email" name="email" type="email" placeholder="Email" required>
    <button type="submit">ENVIAR</button>
  </form>
  <div class="footer-links">
    <div><a href="{r}sobre-mi/">SOBRE MÍ</a><a href="{r}contacto/">CONTACTO</a></div>
    <div><a href="{INSTAGRAM}" rel="noopener">INSTAGRAM</a><a href="{YOUTUBE}" rel="noopener">YOUTUBE</a></div>
  </div>
  <p class="copy">© 2026 ANA MARTINEZ</p>
</footer>"""


def page(r, title, body, current="", desc="Ana Martínez, artista. Pintura, murales, proyectos y talleres.", cls=""):
    full = "Ana Martínez" if title == "Ana Martínez" else f"{title} · Ana Martínez"
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full)}</title>
<meta name="description" content="{e(desc)}">
<link rel="icon" href="{r}assets/firma.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500&family=Cormorant+Garamond:ital,wght@1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{r}assets/style.css">
</head>
<body class="{cls}">
{nav(r, current)}
<main id="main">
{body}
</main>
{footer(r)}
<script>window.AM_ROOT = "{r}";</script>
<script src="{r}assets/products.js" defer></script>
<script src="{r}assets/site.js" defer></script>
</body>
</html>
"""


def write(rel, content):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def card(r, p):
    img = f'<img src="{e(p["cover"])}" alt="" loading="lazy">' if p["cover"] else ""
    return f"""<a class="card" href="{r}obra/{p["slug"]}/">
  {img}<span class="card-veil"></span>
  <span class="card-text"><span class="card-title">{e(p["title"].upper())}</span>
  <span class="card-date">{fecha(p["date"])}</span></span>
</a>"""


def video_embed(url):
    m = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})", url)
    if m:
        return f"https://www.youtube-nocookie.com/embed/{m.group(1)}"
    m = re.search(r"vimeo\.com/(\d+)", url)
    return f"https://player.vimeo.com/video/{m.group(1)}" if m else None


def vendido(src):
    """Estado de concepto: ~1 de cada 3 cuadros aparece vendido (fijo por imagen)."""
    return int(hashlib.md5(src.encode()).hexdigest(), 16) % 100 < 35


def figura(k, im, c, proyecto):
    img = (f'<button type="button" class="zoomable" data-index="{k}" aria-label="Ampliar foto">'
           f'<img src="{e(im["src"])}" alt="{e((c or {}).get("titulo") or im["alt"])}" loading="lazy"></button>')
    if not c or not c.get("es_obra") or not c.get("titulo"):
        return f"<figure>{img}</figure>"
    datos = " · ".join(x for x in (c.get("tecnica"), c.get("medidas")) if x)
    if vendido(im["src"]):
        punto = '<span class="dot dot-sold" title="Vendido · Sold"><span class="sr-only">Vendido</span></span>'
    else:
        punto = (f'<button type="button" class="dot dot-free" title="Disponible · Available" aria-label="Disponible: consultar a la artista" '
                 f'data-inquiry data-img="{e(im["src"])}" data-titulo="{e(c["titulo"])}" data-datos="{e(datos)}" '
                 f'data-proyecto="{e(proyecto)}"></button>')
    return (f'<figure>{img}<figcaption class="cartela">{punto}<span class="cartela-text">'
            f'<span class="cartela-titulo">{e(c["titulo"])}</span><span class="cartela-datos">{e(datos)}</span></span>'
            f'</figcaption></figure>')


INQUIRY = """<dialog class="inquiry" aria-labelledby="inq-title">
  <form method="dialog" class="inq-close-form"><button class="inq-close" aria-label="Cerrar"><svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true" focusable="false"><path d="M.5.5l10 10M10.5.5l-10 10" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button></form>
  <div class="inq-grid">
    <figure class="inq-img"><img alt=""></figure>
    <form class="inq-form" data-email="ana@ana-martinez.com">
      <p class="eyebrow">CONSULTAR OBRA · ENQUIRE</p>
      <h2 id="inq-title"></h2>
      <p class="inq-datos muted"></p>
      <label>Nombre · Name<input name="nombre" autocomplete="name"></label>
      <label>Email<input name="email" type="email" autocomplete="email"></label>
      <label>Mensaje · Message<textarea name="mensaje" rows="9"></textarea></label>
      <button class="btn-buy" type="submit">Enviar · Send</button>
      <p class="muted inq-note">Se abrirá tu programa de correo con el mensaje listo para enviar a Ana.</p>
    </form>
  </div>
</dialog>"""


def documento(doc):
    """Hoja de sala / catálogo integrado en la ficha (en vez del enlace al PDF)."""
    partes = []
    if doc.get("lugar_fechas"):
        partes.append(f'<p class="doc-lugar">{e(doc["lugar_fechas"])}</p>')
    es = render_text(doc.get("es", []))
    if doc.get("firma"):
        es += f'<p class="doc-firma">{e(doc["firma"])}</p>'
    partes.append(bilingue(es, render_text(doc.get("en", []))))
    return f'<section class="doc">{"".join(partes)}</section>'


def render_text(items):
    out = []
    for t in items:
        if isinstance(t, dict) and "pdf" in t:
            out.append(f'<p><a class="btn-link" href="{e(t["pdf"])}" rel="noopener">{e(t["label"])} ↗</a></p>')
        elif isinstance(t, dict) and "youtube" in t:
            out.append(f'<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{e(t["youtube"])}" '
                       'title="Vídeo" loading="lazy" allowfullscreen></iframe></div>')
        elif t.startswith("http") and (vid := video_embed(t)):
            out.append(f'<div class="video"><iframe src="{e(vid)}" title="Vídeo" loading="lazy" allowfullscreen></iframe></div>')
        elif t.startswith("http"):
            out.append(f'<p><a class="btn-link" href="{e(t)}" rel="noopener">Ver documentación ↗</a></p>')
        else:
            out.append("<p>" + e(t).replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>")
    return "\n".join(out)


def bilingue(es, en):
    """Bloque de texto con español a la izquierda e inglés a la derecha (como en el Figma)."""
    if not en:
        return f'<div class="bi bi-one"><div lang="es">{es}</div></div>'
    return (f'<div class="bi"><div lang="es"><p class="lang-tag">ES</p>{es}</div>'
            f'<div lang="en"><p class="lang-tag">EN</p>{en}</div></div>')


def es_texto(t):
    return isinstance(t, str) and not t.startswith("http")


def build():
    data = json.loads((ROOT / "data" / "content.json").read_text())
    posts = data["posts"]
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / ".nojekyll").write_text("")

    # Portada
    write("index.html", page("", "Ana Martínez", f"""<section class="hero">
  <img src="assets/hero.png" alt="Acuarela de Ana Martínez: dos figuras de niñas en azul turquesa, una con gorro rojo">
  <a class="hero-ig" href="{INSTAGRAM}" rel="noopener" aria-label="Instagram"><img src="assets/instagram.svg" alt="" width="48" height="48"></a>
</section>""", cls="home"))

    # Rejillas por sección
    for cat, folder, title, cols in SECCIONES:
        items = [p for p in posts if p["category"] == cat]
        grid = "\n".join(card("../", p) for p in items)
        write(f"{folder}/index.html", page("../", title, f"""<h1 class="sr-only">{title}</h1>
<div class="grid cols-{cols}">
{grid}
</div>""", current=folder))

    # Fichas de obra
    order = {cat: [p for p in posts if p["category"] == cat] for cat, *_ in SECCIONES}
    tr_path = ROOT / "data" / "translations_en.json"
    traducciones = json.loads(tr_path.read_text()) if tr_path.exists() else {}
    doc_path = ROOT / "data" / "documentos.json"
    documentos = json.loads(doc_path.read_text()) if doc_path.exists() else {}
    cuadros = {}
    for f in sorted((ROOT / "data" / "cuadros").glob("*.json")):
        cuadros.update(json.loads(f.read_text()))
    curador = {}
    for f in sorted((ROOT / "data" / "textos_curador").glob("*.json")):
        curador.update(json.loads(f.read_text()))
    for p in posts:
        folder, sec_title = next(((f, t) for c, f, t, _ in SECCIONES if c == p["category"]), ("proyectos", "Proyectos"))
        sib = order.get(p["category"], [])
        i = sib.index(p) if p in sib else -1
        prev_ = sib[i - 1] if i > 0 else None
        next_ = sib[i + 1] if 0 <= i < len(sib) - 1 else None
        imgs = "\n".join(figura(k, im, cuadros.get(im["src"]), p["title"].capitalize()) for k, im in enumerate(p["images"]))
        pager = '<nav class="pager">'
        pager += f'<a href="../{prev_["slug"]}/">← {e(prev_["title"])}</a>' if prev_ else "<span></span>"
        pager += f'<a href="../../{folder}/">{sec_title.upper()}</a>'
        pager += f'<a href="../{next_["slug"]}/">{e(next_["title"])} →</a>' if next_ else "<span></span>"
        pager += "</nav>"
        tr = traducciones.get(p["slug"], {})
        title_en = tr.get("title_en") or p.get("title_en")
        en = tr.get("text_en") or [t for t in p.get("text_en") or [] if es_texto(t)]
        es = [t for t in p["text"] if es_texto(t)]
        media = [t for t in p["text"] if not es_texto(t)]
        doc = documentos.get(p["slug"])
        if doc:  # el PDF se integra en la página: fuera el botón de enlace
            media = [t for t in media if not (isinstance(t, dict) and "pdf" in t)]
        if not es and p["slug"] in curador:
            es, en = curador[p["slug"]]["es"], curador[p["slug"]]["en"]
        sub = (f'<p class="obra-en">{e(title_en)}</p>'
               if title_en and title_en.strip().lower() != p["title"].strip().lower() else "")
        texto = bilingue(render_text(es), render_text(en)) if es else ""
        body = f"""<article class="obra">
  <header class="obra-head">
    <h1>{e(p["title"].upper())}</h1>
    {sub}
    <p class="obra-date">{fecha(p["date"])}</p>
  </header>
  <div class="obra-text">{texto}{documento(doc) if doc else ""}{render_text(media)}</div>
  <div class="obra-gallery" data-gallery>{imgs}</div>
  {pager}
</article>
{tienda.LIGHTBOX}
{INQUIRY}"""
        first = next((t for t in p["text"] if isinstance(t, str) and len(t) > 40), p["title"])
        write(f"obra/{p['slug']}/index.html", page("../../", p["title"], body, current=folder, desc=first[:155]))

    # Sobre mí: foto con marco en L a la izquierda, texto a la derecha; debajo ES | EN
    bio = json.loads((ROOT / "data" / "bio.json").read_text())
    cv = next((t["pdf"] for t in data["pages"]["bio"]["text"] if isinstance(t, dict) and "pdf" in t), None)
    cv_btn = f'<a class="btn-link" href="{e(cv)}" rel="noopener">CV ↗</a>' if cv else ""
    write("sobre-mi/index.html", page("../", "Sobre mí", f"""<article class="bio2">
  <h1 class="bio2-title">Sobre mí <span class="en-sub" lang="en">About</span></h1>
  <div class="bio2-hero">
    <figure class="bio2-photo"><img src="../assets/ana-martinez.jpg" alt="Retrato de Ana Martínez"></figure>
    <div class="bio2-intro">
      <h2>Biografía <span class="en-sub" lang="en">Biography</span></h2>
      <p class="bio2-lead"><strong>{e(bio["lead_es"])}</strong></p>
      <p class="bio2-lead-en" lang="en">{e(bio["lead_en"])}</p>
      {cv_btn}
    </div>
  </div>
  {bilingue(render_text(bio["es"]), render_text(bio["en"]))}
</article>""", current="sobre-mi"))

    # Contacto
    write("contacto/index.html", page("../", "Contacto", f"""<section class="contacto">
  <h1>CONTACTO</h1>
  {bilingue("<p>Murales por encargo, proyectos, talleres y obra disponible.</p>",
            "<p>Commissioned murals, projects, workshops and available work.</p>")}
  <p class="contacto-mail"><a href="mailto:{EMAIL}">{EMAIL}</a></p>
  <p class="contacto-redes"><a href="{INSTAGRAM}" rel="noopener">Instagram</a> · <a href="{YOUTUBE}" rel="noopener">YouTube</a></p>
</section>""", current="contacto"))

    build_tienda()
    print(f"OK docs/: {len(posts)} fichas + portada, 3 secciones, sobre mí, contacto")


def build_tienda():
    ed = json.loads((ROOT / "data" / "ediciones.json").read_text())
    productos = (json.loads((ROOT / "data" / "panuelos.json").read_text())["productos"]
                 + json.loads((ROOT / "data" / "laminas.json").read_text())["productos"])
    (OUT / "assets" / "products.js").write_text(tienda.products_js(ed, productos))
    for clave, titulo, _ in tienda.FILTROS:
        write(f"{clave}/index.html", page("../", "Ediciones" if clave == "ediciones" else titulo,
                                          tienda.listado("../", ed, productos, clave), current="ediciones",
                                          desc="Pañuelos de seda y láminas de Ana Martínez, nacidos de su pintura."))
    for p in productos:
        tipo = ed["tipos"][p["tipo"]]
        write(f"{tipo['dir']}/{p['slug']}/index.html",
              page("../../", tienda.nombre(p, tipo), tienda.ficha("../../", p, ed, productos), current="ediciones",
                   desc=p["descripcion"][:155], cls="pdp-page"))

if __name__ == "__main__":
    build()
