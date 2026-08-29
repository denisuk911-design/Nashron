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
