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
import archivo_drive  # noqa: E402
import tienda  # noqa: E402
import editable  # noqa: E402
from editable import cargar_lotes, campo, ed, foto, t, tx  # noqa: E402

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT = ROOT / "docs"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
SECCIONES = [
    # (categoría WP, carpeta, clave del título en sitio.json › textos, columnas de la rejilla)
    ("PROYECTOS", "proyectos", "menu_proyectos", 3),
    ("PINTAMENTO", "murales", "menu_murales", 2),
    ("TALLERES", "talleres", "menu_talleres", 3),
]
EMAIL = "ana@ana-martinez.com"
INSTAGRAM = "https://www.instagram.com/anamartinez_studio/"
YOUTUBE = "https://www.youtube.com/user/aninanona"
ORIGEN = json.loads((ROOT / "data" / "fotos_origen.json").read_text())
SITIO = json.loads((ROOT / "data" / "sitio.json").read_text())
# Huella de cada fichero de data/ con el que se genera la página: el editor la manda al guardar y
# el Apps Script no guarda si los datos han cambiado desde entonces (evita escribir en otra entrada).
HUELLAS = {str(f.relative_to(ROOT / "data")): hashlib.md5(f.read_bytes()).hexdigest()
           for f in sorted((ROOT / "data").rglob("*.json"))}
editable.TEXTOS.update(SITIO["textos"])

e = html.escape


def src(r, u):
    """Fotos del repo (assets/…) con la ruta relativa de la página; las externas o ya relativas (../) tal cual."""
    return r + u if u.startswith("assets/") else u


def fecha(iso):
    y, m, _ = iso.split("-")
    return f"{MESES[int(m) - 1]}, {y}"


def nav(r, current=""):
    def item(href, label, key):
        cls = ' aria-current="page"' if key == current else ""
        return f'<a href="{r}{href}"{cls}>{label}</a>'

    sub = "".join(item(f"{f}/", t(k, lapiz=True), f) for _, f, k, _ in SECCIONES)
    return f"""<header class="site-header">
  <nav class="nav" aria-label="Principal">
    <a class="nav-brand" href="{r}index.html">ANA MARTINEZ</a>
    <button class="nav-toggle" aria-expanded="false" aria-controls="nav-menu" aria-label="Abrir menú">
      <span></span><span></span><span></span>
    </button>
    <ul class="nav-menu" id="nav-menu">
      <li class="has-sub"><button class="sub-toggle" aria-expanded="false">{t("menu_colecciones", lapiz=True)}</button>
        <div class="sub">{sub}</div></li>
      <li class="has-sub"><button class="sub-toggle" aria-expanded="false"{' aria-current="page"' if current == "ediciones" else ""}>{t("menu_ediciones", lapiz=True)}</button>
        <div class="sub">{item("ediciones/", t("menu_todas", lapiz=True), "sub-ediciones")}{item("panuelos/", t("menu_panuelos", lapiz=True), "sub-panuelos")}{item("laminas/", t("menu_laminas", lapiz=True), "sub-laminas")}</div></li>
      <li>{item("sobre-mi/", t("menu_sobre_mi", lapiz=True), "sobre-mi")}</li>
      <li>{item("contacto/", t("menu_contacto", lapiz=True), "contacto")}</li>
    </ul>
    <button class="cart-open" type="button" aria-label="Abrir la cesta">{t("menu_cesta", lapiz=True)} <span data-cart-count>0</span></button>
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
    <p lang="es"{ed(["sitio.json", "pie_es"])}>{e(SITIO["pie_es"])}</p>
    <p lang="en"{ed(["sitio.json", "pie_en"])}>{e(SITIO["pie_en"])}</p>
  </div>
  <form class="footer-form" action="mailto:{EMAIL}" method="post" enctype="text/plain">
    <label class="sr-only" for="f-email">Email</label>
    <input id="f-email" name="email" type="email" placeholder="Email" required>
    <button type="submit">{t("pie_enviar", lapiz=True)}</button>
  </form>
  <div class="footer-links">
    <div><a href="{r}sobre-mi/">{t("menu_sobre_mi", lapiz=True)}</a><a href="{r}contacto/">{t("menu_contacto", lapiz=True)}</a></div>
    <div><a href="{INSTAGRAM}" rel="noopener">{t("pie_instagram", lapiz=True)}</a><a href="{YOUTUBE}" rel="noopener">{t("pie_youtube", lapiz=True)}</a></div>
  </div>
  <p class="copy">{t("pie_copyright")}</p>
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
<script>window.AM_ROOT = "{r}"; window.AM_EDITOR = {json.dumps(SITIO.get("editor_url", ""))}; window.AM_DATOS = {json.dumps(HUELLAS)};</script>
<script src="{r}assets/products.js" defer></script>
<script src="{r}assets/site.js" defer></script>
<script src="{r}assets/revision.js" defer></script>
<script src="{r}assets/editor.js" defer></script>
</body>
</html>
"""


def write(rel, content):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def card(r, p):
    marca = foto(foto=["content.json", "posts", p["_i"], "cover"], slug=p["slug"])
    img = f'<img src="{e(src(r, p["cover"]))}" alt="" loading="lazy"{marca}>' if p["cover"] else ""
    return f"""<a class="card" href="{r}obra/{p["slug"]}/">
  {img}<span class="card-veil"></span>
  <span class="card-text"><span class="card-title"{ed(["content.json", "posts", p["_i"], "title"], raw=p["title"])}>{e(p["title"].upper())}</span>
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
    src = ORIGEN.get(src, src)  # mismo sorteo que cuando la foto estaba en el WordPress
    return int(hashlib.md5(src.encode()).hexdigest(), 16) % 100 < 35


def figura(r, k, im, c, proyecto, ruta=None, slug=None):
    img = (f'<button type="button" class="zoomable" data-index="{k}" aria-label="Ampliar foto">'
           f'<img src="{e(src(r, im["src"]))}" alt="{e((c or {}).get("titulo") or im["alt"])}" loading="lazy"></button>')
    marca = foto(galeria=ruta, slug=slug, cartela=[c["_f"], c["_k"]] if c and c.get("_f") else None,
                 estado=None if not c or c.get("estado") or not c.get("es_obra") else ("vendido" if vendido(im["src"]) else "disponible"))
    if not c or not c.get("es_obra") or not c.get("titulo"):
        return f'<figure id="img-{k}"{marca}>{img}</figure>'
    datos = " · ".join(x for x in (c.get("tecnica"), c.get("medidas")) if x)
    estado_real = c.get("estado")  # "vendido" / "disponible" fijado a mano manda sobre el concepto
    es_vendido = (estado_real == "vendido") if estado_real in ("vendido", "disponible") else vendido(im["src"])
    ruta_estado = [c["_f"], c["_k"], "estado"]
    marca_estado = f' data-e-abre="Estado"{ed(ruta_estado).replace("data-e=", "data-e-campo=")}'
    estado_campo = campo("Estado de la obra", "vendido" if es_vendido else "disponible", ruta_estado,
                         opciones=["disponible", "vendido"])
    if es_vendido:
        estado = (f'<span class="estado estado-sold"{marca_estado}><span class="dot dot-sold" aria-hidden="true"></span>'
                  'Vendido <span lang="en">· Sold</span></span>')
    else:
        estado = (f'<button type="button" class="estado estado-free"{marca_estado} data-inquiry data-img="{e(src(r, im["src"]))}" '
                  f'data-titulo="{e(c["titulo"])}" data-datos="{e(datos)}" data-proyecto="{e(proyecto)}">'
                  f'<span class="dot dot-free" aria-hidden="true"></span>Disponible · <u>Consultar</u> '
                  f'<span lang="en">· Enquire</span></button>')
    return (f'<figure id="img-{k}"{marca}>{img}<figcaption class="cartela"><span class="cartela-text">'
            f'<span class="cartela-titulo"{ed([c["_f"], c["_k"], "titulo"])}>{e(c["titulo"])}</span>'
            f'<span class="cartela-datos">{cartela_datos(c)}</span>'
            f'{estado}{estado_campo}</span></figcaption></figure>')


def cartela_datos(c):
    """Técnica · medidas, cada una editable por separado."""
    partes = [f'<span{ed([c["_f"], c["_k"], k])}>{e(c[k])}</span>' for k in ("tecnica", "medidas") if c.get(k)]
    return " · ".join(partes)


INQUIRY = """<dialog class="inquiry" aria-labelledby="inq-title">
  <div class="inq-bar">
    <p class="eyebrow">CONSULTAR OBRA · ENQUIRE</p>
    <form method="dialog"><button class="inq-close" aria-label="Cerrar"><svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true" focusable="false"><path d="M.5.5l10 10M10.5.5l-10 10" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button></form>
  </div>
  <div class="inq-grid">
    <figure class="inq-img"><img alt=""></figure>
    <form class="inq-form" data-email="ana@ana-martinez.com">
      <h2 id="inq-title"></h2>
      <p class="inq-datos muted"></p>
      <label>Nombre · Name<input name="nombre" autocomplete="name"></label>
      <label>Email<input name="email" type="email" autocomplete="email"></label>
      <label>Mensaje · Message<textarea name="mensaje" rows="8"></textarea></label>
      <button class="btn-buy" type="submit">Enviar · Send</button>
      <p class="muted inq-note">Se abrirá tu programa de correo con el mensaje listo para enviar a Ana.</p>
    </form>
  </div>
</dialog>"""


def documento(doc, slug):
    """Hoja de sala / catálogo integrado en la ficha (en vez del enlace al PDF)."""
    base = ["documentos.json", slug]
    partes = []
    if doc.get("lugar_fechas"):
        partes.append(f'<p class="doc-lugar"{ed(base + ["lugar_fechas"])}>{e(doc["lugar_fechas"])}</p>')
    es = render_text(doc.get("es", []), base + ["es"])
    if doc.get("firma"):
        es += f'<p class="doc-firma"{ed(base + ["firma"])}>{e(doc["firma"])}</p>'
    partes.append(bilingue(es, render_text(doc.get("en", []), base + ["en"])))
    return f'<section class="doc">{"".join(partes)}</section>'


def render_text(items, base=None, r=""):
    """Párrafos, vídeos y enlaces. `base`: ruta JSON de la lista; con ella cada texto queda editable.
    `items` puede ser una lista o pares (índice en la lista original, valor) si se ha filtrado."""
    out = []
    pares = items if items and isinstance(items[0], tuple) else list(enumerate(items))
    for j, t in pares:
        ruta = base + [j] if base else None
        if isinstance(t, dict) and "pdf" in t:
            out.append(f'<p><a class="btn-link" href="{e(src(r, t["pdf"]))}" rel="noopener">'
                       f'<span{ed(ruta + ["label"] if ruta else None)}>{e(t["label"])}</span> ↗</a></p>')
        elif isinstance(t, dict) and "youtube" in t:
            out.append(f'<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{e(t["youtube"])}" '
                       'title="Vídeo" loading="lazy" allowfullscreen></iframe></div>')
        elif t.startswith("http") and (vid := video_embed(t)):
            out.append(f'<div class="video"><iframe src="{e(vid)}" title="Vídeo" loading="lazy" allowfullscreen></iframe></div>')
        elif t.startswith("http"):
            out.append(f'<p><a class="btn-link" href="{e(t)}" rel="noopener">Ver documentación ↗</a></p>')
        elif "\n\n" in t:  # varios párrafos de un mismo texto: se editan juntos
            out.append(f'<div class="ed-bloque"{ed(ruta)}><p>' + e(t).replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p></div>")
        else:
            out.append(f"<p{ed(ruta)}>" + e(t).replace("\n", "<br>") + "</p>")
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
    for i, p in enumerate(posts):
        p["_i"] = i
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / ".nojekyll").write_text("")

    # Portada
    write("index.html", page("", "Ana Martínez", f"""<section class="hero">
  <img src="assets/hero.png"{foto(fijo="assets/hero.png")} alt="Acuarela de Ana Martínez: dos figuras de niñas en azul turquesa, una con gorro rojo">
  <a class="hero-ig" href="{INSTAGRAM}" rel="noopener" aria-label="Instagram"><img src="assets/instagram.svg" alt="" width="48" height="48"></a>
</section>""", cls="home"))

    # Rejillas por sección
    for cat, folder, clave, cols in SECCIONES:
        title = tx(clave)
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
    cuadros = cargar_lotes(ROOT / "data" / "cuadros")
    curador = cargar_lotes(ROOT / "data" / "textos_curador")
    for p in posts:
        i_post = ["content.json", "posts", p["_i"]]
        folder, sec_title = next(((f, tx(k)) for c, f, k, _ in SECCIONES if c == p["category"]), ("proyectos", tx("menu_proyectos")))
        sib = order.get(p["category"], [])
        i = sib.index(p) if p in sib else -1
        prev_ = sib[i - 1] if i > 0 else None
        next_ = sib[i + 1] if 0 <= i < len(sib) - 1 else None
        imgs = "\n".join(figura("../../", k, im, cuadros.get(im["src"]), p["title"].capitalize(),
                                 i_post + ["images", k], p["slug"]) for k, im in enumerate(p["images"]))
        pager = '<nav class="pager">'
        pager += f'<a href="../{prev_["slug"]}/">← {e(prev_["title"])}</a>' if prev_ else "<span></span>"
        pager += f'<a href="../../{folder}/">{sec_title.upper()}</a>'
        pager += f'<a href="../{next_["slug"]}/">{e(next_["title"])} →</a>' if next_ else "<span></span>"
        pager += "</nav>"
        tr = traducciones.get(p["slug"], {})
        slug_tr = ["translations_en.json", p["slug"]]
        title_en = tr.get("title_en") or p.get("title_en")
        ruta_title_en = slug_tr + ["title_en"] if tr.get("title_en") else i_post + ["title_en"]
        if tr.get("text_en"):
            en, ruta_en = list(enumerate(tr["text_en"])), slug_tr + ["text_en"]
        else:
            en, ruta_en = [(j, t) for j, t in enumerate(p.get("text_en") or []) if es_texto(t)], i_post + ["text_en"]
        es, ruta_es = [(j, t) for j, t in enumerate(p["text"]) if es_texto(t)], i_post + ["text"]
        media = [(j, t) for j, t in enumerate(p["text"]) if not es_texto(t)]
        doc = documentos.get(p["slug"])
        if doc:  # el PDF se integra en la página: fuera el botón de enlace
            media = [(j, t) for j, t in media if not (isinstance(t, dict) and "pdf" in t)]
        if not es and p["slug"] in curador:
            c = curador[p["slug"]]
            es, ruta_es = list(enumerate(c["es"])), [c["_f"], c["_k"], "es"]
            en, ruta_en = list(enumerate(c["en"])), [c["_f"], c["_k"], "en"]
        if title_en and title_en.strip().lower() != p["title"].strip().lower():
            sub = f'<p class="obra-en"{ed(ruta_title_en)}>{e(title_en)}</p>'
        else:  # igual que el español: no se muestra, pero se puede cambiar desde «Otros datos»
            sub = campo("Título en inglés", title_en or "", ruta_title_en)
        texto = bilingue(render_text(es, ruta_es), render_text(en, ruta_en)) if es else ""
        body = f"""<article class="obra">
  <header class="obra-head">
    <h1{ed(i_post + ["title"], raw=p["title"])}>{e(p["title"].upper())}</h1>
    {sub}
    <p class="obra-date" data-e-abre="Fecha">{fecha(p["date"])}</p>{campo("Fecha", p["date"], i_post + ["date"])}
  </header>
  <div class="obra-text" data-fold>{texto}{documento(doc, p["slug"]) if doc else ""}{render_text(media, i_post + ["text"], "../../")}</div>
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
    cv_btn = f'<a class="btn-link" href="{e(src("../", cv))}" rel="noopener">CV ↗</a>' if cv else ""
    write("sobre-mi/index.html", page("../", tx("sobre_titulo"), f"""<article class="bio2">
  <h1 class="bio2-title">{t("sobre_titulo")} <span class="en-sub" lang="en">{t("sobre_titulo_en")}</span></h1>
  <div class="bio2-hero">
    <figure class="bio2-photo"><img src="../assets/ana-martinez.jpg"{foto(fijo="assets/ana-martinez.jpg")} alt="Retrato de Ana Martínez"></figure>
    <div class="bio2-intro">
      <h2>{t("bio_titulo")} <span class="en-sub" lang="en">{t("bio_titulo_en")}</span></h2>
      <p class="bio2-lead"><strong{ed(["bio.json", "lead_es"])}>{e(bio["lead_es"])}</strong></p>
      <p class="bio2-lead-en" lang="en"{ed(["bio.json", "lead_en"])}>{e(bio["lead_en"])}</p>
      {cv_btn}
    </div>
  </div>
  {bilingue(render_text(bio["es"], ["bio.json", "es"]), render_text(bio["en"], ["bio.json", "en"]))}
</article>""", current="sobre-mi"))

    # Contacto
    write("contacto/index.html", page("../", "Contacto", f"""<section class="contacto">
  <h1>{t("contacto_titulo")}</h1>
  <div class="bi bi-intro"><p lang="es"{ed(["sitio.json", "contacto_es"])}>{e(SITIO["contacto_es"])}</p><p lang="en"{ed(["sitio.json", "contacto_en"])}>{e(SITIO["contacto_en"])}</p></div>
  <p class="contacto-mail"><a href="mailto:{EMAIL}">{EMAIL}</a></p>
  <p class="contacto-redes"><a href="{INSTAGRAM}" rel="noopener">Instagram</a> · <a href="{YOUTUBE}" rel="noopener">YouTube</a></p>
</section>""", current="contacto"))

    build_tienda()
    (OUT / "archivo_drive.json").write_text(json.dumps(archivo_drive.generar(ROOT), ensure_ascii=False))
    print(f"OK docs/: {len(posts)} fichas + portada, 3 secciones, sobre mí, contacto")


def build_tienda():
    ed = json.loads((ROOT / "data" / "ediciones.json").read_text())
    productos = []
    for fichero in ("panuelos.json", "laminas.json"):
        for i, p in enumerate(json.loads((ROOT / "data" / fichero).read_text())["productos"]):
            productos.append(dict(p, _ruta=[fichero, "productos", i]))
    posts = json.loads((ROOT / "data" / "content.json").read_text())["posts"]
    donde = {}  # imagen -> [(proyecto, posición)]
    for post in posts:
        for k, im in enumerate(post["images"]):
            donde.setdefault(im["src"], []).append((post["slug"], k))
    proyecto_de = {g["id"]: g.get("obra_slug") for g in ed["grupos"]}
    for p in productos:
        sitios = donde.get((p.get("obra") or {}).get("img"), [])
        if sitios:  # preferimos el proyecto al que pertenece la pieza
            slug, k = next((x for x in sitios if x[0] == proyecto_de.get(p["grupo"])), sitios[0])
            p["obra"]["href"] = f"obra/{slug}/#img-{k}"
    cartelas = cargar_lotes(ROOT / "data" / "cuadros")
    for p in productos:  # misma ficha que la cartela del cuadro
        c = cartelas.get((p.get("obra") or {}).get("img"))
        if c and c.get("es_obra") and c.get("titulo"):
            p["obra"]["titulo"] = c["titulo"]
            p["obra"]["tecnica"] = " · ".join(x for x in (c.get("tecnica"), c.get("medidas")) if x)
            p["obra"]["_cartela"] = c
    (OUT / "assets" / "products.js").write_text(tienda.products_js(ed, productos))
    for clave, titulo, _ in tienda.FILTROS:
        write(f"{clave}/index.html", page("../", tx("tienda_titulo") if clave == "ediciones" else tx(titulo),
                                          tienda.listado("../", ed, productos, clave), current="ediciones",
                                          desc="Pañuelos de seda y láminas de Ana Martínez, nacidos de su pintura."))
    for p in productos:
        tipo = ed["tipos"][p["tipo"]]
        write(f"{tipo['dir']}/{p['slug']}/index.html",
              page("../../", tienda.nombre(p, tipo), tienda.ficha("../../", p, ed, productos), current="ediciones",
                   desc=p["descripcion"][:155], cls="pdp-page"))

if __name__ == "__main__":
    build()
