"""Shape checks where data enters the build. A missing field fails the build, not the page."""
import re

SHAPE_IDS = {"jarvis", "teamwatch", "tcg", "seat", "lock"}  # one per shape in design/src/js/shapes.js
COPY_KEYS = {
    "site": {"title", "description", "skip", "preview_alt"},
    "hero": {"wordmark", "name", "email_label", "github_label", "linkedin_label", "names_label", "quote"},
    "rail": {"label"},
    "lab": {"nav", "intro", "empty", "index_title", "description", "back", "home", "draft"},
    "card": {"use", "how", "in_design", "pause"},
    "missing": {"title", "line", "home"},
    "foot": {"to_top"},
}


def need(cond, msg):
    if not cond:
        raise ValueError(msg)


def check_copy(copy):
    for group, keys in COPY_KEYS.items():
        need(group in copy, f"content.json: missing group {group!r}")
        missing = keys - set(copy[group])
        need(not missing, f"content.json: {group} missing {sorted(missing)}")


def check_projects(data):
    need({"contact", "projects", "factsAsOf", "siteUrl", "previewImage"} <= set(data), "projects.json: needs contact, projects, factsAsOf, siteUrl, previewImage")
    need(re.fullmatch(r"https://[^/\s]+", data["siteUrl"]), "projects.json: siteUrl must be https://host with no trailing slash")
    for k in ("linkedin", "github"):
        v = data["contact"].get(k)
        need(v is None or str(v).startswith("https://"), f"projects.json: contact.{k} must be null or https")
    ids = [p.get("id") for p in data["projects"]]
    need(set(ids) == SHAPE_IDS, f"projects.json: ids {ids} must match shapes {sorted(SHAPE_IDS)}")
    need(len(ids) == len(set(ids)), "projects.json: duplicate id")
    for p in data["projects"]:
        pid = p.get("id")
        for k in ("name", "hook", "draft", "clips", "use"):
            need(k in p, f"projects.json: {pid} missing {k!r}")
        need(p.get("how") is None or str(p["how"]).startswith("https://"), f"projects.json: {pid}.how must be null or https")
        for u in p["use"]:
            need(str(u.get("href", "")).startswith("https://"), f"projects.json: {pid}.use hrefs must be https")
        need(len(p["use"]) < 2 or all(u.get("label") for u in p["use"]), f"projects.json: {pid} has several use links, so each needs a label")
        hl = p.get("headline")
        need(hl is None or {"value", "label"} <= set(hl), f"projects.json: {pid}.headline needs value and label")
        need(1 <= len(p["clips"]) <= 3, f"projects.json: {pid}.clips holds one to three phone clips")
        for c in p["clips"]:
            need({"poster", "alt"} <= set(c), f"projects.json: {pid}.clips need poster and alt (src is optional)")
        for lb in p.get("motif_labels") or []:
            need({"text", "at", "lit"} <= set(lb) and 0 <= lb["at"] <= 100, f"projects.json: {pid}.motif_labels need text, at 0-100, lit")
        bt = p.get("built")
        need(bt is None or {"stack", "points"} <= set(bt), f"projects.json: {pid}.built needs stack and points")
        if bt:
            need(isinstance(bt["stack"], list) and all(isinstance(s, str) for s in bt["stack"]), f"projects.json: {pid}.built.stack is a list of tags")
            need(all(isinstance(x, str) for x in bt["points"]), f"projects.json: {pid}.built.points are plain sentences")


SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def check_posts(posts):
    """Lab notes: each needs a title, an ISO date, a summary, a draft flag and a URL-safe file name."""
    for p in posts:
        slug = p["slug"]
        need(SLUG.fullmatch(slug), f"data/lab/{slug}.md: file name must be lowercase words joined by hyphens")
        for k in ("title", "date", "summary"):
            need(isinstance(p.get(k), str) and p[k], f"data/lab/{slug}.md: missing {k!r}")
        need(re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["date"]), f"data/lab/{slug}.md: date must be YYYY-MM-DD")
        need(isinstance(p.get("draft"), bool), f"data/lab/{slug}.md: draft must be true or false")


def drafts(data):
    """Names of chapters whose copy David has not confirmed."""
    return [p["name"] for p in data["projects"] if p["draft"]]
