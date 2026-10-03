"""Join structure, style, behaviour, copy and data into dist/index.html."""
import json
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from contracts import checks  # noqa: E402
from core import render  # noqa: E402

SRC = REPO / "design" / "src"
CSS = ["tokens", "base", "hero", "chapters"]
JS = ["shapes", "helix", "field", "demos", "built", "totop", "chapters"]  # order matters: shapes -> helix -> field -> ... -> chapters


def read(p):
    return pathlib.Path(p).read_text(encoding="utf-8")


def build():
    copy = json.loads(read(SRC / "content.json"))
    data = json.loads(read(REPO / "data" / "projects.json"))
    checks.check_copy(copy)
    checks.check_projects(data)

    values = dict(
        copy,
        facts_asof=render.date_label(data["factsAsOf"]),
        arrow_up=read(SRC / "icons" / "arrow-up.svg").strip(),
        css="\n".join(read(SRC / "css" / f"{n}.css") for n in CSS),
        js="\n".join(read(SRC / "js" / f"{n}.js") for n in JS),
        chapters="\n".join(render.chapter(p, copy["card"]) for p in data["projects"]),
        names=render.names(data["projects"], copy["hero"]),
        contact_links=render.contact_links(data["contact"], copy["hero"], {k: read(SRC / "icons" / f"{k}.svg").strip() for k in ("linkedin", "github")}),
    )
    raw = {"css", "js", "chapters", "names", "contact_links", "arrow_up"}
    for p in data["projects"]:
        for c in p["clips"]:
            for kind in ("src", "poster"):
                if c.get(kind):
                    checks.need((SRC / c[kind]).is_file(), f"projects.json: {p['id']} clip {kind} {c[kind]} not found under design/src")
    return render.fill(read(SRC / "shell.html"), values, raw=raw), checks.drafts(data)


def main():
    page, drafts = build()
    out = REPO / "dist"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    assets = SRC / "assets"
    if assets.is_dir():
        shutil.rmtree(out / "assets", ignore_errors=True)  # a removed asset must not linger in dist
        shutil.copytree(assets, out / "assets")
    print(f"dist/index.html  {len(page) // 1024} KB")
    if drafts:
        print("draft copy, confirm before launch:", ", ".join(drafts))


if __name__ == "__main__":
    main()
