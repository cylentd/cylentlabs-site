# Cylent Labs site: agent notes

Portfolio at cylentlabs.com. One static page: a particle DNA helix in the hero, then one chapter per project (ff-jarvis, Team Watch, Restock Watch, seat-scout, Team Lock), each with a small particle motif, the project's phone clips, and its links. The particles hand off from the helix to each chapter's motif as you scroll.

## Commands

| Do | Run |
|---|---|
| Build | `python app/build.py` (writes `dist/`) |
| Test | `python -m pytest` (the shape test needs Node) |
| Preview | `python -m http.server 8010 --directory dist` then `http://localhost:8010/` |
| Land | Rebuild, commit `dist/`, then `git land`. Code lands only on David's "land it" |

David opens pages himself. Never open a browser for him.

## Deploy

Vercel serves the committed `dist/` as a static site (framework Other, no build command, output `dist`). `dist/` is generated: never hand-edit it, rebuild it once at land time. cylentlabs.com's DNS is on Cloudflare, DNS only (grey cloud), because Cloudflare's proxy breaks Vercel's certificates.

## Layout (five kinds of file, never mixed)

| Kind | Where |
|---|---|
| Structure | `design/src/shell.html` |
| Style | `design/src/css/` (`tokens.css` holds every colour, space, type, motion value) |
| Behaviour | `design/src/js/` (one concern per file: `field.js` engine, `helix.js` hero, `shapes.js` motifs) |
| Copy | `design/src/content.json` (every user-facing string, keyed) |
| Data | `data/projects.json` (chapters, clips, links, headline numbers) |

`app/build.py` joins them. `contracts/` checks `content.json` and `projects.json` on the way in.

## Rules

- **Numbers are results or nothing.** A headline number must be a real, dated result from the project's own data. Builder stats go under How it's built.
- **Team Lock art:** optimized webp or clip copies only; originals stay outside the repo. Characters are cosmetic role avatars, so cut-in art never carries a real player's name; names appear only on role badges, as fantasy data. Keep the avatars generic: no real player's face, team marks, or matching jersey number.
- Phone clips are recorded at 390x844 and must show real, current-looking content; say in the commit when a clip is edited (sped up, items hidden, snapshot data).
- Vercel Hobby is non-commercial. Upgrade before taking client work.
- Verify at 360px first. Reduced motion gets still frames.
