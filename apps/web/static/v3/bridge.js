(function () {
  const apiBase = window.LUMINIFERA_API_BASE || "";
  let organizationId = localStorage.getItem("luminifera.organizationId") || null;
  const request = async (path, options = {}) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(`${apiBase}${path}`, {
        ...options,
        signal: controller.signal,
        headers: { "Content-Type": "application/json", ...(organizationId ? { "X-Organization-Id": organizationId } : {}), ...(options.headers || {}) },
      });
      if (!response.ok) throw new Error((await response.text()) || `HTTP ${response.status}`);
      return response.json();
    } finally { clearTimeout(timeout); }
  };
  const unwrap = value => value && Array.isArray(value.value) ? value.value : value;
  window.LuminiferaBridge = {
    connected: true,
    setOrganization(id) { organizationId = id || null; if (organizationId) localStorage.setItem("luminifera.organizationId", organizationId); else localStorage.removeItem("luminifera.organizationId"); },
    getOrganizationId() { return organizationId; },
    async getOrganizations() { return unwrap(await request("/api/organizations")); },
    async createOrganization(name, purpose) { return request("/api/organizations", { method: "POST", body: JSON.stringify({ name, purpose }) }); },
    async getHomeState() {
      if (!organizationId) return { organization: null, team: null, work: null, files: null, message: "Создайте рабочее пространство" };
      const [home, filesPayload, messagesPayload] = await Promise.all([request(`/api/organizations/${encodeURIComponent(organizationId)}/home`), request("/api/files"), request("/api/chat")]);
      const files = unwrap(filesPayload) || [], messages = unwrap(messagesPayload) || [];
      return { organization: { name: home.organization_name }, team: { count: home.team_size || 0 }, work: { activeGoal: home.goal_title || null, state: home.goal_state, progress: home.goal_progress || 0 }, files: { count: files.length }, messages };
    },
    async getTeamState() { return { members: organizationId ? (unwrap(await request(`/api/organizations/${encodeURIComponent(organizationId)}/employees`)) || []) : [] }; },
    async getWorkState() { return { work: organizationId ? await request("/api/work") : null, goals: organizationId ? (unwrap(await request("/api/goals")) || []) : [] }; },
    async getFilesState() { return { artifacts: organizationId ? (unwrap(await request("/api/files")) || []) : [] }; },
    async getSettingsState() { return { settings: await request("/api/settings"), providers: unwrap(await request("/api/providers")) || [], feedback: unwrap(await request("/api/feedback")) || [] }; },
    async getDiagnostics(config = {}) {
      const probe = async path => {
        try {
          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), 5000);
          try {
            const response = await fetch(`${apiBase}${path}`, { signal: controller.signal, headers: organizationId ? { "X-Organization-Id": organizationId } : {} });
            return { ok: response.ok, status: response.status };
          } finally { clearTimeout(timeout); }
        } catch (error) { return { ok: false, status: 0 }; }
      };
      const organizations = unwrap(await request("/api/organizations")) || [];
      const current = organizations.find(item => item.id === organizationId);
      const checks = {
        iris: organizationId ? await probe("/api/chat") : { ok: false, status: null },
        team: organizationId ? await probe(`/api/organizations/${encodeURIComponent(organizationId)}/employees`) : { ok: false, status: null },
        work: organizationId ? await probe("/api/work") : { ok: false, status: null },
        files: organizationId ? await probe("/api/files") : { ok: false, status: null },
        feedback: organizationId ? await probe("/api/feedback") : { ok: false, status: null },
      };
      return {
        api: await probe("/api/health"),
        organization: { configured: !!current, name: current?.name || null },
        checks,
        media: {
          background: { type: config.background?.type || "none", source: config.background?.src || null },
          iris: { type: config.iris?.type || "none", source: config.iris?.src || null },
        },
      };
    },
    async chat(message) { const payload = await request("/api/chat", { method: "POST", body: JSON.stringify({ content: message }) }); return { ...payload.result, text: payload.result?.message || payload.result?.text || "Ответ от Iris не получен." }; },
    async createGoal(objective) { return request("/api/goals", { method: "POST", body: JSON.stringify({ objective }) }); },
    async startGoal(planId) { return request(`/api/goals/${encodeURIComponent(planId)}/start`, { method: "POST" }); },
    async saveSettings(settings) { return request("/api/settings", { method: "PATCH", body: JSON.stringify(settings) }); },
    async submitFeedback(category, description) { return request("/api/feedback", { method: "POST", body: JSON.stringify({ category, description }) }); },
    async refresh() { return this.getHomeState(); },
  };
})();
