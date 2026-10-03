"""Join structure, style, behaviour, copy and data into dist/index.html, plus the lab notes under dist/lab/."""
import json
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from contracts import checks  # noqa: E402
from core import lab, render  # noqa: E402

SRC = REPO / "design" / "src"
CSS = ["tokens", "base", "hero", "chapters", "rail", "lab"]
LAB_CSS = ["tokens", "base", "hero", "chapters", "lab"]  # the reading pages: no rail, no field
JS = ["shapes", "helix", "field", "demos", "built", "totop", "rail", "chapters"]  # order matters: shapes -> helix -> field -> ... -> chapters


def read(p):
    return pathlib.Path(p).read_text(encoding="utf-8")


def load_posts():
    posts = [lab.parse(read(f), f.stem) for f in sorted((REPO / "data" / "lab").glob("*.md"))]
    checks.check_posts(posts)
    return posts


def build_lab(copy, data, posts):
    """The notes index and one page per note, keyed by their path under dist/."""
    contact = render.contact_links(data["contact"], copy["hero"], icons())
    css = "\n".join(read(SRC / "css" / f"{n}.css") for n in LAB_CSS)
    shell = read(SRC / "lab.html")
    raw = {"meta", "css", "body", "contact_links"}

    def page(path, title, description, body, kind="website"):
        head = render.meta(data, copy["site"], path, title, description, kind)
        return render.fill(shell, dict(copy, meta=head, css=css, body=body, contact_links=contact), raw=raw)

    c = copy["lab"]
    pages = {"lab/index.html": page("/lab/", f'{c["index_title"]} · {copy["site"]["title"]}', c["description"], lab.index(posts, c))}
    for p in posts:
        pages[f'lab/{p["slug"]}/index.html'] = page(
            f'/lab/{p["slug"]}/', f'{p["title"]} · {copy["site"]["title"]}', p["summary"], lab.post(p, c), "article"
        )
    return pages


def icons():
    return {k: read(SRC / "icons" / f"{k}.svg").strip() for k in ("linkedin", "github")}


def build():
    copy = json.loads(read(SRC / "content.json"))
    data = json.loads(read(REPO / "data" / "projects.json"))
    checks.check_copy(copy)
    checks.check_projects(data)
    posts = load_posts()

    values = dict(
        copy,
        meta=render.meta(data, copy["site"], "/", copy["site"]["title"], copy["site"]["description"]),
        facts_asof=render.date_label(data["factsAsOf"]),
        arrow_up=read(SRC / "icons" / "arrow-up.svg").strip(),
        css="\n".join(read(SRC / "css" / f"{n}.css") for n in CSS),
        js="\n".join(read(SRC / "js" / f"{n}.js") for n in JS),
        chapters="\n".join(render.chapter(p, copy["card"]) for p in data["projects"]),
        names=render.names(data["projects"], copy["hero"]),
        rail=render.section_nav(data["projects"], copy["rail"]),
        contact_links=render.contact_links(data["contact"], copy["hero"], icons()),
    )
    raw = {"meta", "css", "js", "chapters", "names", "rail", "contact_links", "arrow_up"}
    checks.need((SRC / data["previewImage"]).is_file(), f"projects.json: previewImage {data['previewImage']} not found under design/src")
    for p in data["projects"]:
        for c in p["clips"]:
            for kind in ("src", "poster"):
                if c.get(kind):
                    checks.need((SRC / c[kind]).is_file(), f"projects.json: {p['id']} clip {kind} {c[kind]} not found under design/src")
    drafts = checks.drafts(data) + [f'lab: {p["title"]}' for p in posts if p["draft"]]
    return render.fill(read(SRC / "shell.html"), values, raw=raw), drafts


def main():
    page, drafts = build()
    out = REPO / "dist"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    shutil.rmtree(out / "lab", ignore_errors=True)  # a removed note must not linger in dist
    copy = json.loads(read(SRC / "content.json"))
    for rel, html in build_lab(copy, json.loads(read(REPO / "data" / "projects.json")), load_posts()).items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(html, encoding="utf-8")
    assets = SRC / "assets"
    if assets.is_dir():
        shutil.rmtree(out / "assets", ignore_errors=True)  # a removed asset must not linger in dist
        shutil.copytree(assets, out / "assets")
    print(f"dist/index.html  {len(page) // 1024} KB")
    if drafts:
        print("draft copy, confirm before launch:", ", ".join(drafts))


if __name__ == "__main__":
    main()
