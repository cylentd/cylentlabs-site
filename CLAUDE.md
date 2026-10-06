# Cylent Labs site: agent notes

Portfolio at cylentlabs.com. One static page: a particle DNA helix in the hero, then one chapter per project (ff-jarvis, Team Watch, Restock Watch, Seat Scout, Team Lock), each with a small particle motif, the project's phone clips, and its links. The particles hand off from the helix to each chapter's motif as you scroll.

## Commands

| Do | Run |
|---|---|
| Build | `python app/build.py` (writes `dist/`) |
| Preview | The shared dev server, never your own: `http://localhost:8000/cylentlabs/` (main's `dist/`), `http://localhost:8000/cylentlabs-wt/<worktree>/dist/` (a worktree's) |
| Land | Run the Testing gate, rebuild, commit `dist/`, then `git land`. Code lands only on David's "land it" |

David opens pages himself. Never open a browser for him.

## Testing

TDD is the default; standards live in the `testing` skill.

| Do | Run |
|---|---|
| One test | `python -m pytest tests/test_helix.py::test_a_page_scroll_spins_nothing` |
| One file | `python -m pytest tests/test_helix.py` |
| While working | `python -m pytest -x` (stops at the first failure) |
| Full suite | `python -m pytest` (56 tests, about 1.5 s; Node needed, else the Node tests skip) |
| Before land | `python $HOME/.agents/skills/testing/scripts/land_gate.py` |

- **Layers:** unit (`test_site.py` render, `test_lab.py` lab parse and markdown); contract (`contracts/checks.py` rejections, in both); build and golden skeleton (`test_site.py`, `test_lab.py` call `build.build*`); Node shape harness (`test_shapes.py`, `test_helix.py`, `test_field.py`, and the demos test in `test_site.py`). The `render` marker (browser) is declared in `pytest.ini` but unused: no browser test exists.
- **Exemplars:** `tests/test_helix.py` (Node harness run once per module fixture, one behaviour per test, numbers justified in comments); `tests/test_lab.py` (pure unit tests of `core/lab`, including the negative `ValueError` cases); `tests/test_site.py` contract tests (`test_contract_rejects_*`, one broken field each).
- **Building blocks:** JS harnesses are strings inside the test files or `tests/shapes_harness.js`; module fixtures `flick`, `stats`, `mouse` run Node once; `POST`, `COPY`, `DATA` constants in `test_lab.py` and `test_site.py`. No `conftest.py`.
- **Protected:** `dist/` (generated), `data/projects.json` and `design/src/content.json` (the tests read them as the oracle), `tests/shapes_harness.js`, and every existing test: change one only when its behaviour is meant to change, with the diff reviewed.

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
