(() => {
  const escapeText = value => String(value ?? '').replace(/[&<>\"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#039;'}[char]));
  const attachFileActions = async () => {
    const title = document.querySelector('#view-title');
    const view = document.querySelector('#view');
    const select = document.querySelector('#org-select');
    if (!title || !view || !select?.value || title.textContent !== 'Файлы' || view.querySelector('.web-file-actions')) return;
    const response = await fetch('/api/files', {headers: {'X-Organization-Id': select.value}});
    if (!response.ok) return;
    const files = await response.json();
    const actionable = files.filter(file => file.artifact_id);
    if (!actionable.length) return;
    const panel = document.createElement('section');
    panel.className = 'web-file-actions magic-card';
    panel.style.marginTop = '14px';
    panel.innerHTML = `<span class="eyebrow">Результаты работы</span><div class="list">${actionable.map(file => `<div class="list-row"><span><b>${escapeText(file.title)}</b><br><small>${escapeText(file.source_goal || file.creator || 'Артефакт')}</small></span><span style="display:flex;gap:8px"><button class="ghost" data-preview="${escapeText(file.artifact_id)}">Открыть</button><a class="ghost" href="/api/files/${encodeURIComponent(file.artifact_id)}/download" download>Скачать</a></span></div>`).join('')}</div>`;
    view.append(panel);
    panel.querySelectorAll('[data-preview]').forEach(button => button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        const result = await fetch(`/api/files/${encodeURIComponent(button.dataset.preview)}/preview`, {headers: {'X-Organization-Id': select.value}}).then(item => item.json());
        const dialog = document.createElement('dialog');
        dialog.innerHTML = `<form method="dialog" style="padding:24px;max-width:min(760px,80vw)"><button class="dialog-close" value="cancel" aria-label="Закрыть">×</button><span class="eyebrow">Предпросмотр артефакта</span><h2>${escapeText(result.title)}</h2><pre style="white-space:pre-wrap;max-height:60vh;overflow:auto">${escapeText(result.preview || 'Предпросмотр недоступен для бинарного файла.')}</pre><button class="primary">Закрыть</button></form>`;
        document.body.append(dialog); dialog.showModal(); dialog.addEventListener('close', () => dialog.remove(), {once:true});
      } finally { button.disabled = false; }
    }));
  };
  new MutationObserver(() => { attachFileActions().catch(() => {}); }).observe(document.querySelector('#view'), {childList: true, subtree: true});
  document.querySelector('[data-view="files"]')?.addEventListener('click', () => setTimeout(() => attachFileActions().catch(() => {}), 50));
})();

(() => {
  const afterLoad = () => {
    const select = document.querySelector('#org-select');
    const contentHead = document.querySelector('.content-head');
    if (!select || !contentHead) return;
    const action = document.createElement('button');
    action.className = 'primary';
    action.textContent = 'Новая цель ↗';
    contentHead.append(action);
    const dialog = document.createElement('dialog');
    dialog.innerHTML = '<form method="dialog" style="padding:28px;display:grid;gap:14px"><button class="dialog-close" value="cancel" aria-label="Закрыть">×</button><span class="eyebrow">Цель</span><h2>Какой результат нужен?</h2><p>После создания Iris подготовит настоящий план. Запуск работы останется отдельным явным действием.</p><textarea required maxlength="10000" placeholder="Например: подготовить спецификацию продукта и проверить её"></textarea><button class="primary" value="default">Создать план</button><small class="goal-result" style="color:var(--muted)"></small></form>';
    document.body.append(dialog);
    const form = dialog.querySelector('form'); const textarea = dialog.querySelector('textarea'); const result = dialog.querySelector('.goal-result');
    action.onclick = () => { result.textContent = ''; textarea.value = ''; dialog.showModal(); textarea.focus(); };
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!select.value || !textarea.value.trim()) { result.textContent = 'Сначала выберите организацию и опишите результат.'; return; }
      result.textContent = 'Iris создаёт план через Core...';
      try {
        const response = await fetch('/api/goals', {method:'POST',headers:{'Content-Type':'application/json','X-Organization-Id':select.value},body:JSON.stringify({objective:textarea.value.trim()})});
        if (!response.ok) throw new Error(await response.text());
        const plan = await response.json();
        result.textContent = 'План создан. Откройте «Цели и работа», чтобы продолжить.';
        form.querySelector('.primary').disabled = true;
        form.querySelector('.primary').textContent = plan.status || 'Создано';
      } catch (error) { result.textContent = `Не удалось создать план: ${error.message}`; }
    });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', afterLoad); else afterLoad();
})();

(() => {
  const initProfileAndSettings = () => {
    const topActions = document.querySelector('.top-actions');
    const profileButton = topActions?.querySelector('.icon-button:not(.web-settings)');
    const settingsButton = document.querySelector('.web-settings');
    if (!topActions || !profileButton || !settingsButton || document.querySelector('.web-profile-dialog')) {
      if (!document.querySelector('.web-profile-dialog')) window.setTimeout(initProfileAndSettings, 100);
      return;
    }

    const profileDialog = document.createElement('dialog');
    profileDialog.className = 'web-profile-dialog';
    profileDialog.innerHTML = `<form method="dialog" class="web-profile-form"><button class="dialog-close" value="cancel" aria-label="Закрыть">×</button><span class="eyebrow">Профиль владельца</span><h2>Ваш профиль</h2><p class="settings-note">Эти данные относятся только к владельцу и не смешиваются с профилями сотрудников.</p><label>Имя<input name="display_name" required maxlength="120" placeholder="Как к вам обращаться"></label><label>Аватар<select name="avatar"><option value="">Без аватара</option></select></label><div class="profile-preview"><span class="avatar profile-avatar">В</span><span class="profile-avatar-name">Владелец</span></div><button class="primary" value="default">Сохранить профиль</button><small class="profile-result"></small></form>`;
    document.body.append(profileDialog);
    const profileForm = profileDialog.querySelector('form');
    const avatarSelect = profileForm.querySelector('[name="avatar"]');
    const preview = profileForm.querySelector('.profile-avatar');
    const previewName = profileForm.querySelector('.profile-avatar-name');
    const result = profileForm.querySelector('.profile-result');
    const avatarUrl = name => name ? `${window.LUMINIFERA_API_BASE || ''}/api/profile/avatars/${encodeURIComponent(name)}` : '';
    const refreshPreview = () => {
      const name = profileForm.display_name.value.trim() || 'Владелец';
      previewName.textContent = name;
      const src = avatarUrl(avatarSelect.value);
      preview.style.backgroundImage = src ? `url("${src}")` : '';
      preview.textContent = src ? '' : name.slice(0, 1).toUpperCase();
    };
    avatarSelect.addEventListener('change', refreshPreview);
    profileForm.display_name.addEventListener('input', refreshPreview);
    profileButton.onclick = async () => {
      result.textContent = 'Загружаем профиль...';
      try {
        const [current, avatars] = await Promise.all([fetch('/api/profile').then(response => response.json()), fetch('/api/profile/avatars').then(response => response.json())]);
        profileForm.display_name.value = current.display_name || 'Владелец';
        avatarSelect.innerHTML = '<option value="">Без аватара</option>' + avatars.map(item => `<option value="${String(item.name).replace(/[&<>"']/g, '')}">${String(item.name).replace(/[&<>"']/g, '')}</option>`).join('');
        avatarSelect.value = current.avatar || '';
        result.textContent = '';
        refreshPreview();
        profileDialog.showModal();
      } catch (error) { result.textContent = `Не удалось загрузить профиль: ${error.message}`; profileDialog.showModal(); }
    };
    profileForm.addEventListener('submit', async event => {
      event.preventDefault();
      result.textContent = 'Сохраняем...';
      try {
        const response = await fetch('/api/profile', {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({display_name: profileForm.display_name.value.trim(), avatar: avatarSelect.value})});
        if (!response.ok) throw new Error(await response.text());
        result.textContent = 'Профиль сохранён.';
        document.querySelector('.sidebar-foot b').textContent = profileForm.display_name.value.trim();
      } catch (error) { result.textContent = `Не удалось сохранить профиль: ${error.message}`; }
    });

    const settingsForm = Array.from(document.querySelectorAll('dialog form')).find(form => form.querySelector('.settings-result'));
    if (!settingsForm || settingsForm.dataset.phase16Ready) return;
    const settingsDialog = settingsForm.closest('dialog');
    settingsDialog?.classList.add('web-settings-dialog');
    settingsDialog?.querySelector('.dialog-close')?.addEventListener('click', event => {
      event.preventDefault();
      settingsDialog.close();
    });
    settingsForm.dataset.phase16Ready = 'true';
    settingsForm.insertAdjacentHTML('beforeend', '<hr><span class="eyebrow">Интерфейс</span><label style="display:flex;gap:8px;align-items:center"><input type="checkbox" name="reduce_motion"> Уменьшить анимацию</label><span class="eyebrow">AI-подключения</span><p class="settings-note">Провайдеры настраиваются в разделе «Подключения». Web показывает только реальные состояния Core.</p><span class="eyebrow">Данные</span><p class="settings-note">История, настройки и рабочие результаты хранятся локально в профиле Team2050.</p><span class="eyebrow">Дополнительно</span><label style="display:flex;gap:8px;align-items:center"><input type="checkbox" name="developer_mode"> Режим разработчика</label>');
    settingsForm.addEventListener('submit', async () => {
      const payload = {interface_language: settingsForm.interface_language.value, theme: settingsForm.theme.value, message_sounds_enabled: settingsForm.sound.checked, reduce_motion: settingsForm.reduce_motion.checked, developer_mode: settingsForm.developer_mode.checked};
      await fetch('/api/settings', {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)}).catch(() => {});
    });
    settingsButton.addEventListener('click', async () => {
      const current = await fetch('/api/settings').then(response => response.json()).catch(() => ({}));
      settingsForm.reduce_motion.checked = Boolean(current.reduce_motion);
      settingsForm.developer_mode.checked = Boolean(current.developer_mode);
    });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initProfileAndSettings); else initProfileAndSettings();
})();

(() => {
  const renderAttachmentLinks = async () => {
    const list = document.querySelector('.chat-list'); const select = document.querySelector('#org-select');
    if (!list || list.dataset.attachmentsReady || !select?.value) return;
    const response = await fetch('/api/chat', {headers:{'X-Organization-Id':select.value}}); if (!response.ok) return;
    const messages = await response.json(); const nodes = list.querySelectorAll('.message');
    const apiBase = window.LUMINIFERA_API_BASE || '';
    nodes.forEach((node,index) => {
      const files = messages[index]?.attachments || []; if (!files.length) return;
      node.insertAdjacentHTML('beforeend', `<div style="margin-top:8px;display:grid;gap:4px">${files.map(file=>`<a style="color:var(--cyan);font-size:12px" href="${apiBase}/api/chat/attachments/${encodeURIComponent(file.id)}" target="_blank">📎 ${String(file.name)}</a>`).join('')}</div>`);
    }); list.dataset.attachmentsReady='true';
  };
  new MutationObserver(renderAttachmentLinks).observe(document.querySelector('#view'), {childList:true,subtree:true});
  document.querySelector('[data-view="chat"]')?.addEventListener('click', () => setTimeout(renderAttachmentLinks, 80));
})();

(() => {
  const attachChatFiles = () => {
    const composer = document.querySelector('#composer'); const select = document.querySelector('#org-select');
    if (!composer || composer.dataset.filesReady || !select) return;
    composer.dataset.filesReady = 'true';
    const picker = document.createElement('input'); picker.type = 'file'; picker.multiple = true; picker.style.maxWidth = '130px'; picker.setAttribute('aria-label','Добавить файлы');
    composer.prepend(picker); let pending = [];
    picker.addEventListener('change', async () => {
      if (!select.value) return; pending=[];
      for (const file of picker.files) { const data = new FormData(); data.append('file',file); const response=await fetch('/api/chat/attachments',{method:'POST',headers:{'X-Organization-Id':select.value},body:data}); if(!response.ok) throw new Error(await response.text()); pending.push((await response.json()).id); }
    });
    composer.addEventListener('submit', async event => {
      event.preventDefault(); event.stopImmediatePropagation();
      const input=composer.querySelector('#message'); if(!input.value.trim()) return;
      const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','X-Organization-Id':select.value},body:JSON.stringify({content:input.value.trim(),attachment_ids:pending})});
      if(!response.ok) { alert(`Не удалось отправить: ${await response.text()}`); return; }
      input.value=''; picker.value=''; pending=[]; document.querySelector('[data-view="chat"]')?.click();
    }, true);
  };
  new MutationObserver(attachChatFiles).observe(document.querySelector('#view'), {childList:true,subtree:true});
  document.querySelector('[data-view="chat"]')?.addEventListener('click', () => setTimeout(attachChatFiles, 30));
})();

(() => {
  const initSettings = () => {
    const topActions = document.querySelector('.top-actions');
    if (!topActions || document.querySelector('.web-settings')) return;
    const button = document.createElement('button'); button.className = 'icon-button web-settings'; button.textContent = 'Настройки'; button.setAttribute('aria-label','Настройки');
    topActions.append(button);
    const dialog = document.createElement('dialog');
    dialog.innerHTML = '<form method="dialog" style="padding:28px;display:grid;gap:14px"><button class="dialog-close" value="cancel" aria-label="Закрыть">×</button><span class="eyebrow">Профиль и настройки</span><h2>Рабочая среда</h2><label>Язык интерфейса<select name="interface_language"><option value="ru">Русский</option><option value="uk">Українська</option><option value="en">English</option></select></label><label>Тема<select name="theme"><option value="dark">Тёмная</option><option value="light">Светлая</option><option value="night_city">Ночной город</option></select></label><label style="display:flex;gap:8px;align-items:center"><input type="checkbox" name="sound">Звуки сообщений</label><button class="primary" value="default">Сохранить</button><small class="settings-result" style="color:var(--muted)"></small></form>';
    document.body.append(dialog);
    const form = dialog.querySelector('form'); const result = dialog.querySelector('.settings-result');
    button.onclick = async () => { const current = await fetch('/api/settings').then(r=>r.json()); form.interface_language.value=current.interface_language||'ru'; form.theme.value=current.theme||'dark'; form.sound.checked=Boolean(current.message_sounds_enabled); result.textContent=''; dialog.showModal(); };
    form.addEventListener('submit', async event => { event.preventDefault(); result.textContent='Сохраняем...'; try { const response = await fetch('/api/settings',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({interface_language:form.interface_language.value,theme:form.theme.value,message_sounds_enabled:form.sound.checked})}); if(!response.ok) throw new Error(await response.text()); result.textContent='Настройки сохранены.'; document.documentElement.dataset.theme=form.theme.value; window.LuminiferaLocalization?.set(form.interface_language.value); } catch(error) { result.textContent=`Не удалось сохранить: ${error.message}`; }});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',initSettings); else initSettings();
})();

(() => {
  const attachWorkTimeline = async () => {
    const title = document.querySelector('#view-title');
    const view = document.querySelector('#view');
    const select = document.querySelector('#org-select');
    if (!title || !view || !select?.value || title.textContent !== 'Цели и работа' || view.querySelector('.web-work-timeline')) return;
    const response = await fetch('/api/work/timeline', {headers: {'X-Organization-Id': select.value}});
    if (!response.ok) return;
    const timeline = await response.json();
    if (!timeline.length) return;
    const panel = document.createElement('section');
    panel.className = 'web-work-timeline magic-card';
    panel.style.marginTop = '14px';
    panel.innerHTML = `<span class="eyebrow">История выполнения</span><div class="list">${timeline.slice(-12).map(item => `<div class="list-row"><span><b>${String(item.message || '').replace(/[&<>]/g, '')}</b>${item.artifact_created ? '<br><small>Артефакт сохранён</small>' : ''}</span><span class="tag">${String(item.status || '').replace(/[&<>]/g, '')}</span></div>`).join('')}</div>`;
    view.append(panel);
  };
  new MutationObserver(() => { attachWorkTimeline().catch(() => {}); }).observe(document.querySelector('#view'), {childList: true, subtree: true});
  document.querySelector('[data-view="work"]')?.addEventListener('click', () => setTimeout(() => attachWorkTimeline().catch(() => {}), 40));
})();

(() => {
  const attachWorkControls = async () => {
    const title = document.querySelector('#view-title');
    const view = document.querySelector('#view');
    const select = document.querySelector('#org-select');
    if (!title || !view || !select || title.textContent !== 'Цели и работа' || view.querySelector('.web-goals') || !select.value) return;
    const panel = document.createElement('section');
    panel.className = 'web-goals magic-card'; panel.style.marginTop = '14px';
    panel.innerHTML = '<span class="eyebrow">Планы Iris</span><div class="list"><p style="color:var(--muted)">Загружаем цели...</p></div>';
    view.append(panel);
    try {
      const response = await fetch('/api/goals', {headers:{'X-Organization-Id':select.value}});
      if (!response.ok) throw new Error(await response.text());
      const goals = await response.json(); const list = panel.querySelector('.list');
      if (!goals.length) { list.innerHTML = '<p style="color:var(--muted)">Планов пока нет. Создайте цель через кнопку «Новая цель».</p>'; return; }
      list.innerHTML = goals.slice().reverse().map(goal => `<div class="list-row"><span><b>${String(goal.goal || '').replace(/[&<>]/g,'')}</b><br><small>${goal.status || 'Создан'}</small></span><button class="ghost" data-plan="${goal.plan_id}">Запустить</button></div>`).join('');
      list.querySelectorAll('button[data-plan]').forEach(button => button.addEventListener('click', async () => {
        button.disabled = true; button.textContent = 'Запуск...';
        try {
          const start = await fetch(`/api/goals/${button.dataset.plan}/start`, {method:'POST',headers:{'X-Organization-Id':select.value}});
          if (!start.ok) throw new Error(await start.text());
          const result = await start.json(); button.textContent = result.ok ? 'Готово' : 'Нужна проверка';
          const receipt = await fetch('/api/work/receipt', {headers:{'X-Organization-Id':select.value}}).then(r=>r.json());
          panel.insertAdjacentHTML('beforeend', `<p style="margin-top:12px;color:var(--muted)">Результат: ${receipt.artifacts?.length||0} артефактов, ${receipt.evidence_count||0} доказательств, review: ${receipt.review_status||'в процессе'}.</p>`);
        } catch (error) { button.disabled = false; button.textContent = 'Ошибка запуска'; alert(`Работа не запущена: ${error.message}`); }
      }));
    } catch (error) { panel.querySelector('.list').innerHTML = `<p style="color:var(--muted)">Не удалось загрузить планы: ${error.message}</p>`; }
  };
  new MutationObserver(attachWorkControls).observe(document.querySelector('#view'), {childList:true,subtree:true});
  document.querySelector('[data-view="work"]')?.addEventListener('click', () => setTimeout(attachWorkControls, 30));
})();

(() => {
  const showWorkItems = async () => {
    const view = document.querySelector('#view');
    const select = document.querySelector('#org-select');
    if (!view || !select?.value || document.querySelector('.side-nav button.active')?.dataset.view !== 'work' || view.querySelector('.web-work-items')) return;
    const response = await fetch('/api/work/items', {headers: {'X-Organization-Id': select.value}});
    if (!response.ok) return;
    const items = await response.json();
    if (!items.length) return;
    const panel = document.createElement('section');
    panel.className = 'web-work-items magic-card';
    panel.style.marginTop = '14px';
    panel.innerHTML = `<span class="eyebrow">Work items</span><div class="list">${items.map(item => `<div class="list-row"><span><b>${String(item.title).replace(/[&<>]/g, '')}</b><br><small>${String(item.assignee).replace(/[&<>]/g, '')} · attempt ${item.attempt} · artifacts ${item.artifacts} · findings ${item.findings}</small></span><span class="tag">${String(item.status).replace(/[&<>]/g, '')}</span></div>`).join('')}</div>`;
    view.append(panel);
  };
  new MutationObserver(() => { showWorkItems().catch(() => {}); }).observe(document.querySelector('#view'), {childList: true, subtree: true});
  document.querySelector('[data-view="work"]')?.addEventListener('click', () => setTimeout(() => showWorkItems().catch(() => {}), 50));
})();

(() => {
  const showReviewFindings = async () => {
    const view = document.querySelector('#view');
    const select = document.querySelector('#org-select');
    if (!view || !select?.value || document.querySelector('.side-nav button.active')?.dataset.view !== 'work' || view.querySelector('.web-review-findings')) return;
    const response = await fetch('/api/work/review', {headers: {'X-Organization-Id': select.value}});
    if (!response.ok) return;
    const findings = await response.json();
    if (!findings.length) return;
    const panel = document.createElement('section');
    panel.className = 'web-review-findings magic-card';
    panel.style.marginTop = '14px';
    panel.innerHTML = `<span class="eyebrow">Review findings</span><div class="list">${findings.map(finding => `<div class="list-row"><span><b>${String(finding.title).replace(/[&<>]/g, '')}</b><br><small>${String(finding.reviewer).replace(/[&<>]/g, '')}</small></span><span class="tag">${String(finding.severity).replace(/[&<>]/g, '')} · ${String(finding.status).replace(/[&<>]/g, '')}</span></div>`).join('')}</div>`;
    view.append(panel);
  };
  new MutationObserver(() => { showReviewFindings().catch(() => {}); }).observe(document.querySelector('#view'), {childList: true, subtree: true});
  document.querySelector('[data-view="work"]')?.addEventListener('click', () => setTimeout(() => showReviewFindings().catch(() => {}), 70));
})();

(() => {
  const attachTeamControls = () => {
    const title = document.querySelector('#view-title');
    const view = document.querySelector('#view');
    const select = document.querySelector('#org-select');
    if (!title || !view || !select || title.textContent !== 'Команда' || view.querySelector('.web-hire')) return;
    const form = document.createElement('form');
    form.className = 'web-hire composer';
    form.innerHTML = '<input required maxlength="120" placeholder="Имя нового сотрудника"><select aria-label="Роль"><option value="CUSTOM_ROLE">Специалист</option><option value="PROJECT_MANAGER">Руководитель проекта</option><option value="DESIGN_ENGINEER">Инженер-проектировщик</option><option value="QA_ENGINEER">Инженер контроля качества</option><option value="DOCUMENT_CONTROL_OFFICER">Специалист по документации</option></select><button class="primary">Нанять</button>';
    form.style.margin = '0 0 14px';
    view.prepend(form);
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const [name, role] = form.querySelectorAll('input,select');
      if (!select.value) return;
      const button = form.querySelector('button'); button.disabled = true; button.textContent = 'Добавляем...';
      try {
        const response = await fetch(`/api/organizations/${select.value}/employees`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({display_name:name.value.trim(),role_id:role.value})});
        if (!response.ok) throw new Error(await response.text());
        name.value = ''; button.textContent = 'Добавлено';
        document.querySelector('[data-view="team"]')?.click();
      } catch (error) { button.textContent = 'Ошибка'; alert(`Не удалось нанять сотрудника: ${error.message}`); }
      finally { button.disabled = false; }
    });
  };
  new MutationObserver(attachTeamControls).observe(document.querySelector('#view'), {childList:true,subtree:true});
  document.querySelector('[data-view="team"]')?.addEventListener('click', () => setTimeout(attachTeamControls, 30));
})();

(() => {
  const enhanceTeamLifecycle = async () => {
    const view = document.querySelector('#view');
    const select = document.querySelector('#org-select');
    const activeView = document.querySelector('.side-nav button.active')?.dataset.view;
    if (!view || !select?.value || activeView !== 'team' || view.querySelector('[data-archive]')) return;
    const response = await fetch(`/api/organizations/${select.value}/employees`);
    if (!response.ok) return;
    const employees = await response.json();
    const rows = view.querySelectorAll('.list-row');
    if (rows.length !== employees.length) return;
    rows.forEach((row, index) => {
      if (row.querySelector('[data-employee-actions]')) return;
      const employee = employees[index];
      const controls = document.createElement('span');
      controls.dataset.employeeActions = employee.agent_id;
      controls.style.cssText = 'display:flex;gap:6px;align-items:center';
      controls.innerHTML = `<select aria-label="Role for ${employee.display_name}" data-role="${employee.agent_id}"><option value="CUSTOM_ROLE">Specialist</option><option value="PROJECT_MANAGER">Project manager</option><option value="DESIGN_ENGINEER">Design engineer</option><option value="QA_ENGINEER">QA engineer</option><option value="DOCUMENT_CONTROL_OFFICER">Document control</option></select><button class="ghost" data-reassign="${employee.agent_id}">Apply</button><button class="ghost" data-archive="${employee.agent_id}">Archive</button><button class="ghost" data-delete="${employee.agent_id}">Delete</button>`;
      controls.querySelector('[data-role]').value = employee.primary_role || 'CUSTOM_ROLE';
      row.append(controls);
    });
    view.querySelectorAll('[data-archive]').forEach(button => button.addEventListener('click', async () => {
      button.disabled = true;
      const response = await fetch(`/api/organizations/${select.value}/employees/${encodeURIComponent(button.dataset.archive)}/archive`, {method: 'POST'});
      if (!response.ok) { alert(`Archive failed: ${await response.text()}`); button.disabled = false; return; }
      document.querySelector('[data-view="team"]')?.click();
    }));
    view.querySelectorAll('[data-reassign]').forEach(button => button.addEventListener('click', async () => {
      const role = view.querySelector(`[data-role="${button.dataset.reassign}"]`);
      button.disabled = true;
      const response = await fetch(`/api/organizations/${select.value}/employees/${encodeURIComponent(button.dataset.reassign)}/role`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({role_id: role.value}),
      });
      if (!response.ok) { alert(`Role update failed: ${await response.text()}`); button.disabled = false; return; }
      document.querySelector('[data-view="team"]')?.click();
    }));
    view.querySelectorAll('[data-delete]').forEach(button => button.addEventListener('click', async () => {
      if (!window.confirm('Delete this employee permanently? This cannot be undone.')) return;
      button.disabled = true;
      const response = await fetch(`/api/organizations/${select.value}/employees/${encodeURIComponent(button.dataset.delete)}?confirm=true`, {method: 'DELETE'});
      if (!response.ok) { alert(`Delete failed: ${await response.text()}`); button.disabled = false; return; }
      document.querySelector('[data-view="team"]')?.click();
    }));
  };
  new MutationObserver(() => { enhanceTeamLifecycle().catch(() => {}); }).observe(document.querySelector('#view'), {childList: true, subtree: true});
  document.querySelector('[data-view="team"]')?.addEventListener('click', () => setTimeout(() => enhanceTeamLifecycle().catch(() => {}), 60));
})();

(() => {
  const view = document.querySelector('#view');
  const select = document.querySelector('#org-select');
  const button = document.querySelector('[data-view="connections"]');
  if (!view || !select || !button) return;

  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;',
  })[character]);
  const stateLabel = value => ({
    Ready: 'Готов', 'Login required': 'Требуется вход', Unavailable: 'Недоступен', Busy: 'Занят', Error: 'Ошибка',
    ACTIVE: 'Активен', VERIFIED: 'Проверено', CANDIDATE: 'Ожидает проверки', DRAFT: 'Черновик',
  })[String(value)] || String(value || 'Неизвестно');
  const empty = text => `<p class="connections-empty">${escapeHtml(text)}</p>`;
  let rendering = false;

  const renderConnections = async () => {
    if (rendering || document.querySelector('.side-nav button.active')?.dataset.view !== 'connections') return;
    document.querySelector('#view-title').textContent = 'Подключения и знания';
    const organizationId = select.value;
    if (!organizationId) {
      view.innerHTML = '<div class="empty"><h3>Сначала выберите организацию</h3><p>Навыки и память всегда принадлежат конкретной организации.</p></div>';
      return;
    }
    rendering = true;
    view.innerHTML = '<div class="connections-hub"><p class="connections-empty">Загружаем состояние Core...</p></div>';
    const headers = {'X-Organization-Id': organizationId};
    try {
      const responses = await Promise.all([
        fetch('/api/providers'), fetch('/api/skills', {headers}), fetch('/api/knowledge', {headers}), fetch('/api/competence', {headers}),
      ]);
      const failed = responses.find(response => !response.ok);
      if (failed) throw new Error(await failed.text());
      const [providers, skills, knowledge, competence] = await Promise.all(responses.map(response => response.json()));
      view.innerHTML = `<div class="connections-hub">
        <section class="connections-section"><div class="connections-heading"><span><span class="eyebrow">AI-соединения</span><h3>Провайдеры</h3></span><small>Показываются только реально поддерживаемые подключения</small></div><div class="list">${providers.length ? providers.map(provider => `<div class="list-row"><span><b>${escapeHtml(provider.name)}</b><br><small>${provider.available ? 'Готов к выполнению задач' : 'Проверьте установку или авторизацию'}</small></span><span class="connection-actions"><span class="tag ${provider.available ? '' : 'tag-muted'}">${escapeHtml(stateLabel(provider.state))}</span><button class="ghost" data-provider-check="${escapeHtml(provider.id)}">Проверить</button></span></div>`).join('') : empty('Поддерживаемые провайдеры не настроены.')}</div></section>
        <div class="connections-grid">
          <section class="connections-section"><div class="connections-heading"><span><span class="eyebrow">Рабочие возможности</span><h3>Навыки</h3></span><small>${skills.length}</small></div><div class="list">${skills.length ? skills.map(skill => `<div class="list-row"><span><b>${escapeHtml(skill.name)}</b><br><small>${escapeHtml(skill.purpose || 'Описание не указано')}</small></span><span class="tag">${escapeHtml(stateLabel(skill.status))} · v${escapeHtml(skill.version)}</span></div>`).join('') : empty('У организации пока нет установленных навыков.')}</div></section>
          <section class="connections-section"><div class="connections-heading"><span><span class="eyebrow">Память организации</span><h3>Проверенные знания</h3></span><small>${knowledge.filter(item => item.verified).length}/${knowledge.length}</small></div><div class="list">${knowledge.length ? knowledge.map(item => `<div class="list-row"><span><b>${escapeHtml(item.title)}</b><br><small>${escapeHtml(item.summary || 'Без описания')}${item.source ? ` · ${escapeHtml(item.source)}` : ''}</small></span><span class="tag ${item.verified ? '' : 'tag-muted'}">${escapeHtml(stateLabel(item.status))}</span></div>`).join('') : empty('Память появится только после реальной работы и независимой проверки.')}</div></section>
        </div>
        <section class="connections-section"><div class="connections-heading"><span><span class="eyebrow">Рост по доказательствам</span><h3>Компетенции команды</h3></span><small>${competence.length}</small></div><div class="list">${competence.length ? competence.map(item => `<div class="list-row"><span><b>${escapeHtml(item.competence)}</b><br><small>${escapeHtml(item.employee || 'Команда')}</small></span><span class="tag">${Number(item.growth_points || 0)} подтверждённых улучшений</span></div>`).join('') : empty('Компетенции растут только после принятого результата с evidence.')}</div></section>
      </div>`;
      view.querySelectorAll('[data-provider-check]').forEach(check => check.addEventListener('click', async () => {
        check.disabled = true;
        check.textContent = 'Проверяем...';
        const response = await fetch(`/api/providers/${encodeURIComponent(check.dataset.providerCheck)}/check`, {method: 'POST'});
        if (!response.ok) {
          check.disabled = false;
          check.textContent = 'Повторить';
          window.alert(`Проверка не выполнена: ${await response.text()}`);
          return;
        }
        rendering = false;
        await renderConnections();
      }));
    } catch (error) {
      view.innerHTML = `<div class="empty"><h3>Не удалось загрузить подключения</h3><p>${escapeHtml(error.message)}</p></div>`;
    } finally {
      rendering = false;
    }
  };

  let settleTimer = null;
  new MutationObserver(() => {
    if (document.querySelector('.side-nav button.active')?.dataset.view !== 'connections' || view.querySelector('.connections-hub')) return;
    window.clearTimeout(settleTimer);
    settleTimer = window.setTimeout(() => renderConnections().catch(() => {}), 50);
  }).observe(view, {childList: true});
  button.addEventListener('click', () => window.setTimeout(() => renderConnections().catch(() => {}), 80));
  select.addEventListener('change', () => window.setTimeout(() => renderConnections().catch(() => {}), 80));
  document.querySelector('#refresh')?.addEventListener('click', () => window.setTimeout(() => renderConnections().catch(() => {}), 80));
  window.renderConnections = renderConnections;
})();
