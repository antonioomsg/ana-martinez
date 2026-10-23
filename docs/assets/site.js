// Menú móvil y desplegable de colecciones
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".nav-toggle");
  const menu = document.getElementById("nav-menu");
  toggle?.addEventListener("click", () => {
    const open = menu.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });
  document.querySelectorAll(".sub-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const li = btn.closest(".has-sub");
      const open = li.classList.toggle("open");
      btn.setAttribute("aria-expanded", String(open));
    });
  });
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
  const KEY = "am_cart";
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
      total += p.precio * it.qty;
      const row = document.createElement("div");
      row.className = "cart-line";
      row.innerHTML = `<img src="${ROOT}${c.img}" alt=""><div>Carré ${p.nombre}<small>${c.label} · ${it.qty} ud.</small></div>
        <div>${p.precio * it.qty} €<br><button type="button" data-remove="${i}">Quitar</button></div>`;
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
          pdp.querySelectorAll(".swatch").forEach((s) => s.classList.remove("is-active"));
          sw.classList.add("is-active");
          pdp.querySelector("[data-color-label]").textContent = sw.dataset.label;
          pdp.querySelector("[data-flat-img]").src = sw.dataset.flat;
          addBtn.dataset.color = sw.dataset.color;
        });
      });
      addBtn.addEventListener("click", () => {
        const items = load();
        const slug = pdp.dataset.slug, color = addBtn.dataset.color;
        const found = items.find((it) => it.slug === slug && it.color === color);
        if (found) found.qty += 1; else items.push({ slug, color, qty: 1 });
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
  const sources = () => [...document.querySelectorAll(".pdp-photos .zoomable img")];
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
    go(n);
  }

  document.querySelectorAll(".zoomable").forEach((b) => b.addEventListener("click", () => open(Number(b.dataset.index))));
  lb.querySelector(".lb-close").addEventListener("click", () => lb.close());
  lb.querySelector(".lb-in").addEventListener("click", () => setScale(scale + 0.5));
  lb.querySelector(".lb-out").addEventListener("click", () => setScale(scale - 0.5));
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
