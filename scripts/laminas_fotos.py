"""Genera las vistas de una lámina para la tienda a partir de la imagen de la obra.

Uso:
    python3 scripts/laminas_fotos.py <imagen> <nombre>   [--solo centrada|zoom]

Escribe en assets/laminas/:
    lam_<nombre>_centrada.jpg  (1500 × 1874) lámina plana sobre fondo beige, con margen blanco y firma
    lam_<nombre>_zoom.jpg      (1200 × 1500) detalle en ángulo de una esquina, donde se ve el grano del papel

La vista «en casa» (lam_<nombre>_casa.jpg, 1200 × 1500) no se genera aquí: se pide a un modelo de imagen
con la foto centrada como referencia (ver PROMPT_CASA).
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "laminas"

FONDO = (228, 224, 215)      # beige de las vistas existentes
PAPEL = (251, 250, 245)      # blanco roto del papel de algodón
SOMBRA = (120, 112, 100)

PROMPT_CASA = (
    "Fotografía de interiorismo, luz natural cálida de tarde. La lámina adjunta, enmarcada en roble claro "
    "con paspartú blanco, colgada en una pared de yeso beige sobre un sillón de lino crudo; mesa auxiliar de "
    "madera maciza, alfombra de yute, una rama de olivo en un jarrón de cerámica. Estilo mediterráneo sereno, "
    "sin personas, sin texto. La obra debe reproducirse fielmente, sin alterar colores ni composición. "
    "Formato vertical 4:5."
)


def grano(size, fuerza=10, seed=1):
    """Textura de papel: ruido suave desenfocado, para sumar/restar al lienzo."""
    rnd = random.Random(seed)
    w, h = size
    small = Image.effect_noise((w // 3, h // 3), fuerza).resize(size, Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(0.6))
    fine = Image.effect_noise(size, fuerza * 0.7)
    tex = ImageChops.add(small, fine, scale=2.0)
    rnd.random()
    return tex.convert("RGB")


def con_grano(img, fuerza=10, seed=1):
    tex = grano(img.size, fuerza, seed)
    gris = Image.new("RGB", img.size, (128, 128, 128))
    delta = ImageChops.subtract(tex, gris, scale=1.0, offset=128)   # ruido centrado en 128
    return ImageChops.add(ImageChops.subtract(img, gris, offset=128), delta, offset=-128)


def hoja(obra, ancho_hoja, margen):
    """Hoja de papel con la obra centrada y un margen blanco; devuelve (hoja, caja de la obra)."""
    ow, oh = obra.size
    escala = (ancho_hoja - 2 * margen) / ow
    obra = obra.resize((ancho_hoja - 2 * margen, round(oh * escala)), Image.LANCZOS)
    alto_hoja = obra.height + 2 * margen
    sheet = Image.new("RGB", (ancho_hoja, alto_hoja), PAPEL)
    sheet.paste(obra, (margen, margen))
    return sheet, (margen, margen, margen + obra.width, margen + obra.height)


def centrada(obra, out):
    W, H = 1500, 1874
    lienzo = Image.new("RGB", (W, H), FONDO)
    ancho_hoja = 1250
    sheet, _ = hoja(obra, ancho_hoja, margen=78)
    if sheet.height > H - 200:
        sheet, _ = hoja(obra, round(ancho_hoja * (H - 200) / sheet.height), margen=78)
    x = (W - sheet.width) // 2
    y = (H - sheet.height) // 2
    # Sombra suave debajo de la hoja
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rectangle((x + 6, y + 14, x + sheet.width + 6, y + sheet.height + 14), fill=SOMBRA + (110,))
    sombra = sombra.filter(ImageFilter.GaussianBlur(22))
    lienzo = Image.alpha_composite(lienzo.convert("RGBA"), sombra).convert("RGB")
    lienzo.paste(con_grano(sheet, fuerza=6, seed=3), (x, y))
    lienzo.save(out, "JPEG", quality=88, optimize=True, progressive=True)
    return lienzo


def zoom(obra, out):
    """Detalle: esquina superior derecha de la hoja, ampliada e inclinada, con el grano del papel visible."""
    W, H = 1200, 1500
    sheet, (l, t, r, b) = hoja(obra, 2600, margen=160)
    # Recorte alrededor de la esquina superior derecha de la obra (incluye margen blanco y borde de la hoja)
    cw, ch = 1500, 1800
    cx, cy = r - cw // 2 + 120, t + ch // 2 - 220
    cx = min(max(cx, cw // 2), sheet.width - cw // 2 + 160)
    cy = max(cy, ch // 2 - 160)
    fondo = Image.new("RGB", (sheet.width + 800, sheet.height + 800), FONDO)
    fondo.paste(sheet, (400, 400))
    recorte = fondo.crop((cx + 400 - cw // 2, cy + 400 - ch // 2, cx + 400 + cw // 2, cy + 400 + ch // 2))
    recorte = con_grano(recorte, fuerza=14, seed=7)
    recorte = recorte.rotate(-9, resample=Image.BICUBIC, expand=False, fillcolor=FONDO)
    # Recorte central a 4:5 y ligero degradado de luz
    ancho = int(recorte.height * W / H)
    recorte = recorte.crop(((recorte.width - ancho) // 2, 0, (recorte.width + ancho) // 2, recorte.height)).resize((W, H), Image.LANCZOS)
    luz = Image.linear_gradient("L").resize((W, H)).rotate(180).point(lambda v: int(255 - v * 0.22))
    recorte = ImageChops.multiply(recorte, Image.merge("RGB", (luz, luz, luz)))
    recorte.save(out, "JPEG", quality=88, optimize=True, progressive=True)
    return recorte


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    src, nombre = Path(args[0]), args[1]
    solo = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--solo=")), None)
    obra = Image.open(src).convert("RGB")
    OUT.mkdir(parents=True, exist_ok=True)
    if solo in (None, "centrada"):
        centrada(obra, OUT / f"lam_{nombre}_centrada.jpg")
    if solo in (None, "zoom"):
        zoom(obra, OUT / f"lam_{nombre}_zoom.jpg")
    print("ok", nombre)


if __name__ == "__main__":
    main()
