/* ════════════════════════════════════════════════════════════════════
   Hunting & Fishing Supply Co — storefront JS
   Cart (localStorage) · Quote modal · Toast · Product filter · Checkout
   ════════════════════════════════════════════════════════════════════ */
const CART_KEY = "hfsc_cart";
const FREE_SHIP_THRESHOLD = 2000;
const FLAT_SHIP = 500;
// International freight by region (must match backend orders.py FREIGHT_MAP).
const FREIGHT_MAP = {
  "Canada/Mexico": 800, "Caribbean/Central America": 900, "South America": 1000,
  "Europe": 1200, "Middle East/North Africa": 1100, "Sub-Saharan Africa": 1300,
  "Asia Pacific": 1400, "Australia/New Zealand": 1500, "Other": 1600,
};
function checkoutShipping(subtotal) {
  if (subtotal === 0) return 0;
  const sel = document.querySelector('[name="freight_region"]');
  const region = sel ? sel.value : "Domestic (USA)";
  if (region && region !== "Domestic (USA)") return FREIGHT_MAP[region] || 1600;
  return subtotal >= FREE_SHIP_THRESHOLD ? 0 : FLAT_SHIP;   // domestic
}

/* ── helpers ── */
function escHtml(str) {
  return String(str == null ? "" : str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function money(n) { return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function loadCart() { try { return JSON.parse(localStorage.getItem(CART_KEY)) || []; } catch (e) { return []; } }
function saveCart(cart) { localStorage.setItem(CART_KEY, JSON.stringify(cart)); }
function brandFromName(name) { return (name || "").split(" ")[0]; }

/* ── cart mutations ── */
function addToCart(slug, name, price, image, model) {
  const cart = loadCart();
  const found = cart.find(i => i.slug === slug);
  if (found) { found.qty += 1; }
  else { cart.push({ slug, name, price: Number(price), image, model: model || "", qty: 1 }); }
  saveCart(cart);
  renderCartDrawer(cart);
  updateCartBadge(cart);
  showToast("Added to cart — " + name, "success");
}
function removeFromCart(slug) {
  const cart = loadCart().filter(i => i.slug !== slug);
  saveCart(cart); renderCartDrawer(cart); updateCartBadge(cart);
}
function addToCartBtn(btn) {
  // Direct handler for buttons inside clickable cards, where the inline
  // stopPropagation (needed to prevent card navigation) would otherwise keep
  // the click from reaching the delegated document listener.
  if (!btn || btn.disabled) return;
  addToCart(btn.dataset.slug, btn.dataset.name, parseFloat(btn.dataset.price),
            btn.dataset.image, btn.dataset.model);
}
function changeQty(slug, delta) {
  const cart = loadCart();
  const item = cart.find(i => i.slug === slug);
  if (!item) return;
  item.qty += delta;
  if (item.qty < 1) { removeFromCart(slug); return; }
  saveCart(cart); renderCartDrawer(cart); updateCartBadge(cart);
}

/* ── cart rendering ── */
function updateCartBadge(cart) {
  cart = cart || loadCart();
  const count = cart.reduce((s, i) => s + i.qty, 0);
  document.querySelectorAll(".cart-count-badge").forEach(b => {
    b.textContent = count;
    b.style.display = count ? "inline-block" : "none";
  });
}
function renderCartDrawer(cart) {
  cart = cart || loadCart();
  const box = document.getElementById("cart-items");
  if (!box) return;
  if (!cart.length) {
    box.innerHTML = '<div class="cart-empty">Your cart is empty.</div>';
  } else {
    box.innerHTML = cart.map(i => `
      <div class="cart-item">
        <img src="${escHtml(i.image || '/static/images/placeholder.jpg')}" alt=""
             onerror="this.src='/static/images/placeholder.jpg'">
        <div>
          <div class="cart-item-name">${escHtml(i.name)}</div>
          ${i.model ? `<div class="cart-item-model">${escHtml(i.model)}</div>` : ""}
          <div class="cart-qty-row">
            <button onclick="changeQty('${escHtml(i.slug)}',-1)">−</button>
            <span>${i.qty}</span>
            <button onclick="changeQty('${escHtml(i.slug)}',1)">+</button>
            <button class="cart-remove" onclick="removeFromCart('${escHtml(i.slug)}')">Remove</button>
          </div>
        </div>
        <div class="cart-item-price">${money(i.price * i.qty)}</div>
      </div>`).join("");
  }
  const subtotal = cart.reduce((s, i) => s + i.price * i.qty, 0);
  const shipping = subtotal === 0 ? 0 : (subtotal >= FREE_SHIP_THRESHOLD ? 0 : FLAT_SHIP);
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set("cart-subtotal", money(subtotal));
  set("cart-shipping", subtotal === 0 ? "—" : (shipping === 0 ? "FREE" : money(shipping)));
  set("cart-total", money(subtotal + shipping));
  const btn = document.getElementById("cart-checkout-btn");
  if (btn) btn.classList.toggle("disabled", cart.length === 0);
}

/* ── cart drawer UI ── */
function openCart() { renderCartDrawer(loadCart()); document.getElementById("cart-drawer").classList.add("open"); document.getElementById("cart-overlay-bg").classList.add("open"); document.body.style.overflow = "hidden"; }
function closeCart() { document.getElementById("cart-drawer").classList.remove("open"); document.getElementById("cart-overlay-bg").classList.remove("open"); document.body.style.overflow = ""; }

/* ── quote modal ── */
function openQuoteModal(productName) {
  const field = document.getElementById("quote-product-interest");
  if (field) field.value = productName || "";
  document.getElementById("quote-fields").style.display = "block";
  document.getElementById("quote-success").style.display = "none";
  document.getElementById("quote-form").reset();
  if (field) field.value = productName || "";
  document.getElementById("quote-modal").classList.add("open");
  document.body.style.overflow = "hidden";
}
function closeQuoteModal() { document.getElementById("quote-modal").classList.remove("open"); document.body.style.overflow = ""; }

async function submitQuote(e) {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const payload = {
    first_name: fd.get("first_name"), last_name: fd.get("last_name"),
    phone: fd.get("phone"), email: fd.get("email"),
    product_interest: fd.get("product_interest") || null,
    details: fd.get("details") || null,
    service: "Quote Request",
  };
  try {
    const res = await fetch("/api/bookings/", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("bad status " + res.status);
    document.getElementById("quote-fields").style.display = "none";
    document.getElementById("quote-success").style.display = "block";
    showToast("Inquiry sent — we'll be in touch soon!", "success");
  } catch (err) {
    showToast("Error sending inquiry. Call us at +1 (406) 206-9144", "error");
  }
}

/* ── toast ── */
function showToast(msg, type) {
  const c = document.getElementById("toast-container");
  if (!c) return;
  const t = document.createElement("div");
  t.className = "toast " + (type || "success");
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => { t.classList.add("fade"); setTimeout(() => t.remove(), 400); }, 3000);
}

/* ── product filtering (products page) ── */
function filterProducts() {
  const search = (document.getElementById("filter-search")?.value || "").toLowerCase();
  const category = document.getElementById("filter-category")?.value || "";
  const params = new URLSearchParams(window.location.search);
  const badge = (params.get("badge") || "").toLowerCase();
  let shown = 0;
  document.querySelectorAll(".product-card").forEach(card => {
    const name = card.dataset.name || "";
    const brand = card.dataset.brand || "";
    const cat = card.dataset.category || "";
    const bdg = (card.dataset.badge || "");
    const matchText = !search || name.includes(search) || brand.includes(search);
    const matchCat = !category || cat === category;
    const matchBadge = !badge || bdg === badge;
    const show = matchText && matchCat && matchBadge;
    card.style.display = show ? "" : "none";
    if (show) shown++;
  });
  const rc = document.getElementById("results-count");
  if (rc) { const total = rc.dataset.total || shown; rc.textContent = `Showing ${shown} of ${total} products`; }
  const none = document.getElementById("no-results");
  if (none) none.style.display = shown === 0 ? "block" : "none";
}

/* ── checkout page ── */
function renderCheckout() {
  const cart = loadCart();
  const box = document.getElementById("checkout-items");
  if (!box) return;
  const empty = document.getElementById("checkout-empty");
  const btn = document.getElementById("place-order-btn");
  if (!cart.length) {
    box.innerHTML = "";
    if (empty) empty.style.display = "block";
    if (btn) btn.disabled = true;
  } else {
    if (empty) empty.style.display = "none";
    if (btn) btn.disabled = false;
    box.innerHTML = cart.map(i => `
      <div class="co-item">
        <img src="${escHtml(i.image || '/static/images/placeholder.jpg')}" alt=""
             onerror="this.src='/static/images/placeholder.jpg'">
        <div>
          <div class="co-name">${escHtml(i.name)}</div>
          ${i.model ? `<div class="cart-item-model">${escHtml(i.model)}</div>` : ""}
          <div class="muted" style="font-size:.82rem;">Qty ${i.qty} × ${money(i.price)}</div>
        </div>
        <div class="cart-item-price">${money(i.price * i.qty)}</div>
      </div>`).join("");
  }
  const subtotal = cart.reduce((s, i) => s + i.price * i.qty, 0);
  const shipping = checkoutShipping(subtotal);
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set("co-subtotal", money(subtotal));
  set("co-shipping", subtotal === 0 ? "—" : (shipping === 0 ? "FREE" : money(shipping)));
  set("co-total", money(subtotal + shipping));
}

async function submitOrder(e) {
  e.preventDefault();
  const cart = loadCart();
  if (!cart.length) { showToast("Your cart is empty.", "error"); return; }
  const form = e.target;
  const fd = new FormData(form);
  const btn = document.getElementById("place-order-btn");
  const err = document.getElementById("order-error");
  if (err) err.style.display = "none";
  if (btn) { btn.disabled = true; btn.textContent = "Placing Order…"; }

  const items = cart.map(i => ({
    product_id: String(i.slug), name: i.name, model_number: i.model || null,
    unit_price: Number(i.price), quantity: Number(i.qty),
  }));
  const subtotal = cart.reduce((s, i) => s + i.price * i.qty, 0);
  let paymentMethod = fd.get("payment_method") || null;
  if (paymentMethod === "Other") {
    const other = (fd.get("payment_other") || "").trim();
    if (!other) {
      showToast("Please specify your payment method.", "error");
      if (btn) { btn.disabled = false; btn.textContent = "Place Order →"; }
      return;
    }
    paymentMethod = "Other: " + other;
  }
  let city = fd.get("city") || null;
  if (city === "Other") city = (fd.get("city_other") || "").trim() || null;
  const payload = {
    first_name: fd.get("first_name"), last_name: fd.get("last_name"),
    phone: fd.get("phone"), email: fd.get("email"), company: fd.get("company") || null,
    address: fd.get("address") || null, city: city,
    state: fd.get("state") || null, zip: fd.get("zip") || null,
    country: fd.get("country") || null, freight_region: fd.get("freight_region") || null,
    contact_pref: fd.get("contact_pref") || null, best_time: fd.get("best_time") || null,
    notes: fd.get("notes") || null, payment_method: paymentMethod, items, total: subtotal,
  };
  try {
    const res = await fetch("/api/orders/", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("status " + res.status);
    const count = cart.reduce((s, i) => s + i.qty, 0);
    const name = fd.get("first_name");
    saveCart([]); updateCartBadge([]);
    document.getElementById("order-form").style.display = "none";
    const success = document.getElementById("order-success");
    document.getElementById("order-success-msg").innerHTML =
      `Thank you ${escHtml(name)}. We've received your order for ${count} item${count === 1 ? "" : "s"}. ` +
      `Our team will contact you within a few hours at ${escHtml(fd.get("phone"))} or ${escHtml(fd.get("email"))} ` +
      `to confirm availability and arrange payment. You'll also receive a confirmation email shortly.`;
    success.style.display = "block";
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (e2) {
    if (err) { err.textContent = "Submission failed. Please call us directly: +1 (406) 206-9144"; err.style.display = "block"; }
    if (btn) { btn.disabled = false; btn.textContent = "Place Order →"; }
    showToast("Order failed — call +1 (406) 206-9144", "error");
  }
}

/* ── theme (dark / light) ── */
function refreshThemeLabel() {
  var isLight = document.documentElement.getAttribute("data-theme") === "light";
  document.querySelectorAll("#theme-toggle").forEach(function (b) {
    b.textContent = isLight ? "Dark" : "Light";   // shows the mode you'll switch TO
  });
}
function toggleTheme() {
  var isLight = document.documentElement.getAttribute("data-theme") === "light";
  if (isLight) {
    document.documentElement.removeAttribute("data-theme");
    try { localStorage.setItem("hfsc_theme", "dark"); } catch (e) {}
  } else {
    document.documentElement.setAttribute("data-theme", "light");
    try { localStorage.setItem("hfsc_theme", "light"); } catch (e) {}
  }
  refreshThemeLabel();
}

/* ── category bar slider ── */
function scrollCats(dir) {
  const el = document.getElementById("cat-scroll");
  if (el) el.scrollBy({ left: dir * 280, behavior: "smooth" });
}

/* ── init ── */
document.addEventListener("DOMContentLoaded", () => {
  refreshThemeLabel();
  updateCartBadge(loadCart());
  renderCartDrawer(loadCart());

  // Cart toggle buttons
  document.querySelectorAll("[data-cart-toggle]").forEach(b => b.addEventListener("click", openCart));

  // Add-to-cart via event delegation (cards + detail page)
  document.addEventListener("click", e => {
    const btn = e.target.closest(".btn-cart-sm");
    if (!btn || btn.disabled) return;
    e.stopPropagation();
    addToCart(btn.dataset.slug, btn.dataset.name, parseFloat(btn.dataset.price),
              btn.dataset.image, btn.dataset.model);
  });

  // Payment method tiles (checkout): selected highlight + "Other" input toggle
  const payGrid = document.getElementById("pay-grid");
  if (payGrid) {
    payGrid.addEventListener("change", () => {
      const checked = payGrid.querySelector("input[name=payment_method]:checked");
      payGrid.querySelectorAll(".pay-tile").forEach(t =>
        t.classList.toggle("selected", t.contains(checked)));
      const otherWrap = document.getElementById("pay-other-wrap");
      if (otherWrap) {
        const isOther = checked && checked.value === "Other";
        otherWrap.style.display = isOther ? "block" : "none";
        const inp = otherWrap.querySelector("input");
        if (inp) { inp.required = !!isOther; if (isOther) inp.focus(); }
      }
    });
  }

  // Quote modal backdrop click
  const qm = document.getElementById("quote-modal");
  if (qm) qm.addEventListener("click", e => { if (e.target === qm) closeQuoteModal(); });

  // Hamburger / mobile menu
  const ham = document.getElementById("hamburger");
  const panel = document.getElementById("mobile-menu-panel");
  if (ham && panel) ham.addEventListener("click", () => panel.classList.toggle("open"));

  // Category bar active state
  document.querySelectorAll(".cat-inner a").forEach(a => {
    const href = a.getAttribute("href");
    if (href === window.location.pathname + window.location.search) a.classList.add("active");
  });

  // Products page filter wiring
  const fs = document.getElementById("filter-search");
  if (fs) {
    const params = new URLSearchParams(window.location.search);
    if (params.get("q")) fs.value = params.get("q");
    const fc = document.getElementById("filter-category");
    if (fc && params.get("category")) fc.value = params.get("category");
    fs.addEventListener("keyup", filterProducts);
    if (fc) fc.addEventListener("change", filterProducts);
    filterProducts();
  }
});
