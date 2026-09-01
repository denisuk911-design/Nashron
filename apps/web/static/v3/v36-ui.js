(function () {
  "use strict";

  const esc = value => String(value ?? "").replace(/[&<>\"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;", "'":"&#039;"}[c]));
  const friendlyTeamName = "\u0420\u0430\u0431\u043e\u0447\u0430\u044f \u043a\u043e\u043c\u0430\u043d\u0434\u0430";

  function normalizeWorkspaceLabel() {
    document.querySelectorAll("#workspace-select option").forEach(option => {
      if (/ADVISORY_BOARD/i.test(option.textContent)) option.textContent = friendlyTeamName;
    });
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      if (/ADVISORY_BOARD/i.test(node.nodeValue || "")) node.nodeValue = node.nodeValue.replace(/ADVISORY_BOARD(?:\s+team)?/gi, friendlyTeamName);
    });
  }

  function normalizeSettingsCopy() {
    document.querySelectorAll("#preview-media").forEach(button => button.remove());
    const replacements = [
      [/Bridge подключён/gi, "Система подключена"],
      [/Bridge не подключён/gi, "Система не подключена"],
      [/Перечитать config\.js/gi, "Обновить медиа"],
      [/Проверить подключение/gi, "Проверить систему"]
    ];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      if (node.parentElement?.closest("script,style")) return;
      replacements.forEach(([pattern, value]) => { node.nodeValue = (node.nodeValue || "").replace(pattern, value); });
    });
  }

  function decorateWorkEmpty() {
    const stage = document.querySelector("#work-stage");
    if (!stage || stage.querySelector(".work-empty-flow") || stage.querySelector(".work-summary")) return;
    const copy = stage.querySelector(".empty-copy");
    if (!copy) return;
    const flow = document.createElement("div");
    flow.className = "work-empty-flow";
    flow.setAttribute("aria-hidden", "true");
    flow.innerHTML = ["GOAL", "WORK", "ARTIFACTS", "REVIEW"].map((label, index) =>
      `<span class="flow-step"><i>${index + 1}</i><b>${label}</b></span>${index < 3 ? '<span class="flow-link"></span>' : ""}`
    ).join("");
    copy.insertBefore(flow, copy.firstChild);
  }

  function decorateTeam() {
    const board = document.querySelector("#team-stage .constellation-board");
    if (!board || board.dataset.flowReady) return;
    const svg = board.querySelector("svg");
    if (!svg) return;
    const paths = [...svg.querySelectorAll("path")];
    paths.forEach((path, index) => {
      path.id = `constellation-path-${index}`;
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("class", "constellation-flow");
      circle.setAttribute("r", "5");
      circle.setAttribute("aria-hidden", "true");
      const motion = document.createElementNS("http://www.w3.org/2000/svg", "animateMotion");
      motion.setAttribute("dur", `${6 + index * 1.5}s`);
      motion.setAttribute("repeatCount", "indefinite");
      motion.setAttribute("begin", `${index * 1.2}s`);
      const mpath = document.createElementNS("http://www.w3.org/2000/svg", "mpath");
      mpath.setAttribute("href", `#constellation-path-${index}`);
      motion.append(mpath);
      circle.append(motion);
      svg.append(circle);
    });
    board.dataset.flowReady = "1";
  }

  function observe() {
    normalizeWorkspaceLabel();
    normalizeSettingsCopy();
    decorateWorkEmpty();
    decorateTeam();
    const observer = new MutationObserver(() => {
      normalizeWorkspaceLabel();
      normalizeSettingsCopy();
      decorateWorkEmpty();
      decorateTeam();
    });
    observer.observe(document.body, {childList: true, subtree: true});
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", observe, {once: true});
  else observe();
})();
