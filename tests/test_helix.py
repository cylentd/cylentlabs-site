"""The helix's flick to spin, run in Node against a stub DOM. Needs Node; skipped without it.
Guards the 2026-10-03 flick: while held the helix turns at the pointer's sideways speed, scaled to the stage's width;
on release it keeps that speed, capped so the dots never smear into a cloud, and coasts down over about 2.5 s.
A mouse drag selects no text; a touch never blocks the page's scroll; reduced motion gets no spin at all."""
import json
import math
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "design" / "src" / "js"
TOKENS = (ROOT / "design" / "src" / "css" / "tokens.css").read_text(encoding="utf8")


def token(name):
    return float(re.search(rf"{name}:\s*([\d.]+)", TOKENS).group(1))


HARNESS = r"""
const fs = require("fs"), path = require("path"), src = process.argv[2], reduce = process.argv[3] === "reduce";
global.window = global;
const handlers = {}, stageHandlers = {}, out = {};
global.addEventListener = (t, f) => { (handlers[t] = handlers[t] || []).push(f); };
global.removeEventListener = (t, f) => { handlers[t] = (handlers[t] || []).filter((g) => g !== f); };
global.matchMedia = (q) => ({ matches: reduce && q.includes("reduced-motion") });
const css = fs.readFileSync(path.join(src, "..", "css", "tokens.css"), "utf8"), TOK = {};
for (const m of css.matchAll(/(--[\w-]+):\s*([^;]+);/g)) if (!(m[1] in TOK)) TOK[m[1]] = m[2].trim();
global.getComputedStyle = () => ({ getPropertyValue: (n) => TOK[n] || "" });
const classes = new Set();
const stage = { clientWidth: 1000, captured: 0, addEventListener: (t, f) => { stageHandlers[t] = f; },
  setPointerCapture() { stage.captured++; } };
global.document = { querySelector: (s) => (s === ".helix__stage" ? stage : null), querySelectorAll: () => [],
  documentElement: { classList: { add: (c) => classes.add(c), remove: (c) => classes.delete(c) } } };
for (const f of ["shapes.js", "helix.js"]) eval(fs.readFileSync(path.join(src, f), "utf8"));
const L = window.LAB, R = L.helixRules;
out.listens = Object.keys(stageHandlers).sort();
if (reduce) { console.log(JSON.stringify(out)); process.exit(0); }

// pure rules
const pts = [{ t: 0, x: 0 }, { t: 50, x: 100 }, { t: 100, x: 200 }];
out.velocity = R.velocity(pts, 100, 100);
out.velocityStopped = R.velocity(pts, 400, 100);
out.velocityOne = R.velocity([{ t: 0, x: 5 }], 0, 100);
out.rateSlow = R.spinRate(100, 1000, 12, 3.2);
out.rateSlowPhone = R.spinRate(39, 390, 12, 3.2);
out.rateFast = R.spinRate(5000, 1000, 12, 3.2);
out.rateLeft = R.spinRate(-5000, 1000, 12, 3.2);
out.rateNoStage = R.spinRate(100, 0, 12, 3.2);
out.coast = R.coast(2, 0.75, 0.75);

// a drag through the stage's own handlers: x moves `step` px every 16 ms for `n` moves, then waits `hold` ms
const drag = (type, step, n, hold, end = "pointerup") => {
  let t = 0, x = 400, prevented = 0;
  const ev = (more) => ({ pointerId: 1, pointerType: type, button: 0, clientX: x, clientY: 300, timeStamp: t,
    preventDefault: () => prevented++, ...more });
  stageHandlers.pointerdown(ev({ type: "pointerdown" }));
  const during = classes.has("is-spinning"), selectBlocked = (handlers.selectstart || []).length;
  for (let k = 0; k < n; k++) { t += 16; x += step; stageHandlers.pointermove(ev({ type: "pointermove" })); }
  t += hold;
  stageHandlers[end](ev({ type: end }));
  return { spin: L.helixState().spin, prevented, during, selectBlocked, after: classes.has("is-spinning"),
    selectAfter: (handlers.selectstart || []).length };
};
out.mouseFlick = drag("mouse", 40, 6, 0);
out.mouseSlow = drag("mouse", 1, 6, 0);
out.mouseLeft = drag("mouse", -40, 6, 0);
out.mouseHeld = drag("mouse", 40, 6, 300);
out.touchFlick = drag("touch", 40, 6, 0);
out.touchScrolled = drag("touch", 1, 2, 0, "pointercancel");
out.captured = stage.captured;
console.log(JSON.stringify(out));
"""


def run(mode):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    res = subprocess.run(["node", "-", str(SRC), mode], input=HARNESS, capture_output=True, text=True, timeout=60, check=True)
    return json.loads(res.stdout)


@pytest.fixture(scope="module")
def flick():
    return run("motion")


def test_velocity_reads_the_end_of_the_drag(flick):
    assert flick["velocity"] == 2000  # 200 px in 100 ms
    assert flick["velocityStopped"] == 0  # nothing in the last 100 ms: the pointer stopped
    assert flick["velocityOne"] == 0


def test_spin_scales_with_the_stage_and_is_capped(flick):
    assert flick["rateSlow"] == pytest.approx(1.2)  # a tenth of the stage per second
    assert flick["rateSlowPhone"] == pytest.approx(flick["rateSlow"])  # the same swipe, relative to a phone's stage
    assert (flick["rateFast"], flick["rateLeft"]) == (3.2, -3.2)
    assert flick["rateNoStage"] == 0


def test_a_released_spin_coasts_down_in_about_5_seconds(flick):
    assert flick["coast"] == pytest.approx(2 / math.e)
    cap, tau = token("--spin-cap"), token("--spin-coast") / 1000
    resting = 0.2 * token("--field-pace")  # the helix's own turn, rad/s
    fade = tau * math.log(cap / resting)  # seconds from the cap to the resting turn
    assert 4 <= fade <= 6, fade


def test_a_flick_keeps_its_speed_and_direction(flick):
    cap = token("--spin-cap")
    assert flick["mouseFlick"]["spin"] == cap  # 2500 px/s on a 1000 px stage: past the cap
    assert flick["mouseLeft"]["spin"] == -cap  # dragging left turns it the other way
    assert flick["mouseSlow"]["spin"] == pytest.approx(62.5 / 1000 * token("--spin-sens"), rel=0.25)
    assert flick["mouseHeld"]["spin"] == 0  # stopped before letting go: no flick
    assert flick["touchFlick"]["spin"] == cap


def test_a_page_scroll_spins_nothing(flick):
    assert flick["touchScrolled"]["spin"] == 0  # the browser took the touch (pointercancel)


def test_a_mouse_drag_selects_nothing_and_a_touch_blocks_nothing(flick):
    m, t = flick["mouseFlick"], flick["touchFlick"]
    assert m["prevented"] == 1 and m["during"] and m["selectBlocked"] == 1
    assert not m["after"] and m["selectAfter"] == 0  # cleaned up on release
    assert t["prevented"] == 0 and not t["during"]  # the stage stays pan-y: a vertical swipe still scrolls
    assert flick["captured"] == 4  # only the mouse drags capture the pointer


def test_reduced_motion_never_spins():
    assert run("reduce")["listens"] == []
