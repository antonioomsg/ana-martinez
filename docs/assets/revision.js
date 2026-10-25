/* Modo revisión de la web de Ana Martínez.
 *
 * Se activa abriendo cualquier página con ?revisar=CLAVE (la clave queda guardada en este
 * navegador). Permite:
 *   - Comentar un elemento concreto (imagen, texto, título…) con alcance "solo este" o
 *     "todos los parecidos".
 *   - Abrir hilos de conversación con adjuntos (fotos, PDF) para pedir cosas más grandes,
 *     como crear un proyecto nuevo.
 * Todo se envía al puente (Google Apps Script), que lo guarda en revision/ dentro del repo.
 * Un agente lo procesa cada noche, aplica los cambios y publica.
 */
(function () {
  "use strict";

  // URL del puente (Apps Script desplegado como aplicación web). Ver revision/PUENTE.md.
  var ENDPOINT = window.AM_REVISION_ENDPOINT ||
    "https://script.google.com/macros/s/PENDIENTE/exec";

  var LS_KEY = "am-revision-key", LS_NAME = "am-revision-nombre";

  function store(k, v) {
    try { if (v === undefined) return localStorage.getItem(k); if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); }
    catch (_) { return null; }
  }

  // Activación: ?revisar=CLAVE → se guarda y se limpia de la URL. ?revisar=salir → desactiva.
  var params = new URLSearchParams(location.search);
  if (params.has("revisar")) {
    var v = params.get("revisar");
    store(LS_KEY, v === "salir" ? null : v);
    params.delete("revisar");
    var q = params.toString();
    history.replaceState(null, "", location.pathname + (q ? "?" + q : "") + location.hash);
  }
  var KEY = store(LS_KEY);
  if (!KEY) return;

  var ROOT = window.AM_ROOT || "";
  var PAGE = location.pathname.replace(/\/index\.html$/, "/");

  /* ---------- estilos ---------- */
  var css = `
  .rv, .rv * { box-sizing: border-box; font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }
  .rv { --rv-ink: #192e2e; --rv-accent: #8dadad; --rv-bg: #fff; --rv-soft: #f3f1ed; --rv-line: #e2ded7; color: var(--rv-ink); }
  .rv-dock { position: fixed; right: 16px; bottom: calc(16px + env(safe-area-inset-bottom)); z-index: 2147483000; display: flex; gap: 8px; }
  .rv-btn { appearance: none; border: 0; cursor: pointer; font-size: 15px; line-height: 1; padding: 13px 18px; border-radius: 999px;
    background: var(--rv-ink); color: #fff; box-shadow: 0 6px 20px rgba(0,0,0,.18); display: inline-flex; align-items: center; gap: 8px; min-height: 44px; }
  .rv-btn.ghost { background: var(--rv-bg); color: var(--rv-ink); box-shadow: 0 6px 20px rgba(0,0,0,.12), inset 0 0 0 1px var(--rv-line); }
  .rv-btn:disabled { opacity: .5; cursor: default; }
  .rv-badge { background: var(--rv-accent); color: var(--rv-ink); border-radius: 999px; font-size: 12px; padding: 2px 7px; }
  .rv-banner { position: fixed; left: 50%; top: calc(12px + env(safe-area-inset-top)); transform: translateX(-50%); z-index: 2147483001;
    background: var(--rv-ink); color: #fff; padding: 10px 16px; border-radius: 999px; font-size: 14px; box-shadow: 0 6px 20px rgba(0,0,0,.2);
    display: flex; gap: 12px; align-items: center; white-space: nowrap; }
  .rv-banner button { background: none; border: 0; color: var(--rv-accent); font: inherit; cursor: pointer; padding: 4px; }
  body.rv-picking, body.rv-picking * { cursor: crosshair !important; }
  .rv-hover { outline: 2px solid #8dadad !important; outline-offset: 3px !important; }
  .rv-pin { position: absolute; z-index: 2147482999; width: 26px; height: 26px; border-radius: 50%; background: #192e2e; color: #fff;
    font: 600 12px/26px "Helvetica Neue", Arial, sans-serif; text-align: center; box-shadow: 0 0 0 3px #fff, 0 4px 12px rgba(0,0,0,.25);
    cursor: pointer; border: 0; padding: 0; }
  .rv-pin.done { background: #8dadad; }
  .rv-sheet-wrap { position: fixed; inset: 0; z-index: 2147483002; background: rgba(25,46,46,.35); display: flex; align-items: flex-end; justify-content: center; }
  .rv-sheet { background: var(--rv-bg); width: 100%; max-width: 560px; max-height: 88vh; overflow: auto; border-radius: 18px 18px 0 0;
    padding: 20px 20px calc(20px + env(safe-area-inset-bottom)); box-shadow: 0 -10px 40px rgba(0,0,0,.2); }
  @media (min-width: 720px) { .rv-sheet-wrap { align-items: center; } .rv-sheet { border-radius: 18px; } }
  .rv-sheet h2 { font-size: 13px; letter-spacing: 2px; text-transform: uppercase; font-weight: 500; margin: 0 0 14px; display: flex; justify-content: space-between; align-items: center; }
  .rv-x { background: none; border: 0; font-size: 26px; line-height: 1; cursor: pointer; color: var(--rv-ink); padding: 4px 8px; }
  .rv-target { display: flex; gap: 12px; align-items: center; background: var(--rv-soft); border-radius: 12px; padding: 10px; margin-bottom: 14px; font-size: 14px; }
  .rv-target img { width: 56px; height: 56px; object-fit: cover; border-radius: 8px; flex: none; }
  .rv-target small { display: block; color: #6b7a7a; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px; }
  .rv-target p { margin: 0; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
  .rv textarea, .rv input[type=text] { width: 100%; font-size: 16px; border: 1px solid var(--rv-line); border-radius: 12px; padding: 12px; resize: vertical; color: var(--rv-ink); background: #fff; }
  .rv textarea:focus, .rv input[type=text]:focus { outline: 2px solid var(--rv-accent); border-color: transparent; }
  .rv-scope { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 12px 0; }
  .rv-scope label { border: 1px solid var(--rv-line); border-radius: 12px; padding: 10px 12px; font-size: 14px; cursor: pointer; display: block; }
  .rv-scope label:has(input:checked) { border-color: var(--rv-ink); background: var(--rv-soft); }
  .rv-scope input { margin: 0 6px 0 0; }
  .rv-scope span { display: block; font-size: 12px; color: #6b7a7a; margin-top: 2px; }
  .rv-row { display: flex; gap: 8px; justify-content: space-between; align-items: center; margin-top: 12px; flex-wrap: wrap; }
  .rv-hint { font-size: 12px; color: #6b7a7a; margin: 8px 0 0; }
  .rv-list { list-style: none; margin: 0 0 14px; padding: 0; }
  .rv-list li { border-top: 1px solid var(--rv-line); }
  .rv-list button { width: 100%; text-align: left; background: none; border: 0; padding: 14px 4px; cursor: pointer; font-size: 15px; color: var(--rv-ink); display: flex; justify-content: space-between; gap: 10px; }
  .rv-list small { color: #6b7a7a; }
  .rv-msgs { display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px; }
  .rv-msg { max-width: 85%; padding: 10px 12px; border-radius: 14px; font-size: 15px; background: var(--rv-soft); white-space: pre-wrap; word-wrap: break-word; }
  .rv-msg.mine { align-self: flex-end; background: var(--rv-ink); color: #fff; }
  .rv-msg.agent { background: #e6eeee; }
  .rv-msg small { display: block; font-size: 11px; opacity: .7; margin-bottom: 4px; }
  .rv-msg a { color: inherit; }
  .rv-files { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
  .rv-chip { font-size: 12px; background: var(--rv-soft); border-radius: 999px; padding: 4px 10px; display: inline-flex; gap: 6px; align-items: center; color: var(--rv-ink); }
  .rv-chip button { background: none; border: 0; cursor: pointer; padding: 0; font-size: 14px; color: inherit; }
  .rv-toast { position: fixed; left: 50%; bottom: calc(80px + env(safe-area-inset-bottom)); transform: translateX(-50%); z-index: 2147483003;
    background: var(--rv-ink); color: #fff; padding: 12px 18px; border-radius: 12px; font-size: 14px; box-shadow: 0 6px 20px rgba(0,0,0,.2); max-width: 90vw; }
  .rv-state { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; padding: 2px 8px; border-radius: 999px; background: var(--rv-soft); white-space: nowrap; }
  .rv-state.aplicado { background: #dcebe3; } .rv-state.dudoso { background: #f6e7cf; }
  `;
  var styleEl = document.createElement("style");
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  /* ---------- utilidades ---------- */
  function h(tag, attrs, kids) {
    var el = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "class") el.className = attrs[k];
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== false && attrs[k] != null) el.setAttribute(k, attrs[k] === true ? "" : attrs[k]);
    }
    [].concat(kids || []).forEach(function (c) { if (c != null) el.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return el;
  }
  function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
  function toast(msg) {
    var t = h("div", { class: "rv rv-toast", role: "status" }, msg);
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 3200);
  }
  function fmt(iso) {
    try { return new Date(iso).toLocaleString("es-ES", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); }
    catch (_) { return iso; }
  }
  function nombre() {
    var n = store(LS_NAME);
    if (!n) { n = (prompt("¿Quién comenta? (por ejemplo: Ana)") || "").trim() || "Ana"; store(LS_NAME, n); }
    return n;
  }

  function api(payload) {
    // text/plain evita la petición previa CORS, que Apps Script no admite.
    return fetch(ENDPOINT, { method: "POST", headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify(Object.assign({ key: KEY }, payload)) })
      .then(function (r) { return r.json(); })
      .then(function (j) { if (!j.ok) throw new Error(j.error || "Error"); return j; });
  }

  /* ---------- adjuntos: las fotos se reducen antes de subir ---------- */
  function leerArchivo(file) {
    return new Promise(function (resolve, reject) {
      if (file.size > 25 * 1024 * 1024 && !/^image\//.test(file.type)) return reject(new Error(file.name + " pesa más de 25 MB"));
      var fr = new FileReader();
      fr.onerror = function () { reject(new Error("No se pudo leer " + file.name)); };
      fr.onload = function () {
        if (!/^image\/(jpeg|png|webp|heic)/.test(file.type)) return resolve({ nombre: file.name, tipo: file.type, base64: fr.result.split(",")[1] });
        var img = new Image();
        img.onerror = function () { resolve({ nombre: file.name, tipo: file.type, base64: fr.result.split(",")[1] }); };
        img.onload = function () {
          var max = 2400, s = Math.min(1, max / Math.max(img.width, img.height));
          var c = document.createElement("canvas");
          c.width = Math.round(img.width * s); c.height = Math.round(img.height * s);
          c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
          var out = c.toDataURL("image/jpeg", 0.88);
          resolve({ nombre: file.name.replace(/\.\w+$/, "") + ".jpg", tipo: "image/jpeg", base64: out.split(",")[1] });
        };
        img.src = fr.result;
      };
      fr.readAsDataURL(file);
    });
  }

  function selectorArchivos(lista) {
    var chips = h("div", { class: "rv-files" });
    var input = h("input", { type: "file", multiple: true, accept: "image/*,application/pdf,.doc,.docx,.txt", hidden: true,
      onchange: function () { [].forEach.call(input.files, function (f) { lista.push(f); }); input.value = ""; pintar(); } });
    function pintar() {
      chips.innerHTML = "";
      lista.forEach(function (f, i) {
        chips.appendChild(h("span", { class: "rv-chip" }, [f.name,
          h("button", { type: "button", "aria-label": "Quitar", onclick: function () { lista.splice(i, 1); pintar(); } }, "×")]));
      });
    }
    var btn = h("button", { type: "button", class: "rv-btn ghost", onclick: function () { input.click(); } }, "📎 Adjuntar");
    return { boton: btn, input: input, chips: chips };
  }

  /* ---------- describir el elemento elegido ---------- */
  function elegible(el) {
    // Sube hasta un elemento con sentido: figura/cartela, imagen, titular, párrafo, tarjeta, enlace o botón.
    var sel = "figure, .card, img, h1, h2, h3, h4, p, li, figcaption, .cartela, a, button, .hero, section";
    while (el && el !== document.body) {
      if (el.closest(".rv")) return null;
      if (el.matches && el.matches(sel)) {
        if (el.tagName === "IMG") return el.closest("figure, .card") || el;
        return el;
      }
      el = el.parentElement;
    }
    return null;
  }
  function selector(el) {
    if (el.id) return "#" + CSS.escape(el.id);
    var parts = [];
    while (el && el.nodeType === 1 && el !== document.body && parts.length < 6) {
      var part = el.tagName.toLowerCase();
      if (el.id) { parts.unshift("#" + CSS.escape(el.id)); break; }
      var cls = [].filter.call(el.classList, function (c) { return !/^rv-/.test(c); })[0];
      if (cls) part += "." + CSS.escape(cls);
      var p = el.parentElement;
      if (p) {
        var same = [].filter.call(p.children, function (c) { return c.tagName === el.tagName; });
        if (same.length > 1) part += ":nth-of-type(" + (same.indexOf(el) + 1) + ")";
      }
      parts.unshift(part);
      el = p;
    }
    return parts.join(" > ");
  }
  function tipo(el) {
    if (el.matches("figure, .card, .hero") || el.querySelector("img") && !el.matches("section")) return el.querySelector(".cartela-titulo") ? "cuadro" : "imagen";
    if (el.tagName === "IMG") return "imagen";
    if (/^H\d$/.test(el.tagName)) return "título";
    if (el.matches(".cartela, figcaption")) return "cartela";
    if (el.matches("a, button")) return "enlace o botón";
    return "texto";
  }
  function describir(el) {
    var img = el.tagName === "IMG" ? el : el.querySelector("img");
    var titulo = el.querySelector && el.querySelector(".cartela-titulo, .card-title");
    return {
      pagina: PAGE,
      titulo_pagina: document.title,
      selector: selector(el),
      tipo: tipo(el),
      etiqueta: el.tagName.toLowerCase(),
      clases: [].filter.call(el.classList, function (c) { return !/^rv-/.test(c); }).join(" "),
      texto: (el.innerText || "").trim().replace(/\s+/g, " ").slice(0, 400),
      imagen: img ? (img.currentSrc || img.src) : null,
      obra: titulo ? titulo.textContent.trim() : null,
      ancho_pantalla: window.innerWidth
    };
  }

  /* ---------- hoja inferior genérica ---------- */
  var openSheet = null;
  function sheet(title, body) {
    cerrar();
    var wrap = h("div", { class: "rv rv-sheet-wrap", onclick: function (e) { if (e.target === wrap) cerrar(); } },
      h("div", { class: "rv-sheet", role: "dialog", "aria-modal": "true", "aria-label": title }, [
        h("h2", {}, [title, h("button", { class: "rv-x", "aria-label": "Cerrar", onclick: cerrar }, "×")]),
        body
      ]));
    document.body.appendChild(wrap);
    openSheet = wrap;
    var f = wrap.querySelector("textarea, input[type=text]");
    if (f) setTimeout(function () { f.focus(); }, 50);
    return wrap;
  }
  function cerrar() { if (openSheet) { openSheet.remove(); openSheet = null; } }
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { cerrar(); salirPicker(); } });

  /* ---------- modo "elegir elemento" ---------- */
  var picking = false, hoverEl = null, banner = null;
  function entrarPicker() {
    picking = true;
    document.body.classList.add("rv-picking");
    banner = h("div", { class: "rv rv-banner" }, ["Toca lo que quieras comentar",
      h("button", { onclick: function () { salirPicker(); comentarPagina(); } }, "Toda la página"),
      h("button", { onclick: salirPicker }, "Cancelar")]);
    document.body.appendChild(banner);
  }
  function salirPicker() {
    picking = false;
    document.body.classList.remove("rv-picking");
    if (hoverEl) hoverEl.classList.remove("rv-hover");
    hoverEl = null;
    if (banner) { banner.remove(); banner = null; }
  }
  document.addEventListener("mouseover", function (e) {
    if (!picking) return;
    var el = elegible(e.target);
    if (hoverEl && hoverEl !== el) hoverEl.classList.remove("rv-hover");
    hoverEl = el;
    if (el) el.classList.add("rv-hover");
  }, true);
  // Captura: bloquea navegación y zoom de la web mientras se elige.
  ["click", "pointerup"].forEach(function (ev) {
    document.addEventListener(ev, function (e) {
      if (!picking || e.target.closest(".rv")) return;
      e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
      if (ev !== "click") return;
      var el = elegible(e.target);
      if (!el) return;
      salirPicker();
      comentarElemento(el);
    }, true);
  });

  function comentarElemento(el) {
    el.classList.add("rv-hover");
    var d = describir(el);
    var target = h("div", { class: "rv-target" }, [
      d.imagen ? h("img", { src: d.imagen, alt: "" }) : null,
      h("div", {}, [h("small", {}, d.tipo + (d.obra ? " · " + d.obra : "")), h("p", {}, d.texto || "(sin texto)")])
    ]);
    formulario(target, d, function () { el.classList.remove("rv-hover"); });
  }
  function comentarPagina() {
    var d = { pagina: PAGE, titulo_pagina: document.title, tipo: "página", texto: "", ancho_pantalla: window.innerWidth };
    formulario(h("div", { class: "rv-target" }, h("div", {}, [h("small", {}, "toda la página"), h("p", {}, document.title)])), d);
  }

  function formulario(target, d, alCerrar) {
    var archivos = [];
    var ta = h("textarea", { rows: 4, placeholder: "Ej.: este cuadro está vendido · cambia el texto por… · las fotos más pequeñas" });
    var radio = function (val, txt, sub, checked) {
      return h("label", {}, [h("input", { type: "radio", name: "rv-scope", value: val, checked: checked }), txt, h("span", {}, sub)]);
    };
    var scope = h("div", { class: "rv-scope", role: "radiogroup", "aria-label": "Alcance" }, [
      radio("este", "Solo este", "Cambia únicamente esto", true),
      radio("todos", "Todos los parecidos", "Igual en toda la web")
    ]);
    var adj = selectorArchivos(archivos);
    var send = h("button", { class: "rv-btn", type: "submit" }, "Enviar");
    var form = h("form", { onsubmit: function (e) {
      e.preventDefault();
      var texto = ta.value.trim();
      if (!texto) { ta.focus(); return; }
      send.disabled = true; send.textContent = "Enviando…";
      Promise.all(archivos.map(leerArchivo)).then(function (files) {
        return api({ action: "nuevo", item: {
          id: uid(), tipo: "comentario", autor: nombre(), fecha: new Date().toISOString(), texto: texto,
          alcance: (form.querySelector("input[name=rv-scope]:checked") || {}).value || "este", elemento: d
        }, archivos: files });
      }).then(function () {
        cerrar(); if (alCerrar) alCerrar(); toast("Comentario guardado. Se aplicará esta noche."); cargar();
      }).catch(function (err) {
        send.disabled = false; send.textContent = "Enviar"; toast("No se pudo enviar: " + err.message);
      });
    } }, [target, ta, d.tipo === "página" ? null : scope, adj.chips, adj.input,
      h("div", { class: "rv-row" }, [adj.boton, send]),
      h("p", { class: "rv-hint" }, "Los comentarios se revisan y publican automáticamente cada noche.")]);
    var w = sheet("Comentar", form);
    if (alCerrar) {
      var obs = new MutationObserver(function () { if (!document.body.contains(w)) { alCerrar(); obs.disconnect(); } });
      obs.observe(document.body, { childList: true });
    }
  }

  /* ---------- hilos ---------- */
  var DATA = { items: [] };
  function hilos() {
    var map = {};
    DATA.items.forEach(function (it) {
      if (it.tipo !== "mensaje") return;
      (map[it.hilo] = map[it.hilo] || { id: it.hilo, titulo: it.titulo_hilo || "Hilo", msgs: [] }).msgs.push(it);
      if (it.titulo_hilo) map[it.hilo].titulo = it.titulo_hilo;
    });
    return Object.keys(map).map(function (k) {
      var t = map[k];
      t.msgs.sort(function (a, b) { return a.fecha < b.fecha ? -1 : 1; });
      t.ultima = t.msgs[t.msgs.length - 1].fecha;
      return t;
    }).sort(function (a, b) { return a.ultima < b.ultima ? 1 : -1; });
  }

  function verHilos() {
    var lista = hilos();
    var ul = h("ul", { class: "rv-list" }, lista.length ? lista.map(function (t) {
      var pend = t.msgs.some(function (m) { return !m.estado && m.autor !== "Agente"; });
      return h("li", {}, h("button", { onclick: function () { verHilo(t); } }, [
        h("span", {}, [t.titulo, h("br"), h("small", {}, t.msgs.length + " mensajes · " + fmt(t.ultima))]),
        h("span", { class: "rv-state" + (pend ? "" : " aplicado") }, pend ? "pendiente" : "al día")
      ]));
    }) : h("li", {}, h("p", { class: "rv-hint" }, "Aún no hay hilos.")));
    sheet("Hilos", h("div", {}, [ul,
      h("button", { class: "rv-btn", onclick: function () { verHilo(null); } }, "＋ Nuevo hilo"),
      h("p", { class: "rv-hint" }, "Úsalos para pedidos grandes: un proyecto nuevo con sus fotos, un texto largo, una sección…")]));
  }

  function verHilo(t) {
    var nuevo = !t;
    var id = t ? t.id : uid();
    var yo = store(LS_NAME);
    var msgs = h("div", { class: "rv-msgs" }, (t ? t.msgs : []).map(function (m) {
      var cls = m.autor === "Agente" ? "agent" : (m.autor === yo ? "mine" : "");
      return h("div", { class: "rv-msg " + cls }, [
        h("small", {}, m.autor + " · " + fmt(m.fecha) + (m.estado && m.autor !== "Agente" ? " · " + m.estado : "")),
        m.texto,
        m.archivos && m.archivos.length ? h("div", { class: "rv-files" }, m.archivos.map(function (a) { return h("span", { class: "rv-chip" }, "📎 " + a.split("/").pop()); })) : null
      ]);
    }));
    var tituloIn = nuevo ? h("input", { type: "text", placeholder: "Título del hilo (ej.: Proyecto nuevo · Serie Mar)", style: "margin-bottom:10px" }) : null;
    var archivos = [];
    var ta = h("textarea", { rows: 3, placeholder: nuevo ? "Cuéntalo: qué es, textos, fechas, en qué sección va… y adjunta las fotos o el PDF." : "Escribe un mensaje…" });
    var adj = selectorArchivos(archivos);
    var send = h("button", { class: "rv-btn", type: "submit" }, "Enviar");
    var form = h("form", { onsubmit: function (e) {
      e.preventDefault();
      var texto = ta.value.trim();
      var titulo = tituloIn ? tituloIn.value.trim() : t.titulo;
      if (nuevo && !titulo) { tituloIn.focus(); return; }
      if (!texto && !archivos.length) { ta.focus(); return; }
      send.disabled = true; send.textContent = archivos.length ? "Subiendo…" : "Enviando…";
      Promise.all(archivos.map(leerArchivo)).then(function (files) {
        return api({ action: "nuevo", item: {
          id: uid(), tipo: "mensaje", hilo: id, titulo_hilo: titulo, autor: nombre(), fecha: new Date().toISOString(),
          texto: texto, pagina: PAGE
        }, archivos: files });
      }).then(function () { toast("Mensaje guardado. El agente lo atenderá esta noche."); return cargar(); })
        .then(function () { var h2 = hilos().filter(function (x) { return x.id === id; })[0]; if (h2) verHilo(h2); else cerrar(); })
        .catch(function (err) { send.disabled = false; send.textContent = "Enviar"; toast("No se pudo enviar: " + err.message); });
    } }, [tituloIn, ta, adj.chips, adj.input, h("div", { class: "rv-row" }, [adj.boton, send])]);
    sheet(nuevo ? "Nuevo hilo" : t.titulo, h("div", {}, [
      h("button", { class: "rv-btn ghost", style: "margin-bottom:12px", onclick: verHilos }, "‹ Hilos"), msgs, form]));
  }

  /* ---------- marcas sobre los elementos comentados ---------- */
  var pins = [];
  function pintarMarcas() {
    pins.forEach(function (p) { p.remove(); }); pins = [];
    var n = 0;
    DATA.items.forEach(function (it) {
      if (it.tipo !== "comentario" || !it.elemento || it.elemento.pagina !== PAGE || !it.elemento.selector) return;
      var el; try { el = document.querySelector(it.elemento.selector); } catch (_) { el = null; }
      if (!el) return;
      var r = el.getBoundingClientRect();
      if (!r.width) return;
      n++;
      var pin = h("button", { class: "rv rv-pin" + (it.estado ? " done" : ""), title: it.texto,
        style: "left:" + (r.right + scrollX - 13) + "px;top:" + (r.top + scrollY - 13) + "px",
        onclick: function () {
          sheet("Comentario", h("div", {}, [
            h("div", { class: "rv-target" }, h("div", {}, [h("small", {}, it.autor + " · " + fmt(it.fecha) + " · " + (it.alcance === "todos" ? "todos los parecidos" : "solo este")), h("p", {}, it.texto)])),
            h("p", {}, [h("span", { class: "rv-state " + (it.estado || "") }, it.estado || "pendiente"), " ", it.respuesta || ""])
          ]));
        } }, String(n));
      document.body.appendChild(pin);
      pins.push(pin);
    });
  }
  var resizeT;
  window.addEventListener("resize", function () { clearTimeout(resizeT); resizeT = setTimeout(pintarMarcas, 200); });
  window.addEventListener("load", pintarMarcas);

  function cargar() {
    return api({ action: "listar" }).then(function (j) {
      DATA = j; pintarMarcas(); actualizarDock();
    }).catch(function (err) {
      if (/clave/i.test(err.message)) { store(LS_KEY, null); toast("Clave de revisión no válida."); dock.remove(); }
    });
  }

  /* ---------- botones flotantes ---------- */
  var badge = h("span", { class: "rv-badge", hidden: true });
  var dock = h("div", { class: "rv rv-dock" }, [
    h("button", { class: "rv-btn ghost", onclick: function () { verHilos(); cargar().then(function () { if (openSheet && openSheet.querySelector(".rv-list")) verHilos(); }); }, "aria-label": "Hilos" }, ["🧵 Hilos", badge]),
    h("button", { class: "rv-btn", onclick: function () { picking ? salirPicker() : entrarPicker(); } }, "💬 Comentar")
  ]);
  function actualizarDock() {
    var pend = DATA.items.filter(function (it) { return !it.estado && it.autor !== "Agente"; }).length;
    badge.hidden = !pend; badge.textContent = pend;
    badge.title = pend + " pendientes";
  }
  function montar() { document.body.appendChild(dock); cargar(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", montar); else montar();
})();
