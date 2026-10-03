import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "app"))

from contracts import checks  # noqa: E402
from core import lab  # noqa: E402
import build  # noqa: E402

COPY = json.loads((REPO / "design" / "src" / "content.json").read_text(encoding="utf-8"))
DATA = json.loads((REPO / "data" / "projects.json").read_text(encoding="utf-8"))
POST = "---\ntitle: A note\ndate: 2026-10-03\nsummary: What broke.\ndraft: false\n---\n## What broke\n\nOne <b>line</b>.\n"


# unit: core/lab is pure
def test_parse_reads_front_matter_and_body():
    p = lab.parse(POST.replace("\n", "\r\n"), "a-note")
    assert p["title"] == "A note" and p["draft"] is False and p["slug"] == "a-note"
    assert p["body"].startswith("## What broke")


def test_parse_needs_front_matter():
    with pytest.raises(ValueError):
        lab.parse("no front matter", "x")


def test_markdown_subset_escapes_html():
    out = lab.markdown("## Head\n\nSay **this** with `code` and [a link](https://x.dev).\n\n- one\n- two\n\n```\n<raw>\n```")
    assert "<h2>Head</h2>" in out
    assert "<strong>this</strong>" in out and "<code>code</code>" in out and '<a href="https://x.dev">a link</a>' in out
    assert "<ul><li>one</li><li>two</li></ul>" in out
    assert "&lt;raw&gt;" in out and "<raw>" not in out


def test_markdown_drops_unsafe_link_schemes():
    assert "<a " not in lab.markdown("[x](javascript:alert(1))")


# contract
def test_contract_rejects_bad_posts():
    good = lab.parse(POST, "a-note")
    checks.check_posts([good])
    for bad in (dict(good, slug="Bad Name"), dict(good, date="Oct 3"), dict(good, draft="yes"), dict(good, title="")):
        with pytest.raises(ValueError):
            checks.check_posts([bad])
    checks.check_posts([])  # no notes yet is fine: the index says one is coming


# golden: notes build into an index and one page each; the home page links the lab from its header and footer
def test_lab_pages_build():
    older = dict(lab.parse(POST, "older"), date="2026-09-01", title="Older")
    posts = [older, lab.parse(POST, "a-note")]
    pages = build.build_lab(COPY, DATA, posts)
    assert set(pages) == {"lab/index.html", "lab/older/index.html", "lab/a-note/index.html"}
    for html in pages.values():
        assert "{{" not in html and 'href="/"' in html
    idx = pages["lab/index.html"]
    assert idx.index("/lab/a-note/") < idx.index("/lab/older/")  # newest first
    assert "<h2>What broke</h2>" in pages["lab/a-note/index.html"]


def test_empty_lab_says_so():
    assert COPY["lab"]["empty"] in build.build_lab(COPY, DATA, [])["lab/index.html"]


def test_home_links_the_lab_twice():
    page, _ = build.build()
    assert page.count('class="lablink" href="/lab/"') == 2
