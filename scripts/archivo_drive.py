"""Índice del archivo de Ana en Google Drive: qué foto, PDF o texto va en qué carpeta.

build.py lo publica en docs/archivo_drive.json y el Apps Script (copiarADrive) lo recorre
y sube lo que falte, bajando cada fichero de la web publicada. Estructura:

  01 Proyectos | 02 Murales | 03 Talleres / AAAA-MM Título / 01 Nombre de la obra.jpg, Textos
  04 Ediciones / Pañuelos | Láminas / Nombre / Color - vista.jpg, Textos
  05 Sobre mí / retratos, CV, Biografía
  06 Imagen de la web / portada, firma, icono
"""
import json
import re
from pathlib import Path

SECCIONES = {"PROYECTOS": "01 Proyectos", "PINTAMENTO": "02 Murales", "TALLERES": "03 Talleres"}


def limpio(s, largo=90):
    s = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", s or "").strip(" .")
    return re.sub(r"\s+", " ", s)[:largo].strip() or "sin título"


def lineas(items):
    return [t for t in items or [] if isinstance(t, str) and not t.startswith("http")]


def generar(root):
    data = root / "data"
    leer = lambda f: json.loads((data / f).read_text())  # noqa: E731
    content = leer("content.json")
    cuadros, curador = {}, {}
    for f in sorted((data / "cuadros").glob("*.json")):
        cuadros.update(json.loads(f.read_text()))
    for f in sorted((data / "textos_curador").glob("*.json")):
        curador.update(json.loads(f.read_text()))
    traducciones = leer("translations_en.json")
    documentos = leer("documentos.json")
    ficheros, textos = [], []

    for p in content["posts"]:
        carpeta = f'{SECCIONES.get(p["category"], "01 Proyectos")}/{p["date"][:7]} {limpio(p["title"].title())}'
        obras = []
        for k, im in enumerate(p["images"], 1):
            if not im["src"].startswith("assets/"):
                continue
            c = cuadros.get(im["src"]) or {}
            nombre = c.get("titulo", "").split(" / ")[0] if c.get("es_obra") and c.get("titulo") else Path(im["src"]).stem
            ficheros.append({"carpeta": carpeta, "nombre": f"{k:02d} {limpio(nombre)}{Path(im['src']).suffix.lower()}",
                             "fuente": im["src"]})
            if c.get("es_obra") and c.get("titulo"):
                obras.append(f'{k:02d}. ' + " · ".join(x for x in (c["titulo"], c.get("tecnica"), c.get("medidas")) if x))
        for t in p["text"]:
            if isinstance(t, dict) and "pdf" in t and t["pdf"].startswith("assets/"):
                ficheros.append({"carpeta": carpeta, "nombre": limpio(t.get("label") or Path(t["pdf"]).stem) + ".pdf",
                                 "fuente": t["pdf"]})
        tr = traducciones.get(p["slug"], {})
        es, en = lineas(p["text"]), tr.get("text_en") or lineas(p.get("text_en"))
        if not es and p["slug"] in curador:
            es, en = curador[p["slug"]]["es"], curador[p["slug"]]["en"]
        doc = documentos.get(p["slug"]) or {}
        title_en = tr.get("title_en") or p.get("title_en") or ""
        partes = [p["title"], *([title_en] if title_en.strip().lower() != p["title"].strip().lower() else []),
                  f'Fecha: {p["date"]}',
                  f'Web: https://antonioomsg.github.io/ana-martinez/obra/{p["slug"]}/', "",
                  "ESPAÑOL", *es, "", "ENGLISH", *en]
        if doc:
            partes += ["", doc.get("titulo_doc") or "Hoja de sala", doc.get("lugar_fechas") or "", *doc.get("es", []),
                       doc.get("firma") or "", "", *doc.get("en", [])]
        if obras:
            partes += ["", "OBRAS", *obras]
        textos.append({"carpeta": carpeta, "nombre": "Textos", "texto": "\n".join(partes).strip() + "\n"})

    ed = leer("ediciones.json")
    for fichero in ("panuelos.json", "laminas.json"):
        for p in leer(fichero)["productos"]:
            tipo = ed["tipos"][p["tipo"]]
            carpeta = f'04 Ediciones/{tipo["nombre"]}/{limpio(p["nombre"])}'
            vistas = dict(tipo["vistas"])
            for c in p["colores"]:
                for vista, foto in c["fotos"].items():
                    ficheros.append({"carpeta": carpeta,
                                     "nombre": limpio(f'{c["label"]} - {vistas.get(vista, vista)}') + ".jpg",
                                     "fuente": f'assets/{tipo["dir"]}/{foto}.jpg'})
            textos.append({"carpeta": carpeta, "nombre": "Textos", "texto": "\n".join([
                f'{tipo["prefijo"]} {p["nombre"]}', "", p["lema"], p["descripcion"], "", p["lema_en"], p["descripcion_en"],
                "", "Colores: " + ", ".join(c["label"] for c in p["colores"]),
                "Tamaños: " + ", ".join(f'{t["label"]} ({t["precio"]} €)' for t in tipo["tamanos"]),
            ]) + "\n"})

    bio = leer("bio.json")
    for f in ("ana-martinez.jpg", "ana-martinez-roca.jpg"):
        ficheros.append({"carpeta": "05 Sobre mí", "nombre": f"Retrato - {f}", "fuente": f"assets/{f}"})
    for t in content["pages"]["bio"]["text"]:
        if isinstance(t, dict) and "pdf" in t and t["pdf"].startswith("assets/"):
            ficheros.append({"carpeta": "05 Sobre mí", "nombre": f'{limpio(t.get("label", "CV"))}.pdf', "fuente": t["pdf"]})
    textos.append({"carpeta": "05 Sobre mí", "nombre": "Biografía", "texto": "\n".join(
        ["ESPAÑOL", bio["lead_es"], *bio["es"], "", "ENGLISH", bio["lead_en"], *bio["en"]]) + "\n"})
    for f, n in (("hero.png", "Portada de la web.png"), ("firma.png", "Firma.png"), ("instagram.svg", "Icono Instagram.svg")):
        ficheros.append({"carpeta": "06 Imagen de la web", "nombre": n, "fuente": f"assets/{f}"})

    # mismo nombre en la misma carpeta (dos fotos sin cartela iguales): se numeran
    vistos = {}
    for f in ficheros:
        k = (f["carpeta"], f["nombre"])
        vistos[k] = vistos.get(k, 0) + 1
        if vistos[k] > 1:
            stem, dot, ext = f["nombre"].rpartition(".")
            f["nombre"] = f"{stem} ({vistos[k]}).{ext}"
    return {"raiz": "Ana Martínez · Archivo web", "ficheros": ficheros, "textos": textos}


if __name__ == "__main__":
    import sys
    d = generar(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
    print(len(d["ficheros"]), "ficheros,", len(d["textos"]), "textos,",
          len({f["carpeta"] for f in d["ficheros"]}), "carpetas")
