"""The field's frame cost and idle behaviour, run in Node against a stub DOM and canvas. Needs Node; skipped without it.
Guards the 2026-10-03 cleanup: one bucketed draw per frame (it was 56 passes over every dot), no token reads per
frame, no rAF while the page is hidden, and no shape rebuild for a phone URL bar showing or hiding."""
import json
import pathlib
import shutil
import subprocess

import pytest

SRC = pathlib.Path(__file__).resolve().parent.parent / "design" / "src" / "js"

HARNESS = r"""
const fs = require("fs"), path = require("path"), src = process.argv[2];
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
global.innerWidth = 1280; global.innerHeight = 800; global.devicePixelRatio = 1;
global.matchMedia = () => ({ matches: false });
let tokenReads = 0;
const TOK = { "--field-count": "1200", "--field-count-phone": "600", "--dot": "2", "--dot-lit": "3.2", "--dot-phone": "2.2",
  "--dot-lit-phone": "3", "--dust": "0.45" };
global.getComputedStyle = () => ({ getPropertyValue: (n) => { tokenReads++; return TOK[n] || "#a0b0c0"; } });
const calls = [];
const ctx = { fillStyle: "", globalAlpha: 1, setTransform() {}, clearRect() { calls.length = 0; },
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


@pytest.fixture(scope="module")
def stats():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    res = subprocess.run(["node", "-", str(SRC)], input=HARNESS, capture_output=True, text=True, timeout=30, check=True)
    return json.loads(res.stdout)


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
    assert stats["urlBar"] == {"inits": 0, "layouts": 0, "canvasH": 740}


def test_a_width_change_rebuilds_once(stats):
    # nobody handles lab:layout in this harness, so the field rebuilds the shape itself, once
    assert stats["widthChange"] == {"inits": 1, "layouts": 1}
