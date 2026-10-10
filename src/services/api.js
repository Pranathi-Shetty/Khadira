/**
 * Khadira ERP API Client
 * Connects frontend landing page & consoles directly to the FastAPI backend (khadira-2/backend)
 */

const API_BASE = '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Accept': 'application/json',
    ...(options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
    ...options.headers,
  };

  try {
    const res = await fetch(url, {
      ...options,
      headers,
      credentials: 'include', // sends and receives the mill_session HTTP cookie
    });

    if (res.status === 204) {
      return null;
    }

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const errorMsg = data?.detail || data?.message || `Request failed with status ${res.status}`;
      const err = new Error(errorMsg);
      err.status = res.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (err) {
    console.error(`[API Error] ${options.method || 'GET'} ${url}:`, err);
    throw err;
  }
}

export const MillAPI = {
  // --- Meta & Health ---
  async checkHealth() {
    try {
      const res = await request('/health');
      return { online: res?.status === 'ok', app: res?.app || 'Khadira' };
    } catch {
      return { online: false, app: 'Offline' };
    }
  },

  // --- Auth ---
  async login(username, password) {
    return request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  },

  async logout() {
    return request('/auth/logout', {
      method: 'POST',
    });
  },

  async getMe() {
    return request('/auth/me');
  },

  // --- Dashboard Metrics ---
  async getDashboard() {
    return request('/dashboard');
  },

  // --- Inventory & Items ---
  async getItems(itemType = null, q = '') {
    const params = new URLSearchParams();
    if (itemType) params.append('item_type', itemType);
    if (q) params.append('q', q);
    const queryStr = params.toString() ? `?${params.toString()}` : '';
    return request(`/items${queryStr}`);
  },

  // --- Machine Telemetry ---
  async getMachines() {
    return request('/machines');
  },

  async createMachine(code, name, machineType) {
    return request('/machines', {
      method: 'POST',
      body: JSON.stringify({ code, name, machine_type: machineType }),
    });
  },

  // --- Orders ---
  async getOrders(status = null) {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return request(`/orders${query}`);
  },

  async confirmOrder(orderId) {
    return request(`/orders/${orderId}/confirm`, {
      method: 'POST',
    });
  },

  async cancelOrder(orderId) {
    return request(`/orders/${orderId}/cancel`, {
      method: 'POST',
    });
  },

  // --- Production Runs & Looms ---
  async getProductionRuns() {
    return request('/production');
  },

  async advanceProduction(runId, meters, yarnKg = null) {
    return request(`/production/${runId}/advance`, {
      method: 'POST',
      body: JSON.stringify({ meters, yarn_kg: yarnKg }),
    });
  },

  // --- Fabric Rolls & Quality Control ---
  async getRolls(status = null) {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return request(`/rolls${query}`);
  },

  async getPendingQC() {
    return request('/qc/pending');
  },

  async inspectRoll(rollId, verdict, grade = 'A', note = '') {
    return request(`/rolls/${rollId}/inspect`, {
      method: 'POST',
      body: JSON.stringify({ verdict, grade, note }),
    });
  },

  async moveRollToStore(rollId) {
    return request(`/rolls/${rollId}/store`, {
      method: 'POST',
    });
  },

  // --- QC Defects ---
  async reportDefect(rollId, defectType, severity, locationM, notes) {
    return request(`/qc/defects`, {
      method: 'POST',
      body: JSON.stringify({
        roll_id: rollId,
        defect_type: defectType,
        severity,
        location_m: locationM,
        notes,
      }),
    });
  },

  async getDefects(rollId) {
    return request(`/qc/defects/${rollId}`);
  },

  // --- Notifications ---
  async getNotifications() {
    return request('/notifications');
  },

  async markNotificationRead(notifId) {
    return request(`/notifications/${notifId}/read`, {
      method: 'POST',
    });
  },

  // --- Production Downtime ---
  async reportDowntime(machineId, runId, reason, description) {
    return request(`/production/downtime`, {
      method: 'POST',
      body: JSON.stringify({
        machine_id: machineId,
        run_id: runId,
        reason,
        description,
      }),
    });
  },

  // --- Run Reconciliation ---
  async finalizeRun(runId, reconciliationData) {
    return request(`/production/${runId}/finalize`, {
      method: 'POST',
      body: JSON.stringify(reconciliationData),
    });
  },

  // --- Finance & Invoices ---
  async getInvoices() {
    return request('/finance/invoices');
  },

  async payInvoice(invId, amountPaise, method = 'bank') {
    return request(`/finance/invoices/${invId}/pay`, {
      method: 'POST',
      body: JSON.stringify({ amount_paise: amountPaise, method }),
    });
  },

  // --- Purchasing & POs ---
  async getPurchasing() {
    return request('/purchasing');
  },

  // --- Partners ---
  async getSuppliers() {
    return request('/partners/suppliers');
  },

  async getBuyers() {
    return request('/partners/buyers');
  },

  // --- Settings ---
  async getSettings() {
    return request('/settings');
  },
};

export default MillAPI;
