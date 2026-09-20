// ==========================================================================
// JEN & ALBERT PAMINTA - PUBLIC STOREFRONT & CUSTOMER APP
// ==========================================================================

let publicProducts = [];
let customerCart = JSON.parse(localStorage.getItem('ja_customer_cart') || '[]');

document.addEventListener('DOMContentLoaded', () => {
  loadPublicProducts();
  renderCartBadge();
  setupPublicListeners();
});

async function loadPublicProducts() {
  const container = document.getElementById('public-product-grid');
  if (!container) return;

  try {
    const res = await API.get('/api/products');
    if (res.success) {
      publicProducts = res.products;
      renderProductGrid(publicProducts);
    }
  } catch (err) {
    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: #777;">Unable to load products. Please check back shortly.</div>`;
  }
}

function renderProductGrid(products) {
  const container = document.getElementById('public-product-grid');
  if (!container) return;

  if (products.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);">No products found matching your selection.</div>`;
    return;
  }

  container.innerHTML = products.map(p => {
    const isOutOfStock = p.current_stock <= 0;
    let badgeClass = 'badge-in-stock';
    let badgeText = 'In Stock';
    if (isOutOfStock) {
      badgeClass = 'badge-out-of-stock';
      badgeText = 'Sold Out';
    } else if (p.current_stock <= p.min_stock_alert) {
      badgeClass = 'badge-low-stock';
      badgeText = `Few Left (${p.current_stock} ${p.unit})`;
    }

    return `
      <div class="product-card">
        <div class="product-img-wrapper">
          <img src="${p.image_url || '/logo.jpg'}" onerror="this.src='/logo.jpg'" alt="${p.name}" class="product-img" />
          <span class="badge ${badgeClass} stock-tag">${badgeText}</span>
        </div>
        <div class="product-body">
          <span class="product-category">${p.category_name || 'Paminta Estate'}</span>
          <h3 class="product-title">${p.name}</h3>
          <p class="product-desc">${p.description || 'Authentic harvest from Jen & Albert Paminta estate.'}</p>
          <div class="product-footer">
            <div class="product-price">${API.formatCurrency(p.unit_price)} <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: normal;">/ ${p.unit}</span></div>
            <button class="btn ${isOutOfStock ? 'btn-outline-vine' : 'btn-gold'} btn-sm" 
                    ${isOutOfStock ? 'disabled' : ''} 
                    onclick="addToCustomerCart(${p.id})">
              ${isOutOfStock ? 'Sold Out' : '+ Add to Cart'}
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function filterCategory(catName, btnElement) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btnElement.classList.add('active');

  if (catName === 'ALL') {
    renderProductGrid(publicProducts);
  } else {
    const filtered = publicProducts.filter(p => (p.category_name || '').toLowerCase().includes(catName.toLowerCase()));
    renderProductGrid(filtered);
  }
}

function addToCustomerCart(productId) {
  const prod = publicProducts.find(p => p.id === productId);
  if (!prod) return;

  const existing = customerCart.find(it => it.product_id === productId);
  const currentQty = existing ? existing.quantity : 0;

  if (currentQty + 1 > prod.current_stock) {
    API.toast(`Cannot add more. Only ${prod.current_stock} ${prod.unit} available.`, 'warning');
    return;
  }

  if (existing) {
    existing.quantity += 1;
    existing.subtotal = existing.quantity * existing.unit_price;
  } else {
    customerCart.push({
      product_id: prod.id,
      name: prod.name,
      unit: prod.unit,
      image_url: prod.image_url || '/logo.jpg',
      unit_price: parseFloat(prod.unit_price),
      quantity: 1,
      subtotal: parseFloat(prod.unit_price),
      max_stock: parseFloat(prod.current_stock)
    });
  }

  saveCart();
  renderCartBadge();
  renderCartDrawer();
  API.toast(`Added ${prod.name} to your basket!`, 'success');
  openCartDrawer();
}

function updateCartQty(productId, delta) {
  const item = customerCart.find(it => it.product_id === productId);
  if (!item) return;

  const newQty = item.quantity + delta;
  if (newQty <= 0) {
    customerCart = customerCart.filter(it => it.product_id !== productId);
  } else if (newQty > item.max_stock) {
    API.toast(`Maximum available stock reached (${item.max_stock} ${item.unit})`, 'warning');
    return;
  } else {
    item.quantity = newQty;
    item.subtotal = item.quantity * item.unit_price;
  }

  saveCart();
  renderCartBadge();
  renderCartDrawer();
}

function removeCartItem(productId) {
  customerCart = customerCart.filter(it => it.product_id !== productId);
  saveCart();
  renderCartBadge();
  renderCartDrawer();
}

function saveCart() {
  localStorage.setItem('ja_customer_cart', JSON.stringify(customerCart));
}

function renderCartBadge() {
  const count = customerCart.reduce((sum, it) => sum + it.quantity, 0);
  const badge = document.getElementById('cart-badge-count');
  if (badge) badge.innerText = count;
}

function openCartDrawer() {
  renderCartDrawer();
  document.getElementById('cart-drawer-overlay')?.classList.add('active');
}

function closeCartDrawer() {
  document.getElementById('cart-drawer-overlay')?.classList.remove('active');
}

function renderCartDrawer() {
  const container = document.getElementById('drawer-items-list');
  const subtotalDisplay = document.getElementById('drawer-subtotal-display');
  if (!container) return;

  if (customerCart.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">Your shopping basket is currently empty.</div>`;
    if (subtotalDisplay) subtotalDisplay.innerText = API.formatCurrency(0);
    return;
  }

  const subtotal = customerCart.reduce((sum, it) => sum + it.subtotal, 0);
  if (subtotalDisplay) subtotalDisplay.innerText = API.formatCurrency(subtotal);

  container.innerHTML = customerCart.map(it => `
    <div class="cart-item-row">
      <img src="${it.image_url || '/logo.jpg'}" onerror="this.src='/logo.jpg'" alt="${it.name}" style="width: 45px; height: 45px; border-radius: var(--radius-sm); object-fit: cover; background: #FAF6F0; border: 1px solid var(--border-gold);" />
      <div style="flex-grow: 1;">
        <div style="font-weight: 600; font-size: 0.875rem;">${it.name}</div>
        <div style="font-size: 0.775rem; color: var(--text-muted);">${API.formatCurrency(it.unit_price)} / ${it.unit}</div>
        <div style="display: flex; align-items: center; gap: 0.4rem; margin-top: 0.35rem;">
          <button class="btn btn-sm" style="padding: 0.15rem 0.5rem; background: var(--bg-parchment);" onclick="updateCartQty(${it.product_id}, -1)">-</button>
          <span style="font-weight: 700; font-size: 0.85rem;">${it.quantity}</span>
          <button class="btn btn-sm" style="padding: 0.15rem 0.5rem; background: var(--bg-parchment);" onclick="updateCartQty(${it.product_id}, 1)">+</button>
        </div>
      </div>
      <div style="text-align: right;">
        <div style="font-weight: 700; color: var(--color-vine-dark);">${API.formatCurrency(it.subtotal)}</div>
        <button onclick="removeCartItem(${it.product_id})" style="background: none; border: none; color: #C62828; cursor: pointer; font-size: 0.8rem; margin-top: 0.25rem;">Remove</button>
      </div>
    </div>
  `).join('');
}

function openCheckoutModal() {
  if (customerCart.length === 0) {
    API.toast('Your cart is empty', 'warning');
    return;
  }
  closeCartDrawer();
  const subtotal = customerCart.reduce((sum, it) => sum + it.subtotal, 0);
  document.getElementById('checkout-total-display').innerText = API.formatCurrency(subtotal);
  document.getElementById('modal-checkout').classList.add('active');
}

function closeCheckoutModal() {
  document.getElementById('modal-checkout').classList.remove('active');
}

async function submitCustomerOrder() {
  const name = document.getElementById('checkout-name').value.trim();
  const phone = document.getElementById('checkout-phone').value.trim();
  const address = document.getElementById('checkout-address').value.trim();
  const paymentMethod = document.getElementById('checkout-payment').value;
  const notes = document.getElementById('checkout-notes').value.trim();

  if (!name || !phone) {
    API.toast('Please enter your full name and contact phone number', 'warning');
    return;
  }

  const payload = {
    customer_name: name,
    customer_contact: phone,
    payment_method: paymentMethod,
    notes: `Delivery Address: ${address} | Note: ${notes}`,
    created_by: 'online_customer',
    items: customerCart.map(it => ({
      product_id: it.product_id,
      quantity: it.quantity,
      unit_price: it.unit_price
    }))
  };

  try {
    const res = await API.post('/api/sales', payload);
    if (res.success) {
      customerCart = [];
      saveCart();
      renderCartBadge();
      closeCheckoutModal();

      // Show Order Success Modal
      document.getElementById('order-success-invoice').innerText = res.sale.invoice_number;
      document.getElementById('order-success-total').innerText = API.formatCurrency(res.sale.total_amount);
      document.getElementById('modal-order-success').classList.add('active');

      // Refresh products to show updated stock
      loadPublicProducts();
    }
  } catch (err) {
    console.error('Customer checkout failed', err);
  }
}

// Order Tracking
function openTrackModal() {
  document.getElementById('modal-track').classList.add('active');
}

async function lookupOrder() {
  const inv = document.getElementById('track-invoice-input').value.trim();
  const resultDiv = document.getElementById('track-result-div');
  if (!inv) return;

  resultDiv.innerHTML = `<p style="color: #777;">Searching order...</p>`;
  try {
    const res = await API.get(`/api/sales/invoice/${inv}`);
    if (res.success) {
      const s = res.sale;
      const items = res.items;
      resultDiv.innerHTML = `
        <div style="background: var(--color-vine-pale); padding: 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-gold); margin-top: 1rem;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
            <strong>Order #${s.invoice_number}</strong>
            <span class="badge ${s.status === 'COMPLETED' ? 'badge-in-stock' : 'badge-out-of-stock'}">${s.status}</span>
          </div>
          <p style="font-size: 0.85rem; color: var(--text-dark);">Customer: <strong>${s.customer_name}</strong></p>
          <p style="font-size: 0.825rem; color: var(--text-muted);">Date: ${API.formatDate(s.created_at)}</p>
          <p style="font-size: 0.85rem; color: var(--color-vine-primary); font-weight: 700; margin-top: 0.35rem;">Total: ${API.formatCurrency(s.total_amount)} (${s.payment_method})</p>
          <hr style="border: 0; border-top: 1px dashed var(--border-gold); margin: 0.75rem 0;" />
          <div style="font-size: 0.8rem;">
            ${items.map(it => `<div>• ${it.product_name} &times; ${it.quantity} ${it.unit} (${API.formatCurrency(it.subtotal)})</div>`).join('')}
          </div>
        </div>
      `;
    }
  } catch (err) {
    resultDiv.innerHTML = `<p style="color: #C62828; margin-top: 1rem;">Order not found. Please verify the invoice number.</p>`;
  }
}

function setupPublicListeners() {
  const searchInput = document.getElementById('public-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      const filtered = publicProducts.filter(p => p.name.toLowerCase().includes(q) || (p.description || '').toLowerCase().includes(q));
      renderProductGrid(filtered);
    });
  }
}

