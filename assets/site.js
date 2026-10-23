// Menú móvil y desplegable de colecciones
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".nav-toggle");
  const menu = document.getElementById("nav-menu");
  toggle?.addEventListener("click", () => {
    const open = menu.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });
  const subs = [...document.querySelectorAll(".has-sub")];
  const closeOthers = (keep) => subs.forEach((li) => {
    if (li !== keep) {
      li.classList.remove("open");
      li.querySelector(".sub-toggle").setAttribute("aria-expanded", "false");
    }
  });
  document.querySelectorAll(".sub-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const li = btn.closest(".has-sub");
      closeOthers(li);
      const open = li.classList.toggle("open");
      btn.setAttribute("aria-expanded", String(open));
    });
  });
  // Solo un desplegable a la vez: al pasar a otro, se cierra el que estaba abierto
  subs.forEach((li) => li.addEventListener("mouseenter", () => closeOthers(li)));
  document.addEventListener("click", (ev) => {
    document.querySelectorAll(".has-sub.open").forEach((li) => {
      if (!li.contains(ev.target)) {
        li.classList.remove("open");
        li.querySelector(".sub-toggle").setAttribute("aria-expanded", "false");
      }
    });
  });
});

// Cesta de demostración (se guarda en el navegador; no acepta pedidos)
(() => {
  const KEY = "am_cart_v2";
  const ROOT = window.AM_ROOT || "";
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch { return []; } };
  const save = (items) => { try { localStorage.setItem(KEY, JSON.stringify(items)); } catch {} };

  function render() {
    const items = load();
    const products = window.AM_PRODUCTS || {};
    const count = items.reduce((n, it) => n + it.qty, 0);
    document.querySelectorAll("[data-cart-count]").forEach((el) => { el.textContent = count; });
    const list = document.querySelector("[data-cart-items]");
    if (!list) return;
    let total = 0;
    list.innerHTML = items.length ? "" : '<p class="cart-empty">Tu cesta está vacía.</p>';
    items.forEach((it, i) => {
      const p = products[it.slug];
      if (!p) return;
      const c = p.colores[it.color] || Object.values(p.colores)[0];
      const t = p.tamanos[it.size] || Object.values(p.tamanos)[0];
      total += t.precio * it.qty;
      const variante = Object.keys(p.colores).length > 1 ? `${c.label} · ` : "";
      const row = document.createElement("div");
      row.className = "cart-line";
      row.innerHTML = `<img src="${ROOT}${c.img}" alt=""><div>${p.nombre}<small>${variante}${t.label} · ${it.qty} ud.</small></div>
        <div>${t.precio * it.qty} €<br><button type="button" data-remove="${i}">Quitar</button></div>`;
      list.appendChild(row);
    });
    document.querySelector("[data-cart-total]").textContent = `${total} €`;
  }

  function toast(msg) {
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2200);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const cart = document.querySelector(".cart");
    const open = () => { render(); cart.hidden = false; };
    const close = () => { cart.hidden = true; };
    document.querySelector(".cart-open")?.addEventListener("click", open);
    document.querySelector(".cart-close")?.addEventListener("click", close);
    cart?.addEventListener("click", (ev) => {
      if (ev.target === cart) close();
      const rm = ev.target.closest("[data-remove]");
      if (rm) { const items = load(); items.splice(Number(rm.dataset.remove), 1); save(items); render(); }
    });
    document.querySelector(".cart-checkout")?.addEventListener("click", () => {
      close();
      document.querySelector(".demo-note")?.showModal();
    });
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") close(); });

    // Ficha: muestras de color y añadir a la cesta
    const pdp = document.querySelector(".pdp");
    if (pdp) {
      const addBtn = pdp.querySelector(".add-to-cart");
      pdp.querySelectorAll(".swatch").forEach((sw) => {
        sw.addEventListener("click", () => {
          pdp.querySelectorAll(".swatch").forEach((s) => { s.classList.remove("is-active"); s.setAttribute("aria-pressed", "false"); });
          sw.classList.add("is-active");
          sw.setAttribute("aria-pressed", "true");
          pdp.querySelector("[data-color-label]").textContent = sw.dataset.label;
          pdp.querySelector("[data-flat-img]").src = sw.dataset.flat;
          pdp.querySelector("[data-worn-img]").src = sw.dataset.worn;
          pdp.querySelector("[data-zoom-img]").src = sw.dataset.zoom;
          addBtn.dataset.color = sw.dataset.color;
        });
      });
      pdp.querySelectorAll(".size-opt").forEach((opt) => {
        opt.addEventListener("click", () => {
          pdp.querySelectorAll(".size-opt").forEach((o) => { o.classList.remove("is-active"); o.setAttribute("aria-pressed", "false"); });
          opt.classList.add("is-active");
          opt.setAttribute("aria-pressed", "true");
          pdp.querySelector(".buy-price").textContent = `${opt.dataset.price} €`;
          addBtn.dataset.size = opt.dataset.size;
        });
      });
      addBtn.addEventListener("click", () => {
        const items = load();
        const slug = pdp.dataset.slug, color = addBtn.dataset.color, size = addBtn.dataset.size;
        const found = items.find((it) => it.slug === slug && it.color === color && it.size === size);
        if (found) found.qty += 1; else items.push({ slug, color, size, qty: 1 });
        save(items);
        render();
        toast("AÑADIDO A TU CESTA");
      });
    }
    render();
  });
})();

// Listado: flechas para ver las 3 fotos de cada pañuelo (al pasar el ratón sale la foto llevada)
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-carousel]").forEach((box) => {
    const imgs = [...box.querySelectorAll("img")];
    let i = 0;
    const show = (n) => {
      i = (n + imgs.length) % imgs.length;
      imgs.forEach((im, k) => im.classList.toggle("is-on", k === i));
    };
    const fine = window.matchMedia("(hover: hover)").matches;
    if (fine) {
      box.addEventListener("mouseenter", () => { if (i === 0) show(1); });
      box.addEventListener("mouseleave", () => show(0));
    }
    box.querySelector(".car-prev").addEventListener("click", (ev) => { ev.preventDefault(); show(i - 1); });
    box.querySelector(".car-next").addEventListener("click", (ev) => { ev.preventDefault(); show(i + 1); });
  });
});

// Ficha: foto ampliada con zoom (estilo Hermès)
document.addEventListener("DOMContentLoaded", () => {
  const lb = document.querySelector(".lightbox");
  if (!lb) return;
  const stage = lb.querySelector(".lb-stage");
  const img = lb.querySelector(".lb-img");
  const range = lb.querySelector(".lb-range");
  const thumbs = lb.querySelector(".lb-thumbs");
  const sources = () => [...document.querySelectorAll("[data-gallery] .zoomable img")];
  let idx = 0, scale = 1, px = 0.5, py = 0.5;

  function apply() {
    const W = stage.clientWidth, H = stage.clientHeight;
    const w = img.clientWidth * scale, h = img.clientHeight * scale;
    const tx = w > W ? (0.5 - px) * (w - W) : 0;
    const ty = h > H ? (0.5 - py) * (h - H) : 0;
    img.style.transform = `translate(-50%, -50%) translate(${tx}px, ${ty}px) scale(${scale})`;
    range.value = scale;
    stage.style.cursor = scale > 1 ? "move" : "zoom-in";
  }
  function setScale(s) { scale = Math.min(4, Math.max(1, s)); apply(); }
  function go(n) {
    const list = sources();
    idx = (n + list.length) % list.length;
    img.src = list[idx].src;
    img.alt = list[idx].alt;
    thumbs.querySelectorAll("button").forEach((b, k) => b.classList.toggle("is-active", k === idx));
    thumbs.querySelector(".is-active")?.scrollIntoView({ block: "nearest", inline: "center" });
    scale = 1; px = py = 0.5;
    img.onload = apply;
    apply();
  }
  function open(n) {
    thumbs.innerHTML = "";
    sources().forEach((s, k) => {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("aria-label", `Foto ${k + 1}`);
      b.innerHTML = `<img src="${s.src}" alt="">`;
      b.addEventListener("click", () => go(k));
      thumbs.appendChild(b);
    });
    lb.showModal();
    stage.focus({ preventScroll: true });
    go(n);
  }

  document.querySelectorAll(".zoomable").forEach((b) => b.addEventListener("click", () => open(Number(b.dataset.index))));
  lb.querySelector(".lb-close").addEventListener("click", () => lb.close());
  lb.querySelector(".lb-prev").addEventListener("click", () => go(idx - 1));
  lb.querySelector(".lb-next").addEventListener("click", () => go(idx + 1));
  lb.querySelector(".lb-in").addEventListener("click", (ev) => { setScale(scale + 0.5); if (ev.detail) ev.currentTarget.blur(); });
  lb.querySelector(".lb-out").addEventListener("click", (ev) => { setScale(scale - 0.5); if (ev.detail) ev.currentTarget.blur(); });
  range.addEventListener("input", () => setScale(Number(range.value)));
  stage.addEventListener("click", (ev) => {
    if (scale === 1) {
      const r = stage.getBoundingClientRect();
      px = (ev.clientX - r.left) / r.width; py = (ev.clientY - r.top) / r.height;
      setScale(2.5);
    }
  });
  stage.addEventListener("mousemove", (ev) => {
    if (scale === 1) return;
    const r = stage.getBoundingClientRect();
    px = (ev.clientX - r.left) / r.width; py = (ev.clientY - r.top) / r.height;
    apply();
  });
  stage.addEventListener("wheel", (ev) => { ev.preventDefault(); setScale(scale - ev.deltaY * 0.002); }, { passive: false });
  lb.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowRight") go(idx + 1);
    if (ev.key === "ArrowLeft") go(idx - 1);
  });
  window.addEventListener("resize", () => { if (lb.open) apply(); });
});

// Ficha en móvil: puntos que indican qué foto se ve
document.addEventListener("DOMContentLoaded", () => {
  const strip = document.querySelector(".pdp-photos");
  const dots = [...document.querySelectorAll(".pdp-dots span")];
  if (!strip || !dots.length || !("IntersectionObserver" in window)) return;
  const figs = [...strip.querySelectorAll("figure")];
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting && en.intersectionRatio > 0.6) {
        const k = figs.indexOf(en.target);
        dots.forEach((d, i) => d.classList.toggle("is-on", i === k));
      }
    });
  }, { root: strip, threshold: [0.6] });
  figs.forEach((f) => io.observe(f));
});

// Punto verde: consulta por un cuadro disponible (abre el correo con el mensaje editable)
document.addEventListener("DOMContentLoaded", () => {
  const dlg = document.querySelector(".inquiry");
  if (!dlg) return;
  const form = dlg.querySelector(".inq-form");
  document.querySelectorAll("[data-inquiry]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const { img, titulo, datos, proyecto } = btn.dataset;
      dlg.querySelector(".inq-img img").src = img;
      dlg.querySelector(".inq-img img").alt = titulo;
      dlg.querySelector("#inq-title").textContent = titulo;
      dlg.querySelector(".inq-datos").textContent = `${datos}${datos ? " · " : ""}${proyecto}`;
      form.mensaje.value = `Hola Ana,\n\nHe visto en tu web el cuadro «${titulo}»${datos ? ` (${datos})` : ""}, del proyecto ${proyecto}, y estoy interesado en él.\n\n¿Podrías contarme si sigue disponible, su precio y cómo sería el envío?\n\nMuchas gracias,\n`;
      dlg.showModal();
      form.mensaje.scrollTop = 0;
      if (window.matchMedia("(hover: hover)").matches) form.nombre.focus();
      else dlg.querySelector(".inq-grid").scrollTop = 0;
    });
  });
  // cerrar pulsando fuera
  dlg.addEventListener("click", (ev) => { if (ev.target === dlg) dlg.close(); });
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const firma = [form.nombre.value, form.email.value].filter(Boolean).join("\n");
    const asunto = `Consulta: ${dlg.querySelector("#inq-title").textContent}`;
    const cuerpo = form.mensaje.value + (firma ? `\n${firma}` : "");
    window.location.href = `mailto:${form.dataset.email}?subject=${encodeURIComponent(asunto)}&body=${encodeURIComponent(cuerpo)}`;
    dlg.close();
  });
});

// Carrusel «Del mismo proyecto»: flechas que se ocultan cuando no hay más
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-rail]").forEach((wrap) => {
    const rail = wrap.querySelector(".rail");
    const prev = wrap.querySelector(".rail-prev");
    const next = wrap.querySelector(".rail-next");
    const update = () => {
      prev.disabled = rail.scrollLeft <= 2;
      next.disabled = rail.scrollLeft + rail.clientWidth >= rail.scrollWidth - 2;
      wrap.classList.toggle("rail-static", prev.disabled && next.disabled);
    };
    prev.addEventListener("click", (ev) => { rail.scrollBy({ left: -rail.clientWidth * 0.75 }); if (ev.detail) prev.blur(); });
    next.addEventListener("click", (ev) => { rail.scrollBy({ left: rail.clientWidth * 0.75 }); if (ev.detail) next.blur(); });
    rail.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
  });
});

// Llegar a un cuadro concreto (#img-N): cargar antes las imágenes de arriba y bajar hasta él
document.addEventListener("DOMContentLoaded", () => {
  const id = decodeURIComponent(location.hash.slice(1));
  if (!id.startsWith("img-")) return;
  const target = document.getElementById(id);
  if (!target) return;
  const figs = [...document.querySelectorAll(".obra-gallery figure")];
  const idx = figs.indexOf(target);
  const previas = figs.slice(0, idx + 1).map((f) => f.querySelector("img")).filter(Boolean);
  previas.forEach((im) => { im.loading = "eager"; });
  const ir = () => target.scrollIntoView({ block: "start" });
  Promise.all(previas.map((im) => im.complete ? null : new Promise((ok) => { im.addEventListener("load", ok, { once: true }); im.addEventListener("error", ok, { once: true }); })))
    .then(() => requestAnimationFrame(ir));
  ir();
});

// Textos largos de proyectos: plegados con «Leer más · Read more»
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-fold]").forEach((box) => {
    const limite = window.matchMedia("(max-width: 820px)").matches ? 300 : 360;
    if (box.scrollHeight < limite + 160) return;
    box.classList.add("fold");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "fold-btn";
    btn.setAttribute("aria-expanded", "false");
    const pon = (abierto) => {
      btn.innerHTML = abierto ? "Leer menos <span>· Read less</span>" : "Leer más <span>· Read more</span>";
      btn.setAttribute("aria-expanded", String(abierto));
    };
    pon(false);
    btn.addEventListener("click", (ev) => {
      const abierto = box.classList.toggle("fold");
      pon(!abierto);
      if (abierto) box.scrollIntoView({ block: "start", behavior: "smooth" });
      if (ev.detail) btn.blur();
    });
    box.after(btn);
  });
});
