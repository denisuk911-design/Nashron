(function () {
  "use strict";

  const stage = () => document.querySelector("#team-stage");
  const esc = value => String(value ?? "").replace(/[&<>\"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;", "'":"&#039;"}[c]));
  const dormant = [[50,18],[22,29],[78,29],[14,54],[86,54],[28,78],[72,78],[50,88]];

  function pathFor(index, width, height) {
    const cx = width / 2, cy = height / 2;
    const rx = width * (index ? .39 : .27), ry = height * (index ? .31 : .21);
    const k = .5522848;
    return `M ${cx} ${cy-ry} C ${cx+rx*k} ${cy-ry} ${cx+rx} ${cy-ry*k} ${cx+rx} ${cy} C ${cx+rx} ${cy+ry*k} ${cx+rx*k} ${cy+ry} ${cx} ${cy+ry} C ${cx-rx*k} ${cy+ry} ${cx-rx} ${cy+ry*k} ${cx-rx} ${cy} C ${cx-rx} ${cy-ry*k} ${cx-rx*k} ${cy-ry} ${cx} ${cy-ry}`;
  }

  function makeMotion(svg, index, path) {
    path.id = `team-orbit-${index}`;
    path.setAttribute("vector-effect", "non-scaling-stroke");
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("r", index ? "4" : "5");
    dot.setAttribute("class", "constellation-flow");
    const motion = document.createElementNS("http://www.w3.org/2000/svg", "animateMotion");
    motion.setAttribute("dur", `${10 + index * 4}s`);
    motion.setAttribute("repeatCount", "indefinite");
    motion.setAttribute("begin", `${index * 1.8}s`);
    const ref = document.createElementNS("http://www.w3.org/2000/svg", "mpath");
    ref.setAttribute("href", `#team-orbit-${index}`);
    motion.append(ref); dot.append(motion); svg.append(dot);
  }

  function drawPaths(board) {
    const svg = board.querySelector("svg");
    if (!svg) return;
    const box = board.getBoundingClientRect();
    const width = Math.max(320, Math.round(box.width)), height = Math.max(300, Math.round(box.height));
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.innerHTML = "";
    [0, 1].forEach(index => {
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", pathFor(index, width, height));
      path.setAttribute("class", "team-orbit-path");
      makeMotion(svg, index, path); svg.insertBefore(path, svg.lastElementChild);
    });
  }

  function positionMembers(board) {
    const nodes = [...board.querySelectorAll(".constellation-node")];
    const count = nodes.length;
    if (!count) return;
    const box = board.getBoundingClientRect();
    const wide = box.width >= 1200;
    const radiusX = Math.min(wide ? 39 : 35, 41 - Math.max(0, count - 8) * 1.1);
    const radiusY = Math.min(wide ? 33 : 29, 35 - Math.max(0, count - 8) * .8);
    nodes.forEach((node, index) => {
      const angle = -Math.PI / 2 + index * (Math.PI * 2 / count);
      node.style.setProperty("--node-x", `${50 + Math.cos(angle) * radiusX}%`);
      node.style.setProperty("--node-y", `${50 + Math.sin(angle) * radiusY}%`);
    });
  }

  function ensureScene(board) {
    if (!board) return;
    drawPaths(board); positionMembers(board);
    board.querySelectorAll(".runner").forEach(node => node.remove());
    board.querySelectorAll(".dormant-node").forEach(node => node.remove());
    if (!board.querySelector(".constellation-node")) {
      dormant.forEach(([x, y], index) => {
        const node = document.createElement("span");
        node.className = "dormant-node"; node.style.left = `${x}%`; node.style.top = `${y}%`;
        node.style.animationDelay = `${index * 280}ms`; node.setAttribute("aria-hidden", "true"); board.append(node);
      });
      const copy = document.createElement("div"); copy.className = "team-scene-copy";
      copy.innerHTML = `<span class="big-sigil">✦</span><h3>Созвездие ещё не проснулось</h3><p>Здесь появятся реальные сотрудники и их роли после создания команды через Iris.</p><button class="ghost" id="team-empty-action-v40" type="button">Попросить Iris собрать созвездие</button>`;
      board.append(copy);
      copy.querySelector("button").onclick = () => { const input = document.querySelector("#iris-input"); document.querySelector('[data-route="home"]')?.click(); if (input) { input.value = "Собери мне созвездие"; input.focus(); } };
    }
    board.dataset.v40Ready = "1";
  }

  function enhance() {
    const root = stage(); if (!root) return;
    let board = root.querySelector(".constellation-board");
    if (!board) {
      const existing = root.querySelector(".empty-copy");
      board = document.createElement("div"); board.className = "constellation-board";
      board.innerHTML = `<svg class="constellation-lines" aria-hidden="true"></svg><div class="constellation-orbit orbit-one"></div><div class="constellation-orbit orbit-two"></div><div class="constellation-core" aria-label="Iris — центр созвездия">✦<small>Iris</small></div>`;
      root.replaceChildren(board);
    }
    if (board.dataset.v40Ready !== "1") ensureScene(board);
    else positionMembers(board);
  }

  let resizeTimer;
  function observe() {
    enhance();
    new MutationObserver(() => requestAnimationFrame(enhance)).observe(document.body, {childList:true, subtree:true});
    window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { const board = stage()?.querySelector(".constellation-board"); if (board) { drawPaths(board); positionMembers(board); } }, 120); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", observe, {once:true}); else observe();
})();
