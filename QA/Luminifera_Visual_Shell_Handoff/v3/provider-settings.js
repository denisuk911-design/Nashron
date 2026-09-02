(function () {
  "use strict";
  const bridge = window.LuminiferaBridge;
  const esc = value => String(value ?? "").replace(/[&<>\"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[char]));
  const supported = new Set(["GEMINI_CLI", "GEMINI_API", "OPENAI_API", "OPENROUTER_GATEWAY", "ANTHROPIC_API"]);
  const text = { title: "Подключения провайдеров", note: "Подключите AI-провайдера для ответов Iris. Ключ хранится защищённо и не показывается.", key: "Ключ доступа", save: "Сохранить ключ", check: "Проверить", remove: "Отключить", active: "Активное подключение", model: "Модель", choose: "Сохранить выбор", ready: "Готов", missing: "Не подключён", empty: "Доступные подключения не найдены." };
  function render() {
    const stage = document.querySelector('[data-screen="settings"] #settings-stage');
    if (!stage || stage.querySelector("#provider-panel")) return;
    bridge.getSettingsState().then(state => {
      if (!document.body.contains(stage) || stage.querySelector("#provider-panel")) return;
      const providers = (state.providers || []).filter(provider => supported.has(provider.id));
      const settings = state.settings || {};
      const rows = providers.map(provider => `<div class="provider-row"><div><strong>${esc(provider.name)}</strong><small>${esc(provider.model_id || "Модель не выбрана")}</small></div><span class="status-pill ${provider.available ? "ready" : ""}">${provider.available ? text.ready : text.missing}</span><input type="password" data-provider-key="${esc(provider.id)}" placeholder="${text.key}" autocomplete="off"><button class="quiet-button" data-provider-connect="${esc(provider.id)}">${text.save}</button><button class="quiet-button" data-provider-check="${esc(provider.id)}">${text.check}</button><button class="quiet-button" data-provider-remove="${esc(provider.id)}">${text.remove}</button></div>`).join("");
      const panel = document.createElement("article");
      panel.className = "settings-card provider-settings-card";
      panel.id = "provider-panel";
      panel.innerHTML = `<span class="eyebrow">AI</span><h3>${text.title}</h3><p>${text.note}</p><div class="provider-list">${rows || `<p>${text.empty}</p>`}</div><label>${text.active}<select id="active-provider">${providers.map(provider => `<option value="${esc(provider.id)}">${esc(provider.name)}</option>`).join("")}</select></label><label>${text.model}<input id="active-model" maxlength="160" placeholder="gemini-3.5-flash-lite"></label><button class="primary" id="save-provider-choice">${text.choose}</button><small id="provider-status"></small>`;
      stage.querySelector(".settings-grid")?.append(panel);
      const active = panel.querySelector("#active-provider");
      const model = panel.querySelector("#active-model");
      if (settings.active_provider_id) active.value = settings.active_provider_id;
      model.value = settings.active_model_id || providers.find(provider => provider.id === active.value)?.model_id || "";
      const status = panel.querySelector("#provider-status");
      panel.querySelectorAll("[data-provider-connect]").forEach(button => button.onclick = async () => { const input = panel.querySelector(`[data-provider-key="${CSS.escape(button.dataset.providerConnect)}"]`); if (!input.value.trim()) { status.textContent = text.key; return; } button.disabled = true; try { await bridge.connectProvider(button.dataset.providerConnect, input.value.trim()); input.value = ""; status.textContent = "Ключ сохранён. Состояние обновлено."; panel.remove(); render(); } catch (error) { status.textContent = "Не удалось сохранить ключ."; } finally { button.disabled = false; } });
      panel.querySelectorAll("[data-provider-check]").forEach(button => button.onclick = async () => { button.disabled = true; try { const result = await bridge.checkProvider(button.dataset.providerCheck); status.textContent = result.state || "Проверка завершена."; panel.remove(); render(); } catch (error) { status.textContent = "Проверка не выполнена."; } finally { button.disabled = false; } });
      panel.querySelectorAll("[data-provider-remove]").forEach(button => button.onclick = async () => { button.disabled = true; try { await bridge.disconnectProvider(button.dataset.providerRemove); status.textContent = "Подключение отключено."; panel.remove(); render(); } catch (error) { status.textContent = "Не удалось отключить подключение."; } finally { button.disabled = false; } });
      panel.querySelector("#save-provider-choice").onclick = async () => { try { await bridge.saveSettings({ active_provider_id: active.value, active_model_id: model.value.trim() }); status.textContent = "Подключение сохранено."; } catch (error) { status.textContent = "Не удалось сохранить выбор."; } };
    }).catch(() => {});
  }
  new MutationObserver(render).observe(document.body, { childList: true, subtree: true });
  render();
})();
