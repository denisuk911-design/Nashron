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

  async function decorateWorkData() {
    const stage = document.querySelector("#work-stage .data-stage");
    const bridge = window.LuminiferaBridge;
    if (!stage || !bridge || stage.querySelector(".work-proof")) return;
    try {
      const state = await bridge.getWorkState();
      const work = state.work || {};
      const receipt = state.receipt || {};
      const artifacts = Array.isArray(work.artifacts) ? work.artifacts : [];
      const evidence = Number(work.evidence_count ?? receipt.evidence_count ?? 0);
      const review = String(receipt.review_status || (state.review?.length ? "В проверке" : "Не начата"));
      const proof = document.createElement("section");
      proof.className = "work-proof";
      proof.innerHTML = `<div><span class="eyebrow">РЕЗУЛЬТАТЫ</span><strong>${artifacts.length ? artifacts.map(item => esc(item.title || "Артефакт")).join(" · ") : "Артефакты ещё не созданы"}</strong><small>${artifacts.length} артефакта подтверждены движком</small></div><div><span class="eyebrow">ДОКАЗАТЕЛЬСТВА</span><strong>${evidence}</strong><small>зафиксировано в рабочем цикле</small></div><div><span class="eyebrow">ПРОВЕРКА</span><strong>${esc(review)}</strong><small>${Number(receipt.findings_count || 0)} замечаний</small></div>`;
      stage.append(proof);
    } catch (_) {
      // Keep the normal Work state authoritative when the read fails.
    }
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
    decorateWorkData();
    decorateTeam();
    const observer = new MutationObserver(() => {
      normalizeWorkspaceLabel();
      normalizeSettingsCopy();
      decorateWorkEmpty();
      decorateWorkData();
      decorateTeam();
    });
    observer.observe(document.body, {childList: true, subtree: true});
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", observe, {once: true});
  else observe();
})();
