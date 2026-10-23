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
