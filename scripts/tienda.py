"""Sección PAÑUELOS (tienda de demostración) con la disposición de ficha de Hermès:
tira de 3 fotos (planchado · llevado · detalle) con tarjeta de compra flotante, descripción
y desplegables, «Cómo llevarlo», y debajo la obra y el proyecto de los que nace el pañuelo.
"""
import html
import json

e = html.escape


def foto(name):
    return f"assets/panuelos/{name}.jpg"


def precio(n):
    return f"{n} €"


def card(r, p, data):
    c = p["colores"][0]["fotos"]
    return f"""<a class="shop-card" href="{r}panuelos/{p["slug"]}/">
  <span class="shop-media">
    <img class="shop-flat" src="{r}{foto(c["plano"])}" alt="Pañuelo {e(p["nombre"])} extendido" loading="lazy">
    <img class="shop-worn" src="{r}{foto(c["modelo"])}" alt="Pañuelo {e(p["nombre"])} llevado" loading="lazy">
  </span>
  <span class="shop-name">Carré {e(p["nombre"])}</span>
  <span class="shop-price">{precio(data["precio"])}</span>
</a>"""


def listado(r, data):
    cards = "\n".join(card(r, p, data) for p in data["productos"])
    return f"""<section class="shop-intro">
  <h1>PAÑUELOS</h1>
  <p>Carrés de seda twill con bordes cosidos a mano, nacidos de la obra de Ana Martínez.</p>
</section>
<div class="shop-grid">
{cards}
</div>"""


def ficha(r, p, data):
    col = p["colores"][0]
    f = col["fotos"]
    swatches = "".join(
        f'<button type="button" class="swatch{" is-active" if i == 0 else ""}" data-color="{c["id"]}" '
        f'data-label="{e(c["label"])}" data-flat="{r}{foto(c["fotos"]["plano"])}" aria-label="{e(c["label"])}">'
        f'<img src="{r}{foto(c["fotos"]["plano"])}" alt=""></button>'
        for i, c in enumerate(p["colores"]))
    obra = ""
    if p.get("obra"):
        o = p["obra"]
        img = o["img"] if o["img"].startswith("http") else r + o["img"]
        obra = f"""<section class="pdp-obra">
  <figure><img src="{e(img)}" alt="{e(o["titulo"])}, obra de Ana Martínez" loading="lazy"></figure>
  <div>
    <p class="eyebrow">LA OBRA</p>
    <h2>{e(o["titulo"])}</h2>
    <p class="muted">{e(o["tecnica"])}</p>
    <p>El estampado del carré {e(p["nombre"])} nace de esta obra de Ana Martínez.</p>
  </div>
</section>"""
    pr = p["proyecto"]
    enlace = (f'<p><a class="btn-link" href="{r}obra/{pr["slug"]}/">VER EL PROYECTO</a></p>'
              if pr.get("slug") else "")
    parrafos = "".join(f"<p>{e(t)}</p>" for t in pr["texto"])
    proyecto = f"""<section class="pdp-proyecto">
  <p class="eyebrow">EL PROYECTO</p>
  <h2>{e(pr["titulo"])}</h2>
  {f'<p class="muted">{e(pr["fecha"])}</p>' if pr.get("fecha") else ""}
  <blockquote>{parrafos}<cite>{e(pr["fuente"])}</cite></blockquote>
  {enlace}
</section>"""
    otros = "\n".join(card(r, q, data) for q in data["productos"] if q["slug"] != p["slug"])
    return f"""<article class="pdp" data-slug="{p["slug"]}">
  <div class="pdp-strip">
    <div class="pdp-photos">
    <figure class="pdp-flat"><img data-flat-img src="{r}{foto(f["plano"])}" alt="Carré {e(p["nombre"])} extendido"></figure>
    <figure><img src="{r}{foto(f["modelo"])}" alt="Carré {e(p["nombre"])} llevado al cuello"></figure>
    <figure><img src="{r}{foto(f["zoom"])}" alt="Detalle de la seda del carré {e(p["nombre"])}"></figure>
    </div>
    <div class="buy-card">
      <h1>Carré {e(p["nombre"])}</h1>
      <div class="buy-color"><span>COLOR</span><span data-color-label>{e(col["label"])}</span></div>
      <div class="swatches">{swatches}</div>
      <p class="buy-price">{precio(data["precio"])}</p>
      <button class="btn-dark add-to-cart" type="button" data-color="{col["id"]}">AÑADIR A MI CESTA</button>
    </div>
  </div>
  <section class="pdp-info">
    <div>
      <p>{e(data["ficha"])}</p>
      <p>{e(p["descripcion"])}</p>
      <p class="muted">Diseñado por Ana Martínez · {e(data["medida"])}</p>
    </div>
    <div class="accordions">
      <details><summary>MANTENIMIENTO</summary><p>Lavar en seco o a mano en agua fría con jabón neutro. Planchar a temperatura baja por el revés.</p></details>
      <details><summary>ENVÍO Y DEVOLUCIONES</summary><p>Envío en su caja, listo para regalar. Devoluciones en un plazo de 30 días.</p></details>
      <details><summary>HACER UN REGALO</summary><p>Podemos incluir una tarjeta escrita a mano por la artista.</p></details>
    </div>
  </section>
  <section class="pdp-wear">
    <h2>Cómo llevar tu carré</h2>
    <p>{e(p["lema"])} Doblado en triángulo sobre los hombros, plegado en cinta y anudado al cuello o en la cabeza, el carré se mueve con quien lo lleva, como el agua.</p>
  </section>
  {obra}
  {proyecto}
  <section class="pdp-more">
    <h2>Otros carrés</h2>
    <div class="shop-grid">{otros}</div>
  </section>
</article>"""


def products_js(data):
    m = {p["slug"]: {"nombre": p["nombre"], "precio": data["precio"],
                     "colores": {c["id"]: {"label": c["label"], "img": foto(c["fotos"]["plano"])} for c in p["colores"]}}
         for p in data["productos"]}
    return "window.AM_PRODUCTS = " + json.dumps(m, ensure_ascii=False) + ";\n"
