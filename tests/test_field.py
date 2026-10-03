"""The field's frame cost and idle behaviour, run in Node against a stub DOM and canvas. Needs Node; skipped without it.
Guards the 2026-10-03 cleanup: one bucketed draw per frame (it was 56 passes over every dot), no token reads per
frame, no rAF while the page is hidden, and no shape rebuild for a phone URL bar showing or hiding. Dots are round
(one filled circle each, under the bucket's style), not fillRect squares.
Guards the calmer field too: a touch screen gets its full canvas resolution, a full frame rate, no hover or parallax,
one wake for a real tap, and a small capped trail for a swipe (restored 2026-10-03 after the phone lost its swipe)."""
import json
import pathlib
import shutil
import subprocess

import pytest

SRC = pathlib.Path(__file__).resolve().parent.parent / "design" / "src" / "js"

HARNESS = r"""
const fs = require("fs"), path = require("path"), src = process.argv[2], fine = process.argv[3] === "fine";
global.window = global;
const handlers = {}, docHandlers = {}, out = {};
global.addEventListener = (t, f) => { (handlers[t] = handlers[t] || []).push(f); };
global.dispatchEvent = (e) => { for (const f of handlers[e.type] || []) f(e); return !e.defaultPrevented; };
global.CustomEvent = class { constructor(type, o) { this.type = type; this.cancelable = !!(o && o.cancelable); this.defaultPrevented = false; }
  preventDefault() { if (this.cancelable) this.defaultPrevented = true; } };
let raf = [], rafId = 0, timers = [];
global.requestAnimationFrame = (f) => { raf.push(f); return ++rafId; };
global.cancelAnimationFrame = () => { raf = []; };
global.setTimeout = (f) => { timers.push(f); return timers.length; };
global.clearTimeout = () => { timers = []; };
global.innerWidth = 1280; global.innerHeight = 800; global.devicePixelRatio = 3;
// a mouse screen matches the hover query; a touch screen matches nothing (and reduced motion is off in both)
global.matchMedia = (q) => ({ matches: fine && q.includes("hover") });
let tokenReads = 0;
const css = fs.readFileSync(path.join(src, "..", "css", "tokens.css"), "utf8"), TOK = {};
for (const m of css.matchAll(/(--[\w-]+):\s*([^;]+);/g)) if (!(m[1] in TOK)) TOK[m[1]] = m[2].trim();
Object.assign(TOK, { "--field-count": "1200", "--field-count-phone": "600" }); // smaller, so the test runs fast
global.getComputedStyle = () => ({ getPropertyValue: (n) => { tokenReads++; return TOK[n] || "#a0b0c0"; } });
const calls = [];
let clears = 0;
// a dot is one full circle, filled on its own: arc() records it, fill() paints it under the current style
let squares = 0, open = [], radii = [], partial = 0;
const ctx = { fillStyle: "", globalAlpha: 1, setTransform() {},
  clearRect() { clears++; calls.length = 0; radii = []; partial = 0; }, fillRect() { squares++; },
  beginPath() { open = []; }, moveTo() {}, lineTo() {},
  arc(px, py, r, a0, a1) { open.push(r); if (Math.abs(a1 - a0 - 2 * Math.PI) > 1e-9) partial++; },
  fill() { if (open.length === 1) { calls.push(ctx.fillStyle + "@" + ctx.globalAlpha); radii.push(open[0]); } else partial++; } };
const canvas = { width: 0, height: 0, getContext: () => ctx };
global.document = { hidden: false, getElementById: () => canvas, querySelector: () => null, querySelectorAll: () => [],
  documentElement: { addEventListener: (t, f) => { docHandlers[t] = f; } } };
for (const f of ["shapes.js", "helix.js", "field.js"]) eval(fs.readFileSync(path.join(src, f), "utf8"));
const L = window.LAB;
let inits = 0;
const init = L.shapes.hero.init;
L.shapes.hero.init = (P, c) => { inits++; init(P, c); };
L.field.setStop("hero", { sx: 100, sy: 100, sw: 600, sh: 600 }, 0);

const tick = (now) => { const q = raf; raf = []; for (const f of q) f(now); };
for (let k = 1; k <= 120; k++) tick(1000 + k * 16.7); // two seconds: the pour finishes and the dots settle
const before = tokenReads;
squares = 0;
tick(4000);
out.tokenReadsPerFrame = tokenReads - before;
out.squares = squares;
out.partial = partial; // a fill that is not exactly one full circle
out.radii = [Math.min(...radii), Math.max(...radii)];
out.dots = calls.length;
// each colour and alpha forms one run: the frame drew bucket by bucket, not dot by dot
out.runs = calls.filter((c, i) => i === 0 || c !== calls[i - 1]).length;
out.styles = new Set(calls.map((c) => c.split("@")[0])).size;
out.canvasW = canvas.width;
out.moveHandlers = (handlers.pointermove || []).length;

// idle cadence: settle well past the calm threshold, then count draws over 60 frames
let clock = 4000;
const run = (n) => { for (let k = 0; k < n; k++) tick(clock += 16.7); };
run(600);
const c0 = clears;
run(60);
out.drawsPer60 = clears - c0;

// a tap leaves a wake; a swipe, a cancelled touch or a long press leaves none
const press = (x, y, at) => { for (const f of handlers.pointerdown) f({ clientX: x, clientY: y, timeStamp: at, pointerType: "touch" }); };
const lift = (x, y, at) => { for (const f of handlers.pointerup) f({ clientX: x, clientY: y, timeStamp: at, pointerType: "touch" }); };
const wakesAfter = (go) => { go(); const n = L.field.wakeCount(); run(120); return n; };
out.tap = wakesAfter(() => { press(200, 300, 0); lift(203, 302, 120); });
out.swipe = wakesAfter(() => { press(200, 500, 0); lift(205, 300, 200); });
out.cancelled = wakesAfter(() => { press(200, 500, 0); for (const f of handlers.pointercancel) f({}); lift(200, 500, 100); });
out.longPress = wakesAfter(() => { press(200, 300, 0); lift(200, 300, 900); });
// a mouse click leaves a wake however long it was held; a mouse drag (spinning the helix) leaves none
const mouse = (type, x, y, at) => { for (const f of handlers[type]) f({ clientX: x, clientY: y, timeStamp: at, pointerType: "mouse" }); };
out.mouseClick = wakesAfter(() => { mouse("pointerdown", 200, 300, 0); mouse("pointerup", 202, 301, 900); });
out.mouseDrag = wakesAfter(() => { mouse("pointerdown", 200, 300, 0); mouse("pointerup", 500, 310, 200); });
out.wakeGone = L.field.wakeCount();
// a finger's trail: touchmove keeps coming while the page scrolls; one wake per 0.6 radii (0.6 * 128 px here), capped
const touch = (type, x, y) => { for (const f of handlers[type] || []) f({ touches: type === "touchend" ? [] : [{ clientX: x, clientY: y }] }); };
const swipe = (dist) => wakesAfter(() => { touch("touchstart", 200, 700); for (let d = 10; d <= dist; d += 10) touch("touchmove", 200, 700 - d); touch("touchend"); });
out.trailShort = swipe(200);
out.trailLong = swipe(4000);
out.trailStill = swipe(0);
const R = L.fieldRules;
out.rules = { tapEdge: R.isTap(6, 8, 300, 10, 300), tapFar: R.isTap(8, 8, 100, 10, 300), tapSlow: R.isTap(0, 0, 301, 10, 300),
  clickEdge: R.isClick(6, 8, 10), clickFar: R.isClick(8, 8, 10),
  dprPhone: R.dpr(3, false, 2, 3), dprPhone2: R.dpr(2, false, 2, 3), dprDesk: R.dpr(3, true, 2, 3), dprLow: R.dpr(1, false, 2, 3),
  wakePhone: R.wakeRadius(390, 844, 0.16), wakeDesk: R.wakeRadius(1280, 800, 0.16) };

// a mouse parked over the dust (clear of the turning helix): the dots in its dent must settle, not pulse forever.
// Measured as the fastest dot near the cursor over 2 s, against the same spot with no mouse.
if (fine) {
  const fastestNear = () => { let m = 0; for (let k = 0; k < 120; k++) { run(1); m = Math.max(m, L.field.speedNear(1100, 720, 250)); } return m; };
  // the hole: the dust dots within 90 px of the spot, and their mean distance from it before, parked, and after
  const near = L.field.distances(1100, 720).filter(([, d]) => d < 150).map(([i]) => i);
  const meanDist = () => { const ds = L.field.distances(1100, 720, near); return ds.reduce((s, [, d]) => s + d, 0) / (ds.length || 1); };
  run(300); out.freeSpeed = fastestNear(); out.freeCore = near.length; out.freeMean = meanDist();
  for (const f of handlers.pointermove) f({ pointerType: "mouse", clientX: 1100, clientY: 720, buttons: 0 });
  run(600); out.parkedSpeed = fastestNear(); out.parkedMean = meanDist();
  // the cursor leaves: the dots fill the hole back in
  docHandlers.pointerleave(); run(600); out.leftMean = meanDist();
  // parked on the turning helix (its stage spans 100-700): its strands stream past and must not bulge as they go,
  // so the dots near the cursor move no faster than the helix's own turn moves them
  const onHelix = () => { let m = 0; for (let k = 0; k < 240; k++) { run(1); m = Math.max(m, L.field.speedNear(400, 400, 120)); } return m; };
  out.helixFree = onHelix();
  for (const f of handlers.pointermove) f({ pointerType: "mouse", clientX: 400, clientY: 400, buttons: 0 });
  run(300); out.helixParked = onHelix();
  docHandlers.pointerleave(); run(600);
  // the moment a sweep stops over the dust: the hole shrinks from its moving size to its parked one. If that happens
  // in a few frames the dust's springs get kicked and bounce in and out (the "lens pulse" David saw). Measured as
  // the fastest dust dot near the cursor in the 2 s right after it stops, and the same for the cursor arriving.
  const move = (x) => { for (const f of handlers.pointermove) f({ pointerType: "mouse", clientX: x, clientY: 720, buttons: 0 }); };
  // A pulse is dots reversing in and out; a glide home reverses once at most. Over the 3 s after the event, follow
  // every dot within 200 px of the cursor and count how often its distance from the cursor turns around (ignoring
  // sub-0.05 px jitter); report the mean reversals per dot.
  const bounce = () => {
    const ids = L.field.distances(1100, 720).filter(([, d]) => d < 200).map(([i]) => i);
    let prev = new Map(L.field.distances(1100, 720, ids)), dir = new Map(), flips = 0;
    for (let k = 0; k < 180; k++) {
      run(1);
      for (const [i, d] of L.field.distances(1100, 720, ids)) {
        const dd = d - prev.get(i); prev.set(i, d);
        if (Math.abs(dd) < 0.05) continue;
        const s = Math.sign(dd);
        if (dir.has(i) && dir.get(i) !== s) flips++;
        dir.set(i, s);
      }
    }
    return ids.length ? flips / ids.length : 0;
  };
  // the hole's size while sweeping fast, slow, and parked: one size, so it never breathes with the cursor's speed
  const radii = [];
  for (let px = 860; px <= 1100; px += 12) { move(px); run(1); radii.push(L.field.bowRadius()); }
  for (let px = 1100; px <= 1130; px += 2) { move(px); run(1); radii.push(L.field.bowRadius()); }
  run(60); radii.push(L.field.bowRadius());
  out.bowRadii = [Math.min(...radii.filter((r) => r > 0)), Math.max(...radii)];
  docHandlers.pointerleave(); run(600);
  // a sweep straight through the dust near the spot: the dots it touches are shoved aside (measured right as it ends)
  out.preSweepMean = meanDist();
  out.sweepPush = 0; // the fastest dot within 80 px of the moving cursor, during the sweep
  for (let px = 860; px <= 1100; px += 12) { move(px); run(1); out.sweepPush = Math.max(out.sweepPush, L.field.speedNear(px, 720, 80)); }
  out.sweptMean = meanDist();
  out.stopReversals = bounce();
  docHandlers.pointerleave(); run(600);
  move(1100); out.arriveReversals = bounce();
  docHandlers.pointerleave(); run(600);
}

document.hidden = true; for (const f of handlers.visibilitychange) f();
out.rafWhileHidden = raf.length;
document.hidden = false; for (const f of handlers.visibilitychange) f();
out.rafWhenShown = raf.length;

let layouts = 0;
addEventListener("lab:layout", () => layouts++);
inits = 0; innerHeight = 740; for (const f of handlers.resize) f(); for (const f of timers.splice(0)) f();
out.urlBar = { inits, layouts, canvasH: canvas.height };
inits = 0; innerWidth = 1000; for (const f of handlers.resize) f(); for (const f of timers.splice(0)) f();
out.widthChange = { inits, layouts };
console.log(JSON.stringify(out));
"""


def run(screen):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    res = subprocess.run(["node", "-", str(SRC), screen], input=HARNESS, capture_output=True, text=True, timeout=60, check=True)
    return json.loads(res.stdout)


@pytest.fixture(scope="module")
def stats():
    """A touch screen: no hover, a 3x display."""
    return run("touch")


@pytest.fixture(scope="module")
def mouse():
    """A mouse screen: hover and a fine pointer, a 3x display."""
    return run("fine")


def test_the_hover_hole_keeps_one_size_at_every_speed(mouse):
    # a hole that grew while moving and shrank when slowing breathed with the cursor's speed: David's "pulse"
    lo, hi = mouse["bowRadii"]
    assert lo == hi, (lo, hi)


def test_the_dust_glides_home_instead_of_pulsing(mouse):
    # mean in-out reversals per dust dot near the cursor over 3 s. Old shared damping: 4.3 after a sweep stops and 1.4
    # when the cursor arrives (the "lens pulse"); critically damped dust: 1.25 and 0.19. One glide home is 1.
    assert mouse["stopReversals"] < 2, mouse["stopReversals"]
    assert mouse["arriveReversals"] < 0.7, mouse["arriveReversals"]


def test_touch_gets_the_full_canvas_resolution(stats, mouse):
    # a 3x phone draws at 3x since round dots (2026-10-03); a 1.5x cap upscaled the canvas 2x and blurred it
    assert stats["canvasW"] == 1280 * 3
    assert mouse["canvasW"] == 1280 * 2


def test_touch_draws_every_frame_when_calm(stats, mouse):
    assert stats["drawsPer60"] == 60
    # a mouse screen still halves its frame rate while nothing moves (the helix's fork run brings full rate back)
    assert 30 <= mouse["drawsPer60"] < 60


def test_a_parked_mouse_settles_instead_of_pulsing(mouse):
    # the old dent swung dust dots ~80 px to and fro as their drifting targets crossed the cursor's centre
    assert mouse["parkedSpeed"] < 0.5, (mouse["freeSpeed"], mouse["parkedSpeed"])  # 0.5: the field's own calm line


def test_only_a_moving_cursor_pushes_dots(mouse):
    # Parked, the cursor pushes nothing: the dust under it moves no faster than the dust's own drift (0.09 px/frame).
    # (Its mean distance from the spot is no test here: the drift alone moves the ~10 dots' mean by up to ~12 px.)
    m = {k: round(mouse[k], 2) for k in ("freeCore", "freeSpeed", "parkedSpeed", "sweepPush")}
    assert mouse["freeCore"] >= 5, m  # dust sits there to begin with
    assert mouse["parkedSpeed"] < 0.2, m  # parked: no hole, nothing "expanded", nothing moving
    # moving through: the dots it touches are shoved (0.09 px/frame at rest; 13-19 measured during a sweep)
    assert mouse["sweepPush"] > 3, m


def test_a_parked_mouse_does_not_make_the_helix_pulse(mouse):
    # measured 2026-10-03: 0.18 px/frame with shape dots answering only a moving cursor, 0.36 when a parked cursor's
    # hole also moved them (each turning strand bulged as it passed). The line sits between the two.
    assert mouse["helixParked"] < 0.27, mouse["helixParked"]


def test_touch_has_no_hover_or_parallax(stats, mouse):
    assert stats["moveHandlers"] == 0
    assert mouse["moveHandlers"] == 1


def test_a_press_leaves_one_wake_only_when_it_is_a_tap(stats):
    assert stats["tap"] == 1
    assert stats["swipe"] == 0
    assert stats["cancelled"] == 0
    assert stats["longPress"] == 0
    assert stats["wakeGone"] == 0  # it fades within two seconds


def test_a_mouse_drag_leaves_no_wake(mouse):
    assert mouse["mouseClick"] == 1
    assert mouse["mouseDrag"] == 0  # the drag spun the helix; it is not a click


def test_a_swipe_leaves_a_small_capped_trail(stats):
    assert stats["trailShort"] == 2  # 200 px of finger travel, a wake every ~77 px
    assert stats["trailLong"] == 12  # a long swipe keeps only its newest dozen
    assert stats["trailStill"] == 0


def test_the_rules(stats):
    r = stats["rules"]
    assert r["tapEdge"] and not r["tapFar"] and not r["tapSlow"]
    assert r["clickEdge"] and not r["clickFar"]
    assert (r["dprPhone"], r["dprPhone2"], r["dprDesk"], r["dprLow"]) == (3, 2, 2, 1)  # never above the screen's own
    assert round(r["wakePhone"], 1) == 62.4 and r["wakeDesk"] == 128


def test_a_frame_draws_every_dot_once_in_buckets(stats):
    assert stats["dots"] == 1200
    # at most 7 classes x 2 (shape, dust) x 4 levels; a per-dot draw would change colour hundreds of times
    assert stats["runs"] <= 56, stats
    assert stats["runs"] >= stats["styles"]


def test_dots_are_round_not_squares(stats, mouse):
    for s in (stats, mouse):
        # one full circle per fill: a many-circle path rasterizes slowly (the idle frame rate halved, 2026-10-03)
        assert s["squares"] == 0 and s["partial"] == 0, s
        lo, hi = s["radii"]
        assert 0.5 < lo and hi < 3.5, s  # px: dot sizes 2-3.2, depth scale 0.6-1.6, a little wider than the squares


def test_a_frame_reads_no_tokens(stats):
    assert stats["tokenReadsPerFrame"] == 0


def test_the_loop_stops_while_hidden(stats):
    assert stats["rafWhileHidden"] == 0
    assert stats["rafWhenShown"] == 1


def test_a_url_bar_resize_keeps_the_shape(stats):
    assert stats["urlBar"] == {"inits": 0, "layouts": 0, "canvasH": 740 * 3}  # a 3x touch screen's canvas is 3x


def test_a_width_change_rebuilds_once(stats):
    # nobody handles lab:layout in this harness, so the field rebuilds the shape itself, once
    assert stats["widthChange"] == {"inits": 1, "layouts": 1}
