(() => {
  const dictionaries = {
    uk: {
      'Рабочее место':'Робоче місце', 'Обзор':'Огляд', 'Iris чат':'Чат Iris', 'Цели и работа':'Цілі та робота',
      'Файлы':'Файли', 'Команда':'Команда', 'Подключения':'Підключення', 'Организация':'Організація',
      'Выберите организацию':'Оберіть організацію', 'Новая цель ↗':'Нова ціль ↗', 'Обновить ↻':'Оновити ↻',
      'Настройки':'Налаштування', 'Профиль владельца':'Профіль власника', 'Ваш профиль':'Ваш профіль',
      'Сохранить профиль':'Зберегти профіль', 'Открыть':'Відкрити', 'Скачать':'Завантажити', 'Закрыть':'Закрити',
      'Результаты работы':'Результати роботи', 'История выполнения':'Історія виконання', 'Работа начата':'Роботу розпочато',
      'Артефакт сохранён':'Артефакт збережено', 'Проверка пройдена':'Перевірку пройдено', 'working':'виконується',
      'planned':'заплановано', 'complete':'завершено'
    },
    en: {
      'Рабочее место':'Workspace', 'Обзор':'Overview', 'Iris чат':'Iris chat', 'Цели и работа':'Goals & work',
      'Файлы':'Files', 'Команда':'Team', 'Подключения':'Connections', 'Организация':'Organization',
      'Выберите организацию':'Choose an organization', 'Новая цель ↗':'New goal ↗', 'Обновить ↻':'Refresh ↻',
      'Настройки':'Settings', 'Профиль владельца':'Owner profile', 'Ваш профиль':'Your profile',
      'Сохранить профиль':'Save profile', 'Открыть':'Open', 'Скачать':'Download', 'Закрыть':'Close',
      'Результаты работы':'Work results', 'История выполнения':'Execution history', 'Работа начата':'Work started',
      'Артефакт сохранён':'Artifact saved', 'Проверка пройдена':'Review passed', 'working':'working',
      'planned':'planned', 'complete':'complete'
    }
  };
  let language = 'ru';
  const original = new WeakMap();
  const translate = value => dictionaries[language]?.[value] || value;
  const apply = root => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      if (node.parentElement?.closest('script,style')) return;
      if (!original.has(node)) original.set(node, node.nodeValue);
      node.nodeValue = language === 'ru' ? original.get(node) : translate(original.get(node));
    });
    root.querySelectorAll?.('input,textarea,[aria-label]').forEach(element => ['placeholder','aria-label'].forEach(attribute => {
      if (!element.hasAttribute(attribute)) return;
        const key = attribute === 'aria-label' ? 'originalAriaLabel' : 'originalPlaceholder';
      element.dataset[key] ||= element.getAttribute(attribute);
      element.setAttribute(attribute, language === 'ru' ? element.dataset[key] : translate(element.dataset[key]));
    }));
    document.documentElement.lang = language === 'uk' ? 'uk' : language;
  };
  const set = next => { language = ['ru','uk','en'].includes(next) ? next : 'ru'; apply(document.body); };
  window.LuminiferaLocalization = {set, apply, get: () => language};
  new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => {
    if (node.nodeType === Node.ELEMENT_NODE) apply(node);
  }))).observe(document.body, {childList:true, subtree:true});
  fetch(`${window.LUMINIFERA_API_BASE || ''}/api/settings`).then(response => response.ok ? response.json() : null)
    .then(settings => { if (settings?.interface_language) set(settings.interface_language); }).catch(() => {});
})();
