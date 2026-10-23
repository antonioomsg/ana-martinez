"""Genera la web estática de Ana Martínez en docs/ a partir de data/content.json.

Diseño: Figma "Dream-Team" › página "Pg web ANA" (HOME PAGE, PROYECTOS, MURALES,
FLOTABILIDAD NEUTRA). Las páginas usan rutas relativas para funcionar en GitHub Pages.
"""
import html
import json
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
      <li>{item("panuelos/", "PAÑUELOS", "panuelos")}</li>
      <li>{item("sobre-mi/", "SOBRE MÍ", "sobre-mi")}</li>
      <li>{item("contacto/", "CONTACTO", "contacto")}</li>
    </ul>
    <button class="cart-open" type="button" aria-label="Abrir la cesta">CESTA <span data-cart-count>0</span></button>
  </nav>
</header>
<aside class="cart" aria-label="Cesta" hidden>
  <div class="cart-panel">
    <header><h2>CESTA</h2><button class="cart-close" type="button" aria-label="Cerrar">×</button></header>
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
  <p class="footer-lead">Cada pieza es única. Para recibir más información déjanos tu email y nos pondremos en contacto contigo</p>
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


def render_text(items):
    out = []
    for t in items:
        if isinstance(t, dict) and "pdf" in t:
            out.append(f'<p><a class="btn-link" href="{e(t["pdf"])}" rel="noopener">{e(t["label"])} ↗</a></p>')
        elif isinstance(t, dict) and "youtube" in t:
            out.append(f'<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{e(t["youtube"])}" '
                       'title="Vídeo" loading="lazy" allowfullscreen></iframe></div>')
        elif t.startswith("http"):
            out.append(f'<p><a class="btn-link" href="{e(t)}" rel="noopener">Ver documentación ↗</a></p>')
        else:
            out.append("<p>" + e(t).replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>")
    return "\n".join(out)


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
    for p in posts:
        folder, sec_title = next(((f, t) for c, f, t, _ in SECCIONES if c == p["category"]), ("proyectos", "Proyectos"))
        sib = order.get(p["category"], [])
        i = sib.index(p) if p in sib else -1
        prev_ = sib[i - 1] if i > 0 else None
        next_ = sib[i + 1] if 0 <= i < len(sib) - 1 else None
        imgs = "\n".join(
            f'<figure><button type="button" class="zoomable" data-index="{k}" aria-label="Ampliar foto">'
            f'<img src="{e(im["src"])}" alt="{e(im["alt"])}" loading="lazy"></button></figure>'
            for k, im in enumerate(p["images"]))
        pager = '<nav class="pager">'
        pager += f'<a href="../{prev_["slug"]}/">← {e(prev_["title"])}</a>' if prev_ else "<span></span>"
        pager += f'<a href="../../{folder}/">{sec_title.upper()}</a>'
        pager += f'<a href="../{next_["slug"]}/">{e(next_["title"])} →</a>' if next_ else "<span></span>"
        pager += "</nav>"
        body = f"""<article class="obra">
  <header class="obra-head">
    <h1>{e(p["title"].upper())}</h1>
    <p class="obra-date">{fecha(p["date"])}</p>
  </header>
  <div class="obra-text">{render_text(p["text"])}</div>
  <div class="obra-gallery" data-gallery>{imgs}</div>
  {pager}
</article>
{tienda.LIGHTBOX}"""
        first = next((t for t in p["text"] if isinstance(t, str) and len(t) > 40), p["title"])
        write(f"obra/{p['slug']}/index.html", page("../../", p["title"], body, current=folder, desc=first[:155]))

    # Sobre mí
    bio = data["pages"]["bio"]
    texto = [t for t in bio["text"] if not (isinstance(t, str) and t in ("BIO", "CV"))]
    foto = bio["images"][0]["src"] if bio["images"] else ""
    write("sobre-mi/index.html", page("../", "Sobre mí", f"""<article class="bio">
  <figure class="bio-photo"><img src="{e(foto)}" alt="Retrato de Ana Martínez"></figure>
  <div class="bio-text">
    <h1>SOBRE MÍ</h1>
    {render_text(texto)}
  </div>
</article>""", current="sobre-mi"))

    # Contacto
    write("contacto/index.html", page("../", "Contacto", f"""<section class="contacto">
  <h1>CONTACTO</h1>
  <p>Murales por encargo, proyectos, talleres y obra disponible.</p>
  <p class="contacto-mail"><a href="mailto:{EMAIL}">{EMAIL}</a></p>
  <p class="contacto-redes"><a href="{INSTAGRAM}" rel="noopener">Instagram</a> · <a href="{YOUTUBE}" rel="noopener">YouTube</a></p>
</section>""", current="contacto"))

    build_tienda()
    print(f"OK docs/: {len(posts)} fichas + portada, 3 secciones, sobre mí, contacto")


def build_tienda():
    data = json.loads((ROOT / "data" / "panuelos.json").read_text())
    (OUT / "assets" / "products.js").write_text(tienda.products_js(data))
    write("panuelos/index.html", page("../", "Pañuelos", tienda.listado("../", data), current="panuelos",
                                      desc="Carrés de seda de Ana Martínez, nacidos de su pintura."))
    for p in data["productos"]:
        write(f"panuelos/{p['slug']}/index.html",
              page("../../", f"Carré {p['nombre']}", tienda.ficha("../../", p, data), current="panuelos",
                   desc=p["descripcion"][:155], cls="pdp-page"))


if __name__ == "__main__":
    build()
