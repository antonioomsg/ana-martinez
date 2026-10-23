"""Descarga el contenido de ana-martinez.com (WordPress) a data/content.json.

La API REST devuelve el HTML del contenido roto (plugin gamma-gallery), así que
leemos los metadatos por la API y el cuerpo de cada entrada desde su página pública.
"""
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

BASE = "https://www.ana-martinez.com"
ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
DATA = ROOT / "data"
IMG_RE = re.compile(r"\.(jpe?g|png|gif|webp)$", re.I)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def get_json(url):
    s = get(url)
    return json.loads(s[s.index("["):] if not s.lstrip().startswith(("[", "{")) else s)


def https(u):
    return html.unescape(u).replace("http://", "https://")


def entry_content(page):
    i = page.find('class="entry-content"')
    if i < 0:
        return ""
    j = page.find("<!-- .entry-content -->", i)
    return page[i: j if j > 0 else i + 200000]


def best_from_srcset(srcset):
    best, best_w = None, -1
    for part in srcset.split(","):
        bits = part.strip().split()
        if len(bits) == 2 and bits[1].endswith("w"):
            w = int(bits[1][:-1])
            if w > best_w:
                best, best_w = bits[0], w
    return best


def extract_images(body):
    seen, out = set(), []

    def add(url, alt=""):
        url = https(url)
        key = re.sub(r"-\d+x\d+(?=\.\w+$)", "", url)
        if "/wp-content/uploads/" in url and key not in seen:
            seen.add(key)
            out.append({"src": url, "alt": html.unescape(alt)})

    # Galería gamma: cada item trae varios data-src, el primero es el mayor
    for li in re.findall(r'<li>(.*?)</li>', body, re.S):
        srcs = re.findall(r'data-src="([^"]+)"', li)
        if srcs:
            alt = re.search(r'data-alt="([^"]*)"', li)
            add(srcs[0], alt.group(1) if alt else "")
    for m in re.finditer(r'(?:<a [^>]*href="([^"]+)"[^>]*>\s*)?<img ([^>]+)>', body):
        href, attrs = m.group(1), m.group(2)
        alt = re.search(r'alt="([^"]*)"', attrs)
        alt = alt.group(1) if alt else ""
        if href and IMG_RE.search(href):
            add(href, alt)
            continue
        ss = re.search(r'srcset="([^"]+)"', attrs)
        src = best_from_srcset(ss.group(1)) if ss else None
        if not src:
            s = re.search(r'src="([^"]+)"', attrs)
            src = s.group(1) if s else None
        if src:
            add(src, alt)
    return out


def extract_text(body):
    body = re.sub(r"<div class=\"gamma-container.*?gamma-overlay\"></div>\s*</div>", "", body, flags=re.S)
    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", "", body, flags=re.S)
    paras = []
    for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S):
        pdf = re.search(r'<a [^>]*href="([^"]+\.pdf)"[^>]*>(.*?)</a>', p, re.S)
        if pdf:
            label = html.unescape(re.sub(r"<[^>]+>", "", pdf.group(2))).strip() or "PDF"
            paras.append({"pdf": https(pdf.group(1)), "label": label})
            continue
        p = re.sub(r"<br\s*/?>", "\n", p)
        t = html.unescape(re.sub(r"<[^>]+>", "", p)).replace("\xa0", " ").strip()
        if t:
            paras.append(t)
    for v in re.findall(r'(?:youtube\.com/embed/|youtu\.be/)([\w-]{11})', body):
        paras.append({"youtube": v})
    return paras


def scrape_posts(api_base, cats):
    meta = get_json(f"{api_base}/posts?per_page=100&_fields=id,slug,title,date,categories,featured_media,link")
    posts = []
    for p in meta:
        page = get(p["link"])
        body = entry_content(page)
        title_en, text_en = english_version(page)
        feat = None
        if p.get("featured_media"):
            try:
                m = json.loads(get(f"{api_base}/media/{p['featured_media']}?_fields=source_url"))
                feat = https(m["source_url"])
            except Exception:
                feat = None
        imgs = extract_images(body)
        posts.append({
            "slug": p["slug"],
            "title": html.unescape(p["title"]["rendered"]),
            "date": p["date"][:10],
            "category": next((cats[c] for c in p["categories"] if c in cats), ""),
            "cover": feat or (imgs[0]["src"] if imgs else None),
            "images": imgs,
            "text": extract_text(body),
            "title_en": title_en,
            "text_en": text_en,
            "old_url": p["link"],
        })
        print(f"  {p['slug']}: {len(imgs)} imgs", file=sys.stderr)
    return posts


def english_version(page):
    """Título y textos de la traducción inglesa enlazada con hreflang (plugin MSLS)."""
    m = re.search(r'hreflang="en" href="([^"]+)"', page)
    if not m:
        return None, []
    en = get(m.group(1))
    t = re.search(r'<h1 class="entry-title">(.*?)</h1>', en, re.S)
    title = html.unescape(re.sub(r"<[^>]+>", "", t.group(1))).strip() if t else None
    return title, extract_text(entry_content(en))


def scrape_page(url):
    body = entry_content(get(url))
    return {"images": extract_images(body), "text": extract_text(body)}


def main():
    api = f"{BASE}/wp-json/wp/v2"
    cats = {c["id"]: c["name"] for c in get_json(f"{api}/categories?per_page=50")}
    out = {
        "posts": scrape_posts(api, cats),
        "pages": {
            "bio": scrape_page(f"{BASE}/bio/"),
            "contacto": scrape_page(f"{BASE}/contacto/"),
            "talleres": scrape_page(f"{BASE}/talleres/"),
            "bio_en": scrape_page(f"{BASE}/en/biography/"),
        },
    }
    (DATA / "content.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"OK {len(out['posts'])} entradas", file=sys.stderr)


if __name__ == "__main__":
    main()
