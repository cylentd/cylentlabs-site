"""Pure rendering: plain data in, HTML strings out. No I/O, no clock, no env."""
import html
import re

SLOT = re.compile(r"\{\{([\w.]+)\}\}")


def esc(s):
    return html.escape(str(s), quote=True)


def lookup(values, dotted):
    node = values
    for part in dotted.split("."):
        node = node[part]
    return node


def fill(template, values, raw=()):
    """Replace {{a.b}} slots. Keys listed in `raw` are inserted as-is (already-built HTML, css, js)."""
    def sub(m):
        key = m.group(1)
        val = lookup(values, key)
        return str(val) if key in raw else esc(val)
    return SLOT.sub(sub, template)


MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def date_label(iso):
    """2026-10-03 -> Oct 3, 2026."""
    y, mth, d = (int(x) for x in iso.split("-"))
    return f"{MONTHS[mth - 1]} {d}, {y}"


def hue(pid):
    # ids are checked against a fixed set by the contract, so this only ever names a token
    return f'style="--hue: var(--hue-{esc(pid)})"'


def link(href, label, cls):
    return f'<a class="btn {cls}" href="{esc(href)}">{esc(label)}</a>'


def names(projects, copy):
    """The helix's labels: one link per project, lined up with its glowing rungs."""
    items = "".join(f'<a href="#{esc(p["id"])}" {hue(p["id"])}>{esc(p["name"])}</a>' for p in projects)
    return f'<nav class="helix__names" style="--n: {len(projects)}" aria-label="{esc(copy["names_label"])}">{items}</nav>'


def headline(p):
    """One result number, or nothing: builder stats live under How it's built."""
    h = p.get("headline")
    if not h:
        return ""
    return f'<p class="chapter__num"><strong>{esc(h["value"])}</strong><span>{esc(h["label"])}</span></p>'


def motif_labels(p):
    return "".join(
        f'<span class="{"is-lit" if lb["lit"] else ""}" style="left: {float(lb["at"]):g}%">{esc(lb["text"])}</span>'
        for lb in p.get("motif_labels") or []
    )


def shows(p):
    """One or two phones, side by side; on a narrow screen the second peeks in and swipes."""
    return f'<div class="chapter__shows" data-count="{len(p["clips"])}">{"".join(show(c) for c in p["clips"])}</div>'


def show(c):
    """The project's own screen at phone size. A clip plays muted on a loop; its poster is the reduced-motion still."""
    alt = esc(c["alt"])
    if c.get("src"):
        media = (
            f'<video class="chapter__demo" src="{esc(c["src"])}" poster="{esc(c["poster"])}" width="390" height="844" '
            f'muted loop playsinline preload="none" aria-label="{alt}"></video>'
        )
    else:  # a landscape still in the portrait frame: `focus` says which part of it to keep
        focus = f' style="object-position: {esc(c["focus"])}"' if c.get("focus") else ""
        media = f'<img src="{esc(c["poster"])}" alt="{alt}" width="390" height="844" loading="lazy"{focus}>'
    return f'<figure class="chapter__show">{media}</figure>'


def built_toggle(p, copy):
    if not p.get("built"):
        return ""
    pid = esc(p["id"])
    return f'<button type="button" class="btn chapter__how" aria-expanded="false" aria-controls="built-{pid}">{esc(copy["how"])}</button>'


def built(p):
    """Opens in the page's flow under the buttons: it pushes the next chapter down instead of covering its motif."""
    b = p.get("built")
    if not b:
        return ""
    pts = "".join(f"<li>{esc(x)}</li>" for x in b["points"])
    return (
        f'<div class="chapter__built" id="built-{esc(p["id"])}" hidden>'
        f'<p class="chapter__stack">{esc(b["stack"])}</p><ul>{pts}</ul></div>'
    )


def chapter(p, copy):
    links = [link(u["href"], u.get("label") or copy["use"], "btn--use") for u in p["use"]]
    if not links:
        links.append(f'<span class="chapter__status">{esc(copy["in_design"])}</span>')
    if p.get("how"):
        links.append(link(p["how"], copy["how"], ""))
    links.append(built_toggle(p, copy))
    pid = esc(p["id"])
    # name first: the motif and the name read in one glance, the clips then prove the hook, the buttons come last
    return (
        f'  <section class="chapter" id="{pid}" data-stop="{pid}" {hue(p["id"])}>\n'
        f'    <div class="chapter__motif" aria-hidden="true">{motif_labels(p)}</div>\n'
        f'    <div class="chapter__head">\n'
        f'      <h2>{esc(p["name"])}</h2>\n'
        f'      <p class="chapter__hook">{esc(p["hook"])}</p>\n'
        f'    </div>\n'
        f'    {shows(p)}\n'
        f'    <div class="chapter__text">\n'
        f'      {headline(p)}\n'
        f'      <div class="chapter__links">{"".join(links)}</div>\n'
        f'      {built(p)}\n'
        f'    </div>\n'
        f'  </section>'
    )


def contact_links(contact, copy, icons):
    """The name, then an icon link per profile. `icons` maps linkedin/github to inline SVG (trusted, from design/src/icons)."""
    out = [f'<span class="contact__name">{esc(copy["name"])}</span>']
    if contact.get("email"):
        out.append(f'<a href="mailto:{esc(contact["email"])}">{esc(copy["email_label"])}</a>')
    for key in ("linkedin", "github"):
        if contact.get(key):
            out.append(f'<a class="contact__icon" href="{esc(contact[key])}" aria-label="{esc(copy[key + "_label"])}">{icons[key]}</a>')
    return f'<span class="contact">{"".join(out)}</span>'
