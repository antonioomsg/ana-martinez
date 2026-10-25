/**
 * Editor de la web de Ana Martínez (https://antonioomsg.github.io/ana-martinez/).
 *
 * 1. doPost: el modo edición de la web (?editar) entra con usuario y contraseña y guarda
 *    los textos en data/*.json del repo de GitHub. GitHub Actions publica la web en 1-2 min.
 * 2. copiarADrive: sube al Drive compartido, ordenado por carpetas, las fotos, PDF y textos
 *    de la web (según archivo_drive.json, que genera build.py). Se puede repetir: solo añade
 *    lo que falta y actualiza los documentos «Textos» que hayan cambiado.
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
const MAX_FALLOS = 8; // intentos de contraseña fallidos antes de bloquear 15 minutos

// Ficheros de data/ que el editor puede tocar
const FICHEROS = /^(content|panuelos|laminas|ediciones|bio|documentos|translations_en|sitio|cuadros\/[a-z0-9_]+|textos_curador\/[a-z0-9_]+)\.json$/i;
const CLAVES_PROHIBIDAS = ['__proto__', 'constructor', 'prototype', 'editor_url'];

const props = () => PropertiesService.getScriptProperties();

function respuesta(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  return respuesta({ ok: true, mensaje: 'Editor de la web de Ana Martínez: funcionando.' });
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
  return { ok: true, token: exp + '.' + firma_(String(exp)), exp: exp };
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

function validarCambio_(c) {
  if (!c || !Array.isArray(c.ruta) || c.ruta.length < 2 || c.ruta.length > 8) throw new Error('ruta no válida');
  if (!FICHEROS.test(c.ruta[0])) throw new Error('fichero no editable: ' + c.ruta[0]);
  c.ruta.slice(1).forEach(function (k) {
    if (!(typeof k === 'number' || typeof k === 'string') || CLAVES_PROHIBIDAS.indexOf(String(k)) >= 0) throw new Error('ruta no válida');
  });
  if (typeof c.valor === 'string') {
    if (c.valor.length > 20000) throw new Error('texto demasiado largo');
  } else if (typeof c.valor !== 'number' || !isFinite(c.valor) || c.valor < 0) {
    throw new Error('valor no válido');
  }
}

/** Pone `valor` en `ruta` dentro de `obj`. Solo cambia valores que ya existen (del mismo tipo)
 *  o añade un texto nuevo a un objeto existente; nunca cambia la estructura. */
function aplicar_(obj, ruta, valor) {
  let o = obj;
  for (let i = 0; i < ruta.length - 1; i++) {
    if (o === null || typeof o !== 'object' || !(ruta[i] in o)) throw new Error('no existe ' + ruta.slice(0, i + 1).join(' › '));
    o = o[ruta[i]];
  }
  const k = ruta[ruta.length - 1];
  if (o === null || typeof o !== 'object') throw new Error('ruta no válida');
  if (Array.isArray(o)) {
    if (typeof k !== 'number' || k < 0 || k >= o.length) throw new Error('posición no válida');
  } else if (!Object.prototype.hasOwnProperty.call(o, k)) {
    if (typeof valor !== 'string') throw new Error('no existe ' + ruta.join(' › '));
    o[k] = valor;
    return;
  }
  if (o[k] !== null && typeof o[k] !== typeof valor) throw new Error('tipo distinto en ' + ruta.join(' › '));
  o[k] = valor;
}

function guardar_(datos) {
  if (!sesionValida_(datos.token)) return { ok: false, caducada: true, error: 'La sesión ha caducado. Vuelve a entrar.' };
  const cambios = datos.cambios;
  if (!Array.isArray(cambios) || !cambios.length || cambios.length > 500) return { ok: false, error: 'No hay cambios que guardar.' };
  cambios.forEach(validarCambio_);
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    for (let intento = 0; ; intento++) {
      try {
        return { ok: true, commit: commitCambios_(cambios), n: cambios.length };
      } catch (err) {
        if (err.code === 422 && intento < 2) continue; // alguien ha publicado a la vez: se repite sobre lo último
        throw err;
      }
    }
  } finally {
    lock.releaseLock();
  }
}

function commitCambios_(cambios) {
  const ref = github_('get', '/git/ref/heads/' + RAMA);
  const base = ref.object.sha;
  const porFichero = {};
  cambios.forEach(function (c) { (porFichero[c.ruta[0]] = porFichero[c.ruta[0]] || []).push(c); });
  const arbol = [];
  Object.keys(porFichero).forEach(function (f) {
    const texto = github_('get', '/contents/data/' + f + '?ref=' + base, null, true);
    const obj = JSON.parse(texto);
    porFichero[f].forEach(function (c) { aplicar_(obj, c.ruta.slice(1), c.valor); });
    const nuevo = JSON.stringify(obj, null, 1) + '\n';
    if (nuevo === texto) return;
    const blob = github_('post', '/git/blobs', { content: nuevo, encoding: 'utf-8' });
    arbol.push({ path: 'data/' + f, mode: '100644', type: 'blob', sha: blob.sha });
  });
  if (!arbol.length) return base; // ya estaba así
  const commitBase = github_('get', '/git/commits/' + base);
  const tree = github_('post', '/git/trees', { base_tree: commitBase.tree.sha, tree: arbol });
  const resumen = cambios.slice(0, 3).map(function (c) { return c.ruta.join(' › '); }).join('; ');
  const commit = github_('post', '/git/commits', {
    message: 'Ana edita la web: ' + cambios.length + (cambios.length === 1 ? ' cambio' : ' cambios') + '\n\n' + resumen + (cambios.length > 3 ? '; …' : ''),
    tree: tree.sha,
    parents: [base],
    author: { name: 'Ana Martínez (editor web)', email: 'ana@ana-martinez.com', date: new Date().toISOString() },
  });
  github_('patch', '/git/refs/heads/' + RAMA, { sha: commit.sha });
  return commit.sha;
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
