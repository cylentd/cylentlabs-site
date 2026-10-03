import copy
import json
import pathlib
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "app"))

from contracts import checks  # noqa: E402
from core import render  # noqa: E402
import build  # noqa: E402

SRC = REPO / "design" / "src"
DATA = json.loads((REPO / "data" / "projects.json").read_text(encoding="utf-8"))
COPY = json.loads((SRC / "content.json").read_text(encoding="utf-8"))


# unit: core/render is pure
def test_fill_escapes_and_fails_on_missing_key():
    assert render.fill("{{a.b}}", {"a": {"b": "<x>"}}) == "&lt;x&gt;"
    assert render.fill("{{a}}", {"a": "<b>"}, raw={"a"}) == "<b>"
    with pytest.raises(KeyError):
        render.fill("{{nope}}", {})


def test_chapter_without_a_link_says_in_design():
    p = {"id": "lock", "name": "N", "hook": "H", "use": [], "how": None, "clips": [{"poster": "a.webp", "alt": "A"}]}
    html = render.chapter(p, COPY["card"])
    assert "btn--use" not in html and COPY["card"]["in_design"] in html
    assert "<img" in html and "<video" not in html  # no clip src: the still stands in
    p["use"] = [{"href": "https://example.com"}]
    p["clips"][0]["src"] = "a.mp4"
    html = render.chapter(p, COPY["card"])
    assert "btn--use" in html and COPY["card"]["use"] in html and "<video" in html


def test_a_phone_per_clip_and_labels_when_several_links():
    for p in DATA["projects"]:
        html = render.chapter(p, COPY["card"])
        assert f'data-count="{len(p["clips"])}"' in html
        assert html.count("btn--use") == len(p["use"])
    bad = copy.deepcopy(DATA)
    bad["projects"][0]["use"] = [{"href": "https://a.example"}, {"href": "https://b.example"}]
    with pytest.raises(ValueError):
        checks.check_projects(bad)


def test_date_label_reads_like_a_date():
    assert render.date_label("2026-10-03") == "Oct 3, 2026"


def test_headline_is_optional():
    assert render.headline({"headline": None}) == ""
    assert "+55" in render.headline({"headline": {"value": "+55", "label": "pts"}})


# contract: a bad field fails the build, not the page
def test_shipped_data_passes_contracts():
    checks.check_copy(COPY)
    checks.check_projects(DATA)


def test_contract_rejects_unknown_project_id():
    bad = copy.deepcopy(DATA)
    bad["projects"][0]["id"] = "mystery"
    with pytest.raises(ValueError):
        checks.check_projects(bad)


def test_every_clip_file_exists_and_is_small():
    for p in DATA["projects"]:
        for c in p["clips"]:
            poster = SRC / c["poster"]
            assert poster.is_file(), f"{p['id']}: {poster.name} missing"
            assert poster.stat().st_size < 200_000, f"{p['id']}: {poster.name} over 200 KB"
            if c.get("src"):
                f = SRC / c["src"]
                assert f.is_file(), f"{p['id']}: {f.name} missing"
                assert f.stat().st_size < 900_000, f"{p['id']}: {f.name} over 900 KB"


def test_contract_rejects_non_https_use_link():
    bad = copy.deepcopy(DATA)
    bad["projects"][1]["use"] = [{"href": "http://insecure.example"}]
    with pytest.raises(ValueError):
        checks.check_projects(bad)


def test_contract_rejects_missing_copy_key():
    bad = copy.deepcopy(COPY)
    del bad["hero"]["name"]
    with pytest.raises(ValueError):
        checks.check_copy(bad)


# tokens or nothing: no colour literal outside tokens.css
LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(\s*\d|hsla?\(\s*\d")


def test_no_colour_literals_outside_tokens():
    files = [p for p in (SRC / "css").glob("*.css") if p.name != "tokens.css"]
    files += list((SRC / "js").glob("*.js"))
    bad = [f.name for f in files if LITERAL.search(f.read_text(encoding="utf-8"))]
    assert not bad, f"colour literals outside tokens.css: {bad}"


# the shape ids the page uses exist in the JS, each with a hue token in the same order as L.HUES
def test_every_project_has_a_shape_and_a_hue():
    js = (SRC / "js" / "shapes.js").read_text(encoding="utf-8")
    tokens = (SRC / "css" / "tokens.css").read_text(encoding="utf-8")
    for pid in checks.SHAPE_IDS:
        assert f"L.shapes.{pid}" in js
        assert f"--hue-{pid}:" in tokens
    assert "L.shapes.hero" in (SRC / "js" / "helix.js").read_text(encoding="utf-8")
    order = re.search(r"L\.HUES = \[([^\]]+)\]", js).group(1)
    assert set(re.findall(r'"(\w+)"', order)) == checks.SHAPE_IDS


# golden skeleton: the built page keeps its landmarks
def test_built_page_landmarks():
    page, _ = build.build()
    assert page.count('class="chapter"') == len(DATA["projects"])
    assert page.count('data-stop="') == len(DATA["projects"]) + 1  # plus the hero
    for p in DATA["projects"]:
        assert f'href="#{p["id"]}"' in page  # the helix names jump to each chapter
        assert f'data-for="{p["id"]}"' in page  # and the rail has a link to each
    assert page.count('class="rail"') == 1
    assert 'id="field"' in page and 'class="slide' not in page  # the pathology hero was dropped
    assert "{{" not in page
    for name in build.JS:
        assert "</script>" not in (SRC / "js" / f"{name}.js").read_text(encoding="utf-8")


class Landmarks(HTMLParser):
    """Records each header and footer start tag with whether it sits inside <main>."""
    def __init__(self):
        super().__init__()
        self.depth, self.found = 0, []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.depth += 1
        elif tag in ("header", "footer"):
            self.found.append((tag, self.depth > 0))

    def handle_endtag(self, tag):
        if tag == "main":
            self.depth -= 1


def landmarks(page):
    p = Landmarks()
    p.feed(page)
    return p.found


def built_pages():
    page, _ = build.build()
    pages = {"index.html": page, "404.html": build.build_missing(COPY, DATA)}
    pages.update(build.build_lab(COPY, DATA, build.load_posts()))
    return pages


# a header inside <main> is not a banner, a footer there not contentinfo
def test_header_and_footer_sit_outside_main_on_every_page():
    for name, page in built_pages().items():
        found = landmarks(page)
        assert {t for t, _ in found} == {"header", "footer"}, name
        assert not any(inside for _, inside in found), name
        assert page.count("<main") == 1, name


# WCAG 2.2.2: anything that loops gets a pause control
def test_every_clip_has_a_pause_control():
    page, _ = build.build()
    figures = re.findall(r'<figure class="chapter__show">(.*?)</figure>', page)
    videos = [f for f in figures if "<video" in f]
    assert len(videos) == sum(1 for p in DATA["projects"] for c in p["clips"] if c.get("src"))
    for f in videos:
        assert 'class="chapter__pause" aria-pressed="false"' in f
        assert f'aria-label="{COPY["card"]["pause"]}"' in f and " hidden>" in f  # demos.js unhides it unless reduced motion
    assert all("chapter__pause" not in f for f in figures if "<video" not in f)


# calm while scrolling: the timings are tokens, and the scripts read them rather than carrying their own numbers
def test_scroll_calm_timings_are_tokens():
    tokens = (SRC / "css" / "tokens.css").read_text(encoding="utf-8")
    for name in ("--t-chrome-back", "--t-clip-settle"):
        assert re.search(rf"{name}:\s*\d+ms;", tokens), name
    ratio = float(re.search(r"--clip-in-view:\s*([\d.]+);", tokens).group(1))
    assert 0.5 <= ratio <= 1
    assert '"--t-chrome-back"' in (SRC / "js" / "rail.js").read_text(encoding="utf-8")
    demos = (SRC / "js" / "demos.js").read_text(encoding="utf-8")
    assert '"--clip-in-view"' in demos and '"--t-clip-settle"' in demos
    # the phone chrome steps aside only below the wide-screen rail, and never while open or keyboard-focused
    rail_css = (SRC / "css" / "rail.css").read_text(encoding="utf-8")
    assert re.search(r"max-width: 1099px\)[^@]*data-scrolling[^{]*aria-expanded=\"true\"[^{]*:focus-visible", rail_css)


# demos.js against a stub DOM: a clip waits for the scroll to settle, plays on until it leaves, and a held clip stays held
DEMOS_HARNESS = r"""
const fs = require("fs"), src = process.argv[2];
let timers = new Map(), tid = 0, observer, scrollHandler;
global.setTimeout = (f) => { timers.set(++tid, f); return tid; };
global.clearTimeout = (id) => timers.delete(id);
const settle = () => { const fs_ = [...timers.values()]; timers.clear(); fs_.forEach((f) => f()); };
global.matchMedia = () => ({ matches: false });
global.getComputedStyle = () => ({ getPropertyValue: (n) => ({ "--clip-in-view": " 0.6", "--t-clip-settle": " 280ms" })[n] });
global.IntersectionObserver = class { constructor(cb, o) { this.cb = cb; this.o = o; observer = this; } observe() {} };
const btn = { hidden: true, attrs: { "aria-pressed": "false" }, on: {},
  getAttribute(k) { return this.attrs[k]; }, setAttribute(k, v) { this.attrs[k] = v; }, addEventListener(t, f) { this.on[t] = f; } };
const v = { paused: true, dataset: {}, preload: "none", plays: 0,
  play() { this.paused = false; this.plays++; return Promise.resolve(); }, pause() { this.paused = true; },
  parentElement: { querySelector: () => btn } };
global.document = { documentElement: {}, querySelectorAll: () => [v],
  addEventListener: (t, f, o) => { if (t === "scroll" && o && o.capture) scrollHandler = f; } };
eval(fs.readFileSync(src + "/demos.js", "utf8"));
const see = (r) => observer.cb([{ target: v, isIntersecting: r > 0, intersectionRatio: r }]);
const out = { thresholds: observer.o.threshold, unhidden: !btn.hidden };
see(0.7); scrollHandler();                  // mostly on screen, but the thumb is still moving
out.midScroll = v.paused;
settle();                                   // still for --t-clip-settle
out.settled = !v.paused;
see(0.3); settle(); out.keepsPlaying = !v.paused; // drifting out, still partly on screen: no stop-start
see(0); out.leftPaused = v.paused;
btn.on.click(); see(1); settle(); out.heldStays = v.paused; // held by the button: scrolling back does not restart it
btn.on.click(); out.unheld = !v.paused;
see(0.4); see(0); see(0.4); settle(); out.partlyWaits = v.paused; // back on screen but under the bar: wait
console.log(JSON.stringify(out));
"""


def test_a_clip_waits_for_the_scroll_to_settle():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    res = subprocess.run(["node", "-", str(SRC / "js")], input=DEMOS_HARNESS, capture_output=True, text=True, timeout=30, check=True)
    out = json.loads(res.stdout)
    assert out == {"thresholds": [0, 0.6], "unhidden": True, "midScroll": True, "settled": True, "keepsPlaying": True,
                   "leftPaused": True, "heldStays": True, "unheld": True, "partlyWaits": True}, out


# the rail is reached before the chapters by keyboard, not after the footer
def test_rail_precedes_the_chapters():
    page, _ = build.build()
    assert page.index('class="rail"') < page.index('id="projects"')


# the browser bar colour is the --bg token, not a second copy of it
def test_theme_color_comes_from_the_bg_token():
    tokens = (SRC / "css" / "tokens.css").read_text(encoding="utf-8")
    bg = re.search(r"--bg:\s*([^;]+);", tokens).group(1).strip()
    for name, page in built_pages().items():
        assert f'<meta name="theme-color" content="{bg}">' in page, name
    for shell in ("shell.html", "lab.html"):
        assert not LITERAL.search((SRC / shell).read_text(encoding="utf-8")), shell
