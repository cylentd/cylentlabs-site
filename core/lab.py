"""Lab notes: one markdown file per post in data/lab/, front matter on top. Pure: text in, data or HTML out."""
import re

from core.render import date_label, esc

FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def parse(text, slug):
    """Front matter (key: value lines) plus the markdown body. Booleans read as true/false."""
    text = text.replace("\r\n", "\n")
    m = FRONT.match(text)
    if not m:
        raise ValueError(f"data/lab/{slug}.md: needs front matter between --- lines")
    meta = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        v = v.strip()
        meta[k.strip()] = {"true": True, "false": False}.get(v, v)
    return dict(meta, slug=slug, body=text[m.end():])


# a small markdown subset: ## and ### headings, paragraphs, - lists, ``` code blocks; inline `code`, **bold**, [text](url)
INLINE = [
    (re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
    (re.compile(r"\*\*([^*]+)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"\[([^\]]+)\]\(((?:https://|/)[^)\s]*)\)"), r'<a href="\2">\1</a>'),
]


def inline(s):
    s = esc(s)
    for pat, rep in INLINE:
        s = pat.sub(rep, s)
    return s


def markdown(text):
    out, para, items, code = [], [], [], None

    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for line in text.splitlines():
        if code is not None:
            if line.startswith("```"):
                out.append(f"<pre><code>{esc(chr(10).join(code))}</code></pre>")
                code = None
            else:
                code.append(line)
        elif line.startswith("```"):
            flush()
            code = []
        elif m := re.match(r"(#{2,3}) (.+)", line):
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif line.startswith("- "):
            if para:
                flush()
            items.append(line[2:])
        elif not line.strip():
            flush()
        else:
            if items:
                flush()
            para.append(line.strip())
    flush()
    return "\n".join(out)


def newest_first(posts):
    return sorted(posts, key=lambda p: p["date"], reverse=True)


def item(p, copy):
    tag = f' <span class="lab__tag">{esc(copy["draft"])}</span>' if p["draft"] else ""
    return (
        f'<li><a href="/lab/{esc(p["slug"])}/"><span class="lab__title">{esc(p["title"])}</span>{tag}</a>'
        f'<time datetime="{esc(p["date"])}">{esc(date_label(p["date"]))}</time>'
        f'<p>{esc(p["summary"])}</p></li>'
    )


def index(posts, copy):
    items = "".join(item(p, copy) for p in newest_first(posts))
    listing = f'<ol class="lab__list">{items}</ol>' if items else f'<p class="lab__empty">{esc(copy["empty"])}</p>'
    return (
        f'<h1 class="lab__h1">{esc(copy["index_title"])}</h1>'
        f'<p class="lab__intro">{esc(copy["intro"])}</p>'
        f'{listing}'
    )


def post(p, copy):
    tag = f'<span class="lab__tag">{esc(copy["draft"])}</span>' if p["draft"] else ""
    return (
        f'<article class="note">'
        f'<a class="note__back" href="/lab/">{esc(copy["back"])}</a>'
        f'<h1 class="lab__h1">{esc(p["title"])}</h1>'
        f'<p class="note__meta"><time datetime="{esc(p["date"])}">{esc(date_label(p["date"]))}</time>{tag}</p>'
        f'{markdown(p["body"])}'
        f'</article>'
    )
