(function () {
  const bridge = window.LuminiferaBridge;
  const cfg = window.LUMINIFERA_UI_CONFIG || {};
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;", "'":"&#039;"}[c]));
  const screens = [...document.querySelectorAll(".screen")];
  let current = location.hash.slice(1) || "home";
  let messages = [];
  const diagnosticsEnabled = new URLSearchParams(location.search).get("diagnostics") === "1";

  function media(container, value, label) {
    container.innerHTML = "";
    if (!value || value.type === "none" || !value.src) return;
    const fallback = () => {
      container.innerHTML = "";
      if (!value.poster || value.poster === value.src) return;
      const poster = document.createElement("img");
      poster.src = value.poster; poster.alt = label;
      poster.addEventListener("error", () => { container.innerHTML = ""; }, { once: true });
      container.append(poster);
    };
    if (value.type === "video") {
      const video = document.createElement("video"); video.src = value.src; video.poster = value.poster || "";
      video.autoplay = value.autoplay !== false; video.loop = value.loop !== false; video.muted = value.muted !== false; video.playsInline = true; video.setAttribute("aria-label", label); container.append(video);
      video.addEventListener("error", fallback, { once: true });
    } else { const image = document.createElement("img"); image.src = value.src; image.alt = label; image.addEventListener("error", fallback, { once: true }); container.append(image); }
  }
  function applyConfig() {
    const branding = cfg.branding || {};
    $("#brand-name").textContent = branding.productName || "Luminifera";
    $("#brand-subtitle").textContent = branding.subtitle || "AI operating space";
    media($("#background-media"), cfg.background, "Luminifera background");
    media($("#iris-media"), cfg.iris, "Iris");
    const overlay = Number(cfg.background?.overlay); if (Number.isFinite(overlay)) $(".background-overlay").style.opacity = String(Math.max(0, Math.min(1, overlay)));
    if (cfg.ui?.reducedMotion) document.documentElement.classList.add("reduced-motion");
  }
  function route(name) { current = screens.some(s => s.dataset.screen === name) ? name : "home"; screens.forEach(s => s.classList.toggle("active", s.dataset.screen === current)); document.querySelectorAll(".nav button").forEach(b => b.classList.toggle("active", b.dataset.route === current)); history.replaceState(null, "", current === "home" ? "#home" : `#${current}`); render(current); }
  function status(text) { return `<span class="bridge-state"><i class="ready"></i><span>${esc(text)}</span></span>`; }
  function messageMarkup(item) { return `<div class="message ${item.role === "owner" ? "user" : "iris"}"><b>${item.role === "owner" ? "Вы" : "Iris"}</b><div>${esc(item.content)}</div></div>`; }
  function renderChat() { const empty = $("#iris-empty"), chat = $("#iris-chat"); const visibleMessages = messages.filter((item, index, list) => index === 0 || item.role !== list[index - 1].role || item.content !== list[index - 1].content); chat.innerHTML = visibleMessages.map(messageMarkup).join(""); chat.hidden = visibleMessages.length === 0; empty.hidden = visibleMessages.length > 0; chat.scrollTop = chat.scrollHeight; }
  function setSystem(title, subtitle) { $("#system-strip-title").textContent = title; $("#system-strip-subtitle").textContent = subtitle; }
  function emptyStage(icon, title, copy, action = "") { return `<div class="empty-copy"><span class="big-sigil">${icon}</span><h3>${title}</h3><p>${copy}</p>${action}</div>`; }
  function renderTeamState(state) {
    const members = state.members || [], stage = $("#team-stage");
    if (!members.length) { stage.innerHTML = emptyStage("✦", "Команда ещё не собрана", "Здесь появятся реальные сотрудники и их роли после создания команды через Iris.", '<button class="ghost" id="team-empty-action">Попросить Iris собрать команду</button>'); $("#team-empty-action").onclick = () => { route("home"); $("#iris-input").value = "Собери мне команду"; $("#iris-input").focus(); }; return; }
    stage.innerHTML = `<div class="constellation-board"><div class="constellation-orbit orbit-one"></div><div class="constellation-orbit orbit-two"></div><div class="constellation-core">✦<small>команда</small></div>${members.map((member, index) => { const angle = (index / Math.max(members.length, 1)) * Math.PI * 2 - Math.PI / 2; const radius = members.length > 5 ? 35 : 30; const x = 50 + Math.cos(angle) * radius; const y = 50 + Math.sin(angle) * radius; return `<article class="constellation-node" style="--node-x:${x}%;--node-y:${y}%;--node-delay:${index * 180}ms"><div class="member-avatar">${esc((member.display_name || "С").slice(0, 1))}</div><div><strong>${esc(member.display_name || "Сотрудник")}</strong><small>${esc(member.primary_role || "Участник команды")}</small></div><span class="node-status">${esc(member.lifecycle_state || "Активен")}</span></article>`; }).join("")}</div>`;
  }
  function renderWorkState(state) {
    const goals = state.goals || [], work = state.work || {}, stage = $("#work-stage");
    if (!goals.length && !work.goal_title) { stage.innerHTML = emptyStage("◇", "Активной работы пока нет", "Опишите Iris результат, который нужно получить.", '<button class="ghost" id="work-empty-action">Сформулировать цель</button>'); $("#work-empty-action").onclick = () => { route("home"); $("#iris-input").focus(); }; return; }
    const progress = Math.max(0, Math.min(100, Number(work.goal_progress || 0)));
    const actionFor = status => {
      const normalized = String(status || "").toUpperCase();
      if (["COMPLETED", "CANCELLED", "BLOCKED"].includes(normalized)) return [];
      if (["AWAITING_OWNER_APPROVAL", "READY"].includes(normalized)) return [["approve", "Одобрить"], ["start", "Запустить"]];
      return [["replan", "Перепланировать"], ["cancel", "Отменить"]];
    };
    stage.innerHTML = `<div class="data-stage"><div class="work-summary"><span class="eyebrow">АКТИВНЫЙ ФОКУС</span><h3>${esc(work.goal_title || "Цель")}</h3><p>${esc(work.goal_state || "В работе")}</p><div class="work-progress"><i style="width:${progress}%"></i></div><b>${progress}%</b></div><div class="goal-list">${goals.map(goal => `<article class="goal-row"><div><strong>${esc(goal.goal || "Цель")}</strong><small>${esc(goal.status || "Создана")}</small></div><span class="goal-actions">${actionFor(goal.status).map(([action, label]) => `<button class="ghost" data-goal-action="${action}" data-plan-id="${esc(goal.plan_id)}">${label}</button>`).join("")}</span></article>`).join("")}</div>${(state.items || []).length ? `<div class="work-details"><span class="eyebrow">РАБОЧИЕ ШАГИ</span>${state.items.map(item => `<div><strong>${esc(item.title)}</strong><small>${esc(item.assignee)} · ${esc(item.status)}</small></div>`).join("")}</div>` : ""}</div>`;
    stage.querySelectorAll("[data-goal-action]").forEach(button => button.onclick = async () => { button.disabled = true; const action = button.dataset.goalAction; button.textContent = "Выполняется"; try { if (action === "approve") await bridge.approveGoal(button.dataset.planId); else if (action === "start") await bridge.startGoal(button.dataset.planId); else if (action === "replan") await bridge.replanGoal(button.dataset.planId); else await bridge.cancelGoal(button.dataset.planId); await renderWork(); } catch (error) { button.disabled = false; button.textContent = "Повторить"; setSystem("Не удалось выполнить действие", "Движок вернул ошибку. Повторите попытку."); } });
  }
  function renderFilesState(state) {
    const files = state.artifacts || [], stage = $("#files-stage");
    if (!files.length) { stage.innerHTML = emptyStage("▱", "Результатов пока нет", "Проверенные artifacts появятся здесь после завершения реальной работы."); return; }
    stage.innerHTML = `<div class="file-list">${files.map(file => `<article class="file-row"><span class="file-icon">▱</span><div><strong>${esc(file.title || "Результат")}</strong><small>${esc(file.artifact_type || "Артефакт")} · ${esc(file.review_status || file.status || "Проверяется")}</small></div>${file.artifact_id ? `<button class="ghost" data-preview-file="${esc(file.artifact_id)}">Открыть</button>` : ""}</article>`).join("")}</div>`;
    stage.querySelectorAll("[data-preview-file]").forEach(button => button.onclick = async () => { button.disabled = true; try { const preview = await bridge.previewFile(button.dataset.previewFile); const dialog = $("#file-dialog"); $("#file-dialog-title").textContent = preview.title || "Результат"; $("#file-dialog-content").textContent = preview.preview || "Файл доступен для скачивания."; dialog.showModal(); } catch (error) { setSystem("Не удалось открыть результат", "Файл недоступен в текущем рабочем пространстве."); } finally { button.disabled = false; } });
  }
  async function renderHome() { const state = await bridge.getHomeState(); const org = state.organization?.name || "Не настроено"; $("#org-summary").textContent = org; $("#team-summary").textContent = state.team?.count != null ? `${state.team.count} сотрудников` : "Нет данных"; $("#work-summary").textContent = state.work?.activeGoal || "Нет активной работы"; $("#files-summary").textContent = state.files?.count != null ? `${state.files.count} результатов` : "Результатов пока нет"; messages = state.messages || []; renderChat(); setSystem(state.message || "Состояние синхронизировано", bridge.connected ? "Данные получены из движка." : "Bridge не подключён."); }
  async function renderIris() { const state = await bridge.getHomeState(); messages = state.messages || []; renderChat(); }
  async function renderTeam() { renderTeamState(await bridge.getTeamState()); }
  async function renderWork() { renderWorkState(await bridge.getWorkState()); }
  async function renderFiles() { renderFilesState(await bridge.getFilesState()); }
  async function renderSettings() { const state = await bridge.getSettingsState(), settings = state.settings || {}; $("#settings-stage").innerHTML = `<div class="settings-grid"><article class="settings-card"><span class="eyebrow">ПРОСТРАНСТВО</span><h3>Настройки</h3><label>Язык интерфейса<select id="setting-language"><option value="ru">Русский</option><option value="uk">Українська</option><option value="en">English</option></select></label><label>Тема<select id="setting-theme"><option value="dark">Тёмная</option><option value="light">Светлая</option><option value="night_city">Ночной город</option></select></label><button class="primary" id="save-settings">Сохранить</button><small id="settings-status"></small></article><article class="settings-card"><span class="eyebrow">СИСТЕМА</span><h3>Всё готово к работе</h3>${status(bridge.connected ? "Связь с Luminifera активна" : "Связь недоступна")}<p>Состояние рабочего пространства.</p><button class="ghost" id="bridge-check">Проверить</button></article><article class="settings-card"><span class="eyebrow">ОБРАТНАЯ СВЯЗЬ</span><h3>Помочь Iris стать лучше</h3><form id="feedback-form"><label>Категория<select id="feedback-category"><option value="bug">Ошибка</option><option value="ux">Удобство</option><option value="feature">Идея</option></select></label><label>Сообщение<textarea id="feedback-description" required maxlength="10000"></textarea></label><button class="primary">Отправить</button></form><small id="feedback-status"></small></article></div>`; const themeValues = new Set(["dark", "light", "night_city"]); $("#setting-language").value = settings.interface_language || "ru"; $("#setting-theme").value = themeValues.has(settings.theme) ? settings.theme : "dark"; $("#save-settings").onclick = async () => { try { await bridge.saveSettings({ interface_language: $("#setting-language").value, theme: $("#setting-theme").value }); $("#settings-status").textContent = "Настройки сохранены"; } catch (error) { $("#settings-status").textContent = "Не удалось сохранить настройки"; } }; $("#bridge-check").onclick = async () => { const button = $("#bridge-check"); button.disabled = true; try { const health = await bridge.checkHealth(); setSystem("Соединение подтверждено", `Luminifera Core: ${health.status || "готов"}`); } catch (error) { setSystem("Связь недоступна", "Core не ответил на проверку."); } finally { button.disabled = false; } }; $("#feedback-form").onsubmit = async event => { event.preventDefault(); try { await bridge.submitFeedback($("#feedback-category").value, $("#feedback-description").value.trim()); $("#feedback-description").value = ""; $("#feedback-status").textContent = "Отзыв передан Iris"; } catch (error) { $("#feedback-status").textContent = "Не удалось передать отзыв"; } }; }
  function diagnosticStatus(value) { if (value.status === null) return "не настроено"; return value.ok ? `доступен (${value.status})` : `ошибка (${value.status || "нет ответа"})`; }
  async function renderDiagnostics() {
    if (!diagnosticsEnabled || !$("#diagnostic-panel")) return;
    document.body.classList.add("diagnostics-mode"); $("#diagnostic-panel").hidden = false;
    try {
      const state = await bridge.getDiagnostics(cfg);
      const checkRows = Object.entries(state.checks).map(([name, value]) => `<div class="diagnostic-row"><span>${name}</span><b class="${value.ok ? "ok" : "bad"}">${diagnosticStatus(value)}</b></div>`).join("");
      const mediaRows = Object.entries(state.media).map(([name, value]) => `<div class="diagnostic-row"><span>${name}</span><b>${esc(value.type)} · ${esc(value.source || "не задан")}</b></div>`).join("");
      $("#diagnostic-content").innerHTML = `<div class="diagnostic-group"><h3>Соединение</h3><div class="diagnostic-row"><span>Application API</span><b class="${state.api.ok ? "ok" : "bad"}">${diagnosticStatus(state.api)}</b></div><div class="diagnostic-row"><span>Организация</span><b>${esc(state.organization.name || "не выбрана")}</b></div></div><div class="diagnostic-group"><h3>Продуктовые сервисы</h3>${checkRows}</div><div class="diagnostic-group"><h3>Media config</h3>${mediaRows}</div>`;
      $("#diagnostic-time").textContent = new Date().toLocaleTimeString();
    } catch (error) { $("#diagnostic-content").innerHTML = `<div class="diagnostic-group"><h3>Диагностика недоступна</h3><p>Не удалось получить состояние через Application API.</p></div>`; }
  }
  async function render(name) { try { if (name === "home" || name === "iris") await renderHome(); else if (name === "team") await renderTeam(); else if (name === "work") await renderWork(); else if (name === "files") await renderFiles(); else if (name === "settings") await renderSettings(); } catch (error) { setSystem("Не удалось получить данные", "Проверьте соединение с Luminifera Core."); } }
  async function loadOrganizations(preferredId = null) { const organizations = await bridge.getOrganizations(); const select = $("#workspace-select"); select.innerHTML = '<option value="">Рабочее пространство</option>' + organizations.map(org => `<option value="${esc(org.id)}">${esc(org.name)}</option>`).join(""); const selected = organizations.find(org => org.id === preferredId) || organizations.find(org => org.id === bridge.getOrganizationId()) || organizations[0]; if (selected) { bridge.setOrganization(selected.id); select.value = selected.id; await render(current); } else bridge.setOrganization(null); }
  document.querySelectorAll("[data-route]").forEach(button => button.onclick = () => route(button.dataset.route));
  function focusIris(prompt = "") { route("home"); if (prompt) $("#iris-input").value = prompt; $("#iris-input").focus(); }
  $("#focus-iris").onclick = () => focusIris(); $("#hero-iris").onclick = () => focusIris(); $("#profile-button").onclick = () => route("settings");
  document.querySelectorAll("[data-prompt]").forEach(button => button.onclick = () => focusIris(button.dataset.prompt));
  $("#iris-form").onsubmit = async event => { event.preventDefault(); const text = $("#iris-input").value.trim(); if (!text) return; $("#iris-input").value = ""; const item = { role: "owner", content: text }; messages.push(item); renderChat(); try { const result = await bridge.chat(text); messages.push({ role: "assistant", content: result.text || "Ответ от Iris не получен." }); renderChat(); if (result.action === "create_organization" && result.data?.organization_id) await loadOrganizations(result.data.organization_id); } catch (error) { messages.push({ role: "assistant", content: "Не удалось связаться с движком." }); renderChat(); } };
  $("#refresh-home").onclick = () => renderHome().catch(() => setSystem("Движок временно недоступен", "Проверьте подключение и повторите действие.")); $("#refresh-files").onclick = () => renderFiles().catch(() => setSystem("Не удалось загрузить файлы", "Проверьте подключение и повторите действие.")); $("#preview-media").onclick = () => location.reload(); $("#team-create").onclick = () => focusIris("Собери мне команду"); $("#new-goal").onclick = () => focusIris("Создай новую цель"); $("#workspace-select").onchange = async event => { bridge.setOrganization(event.target.value); await render(current); }; $("#workspace-new").onclick = () => $("#org-dialog").showModal(); $("#org-dialog button[aria-label]").onclick = event => { event.preventDefault(); $("#org-dialog").close(); }; $("#org-form").onsubmit = async event => { event.preventDefault(); const org = await bridge.createOrganization($("#org-name").value.trim(), $("#org-purpose").value.trim()); $("#org-dialog").close(); await loadOrganizations(); bridge.setOrganization(org.organization_id); $("#workspace-select").value = org.organization_id; await render(current); };
  applyConfig(); updateBridgeState(); loadOrganizations().then(renderDiagnostics).catch(() => setSystem("Движок временно недоступен", "Проверьте подключение и повторите действие."));
  function updateBridgeState() { const dot = $("#bridge-dot"); if (dot) dot.classList.toggle("ready", !!bridge.connected); if ($("#bridge-title")) $("#bridge-title").textContent = bridge.connected ? "Bridge подключён" : "Bridge не подключён"; }
})();
