// ==========================================================================
// JEN & ALBERT PAMINTA - ADMIN MANAGEMENT PORTAL SCRIPT
// ==========================================================================

let currentTab = 'dashboard';
let allProducts = [];
let allCategories = [];
let posCart = [];

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  checkAuth();
  loadInitialData();
  setupEventListeners();
});

// Authentication
async function checkAuth() {
  try {
    const res = await API.get('/api/auth/me');
    if (res.authenticated) {
      document.getElementById('admin-username-display').innerText = res.user.full_name || res.user.username;
    }
  } catch (err) {
    console.warn('Auth check skipped or offline:', err);
  }
}

async function handleLogout() {
  try {
    await API.post('/api/auth/logout');
    window.location.href = '/login';
  } catch (err) {
    window.location.href = '/login';
  }
}

// Navigation Tabs
function initTabs() {
  const hash = window.location.hash.replace('#', '') || 'dashboard';
  switchTab(hash);

  document.querySelectorAll('.sidebar-nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const tab = item.dataset.tab;
      if (tab) switchTab(tab);
    });
  });
}

function toggleMobileSidebar() {
  const sb = document.getElementById('admin-sidebar');
  const bd = document.getElementById('sidebar-backdrop');
  if (sb) sb.classList.toggle('open');
  if (bd) bd.classList.toggle('active');
}

function switchTab(tabId) {
  currentTab = tabId;
  window.location.hash = tabId;

  // Auto-close sidebar on mobile
  const sb = document.getElementById('admin-sidebar');
  const bd = document.getElementById('sidebar-backdrop');
  if (sb) sb.classList.remove('open');
  if (bd) bd.classList.remove('active');

  document.querySelectorAll('.sidebar-nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.tab === tabId);
  });

  document.querySelectorAll('.tab-pane').forEach(pane => {
    pane.style.display = pane.id === `tab-${tabId}` ? 'block' : 'none';
  });

  if (tabId === 'dashboard') loadDashboard();
  if (tabId === 'inventory') loadInventoryLedger();
  if (tabId === 'sales') initPOS();
  if (tabId === 'history') loadSalesHistory();
  if (tabId === 'movements') loadMovements();
  if (tabId === 'settings') loadSettingsAndHealth();
}

// Data Loaders
async function loadInitialData() {
  try {
    const res = await API.get('/api/products');
    if (res.success) {
      allProducts = res.products;
      populateProductSelects();
    }
    loadDashboard();
  } catch (err) {
    console.error('Initial load failed', err);
  }
}

// 1. DASHBOARD
async function loadDashboard() {
  try {
    const res = await API.get('/api/dashboard/stats');
    if (!res.success) return;

    const k = res.kpis;
    document.getElementById('kpi-today-sales').innerText = API.formatCurrency(k.today_sales);
    document.getElementById('kpi-today-orders').innerText = `${k.today_orders} completed`;
    document.getElementById('kpi-month-sales').innerText = API.formatCurrency(k.month_sales);
    document.getElementById('kpi-month-orders').innerText = `${k.month_orders} completed`;
    document.getElementById('kpi-beginning-val').innerText = API.formatCurrency(k.beginning_inventory_value);
    document.getElementById('kpi-ending-val').innerText = API.formatCurrency(k.ending_inventory_value);
    document.getElementById('kpi-low-stock').innerText = k.low_stock_count;

    // Low stock alerts list
    const alertsContainer = document.getElementById('low-stock-list');
    if (res.low_stock_alerts && res.low_stock_alerts.length > 0) {
      alertsContainer.innerHTML = res.low_stock_alerts.map(item => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 0; border-bottom: 1px dashed var(--border-parchment);">
          <div>
            <strong>${item.name}</strong>
            <div style="font-size: 0.775rem; color: var(--text-muted);">SKU: ${item.sku}</div>
          </div>
          <div style="text-align: right;">
            <span class="badge ${item.is_empty ? 'badge-out-of-stock' : 'badge-low-stock'}">
              ${item.current_stock} ${item.unit} left
            </span>
            <button class="btn btn-gold btn-sm" style="margin-left: 0.5rem;" onclick="openAddStockModal(${item.id})">+ Restock</button>
          </div>
        </div>
      `).join('');
    } else {
      alertsContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">All paminta and wine inventory stocks are healthy.</p>`;
    }

    // Top Selling
    const topContainer = document.getElementById('top-selling-list');
    if (res.top_selling && res.top_selling.length > 0) {
      topContainer.innerHTML = res.top_selling.map((item, idx) => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 0; border-bottom: 1px dashed var(--border-parchment);">
          <div>
            <span style="font-weight: 700; color: var(--color-gold-deep); margin-right: 0.5rem;">#${idx + 1}</span>
            <strong>${item.product_name}</strong>
          </div>
          <div style="text-align: right;">
            <span style="font-weight: 600;">${item.total_qty} ${item.unit}</span>
            <div style="font-size: 0.775rem; color: var(--color-vine-primary); font-weight: 600;">${API.formatCurrency(item.total_revenue)}</div>
          </div>
        </div>
      `).join('');
    } else {
      topContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No sales recorded yet. Ring up a sale in POS!</p>`;
    }

    // Recent Sales
    const recentSalesTbody = document.getElementById('recent-sales-tbody');
    if (res.recent_sales && res.recent_sales.length > 0) {
      recentSalesTbody.innerHTML = res.recent_sales.map(s => `
        <tr>
          <td><strong>${s.invoice_number}</strong></td>
          <td>${s.customer_name}</td>
          <td>${API.formatCurrency(s.total_amount)}</td>
          <td><span class="badge badge-paminta">${s.payment_method}</span></td>
          <td><span class="badge ${s.status === 'COMPLETED' ? 'badge-in-stock' : 'badge-out-of-stock'}">${s.status}</span></td>
          <td><button class="btn btn-outline-vine btn-sm" onclick="viewReceipt('${s.invoice_number}')">Receipt</button></td>
        </tr>
      `).join('');
    } else {
      recentSalesTbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No sales recorded yet.</td></tr>`;
    }

  } catch (err) {
    console.error('Failed loading dashboard:', err);
  }
}

// 2. INVENTORY RECONCILIATION LEDGER (Beginning vs Ending Stock)
async function loadInventoryLedger() {
  try {
    const category = document.getElementById('ledger-category-filter')?.value || '';
    const search = document.getElementById('ledger-search')?.value || '';

    const res = await API.get('/api/inventory/ledger', { category_id: category, search: search });
    if (!res.success) return;

    const tbody = document.getElementById('inventory-ledger-tbody');
    if (!res.ledger || res.ledger.length === 0) {
      tbody.innerHTML = `<tr><td colspan="12" style="text-align: center; padding: 2rem;">No products found in inventory.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.ledger.map(item => {
      let badgeClass = 'badge-in-stock';
      let statusText = 'In Stock';
      if (item.status === 'LOW_STOCK') {
        badgeClass = 'badge-low-stock';
        statusText = 'Low Stock';
      } else if (item.status === 'OUT_OF_STOCK') {
        badgeClass = 'badge-out-of-stock';
        statusText = 'Out of Stock';
      }

      return `
        <tr>
          <td>
            <strong style="color: var(--color-vine-dark); cursor: pointer;" onclick="openEditProductModal(${item.product_id})" title="Click to customize SKU & details">
              ✏️ ${item.sku}
            </strong>
          </td>
          <td style="cursor: pointer;" onclick="openEditProductModal(${item.product_id})" title="Click to customize item description">
            <strong style="color: var(--color-vine-dark);">${item.name}</strong>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${item.category_name}</div>
          </td>
          <td>${item.unit}</td>
          <td><strong>${API.formatCurrency(item.unit_price)}</strong></td>
          <td style="background: var(--bg-card-subtle); font-weight: 600; text-align: center;">
            ${item.beginning_stock}
          </td>
          <td style="color: #2E7D32; font-weight: 600; text-align: center;">
            +${item.stock_added}
          </td>
          <td style="color: #C62828; font-weight: 600; text-align: center;">
            -${item.sales_deducted}
          </td>
          <td style="color: #E65100; font-weight: 600; text-align: center;">
            -${item.less_adjustments}
          </td>
          <td style="font-weight: 700; text-align: center; background: #F4ECE1;">
            ${item.calculated_ending}
          </td>
          <td style="font-weight: 800; font-size: 1rem; text-align: center; color: var(--color-vine-primary);">
            ${item.current_stock}
          </td>
          <td><span class="badge ${badgeClass}">${statusText}</span></td>
          <td>
            <div style="display: flex; gap: 0.35rem; flex-wrap: wrap;">
              <button class="btn btn-sm" style="background: #EBF3EE; color: var(--color-vine-primary); border: 1px solid var(--color-vine-primary); font-weight: 700;" title="Customize SKU, Description, Unit, Price" onclick="openEditProductModal(${item.product_id})">✏️ Edit</button>
              <button class="btn btn-gold btn-sm" title="Add Stock / Restock" onclick="openAddStockModal(${item.product_id})">+ Add</button>
              <button class="btn btn-outline-vine btn-sm" title="Less / Deduct Damaged Stock" onclick="openLessStockModal(${item.product_id})">- Less</button>
              <button class="btn btn-sm" style="background: var(--bg-parchment); border: 1px solid var(--border-parchment);" title="Set Beginning Stock" onclick="openSetBegModal(${item.product_id}, ${item.beginning_stock})">⚙️ Beg</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Summary Cards
    const s = res.summary;
    document.getElementById('ledger-total-beg-val').innerText = API.formatCurrency(s.total_beginning_value);
    document.getElementById('ledger-total-end-val').innerText = API.formatCurrency(s.total_ending_value);
    document.getElementById('ledger-total-retail-val').innerText = API.formatCurrency(s.total_retail_value);

  } catch (err) {
    console.error('Failed loading inventory ledger', err);
  }
}

// 3. POS / SALES MODULE (Directly updates & deducts stock)
async function initPOS() {
  try {
    const res = await API.get('/api/products');
    if (res.success) {
      allProducts = res.products;
      renderPOSCatalog(allProducts);
      renderPOSCart();
    }
  } catch (err) {
    console.error('POS init failed', err);
  }
}

function renderPOSCatalog(products) {
  const container = document.getElementById('pos-catalog-grid');
  if (!container) return;

  const search = (document.getElementById('pos-search')?.value || '').toLowerCase();
  const filtered = products.filter(p => p.name.toLowerCase().includes(search) || p.sku.toLowerCase().includes(search));

  if (filtered.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--text-muted);">No products match your search.</div>`;
    return;
  }

  container.innerHTML = filtered.map(p => {
    const isOut = p.current_stock <= 0;
    return `
      <div class="pos-item-tile ${isOut ? 'disabled' : ''}" onclick="${isOut ? '' : `addToPOSCart(${p.id})`}">
        <div>
          <div style="font-size: 0.725rem; color: var(--color-gold-deep); font-weight: 600;">${p.sku}</div>
          <div style="font-family: var(--font-serif-display); font-size: 0.95rem; font-weight: 700; color: var(--color-vine-dark); margin: 0.2rem 0;">${p.name}</div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 0.75rem;">
          <div style="font-size: 1.05rem; font-weight: 700; color: var(--color-vine-primary);">${API.formatCurrency(p.unit_price)}</div>
          <span class="badge ${isOut ? 'badge-out-of-stock' : (p.current_stock <= p.min_stock_alert ? 'badge-low-stock' : 'badge-in-stock')}">
            ${isOut ? 'Out of Stock' : `${p.current_stock} ${p.unit}`}
          </span>
        </div>
      </div>
    `;
  }).join('');
}

function addToPOSCart(productId) {
  const prod = allProducts.find(p => p.id === productId);
  if (!prod) return;

  const existing = posCart.find(item => item.product_id === productId);
  const currentInCart = existing ? existing.quantity : 0;

  if (currentInCart + 1 > prod.current_stock) {
    API.toast(`Cannot add more. Available stock for ${prod.name} is only ${prod.current_stock} ${prod.unit}`, 'warning');
    return;
  }

  if (existing) {
    existing.quantity += 1;
    existing.subtotal = existing.quantity * existing.unit_price;
  } else {
    posCart.push({
      product_id: prod.id,
      name: prod.name,
      sku: prod.sku,
      unit: prod.unit,
      unit_price: parseFloat(prod.unit_price),
      cost_price: parseFloat(prod.cost_price),
      quantity: 1,
      subtotal: parseFloat(prod.unit_price),
      max_stock: parseFloat(prod.current_stock)
    });
  }

  renderPOSCart();
}

function updatePOSCartQty(productId, delta) {
  const item = posCart.find(it => it.product_id === productId);
  if (!item) return;

  const newQty = item.quantity + delta;
  if (newQty <= 0) {
    posCart = posCart.filter(it => it.product_id !== productId);
  } else if (newQty > item.max_stock) {
    API.toast(`Cannot exceed available stock (${item.max_stock} ${item.unit})`, 'warning');
    return;
  } else {
    item.quantity = newQty;
    item.subtotal = item.quantity * item.unit_price;
  }
  renderPOSCart();
}

function removePOSCartItem(productId) {
  posCart = posCart.filter(it => it.product_id !== productId);
  renderPOSCart();
}

function clearPOSCart() {
  posCart = [];
  renderPOSCart();
}

function renderPOSCart() {
  const container = document.getElementById('pos-cart-items');
  if (!container) return;

  if (posCart.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 2.5rem 1rem; color: var(--text-muted); font-size: 0.9rem;">Cart is empty. Click items from catalog to start selling.</div>`;
    updatePOSCartTotals();
    return;
  }

  container.innerHTML = posCart.map(item => `
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 0; border-bottom: 1px dashed var(--border-parchment);">
      <div style="flex-grow: 1; padding-right: 0.5rem;">
        <div style="font-weight: 600; font-size: 0.875rem;">${item.name}</div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">${API.formatCurrency(item.unit_price)} / ${item.unit}</div>
      </div>
      <div style="display: flex; align-items: center; gap: 0.4rem;">
        <button class="btn btn-sm" style="padding: 0.2rem 0.5rem; background: var(--bg-parchment);" onclick="updatePOSCartQty(${item.product_id}, -1)">-</button>
        <span style="font-weight: 700; min-width: 24px; text-align: center;">${item.quantity}</span>
        <button class="btn btn-sm" style="padding: 0.2rem 0.5rem; background: var(--bg-parchment);" onclick="updatePOSCartQty(${item.product_id}, 1)">+</button>
      </div>
      <div style="width: 80px; text-align: right; font-weight: 700; color: var(--color-vine-dark);">
        ${API.formatCurrency(item.subtotal)}
      </div>
      <button onclick="removePOSCartItem(${item.product_id})" style="background: none; border: none; color: #C62828; cursor: pointer; padding-left: 0.5rem; font-size: 1.1rem;">&times;</button>
    </div>
  `).join('');

  updatePOSCartTotals();
}

function updatePOSCartTotals() {
  const subtotal = posCart.reduce((sum, it) => sum + it.subtotal, 0);
  const discountInput = document.getElementById('pos-discount');
  const discount = parseFloat(discountInput?.value || 0.0);
  const total = Math.max(0, subtotal - discount);

  const tenderedInput = document.getElementById('pos-tendered');
  const tendered = parseFloat(tenderedInput?.value || 0.0);
  const change = Math.max(0, tendered - total);

  document.getElementById('pos-subtotal-display').innerText = API.formatCurrency(subtotal);
  document.getElementById('pos-total-display').innerText = API.formatCurrency(total);
  document.getElementById('pos-change-display').innerText = API.formatCurrency(change);
}

async function handlePOSCheckout() {
  if (posCart.length === 0) {
    API.toast('Cart is empty', 'warning');
    return;
  }

  const customerName = (document.getElementById('pos-customer-name')?.value || 'Walk-in Customer').trim();
  const paymentMethod = document.getElementById('pos-payment-method')?.value || 'CASH';
  const discount = parseFloat(document.getElementById('pos-discount')?.value || 0.0);
  const tendered = parseFloat(document.getElementById('pos-tendered')?.value || 0.0);

  const subtotal = posCart.reduce((sum, it) => sum + it.subtotal, 0);
  const total = Math.max(0, subtotal - discount);

  if (paymentMethod === 'CASH' && tendered < total && tendered > 0) {
    API.toast(`Amount tendered (${API.formatCurrency(tendered)}) is less than total (${API.formatCurrency(total)})`, 'error');
    return;
  }

  const payload = {
    customer_name: customerName,
    payment_method: paymentMethod,
    discount: discount,
    amount_tendered: tendered > 0 ? tendered : total,
    created_by: 'staff',
    items: posCart.map(it => ({
      product_id: it.product_id,
      quantity: it.quantity,
      unit_price: it.unit_price
    }))
  };

  try {
    const res = await API.post('/api/sales', payload);
    if (res.success) {
      API.toast(`Sale ${res.sale.invoice_number} completed! Stock deducted automatically.`, 'success');
      clearPOSCart();
      showReceiptModal(res.sale);
      
      // Refresh inventory in background
      loadInitialData();
    }
  } catch (err) {
    console.error('POS Checkout failed:', err);
  }
}

// 4. MODALS (Add Stock, Less Stock, Set Beginning, Product)
function openAddStockModal(productId) {
  document.getElementById('add-stock-prod-id').value = productId;
  const prod = allProducts.find(p => p.id === productId);
  if (prod) {
    document.getElementById('add-stock-prod-name').innerText = `${prod.name} (${prod.current_stock} ${prod.unit} currently)`;
    document.getElementById('add-stock-qty').placeholder = `Quantity in ${prod.unit}`;
  }
  document.getElementById('modal-add-stock').classList.add('active');
}

function openLessStockModal(productId) {
  document.getElementById('less-stock-prod-id').value = productId;
  const prod = allProducts.find(p => p.id === productId);
  if (prod) {
    document.getElementById('less-stock-prod-name').innerText = `${prod.name} (Max available: ${prod.current_stock} ${prod.unit})`;
    document.getElementById('less-stock-qty').max = prod.current_stock;
  }
  document.getElementById('modal-less-stock').classList.add('active');
}

function openSetBegModal(productId, currentBeg) {
  document.getElementById('set-beg-prod-id').value = productId;
  const prod = allProducts.find(p => p.id === productId);
  if (prod) {
    document.getElementById('set-beg-prod-name').innerText = prod.name;
    document.getElementById('set-beg-qty').value = currentBeg;
  }
  document.getElementById('modal-set-beg').classList.add('active');
}

function openEditProductModal(productId) {
  const prod = allProducts.find(p => p.id === productId);
  if (!prod) return;

  document.getElementById('edit-prod-id').value = prod.id;
  document.getElementById('edit-prod-name').value = prod.name;
  document.getElementById('edit-prod-sku').value = prod.sku;
  document.getElementById('edit-prod-category').value = prod.category_id || 1;
  document.getElementById('edit-prod-unit').value = prod.unit || 'pack';
  document.getElementById('edit-prod-price').value = prod.unit_price;
  document.getElementById('edit-prod-cost').value = prod.cost_price || 0;
  document.getElementById('edit-prod-alert').value = prod.min_stock_alert || 10;
  document.getElementById('edit-prod-desc').value = prod.description || '';

  document.getElementById('modal-edit-product').classList.add('active');
}

async function submitEditProduct() {
  const prodId = parseInt(document.getElementById('edit-prod-id').value);
  const name = document.getElementById('edit-prod-name').value.trim();
  const sku = document.getElementById('edit-prod-sku').value.trim().toUpperCase();
  const categoryId = parseInt(document.getElementById('edit-prod-category').value);
  const unit = document.getElementById('edit-prod-unit').value.trim();
  const price = parseFloat(document.getElementById('edit-prod-price').value || 0);
  const cost = parseFloat(document.getElementById('edit-prod-cost').value || 0);
  const minAlert = parseFloat(document.getElementById('edit-prod-alert').value || 10);
  const desc = document.getElementById('edit-prod-desc').value.trim();

  if (!name || !sku) {
    API.toast('Product name and SKU are required', 'warning');
    return;
  }

  try {
    const res = await API.put(`/api/products/${prodId}`, {
      name, sku, category_id: categoryId, unit,
      unit_price: price, cost_price: cost,
      min_stock_alert: minAlert,
      description: desc
    });
    if (res.success) {
      API.toast(res.message, 'success');
      closeModal('modal-edit-product');
      loadInitialData();
      loadInventoryLedger();
    }
  } catch (err) {
    console.error('Edit product error', err);
  }
}

async function deleteCurrentProduct() {
  const prodId = parseInt(document.getElementById('edit-prod-id').value);
  const prod = allProducts.find(p => p.id === prodId);
  const name = prod ? prod.name : 'this item';

  if (!confirm(`Are you sure you want to remove '${name}' from your active catalog?`)) {
    return;
  }

  try {
    const res = await API.delete(`/api/products/${prodId}`);
    if (res.success) {
      API.toast(res.message, 'success');
      closeModal('modal-edit-product');
      loadInitialData();
      loadInventoryLedger();
    }
  } catch (err) {
    console.error('Delete product error', err);
  }
}

async function handleResetAllRecords() {
  const answer = prompt(
    "WARNING: This will CLEAR ALL products, stock movements, and sales records so you can start fresh with your own stock.\n\nType 'CONFIRM' to clear all records:"
  );

  if (answer !== 'CONFIRM') {
    if (answer !== null) {
      API.toast("Reset cancelled. You must type 'CONFIRM' to wipe records.", 'info');
    }
    return;
  }

  try {
    const res = await API.post('/api/inventory/reset-records', {});
    if (res.success) {
      API.toast(res.message, 'success');
      allProducts = [];
      posCart = [];
      loadInitialData();
      loadInventoryLedger();
      loadDashboard();
      initPOS();
    }
  } catch (err) {
    console.error('Reset records error', err);
  }
}

function closeModal(modalId) {
  document.getElementById(modalId)?.classList.remove('active');
}

async function submitAddStock() {
  const prodId = parseInt(document.getElementById('add-stock-prod-id').value);
  const qty = parseFloat(document.getElementById('add-stock-qty').value || 0);
  const ref = document.getElementById('add-stock-ref').value;
  const notes = document.getElementById('add-stock-notes').value;

  if (qty <= 0) {
    API.toast('Please enter a valid stock quantity greater than 0', 'warning');
    return;
  }

  try {
    const res = await API.post('/api/inventory/add-stock', {
      product_id: prodId,
      quantity: qty,
      reference_id: ref,
      notes: notes
    });
    if (res.success) {
      API.toast(res.message, 'success');
      closeModal('modal-add-stock');
      document.getElementById('form-add-stock').reset();
      loadInventoryLedger();
      loadDashboard();
    }
  } catch (err) {
    console.error('Add stock error', err);
  }
}

async function submitLessStock() {
  const prodId = parseInt(document.getElementById('less-stock-prod-id').value);
  const qty = parseFloat(document.getElementById('less-stock-qty').value || 0);
  const reason = document.getElementById('less-stock-reason').value;
  const ref = document.getElementById('less-stock-ref').value;
  const notes = document.getElementById('less-stock-notes').value;

  if (qty <= 0) {
    API.toast('Please enter a valid deduction quantity greater than 0', 'warning');
    return;
  }

  try {
    const res = await API.post('/api/inventory/less-stock', {
      product_id: prodId,
      quantity: qty,
      reason: reason,
      reference_id: ref,
      notes: notes
    });
    if (res.success) {
      API.toast(res.message, 'success');
      closeModal('modal-less-stock');
      document.getElementById('form-less-stock').reset();
      loadInventoryLedger();
      loadDashboard();
    }
  } catch (err) {
    console.error('Less stock error', err);
  }
}

async function submitSetBeg() {
  const prodId = parseInt(document.getElementById('set-beg-prod-id').value);
  const begStock = parseFloat(document.getElementById('set-beg-qty').value || 0);
  const notes = document.getElementById('set-beg-notes').value;

  try {
    const res = await API.post('/api/inventory/set-beginning-stock', {
      product_id: prodId,
      beginning_stock: begStock,
      notes: notes
    });
    if (res.success) {
      API.toast(res.message, 'success');
      closeModal('modal-set-beg');
      loadInventoryLedger();
      loadDashboard();
    }
  } catch (err) {
    console.error('Set beginning error', err);
  }
}

async function submitNewProduct() {
  const name = document.getElementById('new-prod-name').value;
  const sku = document.getElementById('new-prod-sku').value;
  const categoryId = document.getElementById('new-prod-category').value;
  const unit = document.getElementById('new-prod-unit').value;
  const price = parseFloat(document.getElementById('new-prod-price').value || 0);
  const cost = parseFloat(document.getElementById('new-prod-cost').value || 0);
  const begStock = parseFloat(document.getElementById('new-prod-beg').value || 0);
  const minAlert = parseFloat(document.getElementById('new-prod-alert').value || 10);
  const desc = document.getElementById('new-prod-desc').value;

  if (!name) {
    API.toast('Product name is required', 'warning');
    return;
  }

  try {
    const res = await API.post('/api/products', {
      name, sku, category_id: categoryId, unit,
      unit_price: price, cost_price: cost,
      beginning_stock: begStock, min_stock_alert: minAlert,
      description: desc
    });
    if (res.success) {
      API.toast(res.message, 'success');
      closeModal('modal-new-product');
      document.getElementById('form-new-product').reset();
      loadInitialData();
      loadInventoryLedger();
    }
  } catch (err) {
    console.error('Create product error', err);
  }
}

// 5. SALES HISTORY & RECEIPTS
async function loadSalesHistory() {
  try {
    const res = await API.get('/api/sales');
    if (!res.success) return;

    const tbody = document.getElementById('sales-history-tbody');
    if (!res.sales || res.sales.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem;">No sales history found.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.sales.map(s => `
      <tr>
        <td><strong>${s.invoice_number}</strong></td>
        <td>${API.formatDate(s.created_at)}</td>
        <td>${s.customer_name}</td>
        <td><span class="badge badge-paminta">${s.payment_method}</span></td>
        <td><strong>${API.formatCurrency(s.total_amount)}</strong></td>
        <td><span class="badge ${s.status === 'COMPLETED' ? 'badge-in-stock' : 'badge-out-of-stock'}">${s.status}</span></td>
        <td>
          <button class="btn btn-outline-vine btn-sm" onclick="viewReceipt('${s.invoice_number}')">View Receipt</button>
          ${s.status === 'COMPLETED' ? `<button class="btn btn-danger btn-sm" style="margin-left: 0.35rem;" onclick="voidSale(${s.id}, '${s.invoice_number}')">Void / Restock</button>` : ''}
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Sales history load failed', err);
  }
}

async function viewReceipt(invoiceNumber) {
  try {
    const res = await API.get(`/api/sales/invoice/${invoiceNumber}`);
    if (res.success) {
      showReceiptModal(res.sale, res.items);
    }
  } catch (err) {
    console.error('View receipt failed', err);
  }
}

function showReceiptModal(sale, items = null) {
  const saleItems = items || sale.items || [];
  const container = document.getElementById('printable-receipt');
  
  container.innerHTML = `
    <div style="text-align: center; border-bottom: 2px dashed #000; padding-bottom: 12px; margin-bottom: 12px;">
      <img src="/logo.jpg" style="width: 65px; height: 65px; border-radius: 50%; margin-bottom: 6px;" />
      <h2 style="font-family: var(--font-serif-display); font-size: 1.2rem; margin-bottom: 2px;">JEN & ALBERT PAMINTA</h2>
      <p style="font-size: 0.75rem; color: #555;">Vineyard & Gourmet Paminta Estate</p>
      <p style="font-size: 0.75rem; color: #555;">Invoice #: <strong>${sale.invoice_number}</strong></p>
      <p style="font-size: 0.725rem; color: #777;">Date: ${API.formatDate(sale.created_at)}</p>
    </div>

    <div style="margin-bottom: 10px; font-size: 0.8rem;">
      <div>Customer: <strong>${sale.customer_name}</strong></div>
      <div>Payment Method: <strong>${sale.payment_method}</strong></div>
    </div>

    <table style="width: 100%; border-collapse: collapse; font-size: 0.8rem; margin-bottom: 12px;">
      <thead>
        <tr style="border-bottom: 1px solid #000;">
          <th style="text-align: left; padding: 4px 0;">Item</th>
          <th style="text-align: center; padding: 4px 0;">Qty</th>
          <th style="text-align: right; padding: 4px 0;">Price</th>
          <th style="text-align: right; padding: 4px 0;">Total</th>
        </tr>
      </thead>
      <tbody>
        ${saleItems.map(it => `
          <tr style="border-bottom: 1px dashed #ddd;">
            <td style="padding: 4px 0;">${it.product_name || it.name}</td>
            <td style="text-align: center;">${it.quantity} ${it.unit || ''}</td>
            <td style="text-align: right;">${API.formatCurrency(it.unit_price)}</td>
            <td style="text-align: right;">${API.formatCurrency(it.subtotal)}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>

    <div style="border-top: 1px dashed #000; padding-top: 8px; font-size: 0.85rem;">
      <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
        <span>Subtotal:</span>
        <span>${API.formatCurrency(sale.subtotal)}</span>
      </div>
      ${sale.discount > 0 ? `
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; color: #C62828;">
          <span>Discount:</span>
          <span>-${API.formatCurrency(sale.discount)}</span>
        </div>
      ` : ''}
      <div style="display: flex; justify-content: space-between; font-weight: 800; font-size: 1rem; border-top: 2px solid #000; padding-top: 6px; margin-top: 6px;">
        <span>Total:</span>
        <span>${API.formatCurrency(sale.total_amount)}</span>
      </div>
      ${sale.payment_method === 'CASH' ? `
        <div style="display: flex; justify-content: space-between; margin-top: 4px;">
          <span>Tendered:</span>
          <span>${API.formatCurrency(sale.amount_tendered)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-weight: 700;">
          <span>Change:</span>
          <span>${API.formatCurrency(sale.change_due)}</span>
        </div>
      ` : ''}
    </div>

    <div style="text-align: center; margin-top: 20px; font-size: 0.75rem; color: #555; border-top: 1px dashed #999; padding-top: 10px;">
      <p>Thank you for supporting Jen & Albert Paminta!</p>
      <p>Fine Vineyard Harvest & Premium Spices</p>
    </div>
  `;

  document.getElementById('modal-receipt').classList.add('active');
}

async function voidSale(saleId, invoiceNum) {
  if (!confirm(`Are you sure you want to VOID sale ${invoiceNum}? All items will be restocked back into inventory automatically.`)) {
    return;
  }

  try {
    const res = await API.post(`/api/sales/${saleId}/void`);
    if (res.success) {
      API.toast(res.message, 'success');
      loadSalesHistory();
      loadInventoryLedger();
      loadDashboard();
    }
  } catch (err) {
    console.error('Void sale failed', err);
  }
}

// 6. MOVEMENTS AUDIT TRAIL
async function loadMovements() {
  try {
    const res = await API.get('/api/inventory/movements');
    if (!res.success) return;

    const tbody = document.getElementById('movements-tbody');
    if (!res.movements || res.movements.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem;">No inventory movements logged.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.movements.map(m => {
      let badge = 'badge-paminta';
      let sign = '';
      if (m.movement_type === 'STOCK_IN' || m.movement_type === 'ADJUSTMENT_ADD') {
        badge = 'badge-in-stock';
        sign = '+';
      } else if (m.movement_type === 'SALE_DEDUCTION' || m.movement_type === 'ADJUSTMENT_LESS') {
        badge = 'badge-out-of-stock';
        sign = '-';
      } else if (m.movement_type === 'BEGINNING_BALANCE') {
        badge = 'badge-gold';
      }

      return `
        <tr>
          <td>${API.formatDate(m.created_at)}</td>
          <td>
            <strong>${m.product_name}</strong>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${m.sku}</div>
          </td>
          <td><span class="badge ${badge}">${m.movement_type}</span></td>
          <td style="font-weight: 700; text-align: center;">${sign}${m.quantity} ${m.unit}</td>
          <td style="text-align: center;">${m.previous_stock}</td>
          <td style="text-align: center; font-weight: 700; color: var(--color-vine-primary);">${m.new_stock}</td>
          <td><span style="font-size: 0.8rem; background: #EEE; padding: 2px 6px; border-radius: 4px;">${m.reference_id || 'N/A'}</span></td>
          <td style="font-size: 0.825rem; color: var(--text-muted);">${m.notes || ''}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed loading movements', err);
  }
}

// 7. SETTINGS & TIDB HEALTH
async function loadSettingsAndHealth() {
  checkDbHealth();
  try {
    const res = await API.get('/api/settings');
    if (res.success && res.settings) {
      const s = res.settings;
      if (document.getElementById('setting-estate-name')) document.getElementById('setting-estate-name').value = s.estate_name || '';
      if (document.getElementById('setting-contact-phone')) document.getElementById('setting-contact-phone').value = s.contact_phone || '';
      if (document.getElementById('setting-contact-email')) document.getElementById('setting-contact-email').value = s.contact_email || '';
      if (document.getElementById('setting-address')) document.getElementById('setting-address').value = s.address || '';
    }
  } catch (err) {
    console.error('Settings load error', err);
  }
}

async function checkDbHealth() {
  const statusBadge = document.getElementById('db-status-badge');
  const detailsBox = document.getElementById('db-health-details');
  if (statusBadge) statusBadge.innerText = 'Checking...';

  try {
    const res = await API.get('/api/settings/health');
    const db = res.database;
    if (statusBadge) {
      statusBadge.className = 'badge badge-in-stock';
      statusBadge.innerText = `● Connected to ${db.engine}`;
    }
    if (detailsBox) {
      detailsBox.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
          <div><span style="color: var(--text-muted); font-size: 0.8rem;">Database Engine:</span><br><strong>${db.engine}</strong></div>
          <div><span style="color: var(--text-muted); font-size: 0.8rem;">Host:</span><br><strong>${db.host}:${db.port}</strong></div>
          <div><span style="color: var(--text-muted); font-size: 0.8rem;">Database Name:</span><br><strong>${db.database}</strong></div>
          <div><span style="color: var(--text-muted); font-size: 0.8rem;">Latency:</span><br><strong>${db.latency_ms} ms</strong></div>
          <div><span style="color: var(--text-muted); font-size: 0.8rem;">Engine Version:</span><br><strong>${db.version}</strong></div>
        </div>
        ${db.notice ? `<div style="margin-top: 1rem; padding: 0.75rem; background: var(--color-gold-pale); border-radius: var(--radius-sm); font-size: 0.825rem; color: var(--color-gold-deep);">ℹ️ ${db.notice}</div>` : ''}
      `;
    }
  } catch (err) {
    if (statusBadge) {
      statusBadge.className = 'badge badge-out-of-stock';
      statusBadge.innerText = '● Connection Issue';
    }
  }
}

async function saveSettings() {
  const payload = {
    estate_name: document.getElementById('setting-estate-name').value,
    contact_phone: document.getElementById('setting-contact-phone').value,
    contact_email: document.getElementById('setting-contact-email').value,
    address: document.getElementById('setting-address').value
  };
  try {
    const res = await API.post('/api/settings', payload);
    if (res.success) {
      API.toast(res.message, 'success');
    }
  } catch (err) {
    console.error('Save settings failed', err);
  }
}

function populateProductSelects() {
  const selects = ['add-stock-prod-id', 'less-stock-prod-id', 'set-beg-prod-id'];
  selects.forEach(selId => {
    const el = document.getElementById(selId);
    if (el && el.tagName === 'SELECT') {
      el.innerHTML = allProducts.map(p => `
        <option value="${p.id}">${p.name} (${p.current_stock} ${p.unit} on hand)</option>
      `).join('');
    }
  });
}

function setupEventListeners() {
  // POS Search
  const posSearch = document.getElementById('pos-search');
  if (posSearch) {
    posSearch.addEventListener('input', () => renderPOSCatalog(allProducts));
  }

  // POS Discount & Tendered
  const discountInput = document.getElementById('pos-discount');
  const tenderedInput = document.getElementById('pos-tendered');
  if (discountInput) discountInput.addEventListener('input', updatePOSCartTotals);
  if (tenderedInput) tenderedInput.addEventListener('input', updatePOSCartTotals);

  // Ledger Filter
  const ledgerCat = document.getElementById('ledger-category-filter');
  const ledgerSearch = document.getElementById('ledger-search');
  if (ledgerCat) ledgerCat.addEventListener('change', loadInventoryLedger);
  if (ledgerSearch) ledgerSearch.addEventListener('input', loadInventoryLedger);
}

