(function () {
  "use strict";
  const params = new URLSearchParams(location.search);
  if (params.get("advanced") !== "providers") return;
  const bridge = window.LuminiferaBridge;
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[c]));
  const label = value => ({Ready:"Готов", "Login required":"Нужна авторизация", Unavailable:"Недоступен", Busy:"Занят", Error:"Ошибка"})[value] || value || "Не проверен";
  const dialog = document.createElement("dialog");
  dialog.className = "provider-hub-dialog";
  dialog.innerHTML = '<form method="dialog" class="provider-hub"><button class="provider-hub-close" value="cancel" aria-label="Закрыть">×</button><span class="eyebrow">РАСШИРЕННЫЕ ПОДКЛЮЧЕНИЯ</span><h2>Подключения Iris</h2><p class="provider-hub-note">Ключи хранятся только в защищённом хранилище. Значения ключей никогда не показываются.</p><div class="provider-hub-list" id="provider-hub-list"><p>Загружаем состояние подключений…</p></div><small id="provider-hub-status"></small></form>';
  const list = dialog.querySelector("#provider-hub-list"), status = dialog.querySelector("#provider-hub-status");
  const render = async () => {
    try {
      const state = await bridge.getSettingsState(), settings = state.settings || {}, providers = state.providers || [];
      list.innerHTML = providers.length ? providers.map(provider => `<article class="provider-hub-row"><div><strong>${esc(provider.name)}</strong><small>${esc(label(provider.state))}${provider.model_id ? ` · ${esc(provider.model_id)}` : ""}</small></div><span class="provider-hub-state ${provider.available ? "ready" : ""}">${provider.available ? "Готов" : "Не подключён"}</span><input type="password" data-provider-key="${esc(provider.id)}" placeholder="Новый ключ доступа" autocomplete="off"><div class="provider-hub-actions"><button type="button" class="ghost" data-provider-connect="${esc(provider.id)}">Сохранить ключ</button><button type="button" class="ghost" data-provider-check="${esc(provider.id)}">Проверить</button><button type="button" class="ghost" data-provider-remove="${esc(provider.id)}">Удалить ключ</button></div></article>`).join("") : "<p>Поддерживаемых подключений пока нет.</p>";
      list.insertAdjacentHTML("beforeend", `<label class="provider-hub-active">Активное подключение<select id="provider-hub-active">${providers.map(p => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join("")}</select></label><label class="provider-hub-active">Модель<input id="provider-hub-model" maxlength="160" placeholder="Модель провайдера"></label><button type="button" class="primary" id="provider-hub-save-active">Сохранить выбор</button>`);
      const active = list.querySelector("#provider-hub-active"), model = list.querySelector("#provider-hub-model");
      if (settings.active_provider_id) active.value = settings.active_provider_id;
      model.value = settings.active_model_id || providers.find(p => p.id === active.value)?.model_id || "";
      list.querySelectorAll("[data-provider-connect]").forEach(button => button.onclick = async () => { const input = list.querySelector(`[data-provider-key="${CSS.escape(button.dataset.providerConnect)}"]`); if (!input.value.trim()) { status.textContent = "Введите ключ доступа."; return; } button.disabled = true; try { await bridge.connectProvider(button.dataset.providerConnect, input.value.trim()); input.value = ""; status.textContent = "Ключ сохранён. Проверка выполнена через Core."; await render(); } catch (error) { status.textContent = "Не удалось сохранить ключ."; } finally { button.disabled = false; } });
      list.querySelectorAll("[data-provider-check]").forEach(button => button.onclick = async () => { button.disabled = true; try { const result = await bridge.checkProvider(button.dataset.providerCheck); status.textContent = `${esc(result.state || "Проверка завершена")}.`; await render(); } catch (error) { status.textContent = "Проверка подключения не выполнена."; } finally { button.disabled = false; } });
      list.querySelectorAll("[data-provider-remove]").forEach(button => button.onclick = async () => { button.disabled = true; try { await bridge.disconnectProvider(button.dataset.providerRemove); status.textContent = "Подключение удалено."; await render(); } catch (error) { status.textContent = "Не удалось удалить подключение."; } finally { button.disabled = false; } });
      list.querySelector("#provider-hub-save-active").onclick = async () => { try { const saved = await bridge.saveSettings({active_provider_id: active.value, active_model_id: model.value.trim()}); status.textContent = `Активно: ${saved.active_provider_id || "не выбрано"}.`; } catch (error) { status.textContent = "Не удалось сохранить выбор."; } };
    } catch (error) { list.innerHTML = "<p>Состояние подключений недоступно.</p>"; status.textContent = "Проверьте связь с Core."; }
  };
  document.body.append(dialog);
  render().then(() => dialog.showModal());
})();
