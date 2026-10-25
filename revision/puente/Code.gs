/**
 * Puente del modo revisión de ana-martinez.com
 *
 * Recibe comentarios y mensajes desde la web (assets/revision.js) y los guarda en el repo
 * antonioomsg/ana-martinez, carpeta revision/, usando la API de GitHub. El token de GitHub
 * vive solo aquí (Propiedades del script), nunca en la web.
 *
 * Propiedades del script (Configuración del proyecto → Propiedades del script):
 *   CLAVE         clave larga que lleva el enlace privado (?revisar=CLAVE)
 *   GITHUB_TOKEN  token fine-grained con permiso "Contents: Read and write" solo en el repo
 *   REPO          antonioomsg/ana-martinez
 *   RAMA          main
 *
 * Despliegue: Implementar → Nueva implementación → Aplicación web
 *   Ejecutar como: Yo · Quién tiene acceso: Cualquier usuario
 */

var PEND = "revision/pendiente";
var HIST = "revision/historial.json";
var ARCH = "revision/archivos";

function prop(k) { return PropertiesService.getScriptProperties().getProperty(k); }

function respuesta(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  return respuesta({ ok: true, servicio: "revision ana-martinez" });
}

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    if (!body.key || body.key !== prop("CLAVE")) return respuesta({ ok: false, error: "Clave no válida" });
    if (body.action === "listar") return respuesta(listar());
    if (body.action === "nuevo") return respuesta(nuevo(body.item, body.archivos || []));
    return respuesta({ ok: false, error: "Acción desconocida" });
  } catch (err) {
    return respuesta({ ok: false, error: String(err && err.message || err) });
  }
}

/* ---------- GitHub ---------- */

function gh(method, path, payload) {
  var opts = {
    method: method,
    muteHttpExceptions: true,
    headers: {
      Authorization: "Bearer " + prop("GITHUB_TOKEN"),
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28"
    }
  };
  if (payload) { opts.contentType = "application/json"; opts.payload = JSON.stringify(payload); }
  var res = UrlFetchApp.fetch("https://api.github.com/repos/" + prop("REPO") + path, opts);
  var code = res.getResponseCode();
  if (code === 404) return null;
  if (code >= 300) throw new Error("GitHub " + code + ": " + res.getContentText().slice(0, 200));
  return JSON.parse(res.getContentText() || "null");
}

function ruta(p) { return p.split("/").map(encodeURIComponent).join("/"); }

function guardar(path, base64, mensaje) {
  var rama = prop("RAMA") || "main";
  var actual = gh("get", "/contents/" + ruta(path) + "?ref=" + rama);
  var payload = { message: mensaje, content: base64, branch: rama,
    committer: { name: "Revisión web", email: "revision@ana-martinez.com" } };
  if (actual && actual.sha) payload.sha = actual.sha;
  return gh("put", "/contents/" + ruta(path), payload);
}

function leerJson(path) {
  var rama = prop("RAMA") || "main";
  var f = gh("get", "/contents/" + ruta(path) + "?ref=" + rama);
  if (!f) return null;
  var txt = f.content
    ? Utilities.newBlob(Utilities.base64Decode(f.content.replace(/\n/g, ""))).getDataAsString("UTF-8")
    : UrlFetchApp.fetch(f.download_url, { headers: { Authorization: "Bearer " + prop("GITHUB_TOKEN") } }).getContentText("UTF-8");
  return JSON.parse(txt);
}

/* ---------- acciones ---------- */

function limpio(s) {
  return String(s || "archivo").normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^\w.\-]+/g, "-").replace(/-+/g, "-").slice(0, 80);
}

function nuevo(item, archivos) {
  if (!item || !item.id || !item.tipo) throw new Error("Datos incompletos");
  item.id = limpio(item.id);
  item.recibido = new Date().toISOString();
  item.texto = String(item.texto || "").slice(0, 8000);
  item.archivos = [];

  for (var i = 0; i < archivos.length && i < 30; i++) {
    var a = archivos[i];
    var p = ARCH + "/" + item.id + "/" + (i + 1) + "-" + limpio(a.nombre);
    guardar(p, a.base64, "Revisión: adjunto de " + (item.autor || "Ana"));
    item.archivos.push(p);
  }

  var json = Utilities.base64Encode(JSON.stringify(item, null, 2), Utilities.Charset.UTF_8);
  var resumen = item.tipo === "mensaje" ? "Hilo «" + (item.titulo_hilo || "") + "»" : "Comentario";
  guardar(PEND + "/" + item.recibido.slice(0, 10) + "-" + item.id + ".json", json,
    "Revisión: " + resumen + " de " + (item.autor || "Ana"));
  CacheService.getScriptCache().remove("listado");
  return { ok: true, id: item.id };
}

function listar() {
  var cache = CacheService.getScriptCache();
  var hit = cache.get("listado");
  if (hit) return JSON.parse(hit);

  var items = [];
  var rama = prop("RAMA") || "main";
  var dir = gh("get", "/contents/" + PEND + "?ref=" + rama) || [];
  dir.forEach(function (f) {
    if (f.type === "file" && /\.json$/.test(f.name)) {
      try { items.push(leerJson(f.path)); } catch (_) {}
    }
  });
  var hist = leerJson(HIST);
  if (hist && hist.items) items = items.concat(hist.items);

  var out = { ok: true, items: items };
  var s = JSON.stringify(out);
  if (s.length < 90000) cache.put("listado", s, 60);
  return out;
}
