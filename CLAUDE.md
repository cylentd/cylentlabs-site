# Cylent Labs site: agent notes

Portfolio at cylentlabs.com. One static page: a particle hero that re-forms into each project's shape as you scroll. Projects: ff-jarvis, seat-scout, Team Watch, Team Lock.

## Commands

| Do | Run |
|---|---|
| Build | `python app/build.py` (writes `dist/index.html`) |
| Test | `python -m pytest` |
| Preview | `python -m http.server 8010 --directory dist` then `http://localhost:8010/` |
| Land | `git land` (no `land.ps1` yet). Code lands only on David's "land it" |

David opens pages himself. Never open a browser for him.

## Layout (five kinds of file, never mixed)

| Kind | Where |
|---|---|
| Structure | `design/src/shell.html` |
| Style | `design/src/css/` (`tokens.css` holds every colour, space, type, motion value) |
| Behaviour | `design/src/js/` (one concern per file) |
| Copy | `design/src/content.json` (every user-facing string, keyed) |
| Data | `data/projects.json` (cards, live numbers) |

`app/build.py` joins them. `contracts/` checks `content.json` and `projects.json` on the way in.

## Rules

- **Art comes from the male boards only** (QBCutins, WRCutins, QBFull, WRFull in the Team Lock storyboard). Never copy anything from the "Art (Alt)" page. Originals stay in `C:/Users/David/team-lock-work/`; the repo holds optimized webp copies only.
- Vercel Hobby is non-commercial. Upgrade before taking client work.
- Reduced motion and phones get a still frame and fewer particles. Verify at 360px first.
