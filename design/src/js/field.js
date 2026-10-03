/* Field: one canvas and a few thousand particles. Particles spring toward the targets the active shape sets.
   With a mouse, the pointer pushes them away on hover and tilts the field (parallax). A tap or click leaves a small
   wake that drifts the way the finger or pointer moved and fades; a finger swiping across the screen, scrolling or
   not, leaves a trail of them. Background dust draws fainter. */
window.LAB = window.LAB || {};
(() => {
  const L = window.LAB;
  // pure rules, kept apart from the canvas so tests can run them
  L.fieldRules = {
    // a touch is a tap when it barely moved and lifted quickly; anything else was a scroll or a drag
    isTap: (dx, dy, ms, slop, maxMs) => dx * dx + dy * dy <= slop * slop && ms <= maxMs,
    // a mouse press is a click when it barely moved, however long it was held; a drag (the helix's spin) is not
    isClick: (dx, dy, slop) => dx * dx + dy * dy <= slop * slop,
    // the canvas's pixels per CSS pixel: never above the screen's own, capped lower on touch screens
    dpr: (screen, fine, capFine, capTouch) => Math.max(1, Math.min(screen || 1, fine ? capFine : capTouch)),
    // the wake's radius follows the screen, so a phone's wake is as small next to its screen as a desktop's
    wakeRadius: (w, h, frac) => frac * Math.min(w, h),
  };
  const cv = document.getElementById("field");
  if (!cv) return;
  const ctx = cv.getContext("2d");
  const css = getComputedStyle(document.documentElement);
  const tok = (n) => css.getPropertyValue(n).trim();
  const num = (n) => parseFloat(tok(n));
  const hex = (h) => { const v = parseInt(h.slice(1), 16); return [(v >> 16) & 255, (v >> 8) & 255, v & 255]; };
  const rgb = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;

  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // hover push, parallax and the idle half-rate draw are for a mouse; a touch screen gets only the tap wake
  const fine = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const PACE = num("--field-pace"), DRIFT = num("--field-drift");
  const WAKE = { size: num("--wake-size"), push: num("--wake-push"), life: num("--wake-life") / 1000 };
  const TAP = { slop: num("--tap-slop"), ms: num("--tap-time") };
  const TRAIL = { gap: num("--wake-trail-gap"), max: num("--wake-max") }; // a swipe's trail: spacing in radii, cap
  const BOW = { speed: num("--bow-speed"), still: num("--bow-still"), ease: num("--bow-ease"), depth: num("--bow-depth") };
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

  const view = { dpr: 1, mx: 0.5, my: 0.5, sx: 0.5, sy: 0.5, intro: 0, px: -999, py: -999, hover: false, so: 0, wakeR: 0,
    hvx: 0, hvy: 0, lpx: -999, lpy: -999 }; // the hover's smoothed velocity, and where the cursor was last frame
  const wakes = []; // {x, y, dx, dy, age}: a soft patch left where the screen was tapped, drifting along (dx, dy)
  // the active shape's stage box, in page coordinates
  let shape = null, stopId = "hero", geo = { sx: 0, sy: 0, sw: 0, sh: 0 }, t0 = performance.now(), last = t0;
  const clock = (now) => ((now - t0) / 1000) * PACE; // the shapes' time: slower than the wall clock, so calmer
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
    shape.step && shape.step(P, c, clock(performance.now()));
    for (let i = 0; i < N; i++) {
      y[i] = prev[i] - (P.amb[i] ? 0 : view.so);
      if (handoff && !reduce) hold[i] = ord[i] * HANDOFF; // a re-measure of the same stop keeps any wait in progress
    }
    if (pourPending && geo.sw && !reduce) pour();
    built = { w: P.w, h: P.h };
    wake();
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
  // The canvas follows the window at once; the shape waits until the resizing stops. A height-only change smaller
  // than URLBAR of the height (a phone's URL bar showing or hiding) never rebuilds: the stages are sized in svh, so
  // only the dust's spread changes, and scaling its targets gives exactly what a rebuild would.
  const SETTLE = 150, URLBAR = 0.2; // ms of quiet before a rebuild; fraction of the height
  let dot = 0, dotLit = 0, built = { w: 0, h: 0 }, settleTimer = 0;
  const DPR_FINE = num("--field-dpr"), DPR_TOUCH = num("--field-dpr-touch");
  function fit() {
    view.dpr = L.fieldRules.dpr(devicePixelRatio, fine, DPR_FINE, DPR_TOUCH);
    P.w = innerWidth; P.h = innerHeight; small = P.w < 700;
    view.wakeR = L.fieldRules.wakeRadius(P.w, P.h, WAKE.size);
    const cw = Math.round(P.w * view.dpr), ch = Math.round(P.h * view.dpr);
    if (cv.width !== cw || cv.height !== ch) { cv.width = cw; cv.height = ch; }
    // token reads are slow next to a frame's budget: read the dot sizes here, not in render()
    dot = num(small ? "--dot-phone" : "--dot"); dotLit = num(small ? "--dot-lit-phone" : "--dot-lit");
  }
  function resize() {
    fit();
    render(); // a resized canvas is blank until drawn
    wake();
    clearTimeout(settleTimer);
    settleTimer = setTimeout(settled, SETTLE);
  }
  function settled() {
    const dh = P.h - built.h;
    if (P.w === built.w && Math.abs(dh) <= built.h * URLBAR) {
      for (let i = 0; i < N; i++) if (P.amb[i]) P.ty[i] *= P.h / built.h;
      built.h = P.h;
      if (reduce) { snap(); render(); }
      return;
    }
    // chapters.js re-measures the active stage and calls setStop(), which rebuilds; without it, rebuild here
    if (!dispatchEvent(new CustomEvent("lab:layout", { cancelable: true }))) return;
    build();
    if (reduce) { snap(); render(); }
  }
  function snap() {
    for (let i = 0; i < N; i++) { x[i] = P.tx[i]; y[i] = P.ty[i]; }
    view.intro = 1;
  }

  // One pass sorts the dots into buckets in the order the draw needs: class, then shape before dust, then level
  // (3 = lit). Each bucket then draws under one fillStyle and one globalAlpha. Classes and levels change every frame
  // (forks, lit boxes, pings), so the sort runs per frame; it is stable, so the paint order is the old 56-pass order.
  const NB = CLS.length * 8, start = new Int32Array(NB + 1), at = new Int32Array(NB);
  const key = new Uint16Array(N), order = new Uint32Array(N);
  function sort() {
    start.fill(0);
    for (let i = 0; i < N; i++) {
      const k = P.cls[i] * 8 + P.amb[i] * 4 + (P.lit[i] ? 3 : P.lvl[i]);
      key[i] = k; start[k + 1]++;
    }
    for (let b = 0; b < NB; b++) { start[b + 1] += start[b]; at[b] = start[b]; }
    for (let i = 0; i < N; i++) order[at[key[i]]++] = i;
  }
  function render() {
    ctx.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
    ctx.clearRect(0, 0, P.w, P.h);
    sort();
    const ox = (view.sx - 0.5) * 14, oy = (view.sy - 0.5) * 14;
    let cls = -1;
    for (let b = 0; b < NB; b++) {
      const e = start[b + 1];
      if (start[b] === e) continue;
      const a = (b >> 2) & 1, l = b & 3, base = l === 3 ? dotLit : dot, so = a ? 0 : view.so; // a = 1: dust, fainter
      if (b >> 3 !== cls) { cls = b >> 3; ctx.fillStyle = CLS[cls]; } // setting a colour parses it: once per class
      ctx.globalAlpha = LEVEL[l] * view.intro * (a ? DUST : 1);
      for (let j = start[b]; j < e; j++) {
        const i = order[j], size = base * P.sz[i];
        ctx.fillRect(x[i] - ox * depth[i] - size / 2, y[i] + so - oy * depth[i] - size / 2, size, size);
      }
    }
    ctx.globalAlpha = 1;
  }

  // A wake is a soft Gaussian patch, not a ring: it drifts WAKE_TRAVEL radii along the tap's direction and fades.
  // With a direction it carries dots along it and parts them a little; a still tap stirs them in a small eddy.
  const WAKE_TRAVEL = 0.6;
  function wakePush(i, sx, sy, f) {
    const R = view.wakeR, r2 = R * R;
    for (const w of wakes) {
      const e = w.age / WAKE.life, cx = w.x + w.dx * WAKE_TRAVEL * R * e, cy = w.y + w.dy * WAKE_TRAVEL * R * e;
      const rx = sx - cx, ry = sy - cy, d2 = rx * rx + ry * ry;
      if (d2 > 2.25 * r2) continue;
      const d = Math.sqrt(d2) || 1, k = Math.exp(-2 * d2 / r2) * (1 - e) * (1 - e) * WAKE.push * f;
      const ux = rx / d, uy = ry / d;
      if (w.dx || w.dy) { vx[i] += (w.dx * 0.7 + ux * 0.3) * k; vy[i] += (w.dy * 0.7 + uy * 0.3) * k; }
      else { vx[i] += (ux * 0.5 - uy * 0.5) * k; vy[i] += (uy * 0.5 + ux * 0.5) * k; }
    }
  }
  // The hover is a bow wave: a soft patch (Gaussian, no rim) that the dots move out of. Moving, it stretches ahead
  // along the way the cursor goes, dots parting to either side and filling back in behind. Parked, it shrinks to a
  // small clear hole that holds still; when the cursor leaves, the dots fill it back in.
  // It moves where a dot rests, not the dot: each dot's spring target is offset by a field measured from the target
  // itself, so a dot settles at its new place. History, all 2026-10-03: a push on velocity pulsed under a parked
  // cursor (pushed out of reach, sprung back, pushed again); a smooth radial spread fixed that but was a magnifying
  // lens ("it zooms in"); a moving-only wave fixed that but let the dots ignore a parked cursor. Now: a hole-shaped
  // profile that is smooth at the centre, at every speed.
  // `bow` holds the per-frame shape, set by bowShape() before simulate(); bowOffset() leaves its answer in OFF.
  const bow = { on: false, x: 0, y: 0, ux: 0, uy: 0, e: 0, R: 0, A: 0 };
  const OFF = { x: 0, y: 0 };
  function bowShape(hr) {
    bow.on = view.hover;
    if (!bow.on) return;
    const sp = Math.hypot(view.hvx, view.hvy), e = Math.min(1, sp / BOW.speed);
    bow.x = view.px; bow.y = view.py; bow.e = e;
    bow.ux = sp > 0.01 ? view.hvx / sp : 0; bow.uy = sp > 0.01 ? view.hvy / sp : 0;
    bow.R = hr * (BOW.still + (1 - BOW.still) * e);
    bow.A = bow.R * BOW.depth; // how far it moves the dots it covers: a parked cursor keeps a small clear hole
  }
  function bowOffset(sx, sy) {
    OFF.x = OFF.y = 0;
    const dx = sx - bow.x, dy = sy - bow.y, { ux, uy, e, R } = bow;
    const a = dx * ux + dy * uy, b = dy * ux - dx * uy; // along the motion (ahead > 0), and across it
    const al = a / (R * (a > 0 ? 1 + 0.8 * e : 1 - 0.4 * e)), ac = b / (R * (1 + 0.15 * e));
    const n2 = al * al + ac * ac;
    if (n2 > 2.25) return;
    // A hole, not a lens: the push is near full strength a short way out (core: 0.3 R) and fades with the Gaussian,
    // so dots clear out of the middle instead of all spreading in proportion. It still falls to zero at the exact
    // centre, so a target drifting across it moves smoothly. Directions: out from the cursor, parted sideways
    // across the motion, and a little forward for the dots ahead.
    const d = Math.hypot(dx, dy) || 1, core = 0.3 * R;
    const m = (1 - Math.exp(-(d * d) / (core * core))) * Math.exp(-1.6 * n2) * bow.A;
    const side = Math.max(-1, Math.min(1, b / core)), fwd = a > 0 ? 0.3 * e : 0;
    OFF.x = (dx / d * (1 - 0.5 * e) - uy * side * 0.6 * e + ux * fwd) * m;
    OFF.y = (dy / d * (1 - 0.5 * e) + ux * side * 0.6 * e + uy * fwd) * m;
  }
  // each wake nudges the dots it covers
  function push(i, f) {
    if (wakes.length) wakePush(i, x[i], y[i] + (P.amb[i] ? 0 : view.so), f);
  }

  // moves every dot one step; returns the fastest dot's speed, in px per 60th of a second
  function simulate(dt, f, t) {
    const damp = Math.pow(0.9, f);
    bowShape(small ? 80 : 130);
    let fastest = 0, waiting = 0;
    for (let i = 0; i < N; i++) {
      if (hold[i] > 0) { // still part of the old shape: it waits its turn, but the pointer can still move it
        hold[i] -= dt; vx[i] *= damp; vy[i] *= damp; push(i, f); waiting = 1;
        x[i] += vx[i] * f; y[i] += vy[i] * f;
        if (hold[i] <= 0 && drawn[i]) { // the head has reached it: appear at its place, just above, and settle
          x[i] = P.tx[i]; y[i] = P.ty[i] - SLIDE; drawn[i] = 0;
        }
        continue;
      }
      let ax = P.tx[i] + Math.sin(t * 0.4 + wob[i]) * (P.amb[i] ? DRIFT : 0.6); // shape dots barely breathe, so grids stay crisp
      let ay = P.ty[i] + Math.cos(t * 0.33 + wob[i]) * (P.amb[i] ? DRIFT : 0.6);
      if (bow.on) { bowOffset(ax, ay + (P.amb[i] ? 0 : view.so)); ax += OFF.x; ay += OFF.y; }
      const k = P.fast[i] ? 0.2 : stiff[i]; // the ball and the ping keep up with their targets
      vx[i] = (vx[i] + (ax - x[i]) * k * f) * damp;
      vy[i] = (vy[i] + (ay - y[i]) * k * f) * damp;
      push(i, f);
      x[i] += vx[i] * f; y[i] += vy[i] * f;
      const v = Math.abs(vx[i]) + Math.abs(vy[i]);
      if (v > fastest) fastest = v;
    }
    return waiting ? Infinity : fastest;
  }

  // The field never stops while the page shows: the helix turns, every motif loops, the dust drifts, all by design.
  // So it stops only while the page is hidden. With a mouse, when nothing on screen moves faster than CALM px per
  // 60th of a second for CALM_FRAMES frames in a row (no hand-off, pointer, wake or scroll), it draws every other
  // frame; anything faster brings back every frame at once. Touch screens draw every frame: on a phone the
  // half-rate read as stutter (and at 120 Hz the old 30 ms gate dropped it to a quarter).
  const CALM = 0.5, CALM_FRAMES = 30;
  let loop = 0, calm = 0, skip = 0;
  function wake() { calm = 0; if (!loop && !reduce && !document.hidden) { last = performance.now(); loop = requestAnimationFrame(frame); } }
  function frame(now) {
    loop = requestAnimationFrame(frame);
    if (fine && calm >= CALM_FRAMES && (skip ^= 1)) return;
    const dt = Math.min(0.05, (now - last) / 1000), f = dt * 60; last = now;
    const t = clock(now);
    view.intro = Math.min(1, view.intro + dt / 0.7); // visible almost at once, so the flow-in reads
    const drift = Math.abs(view.mx - view.sx) + Math.abs(view.my - view.sy);
    view.sx += (view.mx - view.sx) * 0.06; view.sy += (view.my - view.sy) * 0.06;
    // the cursor's velocity in px per 60th of a second, smoothed so the bow wave turns and settles gently
    const ease = 1 - Math.pow(1 - BOW.ease, f);
    let jx = view.px - view.lpx, jy = view.py - view.lpy;
    if (Math.abs(jx) + Math.abs(jy) > 300) jx = jy = 0; // the cursor arrived from off the page: not a movement
    view.hvx += (jx / (f || 1) - view.hvx) * ease;
    view.hvy += (jy / (f || 1) - view.hvy) * ease;
    view.lpx = view.px; view.lpy = view.py;
    for (let k = wakes.length - 1; k >= 0; k--) { wakes[k].age += dt; if (wakes[k].age > WAKE.life) wakes.splice(k, 1); }
    shape.step && shape.step(P, L.ctx, t);
    const fastest = simulate(dt, f, t) + drift * 0.06 * 14 * 1.6; // the parallax moves the deepest dots this much
    calm = fastest < CALM && !wakes.length && view.intro === 1 ? calm + 1 : 0;
    render();
  }
  addEventListener("visibilitychange", () => {
    if (!document.hidden) { wake(); return; }
    cancelAnimationFrame(loop); loop = 0;
  });

  L.field = {
    // a new stop hands off (the old shape lets go in order); the same stop re-measured just re-forms
    setStop(id, g, so) { const handoff = id !== stopId; stopId = id; if (g) geo = g; build(so, handoff); if (reduce) { snap(); render(); } },
    setOffset(v) { if (!reduce && v !== view.so) { view.so = v; wake(); } }, // scroll the shape with its stage
    wakeCount: () => wakes.length, // for tests
    countNear(px, py, r) { // for tests: how many dots sit within r of a screen point
      let n = 0;
      for (let i = 0; i < N; i++) { const dx = x[i] - px, dy = y[i] + (P.amb[i] ? 0 : view.so) - py; if (dx * dx + dy * dy < r * r) n++; }
      return n;
    },
    speedNear(px, py, r) { // for tests: the fastest dot within r of a screen point, px per 60th of a second
      let m = 0;
      for (let i = 0; i < N; i++) {
        const dx = x[i] - px, dy = y[i] + (P.amb[i] ? 0 : view.so) - py;
        if (dx * dx + dy * dy < r * r) m = Math.max(m, Math.abs(vx[i]) + Math.abs(vy[i]));
      }
      return m;
    },
  };
  addEventListener("resize", resize);
  if (!reduce) listen();
  // Every listener is passive and none calls preventDefault, so the page always scrolls (touch-action stays pan-y).
  function listen() {
    const leave = (x0, y0, dx, dy) => {
      const d = Math.hypot(dx, dy), dir = d > 2 ? 1 / d : 0;
      wakes.push({ x: x0, y: y0, dx: dx * dir, dy: dy * dir, age: 0 });
      if (wakes.length > TRAIL.max) wakes.shift(); // a long swipe keeps only its newest stretch
      wake();
    };
    // a finger's trail: touchmove keeps firing while the browser scrolls (pointer events stop at pointercancel), so a
    // swipe that scrolls the page still stirs the dots under it, one wake per TRAIL.gap radii travelled
    let finger = null; // where the trail's last wake was left
    addEventListener("touchstart", (e) => { const t = e.touches[0]; finger = { x: t.clientX, y: t.clientY }; }, { passive: true });
    addEventListener("touchmove", (e) => {
      const t = e.touches[0];
      if (!finger || !t) return;
      const dx = t.clientX - finger.x, dy = t.clientY - finger.y;
      if (Math.hypot(dx, dy) < TRAIL.gap * view.wakeR) return;
      leave(t.clientX, t.clientY, dx, dy);
      finger = { x: t.clientX, y: t.clientY };
    }, { passive: true });
    addEventListener("touchend", () => { finger = null; }, { passive: true });
    let down = null; // the press a tap or click starts: where, when, and where it is now
    addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY, at: e.timeStamp, nx: e.clientX, ny: e.clientY }; }, { passive: true });
    addEventListener("pointercancel", () => { down = null; }, { passive: true }); // the browser took the touch to scroll
    addEventListener("pointerup", (e) => {
      if (!down) return;
      const dx = e.clientX - down.x, dy = e.clientY - down.y;
      // a click carries the way the mouse was heading; a tap, the way the finger slid, if it slid at all
      if (fine && e.pointerType === "mouse") { if (L.fieldRules.isClick(dx, dy, TAP.slop)) leave(e.clientX, e.clientY, view.vx || 0, view.vy || 0); }
      else if (L.fieldRules.isTap(dx, dy, e.timeStamp - down.at, TAP.slop, TAP.ms)) leave(e.clientX, e.clientY, dx, dy);
      down = null;
    }, { passive: true });
    if (!fine) return;
    addEventListener("pointermove", (e) => {
      if (e.pointerType !== "mouse") return;
      view.vx = e.clientX - view.px; view.vy = e.clientY - view.py; // the last step's direction, for a click's wake
      // a held button is a drag spinning the helix: the cursor stops pushing dots, so the drag reads as a spin, not a poke
      view.mx = e.clientX / P.w; view.my = e.clientY / P.h; view.px = e.clientX; view.py = e.clientY; view.hover = !e.buttons;
      wake();
    }, { passive: true });
    document.documentElement.addEventListener("pointerleave", () => { view.hover = false; });
  }

  fit(); build();
  // until chapters.js measures the hero and pour() runs, every dot waits just above the screen
  for (let i = 0; i < N; i++) { x[i] = Math.random() * P.w; y[i] = -60; hold[i] = 0.5; }
  if (reduce) { snap(); render(); }
})();
