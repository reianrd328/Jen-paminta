// ==========================================================================
// JEN & ALBERT PAMINTA - API CLIENT & UTILITIES
// ==========================================================================

const API = {
  baseUrl: '',

  async request(endpoint, method = 'GET', data = null) {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
      }
    };

    if (data && (method === 'POST' || method === 'PUT')) {
      options.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, options);
      const resData = await response.json();
      
      if (!response.ok) {
        throw new Error(resData.message || `Request failed with status ${response.status}`);
      }
      return resData;
    } catch (err) {
      console.error(`[API Error] ${method} ${endpoint}:`, err);
      this.toast(err.message, 'error');
      throw err;
    }
  },

  get(endpoint, params = {}) {
    const query = new URLSearchParams(params).toString();
    const url = query ? `${endpoint}?${query}` : endpoint;
    return this.request(url, 'GET');
  },

  post(endpoint, data = {}) {
    return this.request(endpoint, 'POST', data);
  },

  put(endpoint, data = {}) {
    return this.request(endpoint, 'PUT', data);
  },

  delete(endpoint) {
    return this.request(endpoint, 'DELETE');
  },

  // Formatting helpers
  formatCurrency(val, symbol = '₱') {
    const num = parseFloat(val) || 0.0;
    return `${symbol}${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  },

  formatNumber(val) {
    const num = parseFloat(val) || 0.0;
    return num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  },

  formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? dateStr : d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  },

  // Toast Notification System
  toast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '⚠️';
    if (type === 'warning') icon = '🔔';

    toast.innerHTML = `
      <span style="font-size: 1.1rem;">${icon}</span>
      <div style="flex-grow: 1;">${message}</div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
};

