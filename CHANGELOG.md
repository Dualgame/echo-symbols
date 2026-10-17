# Changelog

## 0.3.0 — unreleased

- New view `games/<game>/<platform>/shaders/shadersets.tsv`: shader-set names split into owner, material, pass and
  features. No data table changed.

## 0.2.0 — 2026-10-17

Adds sounds and scripts for Echo VR. Sounds: 3,706 Wwise-32 sound names (events, buses, states, switches, game
parameters), the kinds each platform's banks use them as, and a label for every media file in the banks (labels come
from the events that play them; they are not recovered names). Scripts: 1,304 script function ids with the first
script that lists them (1,070 named in `names.tsv`) and 1,063 script node class names. New hash: Wwise-32
(`hashes/wwise32.py`). New views: `games/echo_vr/<platform>/sounds/` and `games/echo_vr/pc/scripts/`. The 0.1
tables are unchanged.

## 0.1.0 — 2026-10-17

First public data set: 171,015 CSymbol64 names for Lone Echo, Lone Echo II and Echo VR (PC, Quest). Each name has
a verdict, tier and case, and every non-legacy name a source build. Also: membership and per-class coverage for each
of the four game/platform pairs (Lone Echo and Lone Echo II marked partial); flat, type-only and per-game JSON
subsets; a reference hash implementation with test vectors. Counts: [games/STATS.md](games/STATS.md).
