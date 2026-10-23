"""Sección EDICIONES (tienda de demostración): pañuelos y láminas agrupados por proyecto.

Ficha con la disposición de Hermès: tira de 3 fotos con tarjeta de compra flotante
(variante, tamaño, precio), descripción ES | EN y desplegables, uso, y debajo la obra y el
proyecto de los que nace la pieza. Pañuelos: planchado · llevado · detalle.
Láminas: centrada · en casa · detalle del papel.
"""
import html
import json

e = html.escape

LIGHTBOX = """<dialog class="lightbox" aria-label="Foto ampliada">
  <div class="lb-stage"><img class="lb-img" alt=""></div>
  <div class="lb-zoom">
    <button type="button" class="lb-in" aria-label="Acercar">+</button>
    <input type="range" class="lb-range" min="1" max="4" step="0.1" value="1" aria-label="Zoom" orient="vertical">
    <button type="button" class="lb-out" aria-label="Alejar">−</button>
  </div>
  <div class="lb-thumbs"></div>
  <button type="button" class="lb-nav lb-prev" aria-label="Foto anterior">‹</button>
  <button type="button" class="lb-nav lb-next" aria-label="Foto siguiente">›</button>
  <button type="button" class="lb-close" aria-label="Cerrar">×</button>
</dialog>"""

FILTROS = [("ediciones", "Todo", "All"), ("panuelos", "Pañuelos", "Silk carrés"), ("laminas", "Láminas", "Art prints")]


def foto(tipo, name):
    return f"assets/{tipo['dir']}/{name}.jpg"


def precio(n):
    return f"{n} €"


def desde(tipo):
    return min(t["precio"] for t in tipo["tamanos"])


def nombre(p, tipo):
    return f"{tipo['prefijo']} {p['nombre']}"


def card(r, p, ed):
    tipo = ed["tipos"][p["tipo"]]
    c = p["colores"][0]["fotos"]
    href = f"{r}{tipo['dir']}/{p['slug']}/"
    imgs = "".join(
        f'<img class="{"is-on" if i == 0 else ""}" src="{r}{foto(tipo, c[k])}" alt="{e(nombre(p, tipo))}, {alt}" loading="lazy">'
        for i, (k, alt) in enumerate(tipo["vistas"]))
    return f"""<div class="shop-card">
  <div class="shop-media" data-carousel>
    <a href="{href}" tabindex="-1" aria-hidden="true">{imgs}</a>
    <button class="car-btn car-prev" type="button" aria-label="Foto anterior">‹</button>
    <button class="car-btn car-next" type="button" aria-label="Foto siguiente">›</button>
  </div>
  <a class="shop-meta" href="{href}"><span class="shop-kind">{e(tipo["nombre"].upper())}</span>
  <span class="shop-name">{e(nombre(p, tipo))}</span>
  <span class="shop-price">Desde {precio(desde(tipo))}</span></a>
</div>"""


def grupo_header(r, g, n):
    enlace = (f'<a class="group-link" href="{r}obra/{g["obra_slug"]}/">Ver el proyecto ›</a>'
              if g.get("obra_slug") else "")
    fecha = f' <span class="group-date">{e(g["fecha"])}</span>' if g.get("fecha") else ""
    return f"""<header class="group-head">
    <div><h2>{e(g["titulo"])}{fecha}</h2>
    <p class="group-count">{n} {"pieza" if n == 1 else "piezas"} · {n} {"piece" if n == 1 else "pieces"}</p></div>
    {enlace}
  </header>"""


def listado(r, ed, productos, actual):
    filtrados = [p for p in productos if actual == "ediciones" or p["tipo"] == actual]
    seg = "".join(
        f'<a class="seg{" is-active" if k == actual else ""}" href="{r}{k}/"'
        f'{" aria-current=page" if k == actual else ""}>{es}<span lang="en">{en}</span></a>'
        for k, es, en in FILTROS)
    grupos, indice = [], []
    for g in ed["grupos"]:
        items = [p for p in filtrados if p["grupo"] == g["id"]]
        if not items:
            continue
        indice.append(f'<a href="#{g["id"]}">{e(g["titulo"])}</a>')
        bloques = []
        for clave, tipo in ed["tipos"].items():
            sub = [p for p in items if p["tipo"] == clave]
            if not sub:
                continue
            titulo_sub = (f'<h3 class="group-sub">{e(tipo["nombre"])} <span lang="en">· {e(tipo["nombre_en"])}</span></h3>'
                          if actual == "ediciones" else "")
            bloques.append(f'{titulo_sub}<div class="shop-grid">{"".join(card(r, p, ed) for p in sub)}</div>')
        grupos.append(f"""<section class="group" id="{g["id"]}">
  {grupo_header(r, g, len(items))}
  {"".join(bloques)}
</section>""")
    intro = ed if actual == "ediciones" else ed["tipos"][actual]
    titulo = dict((k, es) for k, es, _ in FILTROS)[actual]
    titulo = "Ediciones" if actual == "ediciones" else titulo
    return f"""<section class="shop-intro">
  <h1>{e(titulo)}</h1>
  <div class="bi bi-intro"><p lang="es">{e(intro["intro_es"])}</p><p lang="en">{e(intro["intro_en"])}</p></div>
  <nav class="group-index" aria-label="Proyectos">{"".join(indice)}</nav>
</section>
{"".join(grupos)}"""


def ficha(r, p, ed, productos):
    tipo = ed["tipos"][p["tipo"]]
    g = next(x for x in ed["grupos"] if x["id"] == p["grupo"])
    col = p["colores"][0]
    f = col["fotos"]
    variantes = ""
    etiqueta = tipo["variante"]
    if len(p["colores"]) > 1:
        sw = "".join(
            f'<button type="button" class="swatch{" is-active" if i == 0 else ""}" data-color="{c["id"]}" '
            f'data-label="{e(c["label"])}" data-flat="{r}{foto(tipo, c["fotos"]["plano"])}" '
            f'data-worn="{r}{foto(tipo, c["fotos"]["modelo"])}" data-zoom="{r}{foto(tipo, c["fotos"]["zoom"])}" '
            f'aria-label="{e(c["label"])}" title="{e(c["label"])}" aria-pressed="{"true" if i == 0 else "false"}">'
            f'<img src="{r}{foto(tipo, c["fotos"]["plano"])}" alt=""></button>'
            for i, c in enumerate(p["colores"]))
        variantes = (f'<div class="buy-field"><p class="buy-label">{etiqueta}: <span data-color-label>{e(col["label"])}</span></p>'
                     f'<div class="swatches">{sw}</div></div>')
    elif p["tipo"] == "panuelos":
        variantes = f'<p class="buy-label buy-static">{etiqueta}: <span>{e(col["label"])}</span></p>'
    t0 = tipo["tamanos"][0]
    tallas = "".join(
        f'<button type="button" class="size-opt{" is-active" if i == 0 else ""}" data-size="{t["id"]}" '
        f'data-price="{t["precio"]}" aria-pressed="{"true" if i == 0 else "false"}">'
        f'{e(t["label"])}</button>'
        for i, t in enumerate(tipo["tamanos"]))
    vistas = dict(tipo["vistas"])
    obra = ""
    if p.get("obra"):
        o = p["obra"]
        img = o["img"] if o["img"].startswith("http") else r + o["img"]
        obra = f"""<section class="pdp-obra">
  <figure><img src="{e(img)}" alt="{e(o["titulo"])}, obra de Ana Martínez" loading="lazy"></figure>
  <div>
    <p class="eyebrow">LA OBRA · THE WORK</p>
    <h2>{e(o["titulo"])}</h2>
    <p class="muted">{e(o["tecnica"])}</p>
    <p>{e(nombre(p, tipo))} nace de esta obra de Ana Martínez.</p>
    <p lang="en" class="muted">{e(tipo["prefijo"])} {e(p["nombre"])} is born from this work by Ana Martínez.</p>
  </div>
</section>"""
    parrafos = "".join(f"<p>{e(t)}</p>" for t in g["texto"])
    parrafos_en = "".join(f"<p>{e(t)}</p>" for t in g.get("texto_en", []))
    enlace = (f'<p><a class="btn-link" href="{r}obra/{g["obra_slug"]}/">VER EL PROYECTO</a></p>'
              if g.get("obra_slug") else "")
    proyecto = f"""<section class="pdp-proyecto">
  <p class="eyebrow">EL PROYECTO · THE PROJECT</p>
  <h2>{e(g["titulo"])}</h2>
  {f'<p class="muted">{e(g["fecha"])}</p>' if g.get("fecha") else ""}
  <div class="bi pdp-quote"><blockquote lang="es"><p class="lang-tag">ES</p>{parrafos}</blockquote><blockquote lang="en"><p class="lang-tag">EN</p>{parrafos_en}</blockquote></div>
  <cite>{e(g["fuente"])}</cite>
  {enlace}
</section>"""
    hermanos = [q for q in productos if q["grupo"] == p["grupo"] and q["slug"] != p["slug"]]
    otros = [q for q in productos if q["grupo"] != p["grupo"]][: max(0, 4 - len(hermanos))]
    mas = "\n".join(card(r, q, ed) for q in hermanos + otros)
    acordeon = "".join(f"<details><summary>{e(a)}</summary><p>{e(b)}</p></details>" for a, b in tipo["acordeon"])
    return f"""<article class="pdp" data-slug="{p["slug"]}">
  <nav class="crumbs" aria-label="Migas de pan"><a href="{r}ediciones/">Ediciones</a> › <a href="{r}ediciones/#{g["id"]}">{e(g["titulo"])}</a> › <span aria-current="page">{e(nombre(p, tipo))}</span></nav>
  <div class="pdp-strip">
    <div class="pdp-photos" data-gallery>
    <figure class="pdp-flat"><button type="button" class="zoomable" data-index="0" aria-label="Ampliar foto"><img data-flat-img src="{r}{foto(tipo, f["plano"])}" alt="{e(nombre(p, tipo))}, {vistas["plano"]}"></button></figure>
    <figure><button type="button" class="zoomable" data-index="1" aria-label="Ampliar foto"><img data-worn-img src="{r}{foto(tipo, f["modelo"])}" alt="{e(nombre(p, tipo))}, {vistas["modelo"]}"></button></figure>
    <figure><button type="button" class="zoomable" data-index="2" aria-label="Ampliar foto"><img data-zoom-img src="{r}{foto(tipo, f["zoom"])}" alt="{e(nombre(p, tipo))}, {vistas["zoom"]}"></button></figure>
    </div>
    <div class="pdp-dots" aria-hidden="true"><span class="is-on"></span><span></span><span></span></div>
    <div class="buy-card">
      <p class="buy-kind"><a href="{r}{tipo["dir"]}/">{e(tipo["nombre"])}</a> · <a href="{r}ediciones/#{g["id"]}">{e(g["titulo"])}</a></p>
      <h1>{e(p["nombre"])}</h1>
      <p class="buy-price" aria-live="polite">{precio(t0["precio"])}</p>
      {variantes}
      <div class="buy-field">
        <p class="buy-label">Tamaño · Size</p>
        <div class="sizes" role="group" aria-label="Tamaño">{tallas}</div>
      </div>
      <button class="btn-buy add-to-cart" type="button" data-color="{col["id"]}" data-size="{t0["id"]}">Añadir a la cesta</button>
    </div>
  </div>
  <section class="pdp-info">
    <div lang="es">
      <p class="lang-tag">ES</p>
      <p>{e(tipo["ficha"])}</p>
      <p>{e(p["descripcion"])}</p>
      <p class="muted">Diseñado por Ana Martínez</p>
    </div>
    <div lang="en">
      <p class="lang-tag">EN</p>
      <p>{e(tipo["ficha_en"])}</p>
      <p>{e(p["descripcion_en"])}</p>
      <p class="muted">Designed by Ana Martínez</p>
    </div>
    <div class="accordions">{acordeon}</div>
  </section>
  <section class="pdp-wear">
    <h2>{e(tipo["uso"]["titulo"])} <span>· {e(tipo["uso"]["titulo_en"])}</span></h2>
    <div class="bi">
      <p lang="es">{e(p["lema"])} {e(tipo["uso"]["es"])}</p>
      <p lang="en">{e(p["lema_en"])} {e(tipo["uso"]["en"])}</p>
    </div>
  </section>
  {obra}
  {proyecto}
  <section class="pdp-more">
    <h2>Del mismo proyecto <span>· From the same project</span></h2>
    <div class="shop-grid">{mas}</div>
  </section>
</article>
{LIGHTBOX}"""


def products_js(ed, productos):
    m = {}
    for p in productos:
        tipo = ed["tipos"][p["tipo"]]
        m[p["slug"]] = {"nombre": nombre(p, tipo),
                        "tamanos": {t["id"]: {"label": t["label"], "precio": t["precio"]} for t in tipo["tamanos"]},
                        "colores": {c["id"]: {"label": c["label"], "img": foto(tipo, c["fotos"]["plano"])} for c in p["colores"]}}
    return "window.AM_PRODUCTS = " + json.dumps(m, ensure_ascii=False) + ";\n"
