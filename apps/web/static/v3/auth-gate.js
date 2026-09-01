(function () {
  const apiBase = window.LUMINIFERA_API_BASE || "";
  const gate = document.querySelector("#auth-gate");
  if (!gate) return;
  const $ = id => document.querySelector(id);
  let mode = "login";
  let initialized = false;
  async function request(path, options = {}) {
    const response = await fetch(`${apiBase}${path}`, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { const error = new Error(data.detail || `HTTP ${response.status}`); error.status = response.status; throw error; }
    return data;
  }
  function errorText(error) {
    const messages = { registration_disabled: "Регистрация сейчас отключена владельцем.", invalid_credentials_or_blocked_account: "Профиль недоступен или введены неверные данные.", login_rate_limited: "Слишком много попыток. Повторите позже.", owner_bootstrap_closed: "Первый профиль уже создан.", session_invalid_or_revoked: "Сессия завершена. Войдите снова.", session_expired: "Срок сессии истёк. Войдите снова.", account_already_exists: "Такой идентификатор уже занят.", last_owner_protected: "Нельзя понизить последнего владельца." };
    return messages[error.message] || "Не удалось выполнить действие. Проверьте данные и повторите.";
  }
  function setMode(next) {
    mode = next;
    const bootstrap = mode === "bootstrap", register = mode === "register", change = mode === "password";
    $("#auth-title").textContent = bootstrap ? "Откройте своё рабочее пространство" : register ? "Создайте профиль Luminifera" : change ? "Обновите пароль профиля" : "Войдите в своё рабочее пространство";
    $("#auth-subtitle").textContent = bootstrap ? "Это одноразовая настройка первого владельца. Данные останутся только в вашем профиле." : register ? "После регистрации Iris встретит вас и поможет начать работу." : "Ваши команды, цели и проверенные результаты сохранены в профиле.";
    $("#auth-name-label").hidden = !(bootstrap || register); $("#auth-language-label").hidden = !(bootstrap || register); $("#auth-account-label").hidden = change;
    $("#auth-submit").textContent = bootstrap ? "Создать профиль владельца" : register ? "Создать аккаунт" : change ? "Сохранить пароль" : "Войти";
    $("#auth-alt").hidden = change; $("#auth-alt").textContent = mode === "login" ? "Создать аккаунт" : "Уже есть профиль? Войти"; $("#auth-password").autocomplete = change ? "new-password" : "current-password"; $("#auth-error").hidden = true;
  }
  function ready() { gate.classList.add("auth-ready"); document.body.classList.remove("auth-gate-pending"); }
  function showAccount() { gate.classList.remove("auth-ready"); $("#auth-logout").hidden = false; $("#auth-password-change").hidden = false; setMode("password"); }
  async function open() {
    const token = localStorage.getItem("luminifera.authToken");
    if (token) { try { await request("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } }); ready(); return; } catch (_) { localStorage.removeItem("luminifera.authToken"); } }
    try { const security = await request("/api/admin/security", { headers: { "X-Admin-Role": "owner" } }); setMode(security.owner_bootstrap === "available for fresh install" ? "bootstrap" : "login"); initialized = true; } catch (_) { setMode("login"); initialized = true; }
  }
  $("#auth-alt").onclick = () => { if (initialized) setMode(mode === "login" ? "register" : "login"); }; $("#auth-password-change").onclick = () => { if (initialized) setMode("password"); };
  $("#profile-button")?.addEventListener("click", event => { event.preventDefault(); showAccount(); });
  $("#auth-logout").onclick = async () => { try { await request("/api/auth/logout", { method: "POST", headers: { Authorization: `Bearer ${localStorage.getItem("luminifera.authToken")}` } }); } catch (_) {} localStorage.removeItem("luminifera.authToken"); $("#auth-logout").hidden = true; $("#auth-password-change").hidden = true; setMode("login"); $("#auth-status").textContent = "Вы вышли из профиля."; };
  $("#auth-form").onsubmit = async event => {
    event.preventDefault(); if (!initialized) return; const error = $("#auth-error"); error.hidden = true; const payload = { account_id: $("#auth-account").value.trim(), password: $("#auth-password").value };
    if (mode === "bootstrap" || mode === "register") { payload.display_name = $("#auth-name").value.trim(); payload.language = $("#auth-language").value; }
    try {
      let result;
      if (mode === "bootstrap") result = await request("/api/auth/bootstrap", { method: "POST", body: JSON.stringify(payload) });
      else if (mode === "register") { await request("/api/auth/register", { method: "POST", body: JSON.stringify(payload) }); setMode("login"); $("#auth-account").value = payload.account_id; $("#auth-status").textContent = "Профиль создан. Войдите, чтобы продолжить."; return; }
      else if (mode === "password") { await request("/api/auth/password", { method: "PUT", headers: { Authorization: `Bearer ${localStorage.getItem("luminifera.authToken")}` }, body: JSON.stringify({ password: payload.password }) }); localStorage.removeItem("luminifera.authToken"); setMode("login"); $("#auth-status").textContent = "Пароль изменён. Войдите снова."; return; }
      else result = await request("/api/auth/login", { method: "POST", body: JSON.stringify(payload) });
      if (result.token) localStorage.setItem("luminifera.authToken", result.token); ready();
    } catch (err) { error.textContent = errorText(err); error.hidden = false; }
  };
  open();
})();
