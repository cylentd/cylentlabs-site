/* Field: one canvas and a few thousand particles. Particles spring toward the targets the active shape sets.
   The pointer pushes them away on hover; a tap sends a shock ring through them. Background dust draws fainter. */
window.LAB = window.LAB || {};
(() => {
  const L = window.LAB;
  const cv = document.getElementById("field");
  if (!cv) return;
  const ctx = cv.getContext("2d");
  const css = getComputedStyle(document.documentElement);
  const tok = (n) => css.getPropertyValue(n).trim();
  const num = (n) => parseFloat(tok(n));
  const hex = (h) => { const v = parseInt(h.slice(1), 16); return [(v >> 16) & 255, (v >> 8) & 255, v & 255]; };
  const rgb = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;

  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // `small` picks the phone layout and is re-read on every resize; the dot count is fixed at load
  let small = innerWidth < 700;
  const N = Math.round(small ? num("--field-count-phone") : num("--field-count"));
  // ink, signal, then one hue per project in shapes.js order
  const CLS = ["--ink", "--signal", ...L.HUES.map((h) => `--hue-${h}`)].map((n) => rgb(hex(tok(n))));
  const LEVEL = [0.5, 0.75, 0.95, 1], DUST = num("--dust");

  const P = {
    n: N, w: 0, h: 0, tx: new Float32Array(N), ty: new Float32Array(N),
    cls: new Uint8Array(N), lit: new Uint8Array(N), amb: new Uint8Array(N), fast: new Uint8Array(N),
    lvl: new Uint8Array(N), ord: new Float32Array(N), sz: new Float32Array(N).fill(1), // sz: per-dot size scale, for depth
    enter: new Float32Array(N), // when a dot drops in on first load, 0 to 1 of the pour
  };
  const x = new Float32Array(N), y = new Float32Array(N), vx = new Float32Array(N), vy = new Float32Array(N);
  const stiff = new Float32Array(N), depth = new Float32Array(N), wob = new Float32Array(N), hold = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    stiff[i] = 0.01 + Math.random() * 0.025; depth[i] = 0.4 + Math.random() * 1.2; // settles in about a second, with some stagger
    wob[i] = Math.random() * 6.28;
  }

  const view = { dpr: 1, mx: 0.5, my: 0.5, sx: 0.5, sy: 0.5, intro: 0, px: -999, py: -999, hover: false, so: 0 };
  const shocks = []; // {x, y, age}: a ring that spreads from where the screen was tapped
  // the active shape's stage box, in page coordinates
  let shape = null, stopId = "hero", geo = { sx: 0, sy: 0, sw: 0, sh: 0 }, t0 = performance.now(), last = t0;
  const HANDOFF = 0.8; // seconds over which the old shape lets go, in the order its P.ord says

  // `so` (scroll offset) keeps the shape attached to its place on the page: screen y = y + so for shape dots.
  // When the shape changes, dots keep their on-screen position and fly to the new shape from there.
  function build(newSo, handoff) {
    const prev = new Float32Array(N), ord = P.ord.slice();
    for (let i = 0; i < N; i++) prev[i] = y[i] + (P.amb[i] ? 0 : view.so);
    if (newSo !== undefined && !reduce) view.so = newSo;
    const c = { w: P.w, h: P.h, small, sx: geo.sx, sy: geo.sy, sw: geo.sw, sh: geo.sh };
    shape = L.shapes[stopId] || L.shapes.hero;
    L.ctx = c;
    shape.init(P, c);
    shape.step && shape.step(P, c, (performance.now() - t0) / 1000);
    for (let i = 0; i < N; i++) {
      y[i] = prev[i] - (P.amb[i] ? 0 : view.so);
      if (handoff && !reduce) hold[i] = ord[i] * HANDOFF; // a re-measure of the same stop keeps any wait in progress
    }
    if (pourPending && geo.sw && !reduce) pour();
  }

  // The first time the hero's stage is measured, the shape draws itself: a head runs through it in the order P.enter
  // gives (the helix: down its strands, top to bottom, turning as it goes), and each dot appears at its own place as
  // the head reaches it, sliding in from just above. Dust fades in where it sits.
  let pourPending = true;
  const POUR = 2.2, SLIDE = 14; // seconds for the head's run; px each dot slides in from
  const drawn = new Uint8Array(N); // 1: waiting to be drawn in by the head
  function pour() {
    pourPending = false;
    if (stopId !== "hero" || view.so < -P.h) return; // a reload part-way down the page skips it
    for (let i = 0; i < N; i++) {
      vx[i] = 0; vy[i] = 0;
      if (P.amb[i]) { x[i] = P.tx[i]; y[i] = P.ty[i]; hold[i] = 0; continue; }
      drawn[i] = 1; x[i] = -9999; y[i] = -9999; // out of sight until the head reaches it
      hold[i] = P.enter[i] * POUR + 0.001; // never 0, so even the first dot appears through the hold branch
    }
  }
  function resize() {
    view.dpr = Math.min(devicePixelRatio || 1, 2);
    P.w = innerWidth; P.h = innerHeight; small = P.w < 700;
    cv.width = P.w * view.dpr; cv.height = P.h * view.dpr;
    build();
    if (reduce) { snap(); render(); }
  }
  function snap() {
    for (let i = 0; i < N; i++) { x[i] = P.tx[i]; y[i] = P.ty[i]; }
    view.intro = 1;
  }

  function render() {
    ctx.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
    ctx.clearRect(0, 0, P.w, P.h);
    const s = num(small ? "--dot-phone" : "--dot"), sl = num(small ? "--dot-lit-phone" : "--dot-lit");
    const ox = (view.sx - 0.5) * 14, oy = (view.sy - 0.5) * 14;
    for (let c = 0; c < CLS.length; c++) {
      ctx.fillStyle = CLS[c];
      for (let a = 0; a < 2; a++) { // a = 1: background dust, drawn fainter
        for (let l = 0; l < 4; l++) {
          ctx.globalAlpha = LEVEL[l] * view.intro * (a ? DUST : 1);
          const base = l === 3 ? sl : s;
          for (let i = 0; i < N; i++) {
            if (P.cls[i] !== c || P.amb[i] !== a) continue;
            if ((P.lit[i] ? 3 : P.lvl[i]) !== l) continue;
            const size = base * P.sz[i];
            ctx.fillRect(x[i] - ox * depth[i] - size / 2, y[i] + (a ? 0 : view.so) - oy * depth[i] - size / 2, size, size);
          }
        }
      }
    }
    ctx.globalAlpha = 1;
  }

  // pointer forces: hover pushes nearby dots away; each shock ring kicks the dots it passes outward
  function push(i, f, hr) {
    const sy = y[i] + (P.amb[i] ? 0 : view.so); // where the dot is on screen
    if (view.hover) {
      const dx = x[i] - view.px, dy = sy - view.py, d2 = dx * dx + dy * dy;
      if (d2 < hr * hr) {
        const d = Math.sqrt(d2) || 1, k = Math.pow(1 - d / hr, 1.5) * 6 * f;
        vx[i] += (dx / d) * k; vy[i] += (dy / d) * k;
      }
    }
    for (const s of shocks) {
      const dx = x[i] - s.x, dy = sy - s.y, d = Math.sqrt(dx * dx + dy * dy) || 1;
      const band = Math.abs(d - s.age * 420);
      if (band < 55) {
        const k = (1 - band / 55) * (1 - s.age / 0.9) * 2.4 * f;
        vx[i] += (dx / d) * k; vy[i] += (dy / d) * k;
      }
    }
  }

  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000), f = dt * 60; last = now;
    const t = (now - t0) / 1000;
    view.intro = Math.min(1, view.intro + dt / 0.7); // visible almost at once, so the flow-in reads
    view.sx += (view.mx - view.sx) * 0.06; view.sy += (view.my - view.sy) * 0.06;
    const damp = Math.pow(0.9, f), hr = small ? 80 : 130;
    for (let k = shocks.length - 1; k >= 0; k--) { shocks[k].age += dt; if (shocks[k].age > 0.9) shocks.splice(k, 1); }
    shape.step && shape.step(P, L.ctx, t);
    for (let i = 0; i < N; i++) {
      if (hold[i] > 0) { // still part of the old shape: it waits its turn, but the pointer can still move it
        hold[i] -= dt; vx[i] *= damp; vy[i] *= damp; push(i, f, hr);
        x[i] += vx[i] * f; y[i] += vy[i] * f;
        if (hold[i] <= 0 && drawn[i]) { // the head has reached it: appear at its place, just above, and settle
          x[i] = P.tx[i]; y[i] = P.ty[i] - SLIDE; drawn[i] = 0;
        }
        continue;
      }
      const ax = P.tx[i] + Math.sin(t * 0.4 + wob[i]) * (P.amb[i] ? 18 : 0.6); // shape dots barely breathe, so grids stay crisp
      const ay = P.ty[i] + Math.cos(t * 0.33 + wob[i]) * (P.amb[i] ? 18 : 0.6);
      const k = P.fast[i] ? 0.2 : stiff[i]; // the ball and the ping keep up with their targets
      vx[i] = (vx[i] + (ax - x[i]) * k * f) * damp;
      vy[i] = (vy[i] + (ay - y[i]) * k * f) * damp;
      push(i, f, hr);
      x[i] += vx[i] * f; y[i] += vy[i] * f;
    }
    render();
    requestAnimationFrame(frame);
  }

  L.field = {
    // a new stop hands off (the old shape lets go in order); the same stop re-measured just re-forms
    setStop(id, g, so) { const handoff = id !== stopId; stopId = id; if (g) geo = g; build(so, handoff); if (reduce) { snap(); render(); } },
    setOffset(v) { if (!reduce) view.so = v; }, // scroll the shape with its stage
  };
  addEventListener("resize", resize);
  if (!reduce) {
    addEventListener("pointermove", (e) => {
      view.mx = e.clientX / P.w; view.my = e.clientY / P.h; view.px = e.clientX; view.py = e.clientY; view.hover = true;
    }, { passive: true });
    addEventListener("pointerdown", (e) => { shocks.push({ x: e.clientX, y: e.clientY, age: 0 }); }, { passive: true });
    document.documentElement.addEventListener("pointerleave", () => { view.hover = false; });
    addEventListener("pointerup", (e) => { if (e.pointerType === "touch") view.hover = false; }, { passive: true });
  }

  resize();
  // until chapters.js measures the hero and pour() runs, every dot waits just above the screen
  for (let i = 0; i < N; i++) { x[i] = Math.random() * P.w; y[i] = -60; hold[i] = 0.5; }
  if (reduce) { snap(); render(); } else requestAnimationFrame(frame);
})();
