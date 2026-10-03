/* Shapes: where the particles go. Each shape fills a stage box c = {sx, sy, sw, sh} (page coordinates; the field
   scrolls it with the page) and has init() (once per switch) and an optional step(t) that moves targets or lights dots.
   Classes: 0 ink, 1 signal, then one per project hue in L.HUES order. P.lvl is brightness 0-2; lit dots draw largest.
   P.ord is when a dot lets go on the way to the next shape, in fractions of the hand-off (0 = first). */
window.LAB = window.LAB || {};
(() => {
  const TAU = Math.PI * 2;
  const L = window.LAB;
  L.HUES = ["jarvis", "teamwatch", "tcg", "seat", "lock"]; // page order: the helix lights one rung group per project
  L.hue = (id) => 2 + L.HUES.indexOf(id);

  // seeded so a shape looks the same every visit
  L.rng = (seed) => () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  // dots a shape does not claim drift across the screen as faint dust
  L.ambient = (P, r, i) => {
    P.tx[i] = r() * P.w; P.ty[i] = r() * P.h;
    P.cls[i] = r() < 0.85 ? 0 : 1; P.lit[i] = 0; P.amb[i] = 1; P.fast[i] = 0; P.lvl[i] = r() < 0.5 ? 0 : 1; P.ord[i] = 0; P.sz[i] = 1; P.enter[i] = r();
  };
  // reset everything, colour included: a dot otherwise keeps the class of the last shape that used it
  L.claim = (P, i) => { P.amb[i] = 0; P.cls[i] = 0; P.lit[i] = 0; P.fast[i] = 0; P.lvl[i] = 1 + (i & 1); P.ord[i] = 0; P.sz[i] = 1; P.enter[i] = 0; };
  const motifCount = (P) => Math.floor(P.n * 0.3);
  const put = (P, i, c, fx, fy, j) => { P.tx[i] = c.sx + fx * c.sw + (j ? (Math.random() - 0.5) * j : 0); P.ty[i] = c.sy + fy * c.sh + (j ? (Math.random() - 0.5) * j : 0); };

  // Crisp shapes: a fixed list of slots {x, y (box fractions), cls, lvl, ...}; claimed dots share them round-robin
  // with a pixel of jitter. More slots than dots: keep an even sample, so the outline never has holes in one place.
  const fill = (P, c, m, list, r) => {
    const step = Math.max(1, list.length / m), out = new Array(m);
    for (let i = 0; i < m; i++) {
      const s = list[Math.floor((i * step) % list.length)];
      out[i] = s; L.claim(P, i);
      put(P, i, c, s.x, s.y, 0);
      P.cls[i] = s.cls; P.lvl[i] = s.lvl;
    }
    return out;
  };

  L.shapes = {};

  // ff-jarvis: the model's season totals (its hue) above plain ADP (ink) over 15 backtested seasons; it wins 12.
  // A bright head runs along the model line, season by season.
  L.shapes.jarvis = (() => {
    const N = 15, LOSE = [3, 8, 13];
    let m, kind, fx;
    return {
      init(P, c) {
        const r = L.rng(23), H = L.hue("jarvis"); m = motifCount(P); kind = new Uint8Array(P.n); fx = new Float32Array(P.n);
        const rs = L.rng(3), xs = [], ya = [], ym = [];
        let base = 0.62;
        for (let k = 0; k < N; k++) {
          base = Math.min(0.8, Math.max(0.5, base + (rs() - 0.5) * 0.14));
          xs.push(0.04 + 0.92 * k / (N - 1)); ya.push(base);
          ym.push(base - (LOSE.includes(k) ? -(0.05 + 0.06 * rs()) : 0.14 + 0.26 * rs()));
        }
        for (let i = 0; i < P.n; i++) {
          if (i >= m) { L.ambient(P, r, i); continue; }
          L.claim(P, i);
          const roll = i % 10;
          if (roll === 9) { // a season marker on the model line
            const k = i % N; kind[i] = 2; fx[i] = xs[k];
            put(P, i, c, xs[k], ym[k], 4); P.cls[i] = LOSE.includes(k) ? 0 : H; P.lvl[i] = 2; continue;
          }
          const ys = roll < 4 ? ya : ym, t = r() * (N - 1), k = Math.floor(t), f = t - k;
          kind[i] = roll < 4 ? 0 : 1; fx[i] = xs[k] + (xs[k + 1] - xs[k]) * f;
          put(P, i, c, fx[i], ys[k] + (ys[k + 1] - ys[k]) * f, 2);
          P.cls[i] = kind[i] ? H : 0; P.lvl[i] = kind[i] ? 2 : 0;
        }
      },
      step(P, c, t) {
        const head = ((t % 5) / 5) * 1.2 - 0.05;
        for (let i = 0; i < m; i++) if (kind[i]) P.lit[i] = fx[i] <= head && fx[i] > head - 0.12 ? 1 : 0;
      },
    };
  })();

  // Restock Watch: a shelf of sealed boxes. One at a time a box comes back in stock: its outline lights in the
  // watcher's hue and the alert's ping ripples out above it.
  L.shapes.tcg = (() => {
    const XS = [0.18, 0.34, 0.5, 0.66, 0.82], BASE = 0.9, BW = 0.1, BH = 0.42, EVERY = 2;
    let m, slot;
    return {
      init(P, c) {
        const r = L.rng(51), H = L.hue("tcg"), list = []; m = motifCount(P);
        const sp = Math.max(4, c.sh / 26), dx = sp / c.sw, dy = sp / c.sh;
        for (let x = 0.06; x < 0.94; x += dx * 1.5) list.push({ x, y: BASE + dy * 0.8, cls: 0, lvl: 0 }); // the shelf
        XS.forEach((cx, j) => { // each box: an outline, plus a line across its lid
          for (let x = cx - BW / 2; x <= cx + BW / 2; x += dx) for (const y of [BASE, BASE - BH, BASE - BH + dy * 1.6]) list.push({ x, y, box: j, cls: 0, lvl: 1 });
          for (let y = BASE - BH; y <= BASE; y += dy) for (const x of [cx - BW / 2, cx + BW / 2]) list.push({ x, y, box: j, cls: 0, lvl: 1 });
        });
        for (let k = 0; k < 28; k++) list.push({ ring: (k / 28) * TAU, cls: H, lvl: 2 });
        for (let i = m; i < P.n; i++) L.ambient(P, r, i);
        slot = fill(P, c, m, list, r);
        for (let i = 0; i < m; i++) if (slot[i].ring !== undefined) P.fast[i] = 1;
      },
      step(P, c, t) {
        const H = L.hue("tcg"), on = Math.floor(t / EVERY) % XS.length, k = (t % EVERY) / EVERY;
        const rad = (0.04 + 0.14 * k) * c.sh, cx = c.sx + XS[on] * c.sw, cy = c.sy + (BASE - BH - 0.14) * c.sh;
        for (let i = 0; i < m; i++) {
          const s = slot[i];
          if (s.box !== undefined) { const lit = s.box === on; P.cls[i] = lit ? H : 0; P.lit[i] = lit ? 1 : 0; continue; }
          if (s.ring === undefined) continue;
          P.tx[i] = cx + Math.cos(s.ring) * rad; P.ty[i] = cy + Math.sin(s.ring) * rad;
          P.lvl[i] = k < 0.4 ? 2 : k < 0.75 ? 1 : 0; P.lit[i] = k < 0.2 ? 1 : 0;
        }
      },
    };
  })();

  // seat-scout: a curved auditorium under its screen; the best open block glows, and seats open and close as you watch
  L.shapes.seat = (() => {
    const COLS = 13, ROWS = 7;
    let seat, m, H;
    return {
      init(P, c) {
        const r = L.rng(37); m = motifCount(P); seat = new Int16Array(P.n); H = L.hue("seat");
        const gap = Math.min(1 / (COLS + 1), (c.sh / c.sw) / (ROWS + 2.5)), rowGap = gap * c.sw / c.sh;
        for (let i = 0; i < P.n; i++) {
          if (i >= m) { L.ambient(P, r, i); continue; }
          L.claim(P, i);
          if (i % 9 === 0) { // the screen: a shallow arc across the top
            const u = r() - 0.5; seat[i] = -1;
            put(P, i, c, 0.5 + u * gap * COLS, 0.05 + u * u * 0.25, 0); P.cls[i] = 0; P.lvl[i] = 2; continue;
          }
          const s = i % (COLS * ROWS), col = s % COLS, row = Math.floor(s / COLS), dx = col - (COLS - 1) / 2;
          seat[i] = s;
          put(P, i, c, 0.5 + dx * gap + (r() - 0.5) * gap * 0.15, 0.24 + row * rowGap + dx * dx * rowGap * 0.03 + (r() - 0.5) * rowGap * 0.15, 0);
          const best = row >= 3 && row <= 4 && col >= 5 && col <= 7, taken = !best && r() < 0.45;
          P.cls[i] = best ? H : 0; P.lit[i] = best ? 1 : 0; P.lvl[i] = taken ? 0 : 2;
        }
      },
      step(P, c, t) {
        // one seat outside the best block flips every 1.6 s
        const flip = Math.floor(t / 1.6), a = (flip * 7) % (COLS * ROWS), b = (flip * 13 + 5) % (COLS * ROWS);
        for (let i = 0; i < m; i++) {
          if (seat[i] === a && !P.lit[i]) P.lvl[i] = 0;
          if (seat[i] === b && !P.lit[i]) P.lvl[i] = 2;
        }
      },
    };
  })();

  // Team Watch: its two signature screens. Left, this week's roster as a fanned pack of cards, the lit card cycling
  // like the rip. Right, a player's stat sphere unfolded into its radar: a six-spoke web with the player's season
  // ranks as a shape in the paper's hue, morphing between two players.
  L.shapes.teamwatch = (() => {
    // spoke lengths, 1 = ranked first: workload, red zone, share, big runs, routes, yards over expected
    const PLAYERS = [[1, 1, 0.85, 0.7, 0.6, 0.35], [0.5, 0.35, 0.9, 0.95, 0.45, 0.85]];
    const ang = (k) => -Math.PI / 2 + (k * TAU) / 6;
    let slot, m, H, R;
    const spot = (c, rad, a) => ({ x: 0.7 + (rad * Math.cos(a)) / c.sw, y: 0.5 + (rad * Math.sin(a)) / c.sh });
    return {
      init(P, c) {
        const r = L.rng(71), list = []; m = motifCount(P); H = L.hue("teamwatch");
        const unit = Math.min(c.sh, c.sw * 0.4); R = unit * 0.45; // sized to the box's short side, so a narrow box still fits
        // the web: three hexagon rings and six spokes, dim
        for (const f of [1 / 3, 2 / 3, 1]) for (let k = 0; k < 6; k++) for (let t = 0; t < 1; t += 0.125) {
          const p0 = spot(c, R * f, ang(k)), p1 = spot(c, R * f, ang(k + 1));
          list.push({ x: p0.x + (p1.x - p0.x) * t, y: p0.y + (p1.y - p0.y) * t, cls: 0, lvl: 0 });
        }
        for (let k = 0; k < 6; k++) for (let t = 0.1; t <= 1; t += 0.15) list.push(Object.assign(spot(c, R * t, ang(k)), { cls: 0, lvl: 0 }));
        // the player's shape: slots along its six edges, placed each frame in step()
        for (let k = 0; k < 6; k++) for (let t = 0; t < 1; t += 1 / 12) list.push({ poly: true, k, t, cls: H, lvl: 2 });
        // the pack: three card outlines fanned around a point left of centre
        const cw = unit * 0.42, ch = unit * 0.64, px = c.sw * 0.26, py = c.sh * 0.55;
        for (let j = 0; j < 3; j++) {
          const rot = (j - 1) * 0.24, ox = px + (j - 1) * cw * 0.38, oy = py + Math.abs(j - 1) * unit * 0.04;
          const per = 2 * (cw + ch);
          for (let d = 0; d < per; d += 4) {
            let x, y;
            if (d < cw) { x = d; y = 0; } else if (d < cw + ch) { x = cw; y = d - cw; }
            else if (d < 2 * cw + ch) { x = 2 * cw + ch - d; y = ch; } else { x = 0; y = per - d; }
            x -= cw / 2; y -= ch / 2;
            const cr = Math.cos(rot), sr = Math.sin(rot);
            list.push({ x: (ox + x * cr - y * sr) / c.sw, y: (oy + x * sr + y * cr) / c.sh, cls: 0, lvl: 1, card: j });
          }
        }
        for (let i = m; i < P.n; i++) L.ambient(P, r, i);
        slot = fill(P, c, m, list, r);
      },
      step(P, c, t) {
        const e = 0.5 - 0.5 * Math.cos(((t % 6) / 6) * TAU); // 0 to 1 and back over six seconds
        const val = (k) => PLAYERS[0][k % 6] * (1 - e) + PLAYERS[1][k % 6] * e;
        const lit = Math.floor(t / 1.5) % 3;
        for (let i = 0; i < m; i++) {
          const s = slot[i];
          if (s.poly) {
            const a = spot(c, R * val(s.k), ang(s.k)), b = spot(c, R * val(s.k + 1), ang(s.k + 1));
            P.tx[i] = c.sx + (a.x + (b.x - a.x) * s.t) * c.sw; P.ty[i] = c.sy + (a.y + (b.y - a.y) * s.t) * c.sh;
          } else if (s.card !== undefined) {
            const on = s.card === lit; P.cls[i] = on ? H : 0; P.lit[i] = on ? 1 : 0;
          }
        }
      },
    };
  })();

  // Team Lock: a play call, drawn the way a coach draws one. Offence as O's under the line of scrimmage, the defence
  // as dim X's (the reads you can't see), the receiver's route in the game's hue, and the ball thrown down it.
  L.shapes.lock = (() => {
    const QB = { x: 0.5, y: 0.84 }, CATCH = { x: 0.66, y: 0.1 };
    let slot, m;
    // the right receiver's route: up the sideline, then breaking in toward the middle
    const route = (k) => k < 0.6 ? { x: 0.88, y: 0.58 - (k / 0.6) * 0.36 } : { x: 0.88 - ((k - 0.6) / 0.4) * 0.22, y: 0.22 - ((k - 0.6) / 0.4) * 0.12 };
    return {
      init(P, c) {
        const r = L.rng(63), H = L.hue("lock"), list = []; m = motifCount(P);
        const sp = Math.max(4, c.sw / 85), dx = sp / c.sw, asp = c.sh / c.sw, rad = 0.028; // rad in box widths
        for (let x = 0.03; x < 0.97; x += dx) if ((x / dx) % 4 < 2.6) list.push({ x, y: 0.5, cls: 0, lvl: 0 }); // the line, dashed
        const O = (cx, cy) => { for (let k = 0; k < 14; k++) { const a = k / 14 * TAU; list.push({ x: cx + Math.cos(a) * rad, y: cy + Math.sin(a) * rad / asp, cls: 0, lvl: 2 }); } };
        const X = (cx, cy) => { for (let k = -4; k <= 4; k++) { const d = k / 4 * rad; list.push({ x: cx + d, y: cy + d / asp, cls: 0, lvl: 0 }, { x: cx + d, y: cy - d / asp, cls: 0, lvl: 0 }); } };
        for (const x of [0.38, 0.44, 0.5, 0.56, 0.62]) O(x, 0.62);
        O(QB.x, QB.y); O(0.12, 0.6); O(0.88, 0.6);
        for (const [x, y] of [[0.2, 0.36], [0.38, 0.38], [0.5, 0.34], [0.62, 0.38], [0.8, 0.36], [0.35, 0.14], [0.65, 0.16]]) X(x, y);
        for (let k = 0; k <= 1; k += 0.025) { const p = route(k); list.push({ x: p.x, y: p.y, cls: H, lvl: 2 }); }
        for (let k = 0; k < 18; k++) list.push({ ball: true, cls: H, lvl: 2 });
        for (let i = m; i < P.n; i++) L.ambient(P, r, i);
        slot = fill(P, c, m, list, r);
        for (let i = 0; i < m; i++) if (slot[i].ball) { P.fast[i] = 1; P.lit[i] = 1; }
      },
      step(P, c, t) {
        // the ball leaves the QB, arcs to the catch point, and rests there before the next snap
        const k = Math.min((t * 0.45) % 1.6, 1), lift = Math.sin(k * Math.PI) * 0.25;
        const bx = c.sx + (QB.x + (CATCH.x - QB.x) * k) * c.sw, by = c.sy + (QB.y + (CATCH.y - QB.y) * k - lift) * c.sh;
        for (let i = 0; i < m; i++) {
          if (!slot[i].ball) continue;
          const a = (i * 2.4) % TAU, d = Math.sqrt((i % 18) / 18) * 3.5; // a small blob, not a trail
          P.tx[i] = bx + Math.cos(a) * d; P.ty[i] = by + Math.sin(a) * d;
        }
      },
    };
  })();
})();
