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
