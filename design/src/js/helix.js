/* Hero: a turning double helix in 3D, standing upright and tilted. It is yawed, pitched and rolled, then projected
   with perspective, so its near end is larger and brighter than its far end. One rung group per project glows in its
   hue, and each project's name sits to the right of its group. A sideways drag or flick, by mouse or finger, spins it.
   Every CYCLE seconds a replication fork runs its length; on the way to the first chapter it unzips, far end first. */
window.LAB = window.LAB || {};
(() => {
  const L = window.LAB, TAU = Math.PI * 2;
  // yaw turns the axis away from the viewer, pitch tips its top back, roll tilts it on screen
  const POSE = { yaw: 0.18, pitch: 0.42, roll: 0.1, turns: 3.4 };
  const LEN = 1000, R = 125, SPREAD = 0.2; // model units; the fit scales them to the stage
  // replication: every CYCLE seconds a fork runs the length of the helix in RUN seconds. Ahead of it the helix is
  // whole; at it the strands peel apart and the rungs pull back into them; behind it they zip up again.
  const CYCLE = 16, RUN = 9, FORK = 0.09;
  let m = 0, u, side, frac, jx, nR = 1, phase = 0, spin = 0, last = 0, view = null;
  // spin: extra turn in rad per wall-clock second, positive turns the near side to the right
  let held = null, FLICK = null, wall = 0; // the press spinning it now; the flick tokens; the last step's wall clock

  // pure rules, kept apart from the DOM so tests can run them
  L.helixRules = {
    // the pointer's sideways speed in px/s over its last `win` ms, up to `now`: a pointer that stopped reads 0
    velocity(pts, now, win) {
      const recent = pts.filter((p) => p.t >= now - win);
      if (recent.length < 2) return 0;
      const a = recent[0], b = recent[recent.length - 1], ms = Math.max(now - a.t, 8);
      return ((b.x - a.x) / ms) * 1000;
    },
    // px/s to rad/s: a swipe across the whole stage in one second turns it `sens` radians, on any screen size,
    // capped so the dots' springs never lag into a cloud
    spinRate: (pxPerS, width, sens, cap) => (width > 0 ? Math.max(-cap, Math.min(cap, (pxPerS / width) * sens)) : 0),
    // a released spin decays exponentially with time constant `tau` seconds
    coast: (w, dt, tau) => w * Math.exp(-dt / tau),
  };
  const rate = (h, now) => L.helixRules.spinRate(L.helixRules.velocity(h.pts, now, FLICK.win), h.w, FLICK.sens, FLICK.cap);

  // local coordinates: `along` the axis (top to bottom), `across` it, `deep` toward the viewer
  function rotate(v, along, across, deep) {
    const x = across, y = along, z = deep;
    const x1 = x * v.cy + z * v.sy, z1 = -x * v.sy + z * v.cy;
    const y1 = y * v.cp - z1 * v.sp, z2 = y * v.sp + z1 * v.cp;
    return [x1 * v.cr - y1 * v.sr, x1 * v.sr + y1 * v.cr, z2];
  }
  // perspective, then the fit that places the whole helix in its stage
  function project(v, p) {
    const k = v.F / (v.F - p[2]);
    return { x: v.ox + p[0] * k * v.s, y: v.oy + p[1] * k * v.s, k };
  }
  // the projected outline of the cylinder the helix turns inside, widened so the fork's open strands still fit
  function outline(v) {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const a of [-LEN / 2, 0, LEN / 2]) for (let k = 0; k < 24; k++) {
      const th = (k / 24) * TAU, q = project(v, rotate(v, a, R * (1 + SPREAD) * Math.sin(th), R * Math.cos(th)));
      x0 = Math.min(x0, q.x); x1 = Math.max(x1, q.x); y0 = Math.min(y0, q.y); y1 = Math.max(y1, q.y);
    }
    return { x0, x1, y0, y1, w: x1 - x0, h: y1 - y0 };
  }

  // phones: the helix left of centre, names to its right. Wide screens: the same, with the line on the far right.
  function layout(c) {
    const room = c.small ? { w: c.sw * 0.62, h: c.sh * 0.96, cx: c.sx + c.sw * 0.34 } : { w: c.sw * 0.5, h: c.sh * 0.96, cx: c.sx + c.sw * 0.36 };
    const v = { len: LEN, R, F: LEN * 1.9, s: 1, ox: 0, oy: 0, turns: POSE.turns,
      cy: Math.cos(POSE.yaw), sy: Math.sin(POSE.yaw), cp: Math.cos(POSE.pitch), sp: Math.sin(POSE.pitch), cr: Math.cos(POSE.roll), sr: Math.sin(POSE.roll) };
    const o = outline(v);
    v.s = Math.min(room.w / o.w, room.h / o.h);
    v.ox = room.cx - ((o.x0 + o.x1) / 2) * v.s; v.oy = c.sy + c.sh / 2 - ((o.y0 + o.y1) / 2) * v.s;
    return v;
  }

  // each name sits just right of its rung group's ring, level with the group's middle
  function placeNames(c, v) {
    const box = document.querySelector(".helix"), nav = document.querySelector(".helix__names");
    if (!box || !nav) return;
    const r = box.getBoundingClientRect(), bx = r.left, by = r.top + scrollY, links = nav.querySelectorAll("a"), G = links.length;
    links.forEach((a, g) => {
      const along = ((g + 0.5) / G - 0.5) * LEN, mid = project(v, rotate(v, along, 0, 0));
      let edge = -Infinity;
      for (let k = 0; k < 16; k++) {
        const th = (k / 16) * TAU;
        edge = Math.max(edge, project(v, rotate(v, along, R * Math.sin(th), R * Math.cos(th))).x);
      }
      a.style.left = `${edge + 10 - bx}px`;
      a.style.top = `${mid.y - by}px`;
    });
    box.classList.add("is-placed");
    box.classList.remove("js-wait");
  }

  // the name of the project the fork is passing is marked, so the helix reads the projects one by one
  let names = null, readingNow = -2;
  function reading(fork, G) {
    const g = fork > 0 && fork < 1 ? Math.floor(fork * G) : -1;
    if (g === readingNow) return;
    readingNow = g;
    names = names || document.querySelectorAll(".helix__names a");
    names.forEach((a, k) => a.classList.toggle("is-reading", k === g));
  }

  L.shapes.hero = {
    init(P, c) {
      const r = L.rng(11);
      m = c.sw ? Math.floor(P.n * 0.8) : 0; // no stage measured yet: dust only
      u = new Float32Array(P.n); side = new Int8Array(P.n); frac = new Float32Array(P.n); jx = new Float32Array(P.n);
      view = m ? layout(c) : null;
      nR = Math.round(view ? view.turns * 10 : 5);
      const G = L.HUES.length, lit = (k) => { const g = Math.floor((k / nR) * G); return Math.abs(k - (g + 0.5) * nR / G) <= 1.2 ? g : -1; };
      for (let i = 0; i < P.n; i++) {
        if (i >= m) { L.ambient(P, r, i); continue; }
        L.claim(P, i);
        jx[i] = (r() - 0.5) * 2; // a fixed offset, so the backbones have thickness without shimmering
        if (i % 10 < 7) { side[i] = i & 1 ? 1 : -1; u[i] = r(); } // the two backbones carry the shape, so most dots go there
        else { // a base pair: two half-rungs meeting with a small gap in the middle
          const k = 1 + Math.floor(r() * (nR - 1)), g = lit(k), f = r() * 0.9;
          side[i] = 0; u[i] = k / nR; frac[i] = f < 0.45 ? f : f + 0.1;
          if (g >= 0) { P.cls[i] = 2 + g; P.lit[i] = 1; }
          else if ((k & 1) === (frac[i] < 0.5 ? 1 : 0)) P.cls[i] = 1; // alternate the halves' tone, like paired bases
        }
        P.ord[i] = (1 - u[i]) * 0.9 + r() * 0.1; // leaving: the bottom lets go first
        P.enter[i] = u[i]; // arriving: it fills from the top down
      }
      if (view) placeNames(c, view);
    },
    step(P, c, t) {
      if (!m) return;
      const dt = Math.min(0.05, Math.max(0, t - last)); last = t;
      const now = performance.now(), dw = Math.min(0.05, Math.max(0, (now - wall) / 1000)); wall = now;
      if (held) spin = rate(held, now); // held: it follows the pointer
      else if (spin) spin = Math.abs(spin) < 0.01 ? 0 : L.helixRules.coast(spin, dw, FLICK.tau);
      phase += 0.2 * dt + spin * dw;
      const v = view, k = TAU * v.turns / v.len, G = L.HUES.length;
      const fork = -0.15 + ((t % CYCLE) / RUN) * 1.3; // past 1.15 it has left the helix until the next cycle
      reading(fork, G);
      for (let i = 0; i < m; i++) {
        const a = (u[i] - 0.5) * v.len, th = (u[i] * v.len) * k + phase;
        const d = (u[i] - fork) / FORK, open = Math.exp(-d * d); // 1 at the fork, 0 away from it
        let across, deep;
        if (side[i]) {
          const s = th + (side[i] < 0 ? Math.PI : 0);
          across = R * Math.sin(s) + jx[i] + side[i] * open * R * SPREAD; deep = R * Math.cos(s) * (1 - 0.6 * open);
          // while open, the strands glow in the colour of the project they are passing
          const lit = open > 0.35; P.lit[i] = lit ? 1 : 0; P.cls[i] = lit ? 2 + Math.min(G - 1, Math.floor(u[i] * G)) : 0;
        } else { // each half-rung pulls back into its own strand as the fork opens it
          const f = frac[i] < 0.5 ? frac[i] * (1 - open) : 1 - (1 - frac[i]) * (1 - open), w = 1 - 2 * f;
          across = R * Math.sin(th) * w + (f < 0.5 ? 1 : -1) * open * R * SPREAD; deep = R * Math.cos(th) * w * (1 - 0.6 * open);
        }
        const q = project(v, rotate(v, a, across, deep));
        P.tx[i] = q.x; P.ty[i] = q.y;
        // nearer is larger and brighter; q.k runs from about 0.88 (far) to 1.15 (near). Lit rungs never shrink,
        // so the far end's project still reads.
        const sz = Math.max(0.6, Math.min(1.6, 1 + (q.k - 1) * 4));
        P.sz[i] = P.lit[i] ? Math.max(1, sz) : sz;
        if (!P.lit[i]) P.lvl[i] = side[i] ? (q.k < 0.96 ? 0 : q.k < 1.04 ? 1 : 2) : (q.k < 1 ? 0 : 1);
      }
    },
  };

  // Flick to spin. While held, the helix turns at the pointer's sideways speed (its last FLICK.win ms), so it feels
  // attached; on release it keeps that speed and coasts down like a fidget spinner. On a touch screen the stage is
  // pan-y, so an up-or-down swipe goes to the browser to scroll (pointercancel) and only a sideways swipe spins it.
  L.helixState = () => ({ spin, phase, held: !!held }); // read-only, for tests and the browser checks
  const stage = document.querySelector(".helix__stage");
  if (!stage || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const css = getComputedStyle(document.documentElement), num = (n) => parseFloat(css.getPropertyValue(n));
  FLICK = { sens: num("--spin-sens"), cap: num("--spin-cap"), tau: num("--spin-coast") / 1000, win: num("--spin-window") };
  const root = document.documentElement, noSelect = (e) => e.preventDefault();
  stage.addEventListener("pointerdown", (e) => {
    if (e.button) return; // the main button or a finger only
    held = { id: e.pointerId, w: stage.clientWidth, pts: [{ t: e.timeStamp, x: e.clientX }] };
    if (e.pointerType === "mouse") { // a mouse drag must not select text or start a native drag on the names
      e.preventDefault(); stage.setPointerCapture(e.pointerId);
      root.classList.add("is-spinning"); addEventListener("selectstart", noSelect);
    }
  });
  stage.addEventListener("pointermove", (e) => {
    if (!held || e.pointerId !== held.id) return;
    held.pts.push({ t: e.timeStamp, x: e.clientX });
    if (held.pts.length > 32) held.pts.shift();
  }, { passive: true });
  const release = (e) => {
    if (!held || e.pointerId !== held.id) return;
    // a flick keeps the speed it was released at; a held-still release, none; a cancel (the page scrolled), none
    if (e.type === "pointerup") held.pts.push({ t: e.timeStamp, x: e.clientX });
    spin = e.type === "pointerup" ? rate(held, e.timeStamp) : 0;
    held = null;
    root.classList.remove("is-spinning"); removeEventListener("selectstart", noSelect);
  };
  stage.addEventListener("pointerup", release);
  stage.addEventListener("pointercancel", release);
})();
