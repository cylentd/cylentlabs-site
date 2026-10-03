# Cylent Labs

Source for [cylentlabs.com](https://cylentlabs.com): David Luu's lab of apps and tools, shown as one static page with a particle DNA helix and a chapter per project.

No framework. A Python build joins structure, style, behaviour, copy and data into one page, and checks the data on the way in. The particles are a small canvas engine in plain JavaScript.

```
python app/build.py      # writes dist/
python -m pytest         # unit, contract, page and shape tests
python -m http.server 8010 --directory dist
```

`CLAUDE.md` has the layout and the rules.
