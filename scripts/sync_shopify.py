#!/usr/bin/env python3
"""Sincroniza con Shopify los cambios de data/ entre dos commits (GitHub -> Shopify, un solo sentido).

Uso:
    python3 scripts/sync_shopify.py [--before SHA] [--after SHA] [--dry-run]
                                    [--resumen FICHERO] [--pendientes FICHERO]

Por defecto compara HEAD~1 con HEAD. Es DIFERENCIAL (solo toca lo que cambia entre los dos
commits) e IDEMPOTENTE (si Shopify ya tiene el valor, no hace nada). Lo que detecta pero no
sabe mapear no se adivina: se lista como «pendiente manual».

Credenciales (variables de entorno, nunca se imprimen): SHOPIFY_STORE, SHOPIFY_CLIENT_ID,
SHOPIFY_CLIENT_SECRET. Solo biblioteca estándar.

Código de salida: 0 salvo errores reales de API (1) o de uso (2).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from html import escape, unescape
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_VERSION = "2026-10"
PAGES = "https://antonioomsg.github.io/ana-martinez/"
ZEROS = "0" * 40

ESTADOS = {"vendido": "Vendido", "disponible": "Disponible", "reservado": "Reservado"}
CAMPOS_CUADRO = ("estado", "titulo", "tecnica", "medidas")
# Ficheros de data/ sin equivalente en Shopify: se informa, no se considera pendiente.
SIN_EQUIVALENTE = {"sitio.json", "translations_en.json", "pages.json", "pages_en.json", "posts.json",
                   "posts_en.json", "cats.json", "meta.json", "bio.json", "documentos.json",
                   "fotos_origen.json"}
SIN_EQUIVALENTE_DIRS = ("html/", "textos_curador/")


# --------------------------------------------------------------------------- git

def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def resolver(rev):
    r = git("rev-parse", "--verify", "--quiet", rev + "^{commit}")
    return r.stdout.strip() if r.returncode == 0 else None


def leer_json(rev, ruta):
    r = git("show", f"{rev}:{ruta}")
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def ficheros_cambiados(before, after):
    r = git("diff", "--name-only", before, after, "--", "data")
    return [l for l in r.stdout.splitlines() if l.strip()]


# --------------------------------------------------------------------------- shopify

class ShopifyError(Exception):
    pass


class Shopify:
    def __init__(self):
        try:
            self.store = os.environ["SHOPIFY_STORE"].strip()
            self._id = os.environ["SHOPIFY_CLIENT_ID"].strip()
            self._secret = os.environ["SHOPIFY_CLIENT_SECRET"].strip()
        except KeyError as e:
            sys.exit(f"Falta la variable de entorno {e.args[0]}")
        self._token = None
        self.cache_prod = {}

    def token(self):
        if not self._token:
            data = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": self._id,
                                           "client_secret": self._secret}).encode()
            req = urllib.request.Request(f"https://{self.store}/admin/oauth/access_token", data=data,
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
            try:
                self._token = json.load(urllib.request.urlopen(req, timeout=30))["access_token"]
            except Exception as e:  # no se vuelca el cuerpo: podría contener datos sensibles
                raise ShopifyError(f"no se pudo obtener el token de Shopify ({type(e).__name__})")
        return self._token

    def gql(self, query, variables=None):
        body = json.dumps({"query": query, "variables": variables or {}}).encode()
        for intento in range(6):
            req = urllib.request.Request(
                f"https://{self.store}/admin/api/{API_VERSION}/graphql.json", data=body,
                headers={"X-Shopify-Access-Token": self.token(), "Content-Type": "application/json"})
            try:
                r = json.load(urllib.request.urlopen(req, timeout=60))
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and intento < 5:
                    time.sleep(2 ** intento)
                    continue
                raise ShopifyError(f"HTTP {e.code} de la Admin API")
            except urllib.error.URLError as e:
                if intento < 5:
                    time.sleep(2 ** intento)
                    continue
                raise ShopifyError(f"red: {e.reason}")
            errs = r.get("errors")
            if errs:
                if any("THROTTLED" in json.dumps(x) for x in errs) and intento < 5:
                    time.sleep(2 ** intento)
                    continue
                raise ShopifyError("GraphQL: " + json.dumps(errs, ensure_ascii=False)[:400])
            return r["data"]

    def mutar(self, query, variables):
        d = self.gql(query, variables)
        for v in d.values():
            if isinstance(v, dict) and v.get("userErrors"):
                raise ShopifyError("userErrors: " + json.dumps(v["userErrors"], ensure_ascii=False)[:400])
        return d

    def producto(self, handle):
        if handle not in self.cache_prod:
            self.cache_prod[handle] = self.gql("""query($h:String!){productByHandle(handle:$h){id handle title descriptionHtml productType
              metafields(first:40, namespace:"ana"){nodes{key value}}
              options{id name optionValues{id name}}
              variants(first:100){nodes{id price selectedOptions{name value}}}}}""",
                                               {"h": handle})["productByHandle"]
            q = self.cache_prod[handle]
            if q:
                q["metafields"] = {m["key"]: m["value"] for m in q["metafields"]["nodes"]}
        return self.cache_prod[handle]

    def invalidar(self, handle):
        self.cache_prod.pop(handle, None)

    def obras(self):
        out, after = [], None
        while True:
            r = self.gql("""query($a:String){metaobjects(type:"obra", first:250, after:$a){
              pageInfo{hasNextPage endCursor}
              nodes{id handle titulo:field(key:"titulo"){value} titulo_en:field(key:"titulo_en"){value}
                    tecnica:field(key:"tecnica"){value} medidas:field(key:"medidas"){value}
                    estado:field(key:"estado"){value}
                    imagen:field(key:"imagen"){reference{... on MediaImage{image{url}}}}}}}""", {"a": after})["metaobjects"]
            out += r["nodes"]
            if not r["pageInfo"]["hasNextPage"]:
                return out
            after = r["pageInfo"]["endCursor"]

    def proyecto(self, handle):
        return self.gql("""query($h:MetaobjectHandleInput!){metaobjectByHandle(handle:$h){id
          titulo:field(key:"titulo"){value}
          portada:field(key:"portada"){reference{... on MediaImage{image{url}}}}}}""",
                        {"h": {"type": "proyecto", "handle": handle}})["metaobjectByHandle"]


# --------------------------------------------------------------------------- utilidades

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def sin_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", norm(s)) if unicodedata.category(c) != "Mn")


def titulo_shopify(t):
    """Título de GitHub -> estilo de Shopify. Si está todo en mayúsculas: frase en minúsculas."""
    t = re.sub(r"\s+", " ", t or "").strip()
    letras = [c for c in t if c.isalpha()]
    if letras and all(c.isupper() for c in letras):
        t = t.lower()
        t = re.sub(r"[^\W\d_]", lambda m: m.group(0).upper(), t, count=1)
    return t


def sin_html(h):
    return norm(unescape(re.sub(r"<[^>]+>", " ", h or "")))


def stem_archivo(u):
    """Nombre de archivo sin extensión ni sufijo _<uuid> que Shopify añade, en minúsculas."""
    n = Path(urllib.parse.unquote(urllib.parse.urlparse(u).path)).stem.lower()
    return re.sub(r"_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", "", n)


def ruta_publica(p):
    while p.startswith("../"):
        p = p[3:]
    return p.lstrip("/")


def hojas(a, b, ruta=""):
    """Rutas de las hojas JSON que difieren entre a y b (listas de dicts con 'slug' o 'id' por clave)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            out += hojas(a.get(k), b.get(k), f"{ruta}/{k}" if ruta else str(k))
        return out
    if isinstance(a, list) and isinstance(b, list):
        def clave(x):
            return x.get("slug") or x.get("id") if isinstance(x, dict) else None
        if all(clave(x) for x in a + b) and a + b:
            da, db = {clave(x): x for x in a}, {clave(x): x for x in b}
            out = []
            for k in list(dict.fromkeys(list(da) + list(db))):
                out += hojas(da.get(k), db.get(k), f"{ruta}[{k}]")
            return out
        return [] if a == b else [ruta]
    return [] if a == b else [ruta]


class Resumen:
    def __init__(self):
        self.hechos, self.sin_cambio, self.pendientes, self.info, self.errores = [], [], [], [], []

    def ok(self, t):
        self.hechos.append(t)

    def nada(self, t):
        self.sin_cambio.append(t)

    def pend(self, t):
        if t not in self.pendientes:
            self.pendientes.append(t)

    def inf(self, t):
        if t not in self.info:
            self.info.append(t)

    def err(self, t):
        self.errores.append(t)


# --------------------------------------------------------------------------- sincronización

class Sync:
    def __init__(self, sh, dry, res):
        self.sh, self.dry, self.res = sh, dry, res
        self._obras_img = None

    def mut(self, descr, query, variables):
        """Ejecuta (o simula) una mutación. Devuelve el resultado o None en dry-run."""
        if self.dry:
            self.res.ok(f"[simulado] {descr}")
            return None
        d = self.sh.mutar(query, variables)
        self.res.ok(descr)
        return d

    def protegido(self, descr, fn, *a):
        try:
            fn(*a)
        except ShopifyError as e:
            self.res.err(f"{descr}: {e}")
        except Exception as e:
            self.res.err(f"{descr}: {type(e).__name__}: {e}")

    # ---- cuadros (obras)
    def cuadros(self, before, after, ficheros):
        def cargar(rev):
            d = {}
            for f in ficheros:
                x = leer_json(rev, f"data/cuadros/{f}")
                if isinstance(x, dict):
                    d.update(x)
            return d
        a, b = cargar(before), cargar(after)
        cambios = []
        for k, nuevo in b.items():
            viejo = a.get(k)
            if viejo is None:
                if nuevo.get("es_obra"):
                    self.res.pend(f"Cuadro nuevo en la web: «{nuevo.get('titulo')}» (proyecto {nuevo.get('slug')}); "
                                  "crear la obra en Shopify")
                continue
            dif = {f: nuevo.get(f) for f in CAMPOS_CUADRO if viejo.get(f) != nuevo.get(f)}
            otros = [f for f in hojas(viejo, nuevo) if f not in CAMPOS_CUADRO and f != "fuente"]
            for f in otros:
                self.res.pend(f"Cuadro «{nuevo.get('titulo')}»: cambió «{f}» (sin equivalente automático)")
            if dif:
                cambios.append((viejo, nuevo, dif))
        for k, viejo in a.items():
            if k not in b and viejo.get("es_obra"):
                self.res.pend(f"Cuadro eliminado de la web: «{viejo.get('titulo')}»; retirarlo en Shopify si procede")
        if not cambios:
            return
        obras = self.sh.obras()
        for viejo, nuevo, dif in cambios:
            self.protegido(f"obra «{nuevo.get('titulo')}»", self.obra, obras, viejo, nuevo, dif)

    def obra(self, obras, viejo, nuevo, dif):
        slug = nuevo.get("slug") or viejo.get("slug")
        es = lambda t: norm((t or "").split(" / ")[0])
        cand = []
        for t in (viejo.get("titulo"), nuevo.get("titulo")):
            cand = [o for o in obras if o["handle"].startswith(slug + "-") and es((o["titulo"] or {}).get("value")) == es(t)]
            if cand:
                break
        nombre = (nuevo.get("titulo") or "").split(" / ")[0].strip()
        if len(cand) != 1:
            motivo = "no encuentro la obra en Shopify" if not cand else "varias obras coinciden"
            self.res.pend(f"Cuadro «{nombre}» ({slug}): {motivo}; cambios {json.dumps(dif, ensure_ascii=False)}")
            return
        o = cand[0]
        actual = {k: (o[k] or {}).get("value") or "" for k in ("titulo", "titulo_en", "tecnica", "medidas", "estado")}
        deseado = {}
        for f, v in dif.items():
            if f == "estado":
                if v is None or v == "":
                    self.res.pend(f"Cuadro «{nombre}»: se quitó el estado; decidir en Shopify (¿«Sin indicar»?)")
                elif v in ESTADOS:
                    deseado["estado"] = ESTADOS[v]
                else:
                    self.res.pend(f"Cuadro «{nombre}»: estado desconocido «{v}»")
            elif f == "titulo" and v:
                es_t, _, en_t = v.partition(" / ")
                deseado["titulo"] = es_t.strip()
                if en_t.strip():
                    deseado["titulo_en"] = en_t.strip()
            elif f in ("tecnica", "medidas") and v is not None:
                deseado[f] = v
        campos = [{"key": k, "value": v} for k, v in deseado.items() if actual.get(k) != v]
        if not campos:
            self.res.nada(f"Obra «{nombre}»: ya estaba al día ({', '.join(deseado) or 'sin cambios mapeables'})")
            return
        detalle = ", ".join(f"{c['key']}: {actual.get(c['key']) or '∅'} → {c['value']}" for c in campos)
        self.mut(f"Obra «{nombre}» ({o['handle']}): {detalle}",
                 """mutation($id:ID!,$m:MetaobjectUpdateInput!){metaobjectUpdate(id:$id, metaobject:$m){userErrors{field message}}}""",
                 {"id": o["id"], "m": {"fields": campos}})

    # ---- pañuelos y láminas
    def tienda(self, before, after):
        ed_a, ed_b = leer_json(before, "data/ediciones.json") or {}, leer_json(after, "data/ediciones.json") or {}
        for kind, fichero, tipo, pt in (("pañuelo", "panuelos.json", "panuelos", "Pañuelos"),
                                        ("lámina", "laminas.json", "laminas", "Láminas")):
            pa = leer_json(before, f"data/{fichero}") or {"productos": []}
            pb = leer_json(after, f"data/{fichero}") or {"productos": []}
            tipo_a = (ed_a.get("tipos") or {}).get(tipo) or {}
            tipo_b = (ed_b.get("tipos") or {}).get(tipo) or {}
            tam_a, tam_b = tipo_a.get("tamanos") or [], tipo_b.get("tamanos") or []
            da = {p["slug"]: p for p in pa["productos"]}
            for p in pb["productos"]:
                v = da.get(p["slug"])
                if v is None:
                    self.res.pend(f"Producto nuevo ({kind}) «{p['slug']}»; crearlo en Shopify")
                    continue
                self.tamanos(kind, pt, p["slug"], v.get("tamanos") or tam_a, p.get("tamanos") or tam_b)
                if kind == "pañuelo":
                    self.colores(p["slug"], v, p)
                self.protegido(f"{kind} {p['slug']} ficha", self.campos_producto, kind, pt, v, p, tipo_a, tipo_b)
                resto = [h for h in hojas(v, p)
                         if not h.startswith(("tamanos", "obra", "nombre", "descripcion", "lema", "ficha"))
                         and not re.fullmatch(r"colores\[[^\]]+\]/label", h)]
                for h in resto:
                    self.res.pend(f"{kind.capitalize()} «{p['slug']}»: cambió «{h}» (sin equivalente automático)")
            for s in da:
                if s not in {p["slug"] for p in pb["productos"]}:
                    self.res.pend(f"Producto ({kind}) «{s}» eliminado de la web; retirarlo en Shopify si procede")
            for k in ("precio", "medida", "ficha", "ficha_en", "_nota"):
                if k in pa and k in pb and pa[k] != pb[k] and fichero == "panuelos.json" and k not in ("ficha", "ficha_en"):
                    self.res.pend(f"panuelos.json: cambió «{k}» global (la web ya no lo usa para precios; "
                                  "revisar si afecta a fichas en Shopify)" if k == "precio"
                                  else f"panuelos.json: cambió «{k}» global; revisar fichas en Shopify")
            resto_tipo = [h for h in hojas((ed_a.get("tipos") or {}).get(tipo), (ed_b.get("tipos") or {}).get(tipo))
                          if not h.startswith(("tamanos", "ficha"))]
            for h in resto_tipo:
                self.res.pend(f"ediciones.json › {tipo}: cambió «{h}» (sin equivalente automático)")
        otros = [h for h in hojas({k: v for k, v in ed_a.items() if k != "tipos"},
                                  {k: v for k, v in ed_b.items() if k != "tipos"})]
        for h in otros[:20]:
            self.res.pend(f"ediciones.json: cambió «{h}» (sin equivalente automático)")

    def campos_producto(self, kind, pt, v, n, tipo_a, tipo_b):
        """ficha, descripción, lema, nombre y obra de un pañuelo/lámina -> producto y metafields ana.*"""
        ef = lambda p, t, k: p.get(k) or t.get(k)
        cambios = {}  # clave -> (tipo de dato, valor deseado)
        for k, tipo_mf in (("ficha", "multi_line_text_field"), ("ficha_en", "multi_line_text_field"),
                           ("descripcion_en", "multi_line_text_field"), ("lema", "single_line_text_field"),
                           ("lema_en", "single_line_text_field")):
            a, b = ef(v, tipo_a, k), ef(n, tipo_b, k)
            if a != b and b:
                cambios[k] = (tipo_mf, b)
        desc = n.get("descripcion") if v.get("descripcion") != n.get("descripcion") else None
        nombre = n.get("nombre") if v.get("nombre") != n.get("nombre") else None
        obra_img = (n.get("obra") or {}).get("img")
        obra_cambia = bool(obra_img) and obra_img != (v.get("obra") or {}).get("img")
        if not (cambios or desc or nombre or obra_cambia):
            return
        slug = n["slug"]
        p = self.prod(kind, pt, slug)
        if not p:
            self.res.pend(f"{kind.capitalize()} «{slug}»: no encuentro el producto en Shopify para actualizar "
                          f"{sorted(cambios) + (['descripcion'] if desc else []) + (['nombre'] if nombre else []) + (['obra'] if obra_cambia else [])}")
            return
        et = f"{kind.capitalize()} «{slug}»"
        actual = p["metafields"]
        mf = []
        for k, (tipo_mf, val) in cambios.items():
            if actual.get(k) == val:
                self.res.nada(f"{et}: {k} ya al día")
            else:
                mf.append({"ownerId": p["id"], "namespace": "ana", "key": k, "type": tipo_mf, "value": val})
        if obra_cambia:
            oid = self.obra_por_imagen(obra_img)
            if not oid:
                self.res.pend(f"{et}: obra «{Path(obra_img).name}»: no hay obra en Shopify con esa imagen")
            elif actual.get("obra") == oid:
                self.res.nada(f"{et}: obra ya al día")
            else:
                mf.append({"ownerId": p["id"], "namespace": "ana", "key": "obra",
                           "type": "metaobject_reference", "value": oid})
        if mf:
            self.mut(f"{et}: metafields {', '.join(m['key'] for m in mf)}",
                     """mutation($m:[MetafieldsSetInput!]!){metafieldsSet(metafields:$m){userErrors{field message}}}""",
                     {"m": mf})
        if desc:
            html_ = "".join(f"<p>{escape(x.strip())}</p>" for x in desc.split("\n") if x.strip())
            if sin_html(p["descriptionHtml"]) == norm(desc):
                self.res.nada(f"{et}: descripción ya al día")
            else:
                self.mut(f"{et}: descripción actualizada",
                         """mutation($i:ProductInput!){productUpdate(input:$i){userErrors{field message}}}""",
                         {"i": {"id": p["id"], "descriptionHtml": html_}})
        if nombre:
            self.nombre(et, p, v.get("nombre") or "", nombre)
        self.sh.invalidar(p["handle"])

    def nombre(self, et, p, viejo, nuevo):
        """El título de Shopify lleva el nombre ES (con prefijo p. ej. «Fular»); solo se cambia si termina en el nombre viejo."""
        (v_es, _, v_en), (n_es, _, n_en) = (viejo.partition(" / "), nuevo.partition(" / "))
        v_es, n_es, v_en, n_en = v_es.strip(), n_es.strip(), v_en.strip(), n_en.strip()
        t = p["title"]
        if norm(t).endswith(norm(n_es)):
            self.res.nada(f"{et}: título ya al día")
        elif v_es and norm(t).endswith(norm(v_es)):
            nuevo_t = t[:len(t) - len(v_es)] + n_es
            self.mut(f"{et}: título «{t}» → «{nuevo_t}»",
                     """mutation($i:ProductInput!){productUpdate(input:$i){userErrors{field message}}}""",
                     {"i": {"id": p["id"], "title": nuevo_t}})
        else:
            self.res.pend(f"{et}: el nombre cambió a «{n_es}» pero el título de Shopify («{t}») no coincide; revisar")
            return
        te = p["metafields"].get("titulo_en") or ""
        if n_en and not norm(te).endswith(norm(n_en)) and v_en and norm(te).endswith(norm(v_en)):
            self.mut(f"{et}: titulo_en «{te}» → «{te[:len(te) - len(v_en)] + n_en}»",
                     """mutation($m:[MetafieldsSetInput!]!){metafieldsSet(metafields:$m){userErrors{field message}}}""",
                     {"m": [{"ownerId": p["id"], "namespace": "ana", "key": "titulo_en",
                             "type": "single_line_text_field", "value": te[:len(te) - len(v_en)] + n_en}]})

    def obra_por_imagen(self, img):
        if self._obras_img is None:
            self._obras_img = {}
            for o in self.sh.obras():
                u = ((o.get("imagen") or {}).get("reference") or {}).get("image", {}).get("url", "")
                self._obras_img.setdefault(stem_archivo(u), o["id"])
        return self._obras_img.get(stem_archivo(img))

    def handles(self, kind, slug):
        return [f"lamina-{slug}", slug] if kind == "lámina" else [slug]

    def prod(self, kind, pt, slug):
        for h in self.handles(kind, slug):
            p = self.sh.producto(h)
            if p and p["productType"] == pt:
                return p
        return None

    def tamanos(self, kind, pt, slug, ta, tb):
        if {t["id"] for t in ta} == {t["id"] for t in tb}:
            da, db = {t["id"]: t for t in ta}, {t["id"]: t for t in tb}
            pares = [(da[i], db[i]) for i in db]
        elif len(ta) == len(tb):  # mismos tamaños con otros ids: se emparejan por posición
            pares = list(zip(ta, tb))
        else:
            self.res.pend(f"{kind.capitalize()} «{slug}»: cambió el número de tamaños "
                          f"({len(ta)} → {len(tb)}); añadir/quitar variantes en Shopify")
            return
        for v, n in pares:
            if v["label"] == n["label"] and v["precio"] == n["precio"]:
                continue
            self.protegido(f"{kind} {slug} tamaño {n['label']}", self.tamano, kind, pt, slug, v, n)

    def tamano(self, kind, pt, slug, v, n):
        p = self.prod(kind, pt, slug)
        if not p:
            self.res.pend(f"{kind.capitalize()} «{slug}»: no encuentro el producto en Shopify; "
                          f"tamaño {v['label']} → {n['label']}, precio {v['precio']} → {n['precio']}")
            return
        if v["label"] != n["label"]:
            self.renombrar(p, v["label"], n["label"], f"{kind.capitalize()} «{slug}» tamaño")
            self.sh.invalidar(p["handle"])
            p = self.sh.producto(p["handle"])  # en simulación sigue con el nombre viejo: se busca por ambos
        precio = f"{float(n['precio']):.2f}"
        vs = [x for x in p["variants"]["nodes"] if any(s["value"] in (n["label"], v["label"]) for s in x["selectedOptions"])]
        if not vs:
            self.res.pend(f"{kind.capitalize()} «{slug}»: no encuentro la variante «{n['label']}» en Shopify "
                          f"(precio {v['precio']} → {n['precio']})")
            return
        cambiar = [x for x in vs if float(x["price"]) != float(precio)]
        if not cambiar:
            self.res.nada(f"{kind.capitalize()} «{slug}» «{n['label']}»: precio {precio} ya estaba al día")
            return
        self.mut(f"{kind.capitalize()} «{slug}» «{n['label']}»: precio {cambiar[0]['price']} → {precio} "
                 f"({len(cambiar)} variante/s)",
                 """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){productVariantsBulkUpdate(productId:$p, variants:$v){userErrors{field message}}}""",
                 {"p": p["id"], "v": [{"id": x["id"], "price": precio} for x in cambiar]})
        self.sh.invalidar(p["handle"])

    def renombrar(self, p, viejo, nuevo, descr, solo_opcion=None):
        """Renombra un valor de opción de un producto. True si lo hizo o ya estaba hecho."""
        for o in p["options"]:
            if solo_opcion and o["name"] != solo_opcion:
                continue
            nombres = {ov["name"]: ov for ov in o["optionValues"]}
            if nuevo in nombres:
                self.res.nada(f"{descr} «{nuevo}» en {p['handle']}: ya estaba renombrado")
                return True
            if viejo in nombres:
                self.mut(f"{descr}: «{viejo}» → «{nuevo}» en {p['handle']}",
                         """mutation($p:ID!,$o:OptionUpdateInput!,$v:[OptionValueUpdateInput!]){
                            productOptionUpdate(productId:$p, option:$o, optionValuesToUpdate:$v){userErrors{field message}}}""",
                         {"p": p["id"], "o": {"id": o["id"]}, "v": [{"id": nombres[viejo]["id"], "name": nuevo}]})
                self.sh.invalidar(p["handle"])
                return True
        self.res.pend(f"{descr} en {p['handle']}: no encuentro el valor «{viejo}» ni «{nuevo}» en Shopify")
        return False

    def colores(self, slug, v, n):
        da = {c["id"]: c["label"] for c in v.get("colores") or []}
        for c in n.get("colores") or []:
            if c["id"] in da and da[c["id"]] != c["label"]:
                self.protegido(f"pañuelo {slug} color {c['id']}", self.color, slug, da[c["id"]], c["label"])

    def color(self, slug, viejo, nuevo):
        p = self.prod("pañuelo", "Pañuelos", slug)
        if not p or not any(o["name"] == "Color" for o in p["options"]):
            return  # sin opción Color en Shopify: se ignora en silencio
        self.renombrar(p, viejo, nuevo, f"Pañuelo «{slug}» color", solo_opcion="Color")

    # ---- proyectos
    def proyectos(self, before, after):
        a = (leer_json(before, "data/content.json") or {}).get("posts", [])
        b = (leer_json(after, "data/content.json") or {}).get("posts", [])
        da = {p["slug"]: p for p in a}
        for p in b:
            v = da.get(p["slug"])
            if v is None:
                self.res.pend(f"Proyecto nuevo «{p['slug']}» ({p.get('title')}); crearlo en Shopify con sus imágenes y textos")
                continue
            if v.get("title") != p.get("title"):
                self.protegido(f"proyecto {p['slug']} título", self.titulo_proyecto, p["slug"], p["title"])
            if v.get("cover") != p.get("cover"):
                self.protegido(f"proyecto {p['slug']} portada", self.portada, p["slug"], p["cover"], p.get("title"))
            for h in hojas({k: x for k, x in v.items() if k not in ("title", "cover")},
                           {k: x for k, x in p.items() if k not in ("title", "cover")}):
                if h.startswith("images"):
                    h = "images (fotos del proyecto añadidas/quitadas/reordenadas)"
                self.res.pend(f"Proyecto «{p['slug']}»: cambió «{h}» (sin equivalente automático)")
        for s in da:
            if s not in {p["slug"] for p in b}:
                self.res.pend(f"Proyecto «{s}» eliminado de la web; retirarlo en Shopify si procede")
        if (leer_json(before, "data/content.json") or {}).get("pages") != (leer_json(after, "data/content.json") or {}).get("pages"):
            self.res.inf("content.json › pages: cambió (páginas de la web, sin equivalente en Shopify)")

    def titulo_proyecto(self, slug, titulo_gh):
        pr = self.sh.proyecto(slug)
        if not pr:
            self.res.pend(f"Proyecto «{slug}»: título → «{titulo_gh}», pero no existe el proyecto en Shopify")
            return
        nuevo = titulo_shopify(titulo_gh)
        actual = (pr["titulo"] or {}).get("value") or ""
        if actual == nuevo:
            self.res.nada(f"Proyecto «{slug}»: título ya al día")
        elif sin_acentos(actual) == sin_acentos(nuevo):
            self.res.nada(f"Proyecto «{slug}»: título solo difiere en acentos/mayúsculas («{actual}» / «{nuevo}»); no se toca")
        else:
            self.mut(f"Proyecto «{slug}»: título «{actual}» → «{nuevo}»",
                     """mutation($h:MetaobjectHandleInput!,$m:MetaobjectUpsertInput!){
                        metaobjectUpsert(handle:$h, metaobject:$m){userErrors{field message}}}""",
                     {"h": {"type": "proyecto", "handle": slug}, "m": {"fields": [{"key": "titulo", "value": nuevo}]}})

    def portada(self, slug, cover, titulo):
        if not cover:
            self.res.pend(f"Proyecto «{slug}»: se quitó la portada; decidir en Shopify")
            return
        pr = self.sh.proyecto(slug)
        if not pr:
            self.res.pend(f"Proyecto «{slug}»: portada → {cover}, pero no existe el proyecto en Shopify")
            return
        ruta = ruta_publica(cover)
        url = ruta if ruta.startswith("http") else PAGES + urllib.parse.quote(ruta)
        nombre = Path(urllib.parse.unquote(ruta)).stem
        ref = ((pr["portada"] or {}).get("reference") or {}).get("image") or {}
        actual = Path(urllib.parse.unquote(urllib.parse.urlparse(ref.get("url", "")).path)).stem
        if actual and (actual == nombre or actual.startswith(nombre)):
            self.res.nada(f"Proyecto «{slug}»: portada ya al día ({nombre})")
            return
        if self.dry:
            self.res.ok(f"[simulado] Proyecto «{slug}»: portada {actual or '∅'} → {nombre} (subir {url})")
            return
        if not esperar_url(url):
            self.res.pend(f"Proyecto «{slug}»: portada → {ruta}; la imagen aún no está publicada en GitHub Pages. "
                          "Relanzar la sincronización cuando la web esté desplegada")
            return
        d = self.sh.mutar("""mutation($f:[FileCreateInput!]!){fileCreate(files:$f){files{id} userErrors{field message}}}""",
                          {"f": [{"originalSource": url, "contentType": "IMAGE", "alt": (titulo or slug)[:120]}]})
        fid = d["fileCreate"]["files"][0]["id"]
        self.sh.mutar("""mutation($h:MetaobjectHandleInput!,$m:MetaobjectUpsertInput!){
            metaobjectUpsert(handle:$h, metaobject:$m){userErrors{field message}}}""",
                      {"h": {"type": "proyecto", "handle": slug}, "m": {"fields": [{"key": "portada", "value": fid}]}})
        self.res.ok(f"Proyecto «{slug}»: portada {actual or '∅'} → {nombre} (archivo subido desde GitHub Pages)")


def esperar_url(url, maximo=480):
    """Espera a que GitHub Pages sirva la imagen (el despliegue corre en paralelo a este flujo)."""
    fin = time.time() + maximo
    while True:
        try:
            req = urllib.request.Request(url, method="HEAD")
            if urllib.request.urlopen(req, timeout=20).status == 200:
                return True
        except Exception:
            pass
        if time.time() > fin:
            return False
        time.sleep(15)


# --------------------------------------------------------------------------- principal

def informe(res, before, after, dry):
    L = [f"# Sincronización GitHub → Shopify{' (simulación)' if dry else ''}",
         f"Rango: `{before[:7]}..{after[:7]}`", ""]

    def sec(titulo, items):
        L.append(f"## {titulo} ({len(items)})")
        L.extend(f"- {i}" for i in items) if items else L.append("- ninguno")
        L.append("")
    sec("Aplicado en Shopify" if not dry else "Se aplicaría en Shopify", res.hechos)
    sec("Ya estaba al día", res.sin_cambio if len(res.sin_cambio) <= 15 else
        [f"{len(res.sin_cambio)} comprobaciones sin diferencias (omitidas por brevedad)"])
    sec("Pendiente manual", res.pendientes)
    sec("Informativo (sin equivalente en Shopify)", res.info)
    if res.errores:
        sec("ERRORES de API", res.errores)
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", default="HEAD~1")
    ap.add_argument("--after", default="HEAD")
    ap.add_argument("--dry-run", action="store_true", help="no escribe en Shopify (sí lo lee)")
    ap.add_argument("--resumen", help="guarda el resumen en este fichero")
    ap.add_argument("--pendientes", help="guarda aquí los pendientes manuales (vacío si no hay)")
    a = ap.parse_args()

    after = resolver(a.after)
    if not after:
        sys.exit(f"No encuentro el commit {a.after}")
    before = None if a.before in ("", ZEROS) else resolver(a.before)
    if not before:
        before = resolver(after + "~1")
        print(f"AVISO: commit «before» no válido; se usa {after[:7]}~1", file=sys.stderr)
    if not before:
        sys.exit("No hay commit anterior con el que comparar")

    res = Resumen()
    cambiados = ficheros_cambiados(before, after)
    if not cambiados:
        print("Sin cambios en data/ en este rango. Nada que hacer.")
    else:
        sync = Sync(Shopify(), a.dry_run, res)
        lotes = sorted(Path(f).name for f in cambiados if f.startswith("data/cuadros/"))
        pasos = []
        if lotes:
            pasos.append(("cuadros", lambda: sync.cuadros(before, after, lotes)))
        if any(f in ("data/panuelos.json", "data/laminas.json", "data/ediciones.json") for f in cambiados):
            pasos.append(("tienda", lambda: sync.tienda(before, after)))
        if "data/content.json" in cambiados:
            pasos.append(("proyectos", lambda: sync.proyectos(before, after)))
        for nombre, fn in pasos:
            sync.protegido(nombre, fn)
        for f in cambiados:
            n = f[len("data/"):]
            if n in SIN_EQUIVALENTE or n.startswith(SIN_EQUIVALENTE_DIRS):
                res.inf(f"{n} modificado")
            elif f.startswith("data/cuadros/") or n in ("panuelos.json", "laminas.json", "ediciones.json", "content.json"):
                pass
            else:
                res.pend(f"Fichero {n} modificado (sin mapeo conocido)")

    texto = informe(res, before, after, a.dry_run)
    print(texto)
    if a.resumen:
        Path(a.resumen).write_text(texto + "\n")
    if a.pendientes:
        Path(a.pendientes).write_text(
            "\n".join(f"- {p}" for p in res.pendientes) + "\n" if res.pendientes else "")
    sys.exit(1 if res.errores else 0)


if __name__ == "__main__":
    main()
