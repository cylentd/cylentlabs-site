"""Every shape puts its dots inside its stage, on wide screens and on phones. Needs Node; skipped without it.
Guards the 2026-10-03 bug where a comment swallowed the helix's wide-screen branch and the hero drew nothing."""
import json
import pathlib
import shutil
import subprocess

import pytest

HERE = pathlib.Path(__file__).resolve().parent


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_every_shape_lands_in_its_stage():
    res = subprocess.run(["node", str(HERE / "shapes_harness.js")], capture_output=True, text=True, timeout=30, check=True)
    stats = json.loads(res.stdout)
    assert {k.split("/")[0] for k in stats} >= {"hero", "jarvis", "teamwatch", "tcg", "seat", "lock"}
    for key, s in stats.items():
        assert s["claimed"] > 100, f"{key}: only {s['claimed']} dots claimed"
        assert s["inside"] / s["claimed"] > 0.95, f"{key}: {s['inside']} of {s['claimed']} dots inside the stage"
    # the hero's helix stands upright and fills its stage's height (2026-10-03: a lying helix sat at 40-50% of it)
    for layout in ("wide", "phone"):
        s = stats[f"hero/{layout}"]
        assert s["fillH"] > 0.6 and s["fillW"] > 0.15, f"hero/{layout}: fills {s['fillW']:.0%} wide, {s['fillH']:.0%} high"
        # only lit rung groups and the fork's glow wear a project's hue (2026-10-03: stale colours speckled the helix)
        assert s["stray"] == 0, f"hero/{layout}: {s['stray']} unlit dots in a project hue"
