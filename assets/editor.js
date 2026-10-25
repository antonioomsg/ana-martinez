// Modo edición: se entra con ?editar en la dirección. Usuario y contraseña los comprueba el
// Apps Script (window.AM_EDITOR), que guarda cada cambio en data/*.json del repo; GitHub vuelve
// a generar y publicar la web en 1-2 minutos. Los visitantes normales no cargan nada más.
(() => {
  const URL_API = window.AM_EDITOR;
  const K_TOKEN = "am-editor-token";
  const K_RECIENTES = "am-editor-recientes";
  const MIN_PUBLICAR = 20; // minutos durante los que se muestran los cambios aún no publicados

  const leer = (k) => { try { return JSON.parse(localStorage.getItem(k)); } catch (_) { return null; } };
  const guardarLocal = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento: se pedirá la contraseña en cada página */ } };
  const tokenValido = () => { const t = leer(K_TOKEN); return t && t.exp > Date.now() + 60000 ? t.token : null; };

  const pideEditar = /[?&#]editar\b/.test(location.search + location.hash);
  if (!pideEditar && !tokenValido()) return;

  const ESTILO = `
.am-editando [data-e]:not([hidden]) { outline: 1px dashed rgba(0,120,140,.45); outline-offset: 3px; cursor: text; white-space: pre-wrap; border-radius: 2px; }
.am-editando [data-e]:not([hidden]):hover { outline-color: #00788c; }
.am-editando [data-e]:focus { outline: 2px solid #00788c; background: rgba(0,120,140,.06); }
.am-editando [data-e].am-cambiado { background: rgba(255,214,0,.28); }
.am-editando [data-e].am-publicando { background: rgba(0,170,90,.16); }
.am-editando .fold { max-height: none; -webkit-mask-image: none; mask-image: none; }
.am-editando .fold-btn { display: none; }
.am-editando .card-veil { background: rgba(0,0,0,.45); }
.am-editando [data-e-abre] { outline: 1px dashed rgba(0,120,140,.45); outline-offset: 3px; cursor: pointer; border-radius: 2px; }
.am-editando [data-e-abre]:hover { outline-color: #00788c; background: rgba(0,120,140,.06); }
.am-dlg .am-ayuda { margin: -6px 0 16px; color: #666; font-size: 13px; }
.am-barra { position: fixed; z-index: 9999; left: 50%; bottom: 16px; transform: translateX(-50%); display: flex; flex-wrap: wrap; align-items: center; gap: 8px; max-width: calc(100vw - 32px); padding: 10px 12px; background: #111; color: #fff; font: 14px/1.3 Jost, system-ui, sans-serif; box-shadow: 0 6px 24px rgba(0,0,0,.25); }
.am-barra b { font-weight: 500; letter-spacing: 1px; margin-right: 4px; }
.am-barra .am-estado { color: #cfd8d8; margin-right: 6px; }
.am-barra button, .am-dlg button { min-height: 40px; padding: 0 16px; border: 1px solid #fff; background: transparent; color: inherit; font: inherit; cursor: pointer; }
.am-barra .am-guardar { background: #fff; color: #111; }
.am-barra button:disabled { opacity: .4; cursor: default; }
.am-dlg { border: 0; padding: 28px; width: min(440px, calc(100vw - 32px)); font: 15px/1.4 Jost, system-ui, sans-serif; color: #111; }
.am-dlg::backdrop { background: rgba(0,0,0,.4); }
.am-dlg h2 { margin: 0 0 16px; font-weight: 400; letter-spacing: 2px; font-size: 18px; }
.am-dlg label { display: block; margin: 0 0 14px; font-size: 13px; letter-spacing: .5px; }
.am-dlg input { display: block; width: 100%; box-sizing: border-box; margin-top: 6px; min-height: 44px; padding: 0 12px; border: 1px solid #ccc; font: inherit; font-size: 16px; }
.am-dlg .am-acciones { display: flex; gap: 8px; justify-content: flex-end; margin-top: 18px; }
.am-dlg button { border-color: #111; }
.am-dlg .am-principal { background: #111; color: #fff; }
.am-dlg .am-error { color: #b00020; min-height: 1.4em; margin: 0; }
.am-dlg .am-campos { max-height: 60vh; overflow: auto; }`;

  const clave = (el) => el.getAttribute("data-e");
  const texto = (el) => (el.hasAttribute("hidden") ? el.dataset.v : el.innerText)
    .replace(/\r/g, "").replace(/ /g, " ").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();

  const pendientes = new Map(); // clave -> { ruta, valor }
  let barra, estado, botonGuardar;

  function dialogo(html) {
    const d = document.createElement("dialog");
    d.className = "am-dlg";
    d.innerHTML = html;
    document.body.append(d);
    d.addEventListener("close", () => d.remove());
    d.showModal();
    return d;
  }

  async function llamar(datos) {
    const r = await fetch(URL_API, { method: "POST", body: JSON.stringify(datos), headers: { "Content-Type": "text/plain;charset=utf-8" } });
    return r.json();
  }

  function entrar() {
    return new Promise((ok) => {
      if (!URL_API) {
        const d = dialogo(`<h2>MODO EDICIÓN</h2><p>Falta conectar el editor (la dirección del Apps Script en data/sitio.json).</p><div class="am-acciones"><button class="am-principal" value="x">Cerrar</button></div>`);
        d.querySelector("button").onclick = () => d.close();
        return ok(false);
      }
      const d = dialogo(`<h2>MODO EDICIÓN</h2>
<form>
  <label>Usuario<input name="usuario" autocomplete="username" required autocapitalize="off"></label>
  <label>Contraseña<input name="contrasena" type="password" autocomplete="current-password" required></label>
  <p class="am-error" aria-live="polite"></p>
  <div class="am-acciones"><button type="button" class="am-cancelar">Cancelar</button><button class="am-principal">Entrar</button></div>
</form>`);
      const f = d.querySelector("form");
      const err = d.querySelector(".am-error");
      d.querySelector(".am-cancelar").onclick = () => { d.close(); ok(false); };
      d.addEventListener("cancel", () => ok(false));
      f.onsubmit = async (ev) => {
        ev.preventDefault();
        err.textContent = "Comprobando…";
        try {
          const r = await llamar({ accion: "entrar", usuario: f.usuario.value.trim(), contrasena: f.contrasena.value });
          if (!r.ok) { err.textContent = r.error || "No se ha podido entrar."; return; }
          guardarLocal(K_TOKEN, { token: r.token, exp: r.exp });
          d.close();
          ok(true);
        } catch (_) {
          err.textContent = "Sin conexión con el editor. Inténtalo de nuevo.";
        }
      };
    });
  }

  function marcar(el) {
    const k = clave(el);
    const valor = texto(el);
    const iguales = document.querySelectorAll(`[data-e="${CSS.escape(k)}"]`);
    if (valor === el.dataset.amOrig) pendientes.delete(k);
    else pendientes.set(k, { ruta: JSON.parse(k), valor: el.dataset.eTipo === "num" ? Number(valor) : valor });
    iguales.forEach((x) => x.classList.toggle("am-cambiado", pendientes.has(k)));
    pintarEstado();
  }

  function pintarEstado(msg) {
    const n = pendientes.size;
    estado.textContent = msg || (n ? `${n} ${n === 1 ? "cambio" : "cambios"} sin guardar` : "Pulsa un texto para cambiarlo");
    botonGuardar.disabled = !n;
  }

  function aplicarRecientes() {
    const rec = leer(K_RECIENTES) || {};
    const limite = Date.now() - MIN_PUBLICAR * 60000;
    let quedan = 0;
    for (const [k, v] of Object.entries(rec)) {
      if (v.t < limite) { delete rec[k]; continue; }
      document.querySelectorAll(`[data-e="${CSS.escape(k)}"]`).forEach((el) => {
        if (texto(el) === String(v.valor)) return; // ya publicado
        quedan++;
        if (el.hasAttribute("hidden")) el.dataset.v = v.valor; else el.innerText = v.valor;
        el.dataset.amOrig = String(v.valor);
        el.classList.add("am-publicando");
      });
    }
    guardarLocal(K_RECIENTES, rec);
    return quedan;
  }

  async function guardar() {
    if (!pendientes.size) return;
    if (!tokenValido() && !(await entrar())) return;
    botonGuardar.disabled = true;
    pintarEstado("Guardando…");
    const cambios = [...pendientes.values()];
    let r;
    try {
      r = await llamar({ accion: "guardar", token: tokenValido(), cambios });
    } catch (_) {
      pintarEstado("No se ha podido guardar (sin conexión). Vuelve a pulsar Guardar.");
      botonGuardar.disabled = false;
      return;
    }
    if (!r.ok && r.caducada) { guardarLocal(K_TOKEN, null); if (await entrar()) return guardar(); }
    if (!r.ok) { pintarEstado(r.error || "No se ha podido guardar."); botonGuardar.disabled = false; return; }
    const rec = leer(K_RECIENTES) || {};
    for (const [k, c] of pendientes) {
      rec[k] = { valor: c.valor, t: Date.now() };
      document.querySelectorAll(`[data-e="${CSS.escape(k)}"]`).forEach((el) => {
        el.dataset.amOrig = String(c.valor);
        el.classList.remove("am-cambiado");
        el.classList.add("am-publicando");
      });
    }
    guardarLocal(K_RECIENTES, rec);
    pendientes.clear();
    pintarEstado("Guardado ✓ Se publica en 1-2 minutos");
  }

  // Datos que no son texto escrito encima (fecha, precios, colores): se cambian en un formulario
  const GRUPOS = [[/^Fecha/, "Fecha"], [/^Título en inglés/, "Título en inglés"], [/^Tamaño/, "Precios y tamaños"], [/^Color/, "Colores"]];
  const grupoDe = (etq) => (GRUPOS.find(([re]) => re.test(etq)) || [, "Más datos"])[1];
  const camposOcultos = () => [...document.querySelectorAll("[data-e][hidden][data-e-etq]")];
  const nombreOtros = () => [...new Set(camposOcultos().map((el) => grupoDe(el.dataset.eEtq)))].join(" · ");

  function otrosDatos(enfocar) {
    const campos = camposOcultos();
    if (!campos.length) return;
    const d = dialogo(`<h2>${nombreOtros().toUpperCase()}</h2>
<p class="am-ayuda">Estos datos no se escriben encima de la página: cámbialos aquí y pulsa Aplicar y después Guardar.</p>
<form><div class="am-campos"></div>
<div class="am-acciones"><button type="button" class="am-cancelar">Cancelar</button><button class="am-principal">Aplicar</button></div></form>`);
    const caja = d.querySelector(".am-campos");
    campos.forEach((el, i) => {
      const l = document.createElement("label");
      l.textContent = el.dataset.eEtq;
      const inp = document.createElement("input");
      inp.name = `c${i}`;
      inp.value = el.dataset.v;
      if (el.dataset.eTipo === "num") { inp.type = "number"; inp.min = "0"; inp.step = "1"; inp.required = true; }
      if (/^Fecha/.test(el.dataset.eEtq)) { inp.type = "date"; inp.required = true; }
      l.append(inp);
      caja.append(l);
    });
    const foco = campos.findIndex((el) => enfocar && el.dataset.eEtq.startsWith(enfocar));
    if (foco >= 0) d.querySelector(`[name=c${foco}]`).focus();
    d.querySelector(".am-cancelar").onclick = () => d.close();
    d.querySelector("form").onsubmit = (ev) => {
      ev.preventDefault();
      campos.forEach((el, i) => { el.dataset.v = d.querySelector(`[name=c${i}]`).value.trim(); marcar(el); });
      d.close();
    };
  }

  function salir() {
    if (pendientes.size && !confirm("Tienes cambios sin guardar. ¿Salir y perderlos?")) return;
    pendientes.clear();
    guardarLocal(K_TOKEN, null);
    location.href = location.pathname;
  }

  function activar() {
    document.head.insertAdjacentHTML("beforeend", `<style>${ESTILO}</style>`);
    document.body.classList.add("am-editando");
    document.querySelectorAll("[data-fold]").forEach((b) => b.classList.remove("fold"));
    document.querySelectorAll(".pdp-info details").forEach((d) => { d.open = true; });
    document.querySelectorAll("[data-e]:not([hidden])").forEach((el) => {
      if (el.dataset.raw != null) el.textContent = el.dataset.raw; // se ve en mayúsculas, se guarda tal cual
      el.contentEditable = "plaintext-only";
      if (el.contentEditable !== "plaintext-only") el.contentEditable = "true";
      el.spellcheck = true;
    });
    document.querySelectorAll("[data-e]").forEach((el) => { el.dataset.amOrig = texto(el); });

    barra = document.createElement("div");
    barra.className = "am-barra";
    barra.innerHTML = `<b>EDICIÓN</b><span class="am-estado"></span>
<button type="button" class="am-otros" hidden></button>
<button type="button" class="am-guardar">Guardar</button><button type="button" class="am-salir">Salir</button>`;
    document.body.append(barra);
    estado = barra.querySelector(".am-estado");
    botonGuardar = barra.querySelector(".am-guardar");
    const otros = barra.querySelector(".am-otros");
    otros.textContent = nombreOtros();
    otros.hidden = !otros.textContent;
    otros.onclick = () => otrosDatos();
    botonGuardar.onclick = guardar;
    barra.querySelector(".am-salir").onclick = salir;
    const publicando = aplicarRecientes();
    pintarEstado(publicando ? "Hay cambios guardados publicándose (en verde)…" : "");

    document.addEventListener("input", (ev) => { const el = ev.target.closest?.("[data-e]"); if (el) marcar(el); });
    document.addEventListener("focusout", (ev) => { // mismo texto repetido en la página: se copia al resto
      const el = ev.target.closest?.("[data-e]");
      if (!el || !pendientes.has(clave(el))) return;
      document.querySelectorAll(`[data-e="${CSS.escape(clave(el))}"]`).forEach((x) => { if (x !== el && !x.hidden) x.innerText = texto(el); });
    });
    // Pulsar la fecha o el precio abre su formulario
    document.addEventListener("click", (ev) => {
      const abre = ev.target.closest?.("[data-e-abre]");
      if (abre && camposOcultos().length) { ev.preventDefault(); otrosDatos(abre.dataset.eAbre); }
    });
    // Dentro de enlaces y botones, pulsar sirve para escribir, no para navegar
    document.addEventListener("click", (ev) => {
      if (ev.target.closest?.("[data-e]") && ev.target.closest("a, button, summary")) ev.preventDefault();
    }, true);
    document.addEventListener("paste", (ev) => {
      if (!ev.target.closest?.("[data-e]")) return;
      ev.preventDefault();
      document.execCommand("insertText", false, (ev.clipboardData || window.clipboardData).getData("text/plain"));
    });
    document.addEventListener("keydown", (ev) => {
      if ((ev.metaKey || ev.ctrlKey) && ev.key.toLowerCase() === "s") { ev.preventDefault(); guardar(); }
    });
    // Seguir en modo edición al navegar por la web
    document.addEventListener("click", (ev) => {
      const a = ev.target.closest?.("a[href]");
      if (!a || ev.defaultPrevented || a.closest("[data-e]")) return;
      if (pendientes.size && !confirm("Tienes cambios sin guardar. ¿Cambiar de página y perderlos?")) ev.preventDefault();
    });
    window.addEventListener("beforeunload", (ev) => { if (pendientes.size) { ev.preventDefault(); ev.returnValue = ""; } });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    if (tokenValido() || (await entrar())) activar();
  });
})();
