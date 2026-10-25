/**
 * Editor de la web de Ana Martínez (https://antonioomsg.github.io/ana-martinez/).
 *
 * 1. doPost: el modo edición de la web (?editar) entra con usuario y contraseña y guarda
 *    textos, datos y fotos en el repo de GitHub (data/*.json, assets/). GitHub Actions publica
 *    la web en 1-2 min.
 * 2. Modo revisión (assets/revision.js): Ana deja comentarios e hilos con adjuntos en
 *    revision/pendiente/ y un agente en la nube los aplica cada noche (revision/AGENTE.md).
 * 3. copiarADrive: sube al Drive compartido, ordenado por carpetas, las fotos, PDF y textos
 *    de la web (según archivo_drive.json, que genera build.py). Se puede repetir: solo añade
 *    lo que falta y actualiza los documentos «Textos» que hayan cambiado. Se lanza sola 5 min
 *    después de que Ana guarde fotos, y cada noche si se ejecuta una vez programarCopiaDiaria.
 *
 * Configuración (Configuración del proyecto ⚙ → Propiedades del script):
 *   USUARIO        usuario de Ana para entrar en modo edición
 *   CONTRASENA     su contraseña
 *   GITHUB_TOKEN   token de GitHub con permiso «Contents: read and write» solo en antonioomsg/ana-martinez
 *   DRIVE_CARPETA  (opcional) id de la unidad o carpeta de Drive; por defecto la unidad de Ana
 * Después: ejecutar «comprobar», y Implementar → Nueva implementación → Aplicación web
 * (Ejecutar como: yo · Quién tiene acceso: cualquier usuario).
 */

const REPO = 'antonioomsg/ana-martinez';
const RAMA = 'main';
const WEB = 'https://antonioomsg.github.io/ana-martinez/';
const DRIVE_POR_DEFECTO = '0ACbqrv17fXYDUk9PVA';
const HORAS_SESION = 12;
const VERSION = 4; // 2: fotos y párrafos · 3: comentarios del modo revisión · 4: huellas
const MAX_FALLOS = 8; // intentos de contraseña fallidos antes de bloquear 15 minutos

// Ficheros de data/ que el editor puede tocar
const FICHEROS = /^(content|panuelos|laminas|ediciones|bio|documentos|translations_en|sitio|cuadros\/[a-z0-9_]+|textos_curador\/[a-z0-9_]+)\.json$/i;
const CLAVES_PROHIBIDAS = ['__proto__', 'constructor', 'prototype', 'editor_url'];

const props = () => PropertiesService.getScriptProperties();

function respuesta(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  return respuesta({ ok: true, version: VERSION, mensaje: 'Editor de la web de Ana Martínez: funcionando.' });
}

function doPost(e) {
  let datos;
  try {
    datos = JSON.parse(e.postData.contents);
  } catch (err) {
    return respuesta({ ok: false, error: 'Petición no válida.' });
  }
  try {
    if (datos.accion === 'entrar') return respuesta(entrar_(datos));
    if (datos.accion === 'guardar') return respuesta(guardar_(datos));
    if (datos.action === 'listar' || datos.action === 'nuevo') return respuesta(revision_(datos));
    return respuesta({ ok: false, error: 'Acción desconocida.' });
  } catch (err) {
    console.error(err && err.stack || err);
    return respuesta({ ok: false, error: 'Error al guardar: ' + (err && err.message || err) });
  }
}

// ---------- Sesión ----------

function secreto_() {
  let s = props().getProperty('SECRETO');
  if (!s) {
    s = Utilities.getUuid() + Utilities.getUuid();
    props().setProperty('SECRETO', s);
  }
  return s;
}

function firma_(texto) {
  return Utilities.base64EncodeWebSafe(Utilities.computeHmacSha256Signature(texto, secreto_()));
}

function iguales_(a, b) {
  a = String(a); b = String(b);
  let dif = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) dif |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return dif === 0;
}

function entrar_(datos) {
  const cache = CacheService.getScriptCache();
  const fallos = Number(cache.get('fallos') || 0);
  if (fallos >= MAX_FALLOS) return { ok: false, error: 'Demasiados intentos. Espera 15 minutos y vuelve a probar.' };
  const usuario = props().getProperty('USUARIO');
  const contrasena = props().getProperty('CONTRASENA');
  if (!usuario || !contrasena) return { ok: false, error: 'El editor no tiene usuario configurado.' };
  if (!iguales_(String(datos.usuario || '').toLowerCase(), usuario.toLowerCase()) || !iguales_(datos.contrasena || '', contrasena)) {
    cache.put('fallos', String(fallos + 1), 15 * 60);
    Utilities.sleep(800);
    return { ok: false, error: 'Usuario o contraseña incorrectos.' };
  }
  const exp = Date.now() + HORAS_SESION * 3600 * 1000;
  return { ok: true, token: exp + '.' + firma_(String(exp)), exp: exp, version: VERSION };
}

function sesionValida_(token) {
  const partes = String(token || '').split('.');
  if (partes.length !== 2) return false;
  const exp = Number(partes[0]);
  return exp > Date.now() && iguales_(partes[1], firma_(String(exp)));
}

// ---------- Guardar en GitHub ----------

function github_(metodo, ruta, cuerpo, crudo) {
  const token = props().getProperty('GITHUB_TOKEN');
  if (!token) throw new Error('falta GITHUB_TOKEN en las propiedades del script');
  const r = UrlFetchApp.fetch('https://api.github.com/repos/' + REPO + ruta, {
    method: metodo,
    contentType: 'application/json',
    payload: cuerpo ? JSON.stringify(cuerpo) : undefined,
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: crudo ? 'application/vnd.github.raw+json' : 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    muteHttpExceptions: true,
  });
  const code = r.getResponseCode();
  const texto = r.getContentText('UTF-8');
  if (code >= 300) {
    const err = new Error('GitHub ' + code + ' en ' + ruta + ': ' + texto.slice(0, 200));
    err.code = code;
    throw err;
  }
  return crudo ? texto : JSON.parse(texto);
}

// Listas de párrafos: un texto con líneas en blanco se parte en varios párrafos y uno vacío se quita
const LISTAS_PARRAFOS = ['text', 'text_en', 'es', 'en', 'texto', 'texto_en'];
// Fotos que se pueden subir: carpetas de subidas y de las ediciones, más la portada y el retrato fijos
const ARCHIVOS = /^assets\/(subidas\/[a-z0-9-]+|panuelos|laminas)\/[a-z0-9_.-]+\.(jpg|png)$|^assets\/(hero\.png|ana-martinez\.jpg|ana-martinez-roca\.jpg)$/;
const FOTO = /^assets\/[A-Za-z0-9_.\/-]+\.(jpe?g|png|gif|webp)$/i;

function validarCambio_(c) {
  if (!c || !Array.isArray(c.ruta) || c.ruta.length < 2 || c.ruta.length > 8) throw new Error('ruta no válida');
  if (!FICHEROS.test(c.ruta[0])) throw new Error('fichero no editable: ' + c.ruta[0]);
  c.ruta.slice(1).forEach(function (k) {
    if (!(typeof k === 'number' || typeof k === 'string') || CLAVES_PROHIBIDAS.indexOf(String(k)) >= 0) throw new Error('ruta no válida');
  });
  const op = c.op || 'poner';
  const ultimo = c.ruta[c.ruta.length - 1];
  if (op === 'poner') {
    if (typeof c.valor === 'string') {
      if (c.valor.length > 20000) throw new Error('texto demasiado largo');
    } else if (typeof c.valor !== 'number' || !isFinite(c.valor) || c.valor < 0) {
      throw new Error('valor no válido');
    }
  } else if (op === 'insertar') { // después de la posición indicada (-1 = al principio)
    if (typeof ultimo !== 'number' || ultimo < -1) throw new Error('posición no válida');
    const v = c.valor;
    const esFoto = v && typeof v === 'object' && typeof v.src === 'string' && FOTO.test(v.src) &&
      typeof (v.alt || '') === 'string' && Object.keys(v).every(function (k) { return k === 'src' || k === 'alt'; });
    if (!esFoto && !(typeof v === 'string' && v.length <= 20000)) throw new Error('elemento no válido');
  } else if (op === 'quitar') {
    if (typeof ultimo !== 'number' || ultimo < 0) throw new Error('posición no válida');
  } else if (op === 'reclave') { // la cartela pasa a la foto nueva
    if (!/^cuadros\//.test(c.ruta[0]) || c.ruta.length !== 2 || typeof c.valor !== 'string' || !FOTO.test(c.valor)) throw new Error('cartela no válida');
  } else {
    throw new Error('operación no válida');
  }
}

function validarArchivo_(a) {
  if (!a || typeof a.ruta !== 'string' || !ARCHIVOS.test(a.ruta)) throw new Error('nombre de foto no válido');
  if (typeof a.base64 !== 'string' || !a.base64.length || a.base64.length > 15 * 1024 * 1024) throw new Error('foto demasiado grande');
}

function padre_(obj, ruta) {
  let o = obj;
  for (let i = 0; i < ruta.length - 1; i++) {
    if (o === null || typeof o !== 'object' || !(ruta[i] in o)) throw new Error('no existe ' + ruta.slice(0, i + 1).join(' › '));
    o = o[ruta[i]];
  }
  if (o === null || typeof o !== 'object') throw new Error('ruta no válida');
  return o;
}

/** Pone `valor` en `ruta` dentro de `obj`. Solo cambia valores que ya existen (del mismo tipo)
 *  o añade un texto nuevo a un objeto existente; nunca cambia la estructura. */
function aplicar_(obj, ruta, valor) {
  const o = padre_(obj, ruta);
  const k = ruta[ruta.length - 1];
  if (Array.isArray(o)) {
    if (typeof k !== 'number' || k < 0 || k >= o.length) throw new Error('posición no válida');
    if (typeof o[k] === 'string' && typeof valor === 'string' && LISTAS_PARRAFOS.indexOf(String(ruta[ruta.length - 2])) >= 0) {
      const partes = valor.split(/\n\s*\n/).map(function (s) { return s.trim(); }).filter(Boolean);
      o.splice.apply(o, [k, 1].concat(partes)); // vacío: se quita; con líneas en blanco: varios párrafos
      return;
    }
  } else if (!Object.prototype.hasOwnProperty.call(o, k)) {
    if (typeof valor !== 'string') throw new Error('no existe ' + ruta.join(' › '));
    o[k] = valor;
    return;
  }
  if (o[k] !== null && typeof o[k] !== typeof valor) throw new Error('tipo distinto en ' + ruta.join(' › '));
  o[k] = valor;
}

function operar_(obj, c) {
  const ruta = c.ruta.slice(1);
  const op = c.op || 'poner';
  if (op === 'poner') return aplicar_(obj, ruta, c.valor);
  const o = padre_(obj, ruta);
  const k = ruta[ruta.length - 1];
  if (op === 'reclave') {
    if (!Object.prototype.hasOwnProperty.call(o, k)) return; // ya no tenía cartela
    if (Object.prototype.hasOwnProperty.call(o, c.valor)) throw new Error('esa foto ya tiene cartela');
    o[c.valor] = o[k];
    delete o[k];
    return;
  }
  if (!Array.isArray(o)) throw new Error('no es una lista: ' + ruta.join(' › '));
  const lista = String(ruta[ruta.length - 2]);
  const esFoto = typeof c.valor === 'object';
  if (op === 'insertar') {
    if (k >= o.length) throw new Error('posición no válida');
    if (esFoto ? lista !== 'images' : LISTAS_PARRAFOS.indexOf(lista) < 0) throw new Error('aquí no se puede añadir');
    o.splice(k + 1, 0, esFoto ? { src: c.valor.src, alt: c.valor.alt || '' } : c.valor);
  } else { // quitar
    if (k >= o.length) throw new Error('posición no válida');
    if (lista !== 'images' && LISTAS_PARRAFOS.indexOf(lista) < 0) throw new Error('aquí no se puede quitar');
    o.splice(k, 1);
  }
}

/** Orden para aplicar varios cambios de una misma lista con las posiciones de la página:
 *  de la última posición a la primera, y en cada una primero lo que se añade detrás. */
function ordenar_(cambios) {
  const clave = function (c) { return JSON.stringify(c.ruta.slice(0, -1)); };
  return cambios.slice().sort(function (a, b) {
    const pa = clave(a), pb = clave(b);
    if (pa !== pb) return pa < pb ? -1 : 1;
    const ka = a.ruta[a.ruta.length - 1], kb = b.ruta[b.ruta.length - 1];
    if (typeof ka === 'number' && typeof kb === 'number' && ka !== kb) return kb - ka;
    return (a.op === 'insertar' ? 0 : 1) - (b.op === 'insertar' ? 0 : 1);
  });
}

function guardar_(datos) {
  if (!sesionValida_(datos.token)) return { ok: false, caducada: true, error: 'La sesión ha caducado. Vuelve a entrar.' };
  const cambios = datos.cambios || [];
  const archivos = datos.archivos || [];
  if (!Array.isArray(cambios) || !Array.isArray(archivos) || (!cambios.length && !archivos.length) ||
      cambios.length > 500 || archivos.length > 30) return { ok: false, error: 'No hay cambios que guardar.' };
  cambios.forEach(validarCambio_);
  archivos.forEach(validarArchivo_);
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    for (let intento = 0; ; intento++) {
      try {
        const huellas = {};
        const commit = commitCambios_(cambios, archivos, datos.huellas || {}, huellas);
        if (archivos.length) copiaPronto_(); // las fotos nuevas también al Drive, en cuanto la web las publique
        return { ok: true, commit: commit, n: cambios.length + archivos.length, huellas: huellas };
      } catch (err) {
        if (err.desactualizada) return { ok: false, desactualizada: true, error: err.message };
        if (err.code === 422 && intento < 2) continue; // alguien ha publicado a la vez: se repite sobre lo último
        throw err;
      }
    }
  } finally {
    lock.releaseLock();
  }
}

function md5_(texto) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, texto, Utilities.Charset.UTF_8)
    .map(function (b) { return ('0' + (b & 0xff).toString(16)).slice(-2); }).join('');
}

/** `huellas`: md5 de cada fichero tal y como estaba cuando se generó la página que edita Ana.
 *  Si ya no coincide (el agente nocturno u otro guardado lo ha cambiado), las posiciones de la
 *  página pueden apuntar a otra entrada: no se guarda nada. `nuevas` recibe las huellas resultantes. */
function commitCambios_(cambios, archivos, huellas, nuevas) {
  huellas = huellas || {};
  nuevas = nuevas || {};
  const ref = github_('get', '/git/ref/heads/' + RAMA);
  const base = ref.object.sha;
  const porFichero = {};
  cambios.forEach(function (c) { (porFichero[c.ruta[0]] = porFichero[c.ruta[0]] || []).push(c); });
  const arbol = [];
  Object.keys(porFichero).forEach(function (f) {
    const texto = github_('get', '/contents/data/' + f + '?ref=' + base, null, true);
    if (huellas[f] && huellas[f] !== md5_(texto)) {
      const err = new Error('La web ha cambiado desde que abriste la página: recárgala y vuelve a hacer el cambio.');
      err.desactualizada = true;
      throw err;
    }
    const obj = JSON.parse(texto);
    ordenar_(porFichero[f]).forEach(function (c) { operar_(obj, c); });
    const nuevo = JSON.stringify(obj, null, 1) + '\n';
    nuevas[f] = md5_(nuevo);
    if (nuevo === texto) return;
    const blob = github_('post', '/git/blobs', { content: nuevo, encoding: 'utf-8' });
    arbol.push({ path: 'data/' + f, mode: '100644', type: 'blob', sha: blob.sha });
  });
  archivos.forEach(function (a) {
    const blob = github_('post', '/git/blobs', { content: a.base64, encoding: 'base64' });
    arbol.push({ path: a.ruta, mode: '100644', type: 'blob', sha: blob.sha });
  });
  if (!arbol.length) return base; // ya estaba así
  const commitBase = github_('get', '/git/commits/' + base);
  const tree = github_('post', '/git/trees', { base_tree: commitBase.tree.sha, tree: arbol });
  const n = cambios.length + archivos.length;
  const resumen = cambios.slice(0, 3).map(function (c) { return (c.op && c.op !== 'poner' ? c.op + ' ' : '') + c.ruta.join(' › '); })
    .concat(archivos.length ? [archivos.length + (archivos.length === 1 ? ' foto' : ' fotos')] : []).join('; ');
  const commit = github_('post', '/git/commits', {
    message: 'Ana edita la web: ' + n + (n === 1 ? ' cambio' : ' cambios') + '\n\n' + resumen + (cambios.length > 3 ? '; …' : ''),
    tree: tree.sha,
    parents: [base],
    author: { name: 'Ana Martínez (editor web)', email: 'ana@ana-martinez.com', date: new Date().toISOString() },
  });
  github_('patch', '/git/refs/heads/' + RAMA, { sha: commit.sha });
  return commit.sha;
}

// ---------- Modo revisión: comentarios para el agente nocturno ----------

const PEND = 'revision/pendiente';
const HIST = 'revision/historial.json';
const ADJ = 'revision/archivos';

function revision_(datos) {
  const clave = props().getProperty('CLAVE'); // opcional: enlace ?revisar=CLAVE sin usuario y contraseña
  if (!sesionValida_(datos.token) && !(clave && datos.key && iguales_(datos.key, clave))) {
    return { ok: false, error: 'Clave no válida: vuelve a entrar en el modo edición.' };
  }
  return datos.action === 'listar' ? listarRevision_() : nuevoComentario_(datos.item, datos.archivos || []);
}

function rutaUrl_(p) { return p.split('/').map(encodeURIComponent).join('/'); }

function leerRepoJson_(path) {
  try {
    return JSON.parse(github_('get', '/contents/' + rutaUrl_(path) + '?ref=' + RAMA, null, true));
  } catch (err) {
    if (err.code === 404) return null;
    throw err;
  }
}

function subirRepo_(path, base64, mensaje) {
  github_('put', '/contents/' + rutaUrl_(path), {
    message: mensaje, content: base64, branch: RAMA,
    committer: { name: 'Revisión web', email: 'revision@ana-martinez.com' },
  });
}

function limpioNombre_(s) {
  return String(s || 'archivo').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\w.\-]+/g, '-').replace(/-+/g, '-').slice(0, 80);
}

function nuevoComentario_(item, archivos) {
  if (!item || !item.id || !item.tipo) throw new Error('Datos incompletos');
  if (!Array.isArray(archivos) || archivos.length > 30) throw new Error('Demasiados adjuntos');
  item.id = limpioNombre_(item.id);
  item.recibido = new Date().toISOString();
  item.texto = String(item.texto || '').slice(0, 8000);
  delete item.estado; delete item.respuesta; delete item.procesado; // eso lo escribe solo el agente
  item.archivos = [];
  archivos.forEach(function (a, i) {
    if (!a || typeof a.base64 !== 'string' || a.base64.length > 15 * 1024 * 1024) throw new Error('Adjunto no válido');
    const p = ADJ + '/' + item.id + '/' + (i + 1) + '-' + limpioNombre_(a.nombre);
    subirRepo_(p, a.base64, 'Revisión: adjunto de ' + (item.autor || 'Ana'));
    item.archivos.push(p);
  });
  const json = Utilities.base64Encode(JSON.stringify(item, null, 2), Utilities.Charset.UTF_8);
  const resumen = item.tipo === 'mensaje' ? 'Hilo «' + (item.titulo_hilo || '') + '»' : 'Comentario';
  subirRepo_(PEND + '/' + item.recibido.slice(0, 10) + '-' + item.id + '.json', json, 'Revisión: ' + resumen + ' de ' + (item.autor || 'Ana'));
  CacheService.getScriptCache().remove('listado');
  return { ok: true, id: item.id };
}

function listarRevision_() {
  const cache = CacheService.getScriptCache();
  const hit = cache.get('listado');
  if (hit) return JSON.parse(hit);
  let items = [];
  let dir;
  try { dir = github_('get', '/contents/' + PEND + '?ref=' + RAMA); } catch (err) { if (err.code !== 404) throw err; dir = []; }
  (dir || []).forEach(function (f) {
    if (f.type === 'file' && /\.json$/.test(f.name)) {
      try { items.push(leerRepoJson_(f.path)); } catch (_) { /* uno roto no impide ver el resto */ }
    }
  });
  const hist = leerRepoJson_(HIST);
  if (hist && hist.items) items = items.concat(hist.items);
  const out = { ok: true, items: items.filter(Boolean) };
  const s = JSON.stringify(out);
  if (s.length < 90000) cache.put('listado', s, 60);
  return out;
}

// ---------- Archivo en Drive ----------

const LIMITE_MS = 5 * 60 * 1000; // Apps Script corta a los 6 minutos: se sigue sola en otra ejecución

function copiarADrive() {
  const inicio = Date.now();
  borrarDisparadores_('copiarADrive');
  const indice = JSON.parse(UrlFetchApp.fetch(WEB + 'archivo_drive.json').getContentText('UTF-8'));
  const unidad = DriveApp.getFolderById(props().getProperty('DRIVE_CARPETA') || DRIVE_POR_DEFECTO);
  const raiz = carpetaHija_(unidad, indice.raiz);
  const carpetas = {};
  const carpeta = function (ruta) {
    if (!carpetas[ruta]) carpetas[ruta] = ruta.split('/').reduce(carpetaHija_, raiz);
    return carpetas[ruta];
  };
  let subidos = 0, textos = 0, pendientes = 0;

  indice.ficheros.forEach(function (f) {
    if (Date.now() - inicio > LIMITE_MS) { pendientes++; return; }
    const c = carpeta(f.carpeta);
    if (c.getFilesByName(f.nombre).hasNext()) return;
    const r = UrlFetchApp.fetch(WEB + f.fuente.split('/').map(encodeURIComponent).join('/'), { muteHttpExceptions: true });
    if (r.getResponseCode() !== 200) { console.warn('No se pudo bajar ' + f.fuente + ' (' + r.getResponseCode() + ')'); return; }
    c.createFile(r.getBlob().setName(f.nombre));
    subidos++;
  });

  indice.textos.forEach(function (t) {
    if (Date.now() - inicio > LIMITE_MS) { pendientes++; return; }
    const c = carpeta(t.carpeta);
    const huella = Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, t.texto, Utilities.Charset.UTF_8));
    const existentes = c.getFilesByName(t.nombre);
    let doc;
    if (existentes.hasNext()) {
      const fichero = existentes.next();
      if (fichero.getDescription() === huella) return;
      doc = DocumentApp.openById(fichero.getId());
      doc.getBody().clear();
    } else {
      doc = DocumentApp.create(t.nombre);
      DriveApp.getFileById(doc.getId()).moveTo(c);
    }
    const cuerpo = doc.getBody();
    t.texto.split('\n').forEach(function (linea, i) {
      const p = i === 0 ? cuerpo.getParagraphs()[0].setText(linea) : cuerpo.appendParagraph(linea);
      if (i === 0) p.setHeading(DocumentApp.ParagraphHeading.HEADING1);
      else if (/^(ESPAÑOL|ENGLISH|OBRAS)$/.test(linea)) p.setHeading(DocumentApp.ParagraphHeading.HEADING2);
      else p.setHeading(DocumentApp.ParagraphHeading.NORMAL);
    });
    doc.saveAndClose();
    DriveApp.getFileById(doc.getId()).setDescription(huella);
    textos++;
  });

  if (pendientes) {
    ScriptApp.newTrigger('copiarADrive').timeBased().after(60 * 1000).create();
    console.log('Subidos ' + subidos + ' ficheros y ' + textos + ' textos. Quedan ' + pendientes + ': sigue sola en 1 minuto.');
  } else {
    console.log('Archivo al día: ' + subidos + ' ficheros nuevos, ' + textos + ' textos actualizados. Carpeta: ' + raiz.getUrl());
  }
}

/** Copia al Drive dentro de 5 minutos (lo que tarda la web en publicar). Si ya había una programada, la sustituye. */
function copiaPronto_() {
  try {
    borrarDisparadores_('copiarADrive');
    ScriptApp.newTrigger('copiarADrive').timeBased().after(5 * 60 * 1000).create();
  } catch (err) {
    console.warn('No se pudo programar la copia al Drive: ' + err); // la copia nocturna lo recogerá
  }
}

/** Opcional: repasar el archivo cada noche para que lo nuevo de la web llegue solo al Drive. */
function programarCopiaDiaria() {
  borrarDisparadores_('copiaDiaria');
  ScriptApp.newTrigger('copiaDiaria').timeBased().everyDays(1).atHour(4).create();
}

function copiaDiaria() {
  copiarADrive();
}

function carpetaHija_(padre, nombre) {
  const it = padre.getFoldersByName(nombre);
  return it.hasNext() ? it.next() : padre.createFolder(nombre);
}

function borrarDisparadores_(funcion) {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === funcion) ScriptApp.deleteTrigger(t);
  });
}

// ---------- Comprobación ----------

/** Ejecutar una vez tras configurar: revisa propiedades, GitHub y Drive y lo cuenta en el registro. */
function comprobar() {
  ['USUARIO', 'CONTRASENA', 'GITHUB_TOKEN'].forEach(function (k) {
    console.log(k + ': ' + (props().getProperty(k) ? 'configurado' : 'FALTA'));
  });
  const ref = github_('get', '/git/ref/heads/' + RAMA);
  console.log('GitHub: acceso a ' + REPO + ' OK (último commit ' + ref.object.sha.slice(0, 7) + ')');
  const permisos = github_('get', '').permissions || {};
  console.log('GitHub: ' + (permisos.push ? 'puede guardar' : 'OJO: el token no puede escribir'));
  const unidad = DriveApp.getFolderById(props().getProperty('DRIVE_CARPETA') || DRIVE_POR_DEFECTO);
  console.log('Drive: «' + unidad.getName() + '» OK');
}
