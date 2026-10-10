/**
 * Khadira ERP API Client
 * Centralized API client connected directly to the FastAPI + SQLite backend.
 * Reads base URL from import.meta.env.VITE_API_BASE_URL (defaults to '/api').
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export async function apiRequest(endpoint, options = {}) {
  const { silent = false, ...requestOptions } = options;
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE}${cleanEndpoint}`;
  const headers = {
    'Accept': 'application/json',
    ...(requestOptions.body && !(requestOptions.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
    ...requestOptions.headers,
  };

  try {
    const res = await fetch(url, {
      ...requestOptions,
      headers,
      credentials: 'include', // Sends & receives mill_session cookie
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
    if (!silent) {
      console.error(`[API Error] ${requestOptions.method || 'GET'} ${url}:`, err);
    }
    throw err;
  }
}

// Typed generic CRUD helpers
export const apiClient = {
  async getList(resource, params = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        searchParams.append(k, String(v));
      }
    });
    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return apiRequest(`/${resource}${query}`);
  },

  async getById(resource, id) {
    return apiRequest(`/${resource}/${id}`);
  },

  async create(resource, data) {
    return apiRequest(`/${resource}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async update(resource, id, data) {
    return apiRequest(`/${resource}/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async remove(resource, id) {
    return apiRequest(`/${resource}/${id}`, {
      method: 'DELETE',
    });
  },
};

export const MillAPI = {
  // Generic CRUD pass-through
  getList: apiClient.getList,
  getById: apiClient.getById,
  create: apiClient.create,
  update: apiClient.update,
  remove: apiClient.remove,

  // --- Meta & Health ---
  async checkHealth() {
    try {
      const res = await apiRequest('/health');
      return { online: res?.status === 'ok', app: res?.app || 'Khadira' };
    } catch {
      return { online: false, app: 'Offline' };
    }
  },

  // --- Auth ---
  async login(username, password) {
    return apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  },

  async logout() {
    return apiRequest('/auth/logout', {
      method: 'POST',
    });
  },

  async getMe() {
    // A missing session is normal on first load, so avoid a misleading console error.
    return apiRequest('/auth/me', { silent: true });
  },

  // --- Dashboard Metrics ---
  async getDashboard() {
    return apiRequest('/dashboard');
  },

  // --- Inventory & Items ---
  async getItems(itemType = null, q = '') {
    const params = {};
    if (itemType) params.item_type = itemType;
    if (q) params.q = q;
    return apiClient.getList('items', params);
  },

  async createItem(itemData) {
    return apiClient.create('items', itemData);
  },

  async updateItem(itemId, itemData) {
    return apiClient.update('items', itemId, itemData);
  },

  // --- Machine Telemetry ---
  async getMachines() {
    return apiRequest('/machines');
  },

  async createMachine(code, name, machineType) {
    return apiRequest('/machines', {
      method: 'POST',
      body: JSON.stringify({ code, name, machine_type: machineType }),
    });
  },

  // --- Sales Orders ---
  async getOrders(status = null, q = '') {
    const params = {};
    if (status) params.status = status;
    if (q) params.q = q;
    return apiClient.getList('orders', params);
  },

  async createOrder(orderData) {
    return apiClient.create('orders', orderData);
  },

  async confirmOrder(orderId) {
    return apiRequest(`/orders/${orderId}/confirm`, {
      method: 'POST',
    });
  },

  async cancelOrder(orderId) {
    return apiRequest(`/orders/${orderId}/cancel`, {
      method: 'POST',
    });
  },

  // --- Production Runs & Looms ---
  async getProductionRuns(status = null) {
    const params = status ? { status } : {};
    return apiClient.getList('production', params);
  },

  async startProductionRun(machineId, itemId, orderId = null) {
    return apiRequest('/production', {
      method: 'POST',
      body: JSON.stringify({ machine_id: machineId, item_id: itemId, order_id: orderId }),
    });
  },

  async advanceProduction(runId, yarnKg = null) {
    return apiRequest(`/production/${runId}/advance`, {
      method: 'POST',
      body: JSON.stringify({ yarn_kg: yarnKg }),
    });
  },

  // --- Fabric Rolls & Quality Control ---
  async getRolls(status = null) {
    const params = status ? { status } : {};
    return apiClient.getList('rolls', params);
  },

  async getPendingQC() {
    return apiRequest('/qc/pending');
  },

  async inspectRoll(rollId, verdict, grade = 'A', note = '') {
    return apiRequest(`/rolls/${rollId}/inspect`, {
      method: 'POST',
      body: JSON.stringify({ verdict, grade, note }),
    });
  },

  async moveRollToStore(rollId) {
    return apiRequest(`/rolls/${rollId}/store`, {
      method: 'POST',
    });
  },

  // --- QC Defects ---
  async reportDefect(rollId, defectType, severity, locationM, notes) {
    return apiRequest(`/qc/defects`, {
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
    return apiRequest(`/qc/defects/${rollId}`);
  },

  // --- Production Downtime ---
  async reportDowntime(machineId, runId, reason, description) {
    return apiRequest(`/production/downtime`, {
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
    return apiRequest(`/production/${runId}/finalize`, {
      method: 'POST',
      body: JSON.stringify(reconciliationData),
    });
  },

  // --- Finance & Invoices ---
  async getInvoices(invType = null) {
    return apiRequest(`/finance/invoices${invType ? `?inv_type=${invType}` : ''}`);
  },

  async payInvoice(invId, amountPaise, method = 'bank') {
    return apiRequest(`/finance/invoices/${invId}/pay`, {
      method: 'POST',
      body: JSON.stringify({ amount_paise: amountPaise, method }),
    });
  },

  // --- Purchasing & POs ---
  async getPurchasing() {
    return apiRequest('/purchasing');
  },

  async createPO(poData) {
    return apiRequest('/purchasing', {
      method: 'POST',
      body: JSON.stringify(poData),
    });
  },

  async confirmPO(poId) {
    return apiRequest(`/purchasing/${poId}/confirm`, {
      method: 'POST',
    });
  },

  async cancelPO(poId) {
    return apiRequest(`/purchasing/${poId}/cancel`, {
      method: 'POST',
    });
  },

  async receivePOYarn(poId, receiptData) {
    return apiRequest(`/purchasing/${poId}/receive`, {
      method: 'POST',
      body: JSON.stringify(receiptData),
    });
  },

  // --- Partners ---
  async getSuppliers(q = '') {
    return apiClient.getList('partners/suppliers', { q });
  },

  async createSupplier(data) {
    return apiRequest('/partners/suppliers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getBuyers(q = '') {
    return apiClient.getList('partners/buyers', { q });
  },

  async createBuyer(data) {
    return apiRequest('/partners/buyers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // --- Settings ---
  async getSettings() {
    return apiRequest('/settings');
  },

  // --- Notifications ---
  async getNotifications(unreadOnly = false) {
    const query = unreadOnly ? '?unread_only=true' : '';
    return apiRequest(`/notifications${query}`);
  },

  async markNotificationRead(id) {
    return apiRequest(`/notifications/${id}/read`, {
      method: 'POST',
    });
  },

  async markAllNotificationsRead() {
    return apiRequest('/notifications/read-all', {
      method: 'POST',
    });
  },

  // --- Workforce & Attendance ---
  async getWorkers() {
    return apiRequest('/attendance/workers');
  },

  async createWorker(data) {
    return apiRequest('/attendance/workers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getAttendance(params = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        searchParams.append(k, String(v));
      }
    });
    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return apiRequest(`/attendance${query}`);
  },

  async recordAttendance(data) {
    return apiRequest('/attendance', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async approveAttendance(entryId) {
    return apiRequest(`/attendance/${entryId}/approve`, {
      method: 'POST',
    });
  },

  // --- Wages ---
  async getWageRuns() {
    return apiRequest('/wages');
  },

  async calculateWages(period) {
    return apiRequest('/wages/calculate', {
      method: 'POST',
      body: JSON.stringify(period),
    });
  },

  async finaliseWages(runId) {
    return apiRequest(`/wages/${runId}/finalise`, {
      method: 'POST',
    });
  },

  // --- Order Costing ---
  async getOrderCost(orderId) {
    return apiRequest(`/costing/orders/${orderId}`);
  },

  async calculateOrderCost(orderId) {
    return apiRequest(`/costing/orders/${orderId}/calculate`, {
      method: 'POST',
    });
  },
};

export default MillAPI;
