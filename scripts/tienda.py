"""Sección EDICIONES (tienda de demostración): pañuelos y láminas agrupados por proyecto.

Ficha con la disposición de Hermès: tira de 3 fotos con tarjeta de compra flotante
(variante, tamaño, precio), descripción ES | EN y desplegables, uso, y debajo la obra y el
proyecto de los que nace la pieza. Pañuelos: planchado · llevado · detalle.
Láminas: centrada · en casa · detalle del papel.
"""
import html
import json

from editable import campo, ed

e = html.escape

LIGHTBOX = """<dialog class="lightbox" aria-label="Foto ampliada">
  <div class="lb-stage" tabindex="-1"><img class="lb-img" alt=""></div>
  <div class="lb-zoom">
    <button type="button" class="lb-in" aria-label="Acercar"><svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true" focusable="false"><path d="M5.5 0v11M0 5.5h11" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button>
    <input type="range" class="lb-range" min="1" max="4" step="0.1" value="1" aria-label="Zoom" orient="vertical">
    <button type="button" class="lb-out" aria-label="Alejar"><svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true" focusable="false"><path d="M0 5.5h11" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button>
  </div>
  <div class="lb-thumbs"></div>
  <button type="button" class="lb-nav lb-prev" aria-label="Foto anterior"><svg width="7" height="14" viewBox="0 0 7 14" aria-hidden="true" focusable="false"><path d="M6.5.5L.5 7l6 6.5" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button>
  <button type="button" class="lb-nav lb-next" aria-label="Foto siguiente"><svg width="7" height="14" viewBox="0 0 7 14" aria-hidden="true" focusable="false"><path d="M.5.5l6 6.5-6 6.5" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button>
  <button type="button" class="lb-close" aria-label="Cerrar"><svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true" focusable="false"><path d="M.5.5l10 10M10.5.5l-10 10" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button>
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


def ruta_tipo(p):
    return ["ediciones.json", "tipos", p["tipo"]]


def nombre_ed(p, tipo):
    """Nombre con el prefijo fijo del tipo («Carré») y la parte propia editable."""
    return f'{e(tipo["prefijo"])} <span{ed(p["_ruta"] + ["nombre"])}>{e(p["nombre"])}</span>'


def ruta_grupo(ed_, g):
    return ["ediciones.json", "grupos", ed_["grupos"].index(g)]


def card(r, p, ed_):
    tipo = ed_["tipos"][p["tipo"]]
    c = p["colores"][0]["fotos"]
    href = f"{r}{tipo['dir']}/{p['slug']}/"
    imgs = "".join(
        f'<img class="{"is-on" if i == 0 else ""}" src="{r}{foto(tipo, c[k])}" alt="{e(nombre(p, tipo))}, {alt}" loading="lazy">'
        for i, (k, alt) in enumerate(tipo["vistas"]))
    return f"""<div class="shop-card">
  <div class="shop-media" data-carousel>
    <a href="{href}" tabindex="-1" aria-hidden="true">{imgs}</a>
    <button class="car-btn car-prev" type="button" aria-label="Foto anterior"><svg width="7" height="14" viewBox="0 0 7 14" aria-hidden="true" focusable="false"><path d="M6.5.5L.5 7l6 6.5" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button>
    <button class="car-btn car-next" type="button" aria-label="Foto siguiente"><svg width="7" height="14" viewBox="0 0 7 14" aria-hidden="true" focusable="false"><path d="M.5.5l6 6.5-6 6.5" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button>
  </div>
  <a class="shop-meta" href="{href}"><span class="shop-kind"{ed(ruta_tipo(p) + ["nombre"], raw=tipo["nombre"])}>{e(tipo["nombre"].upper())}</span>
  <span class="shop-name">{nombre_ed(p, tipo)}</span>
  <span class="shop-price">Desde {precio(desde(tipo))}</span></a>
</div>"""


def grupo_header(r, g, n, ruta):
    enlace = (f'<a class="group-link" href="{r}obra/{g["obra_slug"]}/">Ver el proyecto ›</a>'
              if g.get("obra_slug") else "")
    fecha = f' <span class="group-date"{ed(ruta + ["fecha"])}>{e(g["fecha"])}</span>' if g.get("fecha") else ""
    return f"""<header class="group-head">
    <div><h2><span{ed(ruta + ["titulo"])}>{e(g["titulo"])}</span>{fecha}</h2>
    <p class="group-count">{n} {"pieza" if n == 1 else "piezas"} · {n} {"piece" if n == 1 else "pieces"}</p></div>
    {enlace}
  </header>"""


def listado(r, ed_, productos, actual):
    filtrados = [p for p in productos if actual == "ediciones" or p["tipo"] == actual]
    seg = "".join(
        f'<a class="seg{" is-active" if k == actual else ""}" href="{r}{k}/"'
        f'{" aria-current=page" if k == actual else ""}>{es}<span lang="en">{en}</span></a>'
        for k, es, en in FILTROS)
    grupos, indice = [], []
    for g in ed_["grupos"]:
        items = [p for p in filtrados if p["grupo"] == g["id"]]
        if not items:
            continue
        indice.append(f'<a href="#{g["id"]}">{e(g["titulo"])}</a>')
        bloques = []
        for clave, tipo in ed_["tipos"].items():
            sub = [p for p in items if p["tipo"] == clave]
            if not sub:
                continue
            rt = ["ediciones.json", "tipos", clave]
            titulo_sub = (f'<h3 class="group-sub"><span{ed(rt + ["nombre"])}>{e(tipo["nombre"])}</span> '
                          f'<span lang="en">· <span{ed(rt + ["nombre_en"])}>{e(tipo["nombre_en"])}</span></span></h3>'
                          if actual == "ediciones" else "")
            bloques.append(f'{titulo_sub}<div class="shop-grid">{"".join(card(r, p, ed_) for p in sub)}</div>')
        grupos.append(f"""<section class="group" id="{g["id"]}">
  {grupo_header(r, g, len(items), ruta_grupo(ed_, g))}
  {"".join(bloques)}
</section>""")
    intro = ed_ if actual == "ediciones" else ed_["tipos"][actual]
    ri = ["ediciones.json"] if actual == "ediciones" else ["ediciones.json", "tipos", actual]
    titulo = dict((k, es) for k, es, _ in FILTROS)[actual]
    titulo = "Ediciones" if actual == "ediciones" else titulo
    return f"""<section class="shop-intro">
  <h1>{e(titulo)}</h1>
  <div class="bi bi-intro"><p lang="es"{ed(ri + ["intro_es"])}>{e(intro["intro_es"])}</p><p lang="en"{ed(ri + ["intro_en"])}>{e(intro["intro_en"])}</p></div>
  <nav class="group-index" aria-label="Proyectos">{"".join(indice)}</nav>
</section>
{"".join(grupos)}"""


def ficha(r, p, ed_, productos):
    tipo = ed_["tipos"][p["tipo"]]
    g = next(x for x in ed_["grupos"] if x["id"] == p["grupo"])
    rp, rt, rg = p["_ruta"], ruta_tipo(p), ruta_grupo(ed_, g)
    otros_datos = "".join(
        campo(f"Tamaño {k + 1} · nombre", t["label"], rt + ["tamanos", k, "label"])
        + campo(f"Tamaño {k + 1} · precio (€)", t["precio"], rt + ["tamanos", k, "precio"])
        for k, t in enumerate(tipo["tamanos"]))
    otros_datos += "".join(campo(f"Color {k + 1}", c["label"], rp + ["colores", k, "label"])
                           for k, c in enumerate(p["colores"]))
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
        variantes = (f'<div class="buy-field"><p class="buy-label">{etiqueta}: <span data-color-label data-e-abre="Color">{e(col["label"])}</span></p>'
                     f'<div class="swatches">{sw}</div></div>')
    elif p["tipo"] == "panuelos":
        variantes = f'<p class="buy-label buy-static">{etiqueta}: <span data-e-abre="Color">{e(col["label"])}</span></p>'
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
        href = f'{r}{o["href"]}' if o.get("href") else None
        c = o.get("_cartela")
        ro = [c["_f"], c["_k"]] if c else rp + ["obra"]
        foto_obra = f'<img src="{e(img)}" alt="{e(o["titulo"])}, obra de Ana Martínez" loading="lazy">'
        if href:
            foto_obra = f'<a href="{href}" aria-label="Ver la obra {e(o["titulo"])}">{foto_obra}</a>'
        titulo_obra = f'<span{ed(ro + ["titulo"])}>{e(o["titulo"])}</span>'
        titulo_obra = f'<a href="{href}">{titulo_obra}</a>' if href else titulo_obra
        tecnica = (" · ".join(f'<span{ed(ro + [k])}>{e(c[k])}</span>' for k in ("tecnica", "medidas") if c.get(k))
                   if c else f'<span{ed(ro + ["tecnica"])}>{e(o["tecnica"])}</span>')
        ver = f'<p><a class="link-arrow" href="{href}">Ver la obra en su proyecto ›</a></p>' if href else ""
        obra = f"""<section class="pdp-obra">
  <figure>{foto_obra}</figure>
  <div>
    <p class="eyebrow">LA OBRA · THE WORK</p>
    <h2>{titulo_obra}</h2>
    <p class="muted">{tecnica}</p>
    <p>{e(nombre(p, tipo))} nace de esta obra de Ana Martínez.</p>
    <p lang="en" class="muted">{e(tipo["prefijo"])} {e(p["nombre"])} is born from this work by Ana Martínez.</p>
    {ver}
  </div>
</section>"""
    parrafos = "".join(f'<p{ed(rg + ["texto", k])}>{e(t)}</p>' for k, t in enumerate(g["texto"]))
    parrafos_en = "".join(f'<p{ed(rg + ["texto_en", k])}>{e(t)}</p>' for k, t in enumerate(g.get("texto_en", [])))
    enlace = (f'<p><a class="btn-link" href="{r}obra/{g["obra_slug"]}/">VER EL PROYECTO</a></p>'
              if g.get("obra_slug") else "")
    proyecto = f"""<section class="pdp-proyecto">
  <p class="eyebrow">EL PROYECTO · THE PROJECT</p>
  <h2{ed(rg + ["titulo"])}>{e(g["titulo"])}</h2>
  {f'<p class="muted"{ed(rg + ["fecha"])}>{e(g["fecha"])}</p>' if g.get("fecha") else ""}
  <div class="bi pdp-quote"><blockquote lang="es"><p class="lang-tag">ES</p>{parrafos}</blockquote><blockquote lang="en"><p class="lang-tag">EN</p>{parrafos_en}</blockquote></div>
  <cite{ed(rg + ["fuente"])}>{e(g["fuente"])}</cite>
  {enlace}
</section>"""
    serie = sorted((q for q in productos if q["grupo"] == p["grupo"]),
                   key=lambda q: list(ed_["tipos"]).index(q["tipo"]))
    i = next(k for k, q in enumerate(serie) if q["slug"] == p["slug"])

    def enlace_pieza(q, flecha_izq):
        tq = ed_["tipos"][q["tipo"]]
        txt = f"‹ {e(nombre(q, tq))}" if flecha_izq else f"{e(nombre(q, tq))} ›"
        return f'<a href="{r}{tq["dir"]}/{q["slug"]}/">{txt}</a>'
    pager = ""
    if len(serie) > 1:
        ant = enlace_pieza(serie[i - 1], True) if i > 0 else "<span></span>"
        sig = enlace_pieza(serie[i + 1], False) if i < len(serie) - 1 else "<span></span>"
        pager = (f'<nav class="piece-nav" aria-label="Piezas del proyecto">{ant}'
                 f'<span class="piece-count">{i + 1} / {len(serie)}</span>{sig}</nav>')
    hermanos = [q for q in productos if q["grupo"] == p["grupo"] and q["slug"] != p["slug"]]
    otros = [q for q in productos if q["grupo"] != p["grupo"]][: max(0, 4 - len(hermanos))]
    mas = "\n".join(card(r, q, ed_) for q in hermanos + otros)
    acordeon = "".join(f'<details><summary{ed(rt + ["acordeon", k, 0])}>{e(a)}</summary><p{ed(rt + ["acordeon", k, 1])}>{e(b)}</p></details>'
                       for k, (a, b) in enumerate(tipo["acordeon"]))
    return f"""<article class="pdp" data-slug="{p["slug"]}">
  <div class="pdp-top">
    <nav class="crumbs" aria-label="Migas de pan"><a href="{r}ediciones/">Ediciones</a> › <a href="{r}ediciones/#{g["id"]}">{e(g["titulo"])}</a> › <span aria-current="page">{e(nombre(p, tipo))}</span></nav>
    {pager}
  </div>
  <div class="pdp-strip">
    <div class="pdp-photos" data-gallery>
    <figure class="pdp-flat"><button type="button" class="zoomable" data-index="0" aria-label="Ampliar foto"><img data-flat-img src="{r}{foto(tipo, f["plano"])}" alt="{e(nombre(p, tipo))}, {vistas["plano"]}"></button></figure>
    <figure><button type="button" class="zoomable" data-index="1" aria-label="Ampliar foto"><img data-worn-img src="{r}{foto(tipo, f["modelo"])}" alt="{e(nombre(p, tipo))}, {vistas["modelo"]}"></button></figure>
    <figure><button type="button" class="zoomable" data-index="2" aria-label="Ampliar foto"><img data-zoom-img src="{r}{foto(tipo, f["zoom"])}" alt="{e(nombre(p, tipo))}, {vistas["zoom"]}"></button></figure>
    </div>
    <div class="pdp-dots" aria-hidden="true"><span class="is-on"></span><span></span><span></span></div>
    <div class="buy-card">
      <p class="buy-kind"><a href="{r}{tipo["dir"]}/">{e(tipo["nombre"])}</a> · <a href="{r}ediciones/#{g["id"]}">{e(g["titulo"])}</a></p>
      <h1{ed(rp + ["nombre"])}>{e(p["nombre"])}</h1>{otros_datos}
      <p class="buy-price" aria-live="polite" data-e-abre="Tamaño 1 · precio">{precio(t0["precio"])}</p>
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
      <p{ed(rt + ["ficha"])}>{e(tipo["ficha"])}</p>
      <p{ed(rp + ["descripcion"])}>{e(p["descripcion"])}</p>
      <p class="muted">Diseñado por Ana Martínez</p>
    </div>
    <div lang="en">
      <p class="lang-tag">EN</p>
      <p{ed(rt + ["ficha_en"])}>{e(tipo["ficha_en"])}</p>
      <p{ed(rp + ["descripcion_en"])}>{e(p["descripcion_en"])}</p>
      <p class="muted">Designed by Ana Martínez</p>
    </div>
    <div class="accordions">{acordeon}</div>
  </section>
  <section class="pdp-wear">
    <h2><span{ed(rt + ["uso", "titulo"])}>{e(tipo["uso"]["titulo"])}</span> <span class="en-sub" lang="en"{ed(rt + ["uso", "titulo_en"])}>{e(tipo["uso"]["titulo_en"])}</span></h2>
    <div class="bi">
      <p lang="es"><span{ed(rp + ["lema"])}>{e(p["lema"])}</span> <span{ed(rt + ["uso", "es"])}>{e(tipo["uso"]["es"])}</span></p>
      <p lang="en"><span{ed(rp + ["lema_en"])}>{e(p["lema_en"])}</span> <span{ed(rt + ["uso", "en"])}>{e(tipo["uso"]["en"])}</span></p>
    </div>
  </section>
  {obra}
  {proyecto}
  <section class="pdp-more">
    <h2>Del mismo proyecto <span class="en-sub" lang="en">From the same project</span></h2>
    <div class="rail-wrap" data-rail>
      <button type="button" class="rail-btn rail-prev" aria-label="Anteriores"><svg width="7" height="14" viewBox="0 0 7 14" aria-hidden="true" focusable="false"><path d="M6.5.5L.5 7l6 6.5" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button>
      <div class="rail">{mas}</div>
      <button type="button" class="rail-btn rail-next" aria-label="Siguientes"><svg width="7" height="14" viewBox="0 0 7 14" aria-hidden="true" focusable="false"><path d="M.5.5l6 6.5-6 6.5" stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke"/></svg></button>
    </div>
  </section>
</article>
{LIGHTBOX}"""


def products_js(ed_, productos):
    m = {}
    for p in productos:
        tipo = ed_["tipos"][p["tipo"]]
        m[p["slug"]] = {"nombre": nombre(p, tipo),
                        "tamanos": {t["id"]: {"label": t["label"], "precio": t["precio"]} for t in tipo["tamanos"]},
                        "colores": {c["id"]: {"label": c["label"], "img": foto(tipo, c["fotos"]["plano"])} for c in p["colores"]}}
    return "window.AM_PRODUCTS = " + json.dumps(m, ensure_ascii=False) + ";\n"
