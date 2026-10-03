"""The field's frame cost and idle behaviour, run in Node against a stub DOM and canvas. Needs Node; skipped without it.
Guards the 2026-10-03 cleanup: one bucketed draw per frame (it was 56 passes over every dot), no token reads per
frame, no rAF while the page is hidden, and no shape rebuild for a phone URL bar showing or hiding.
Guards the calmer field too: a touch screen gets a capped canvas resolution, a full frame rate, no hover or parallax,
and a wake only for a real tap, never for a swipe."""
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
const ctx = { fillStyle: "", globalAlpha: 1, setTransform() {}, clearRect() { clears++; calls.length = 0; },
  fillRect() { calls.push(ctx.fillStyle + "@" + ctx.globalAlpha); } };
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
tick(4000);
out.tokenReadsPerFrame = tokenReads - before;
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
out.wakeGone = L.field.wakeCount();
const R = L.fieldRules;
out.rules = { tapEdge: R.isTap(6, 8, 300, 10, 300), tapFar: R.isTap(8, 8, 100, 10, 300), tapSlow: R.isTap(0, 0, 301, 10, 300),
  dprPhone: R.dpr(3, false, 2, 1.5), dprDesk: R.dpr(3, true, 2, 1.5), dprLow: R.dpr(1, false, 2, 1.5),
  wakePhone: R.wakeRadius(390, 844, 0.16), wakeDesk: R.wakeRadius(1280, 800, 0.16) };

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


def test_touch_caps_the_canvas_resolution(stats, mouse):
    assert stats["canvasW"] == 1280 * 1.5
    assert mouse["canvasW"] == 1280 * 2


def test_touch_draws_every_frame_when_calm(stats, mouse):
    assert stats["drawsPer60"] == 60
    # a mouse screen still halves its frame rate while nothing moves (the helix's fork run brings full rate back)
    assert 30 <= mouse["drawsPer60"] < 60


def test_touch_has_no_hover_or_parallax(stats, mouse):
    assert stats["moveHandlers"] == 0
    assert mouse["moveHandlers"] == 1


def test_only_a_tap_leaves_a_wake(stats):
    assert stats["tap"] == 1
    assert stats["swipe"] == 0
    assert stats["cancelled"] == 0
    assert stats["longPress"] == 0
    assert stats["wakeGone"] == 0  # it fades within two seconds


def test_the_rules(stats):
    r = stats["rules"]
    assert r["tapEdge"] and not r["tapFar"] and not r["tapSlow"]
    assert (r["dprPhone"], r["dprDesk"], r["dprLow"]) == (1.5, 2, 1)
    assert round(r["wakePhone"], 1) == 62.4 and r["wakeDesk"] == 128


def test_a_frame_draws_every_dot_once_in_buckets(stats):
    assert stats["dots"] == 1200
    # at most 7 classes x 2 (shape, dust) x 4 levels; a per-dot draw would change colour hundreds of times
    assert stats["runs"] <= 56, stats
    assert stats["runs"] >= stats["styles"]


def test_a_frame_reads_no_tokens(stats):
    assert stats["tokenReadsPerFrame"] == 0


def test_the_loop_stops_while_hidden(stats):
    assert stats["rafWhileHidden"] == 0
    assert stats["rafWhenShown"] == 1


def test_a_url_bar_resize_keeps_the_shape(stats):
    assert stats["urlBar"] == {"inits": 0, "layouts": 0, "canvasH": 740 * 1.5}  # a touch screen's canvas is 1.5x


def test_a_width_change_rebuilds_once(stats):
    # nobody handles lab:layout in this harness, so the field rebuilds the shape itself, once
    assert stats["widthChange"] == {"inits": 1, "layouts": 1}
