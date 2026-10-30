# Changelog

## 0.4.0 — 2026-10-30

- 32,702 more names (171,015 → 203,717); no row removed. Almost all are Lone Echo II: its named asset ids rise from
  63,925 to 95,946, that is 65.1 % of the 147,455 ids in the 4 indexed Lone Echo II builds (`data/lanes.tsv`).
  Echo VR asset names: PC +341, Quest +85. Names outside the build index (`other.tsv`): Echo VR PC +375, Lone Echo
  +273, Lone Echo II +26.
- Of the added rows, 29,708 are `KEEP-bounded` search results, 2,333 `KEEP-corroborated` and 661 `KEEP-observed`;
  the observed share of all rows drops to 22 %. 119 existing rows were upgraded from `KEEP-bounded` to
  `KEEP-corroborated`; no row was downgraded.
- **Three names corrected.** Three Echo VR graph constants each had two names that hash to the same id, and 0.3
  published the wrong one. Each correct name is the missing sibling in its canvas (PC 6323983201049540):
  `0x6896509e625cdbbb` `talkuhbkahwg` → `group_legal_text_actions`, `0xf1d68850a07da16a` `r14flaggmq9bpx` →
  `opt0_select`, `0xa2cd843076df37eb` `ngki8108l9s` → `tier_2_item_preview`. The rows now have `kind = other`
  (was `script_constant`) and `p_chance` 1.1e-06; the new names also appear in the PC and Quest
  `scripts/constants.tsv` views and in every `subsets/` file. If you copied a lookup from 0.3, replace these three rows.
- 18 more type symbols have a class name (4 remain without one). `data/builds.tsv` cites 10 more builds.
- No column or format changes. `SPEC.md`: the `legacy` tier is defined as any entry with no recorded source.

## 0.3.0 — 2026-10-17

- Echo VR Quest scripts: 1,003 script function ids (813 named), 1,890 script/function pairs, 2,096 named graph
  constants in 4,749 script/constant pairs and 936 node classes; view `games/echo_vr/quest/scripts/`.
  **Key change:** the `data/scripts/` tables now hold PC and Quest rows, so each key includes `build`
  (`functions.tsv` and `node_classes.tsv`: `hash`, `build`). Columns are unchanged; a reader that keyed a table by
  `hash` alone should filter on `build` first.
- New table `data/scripts/function_scripts.tsv` (PC): every script that declares or references each script function
  (2,760 pairs over 375 scripts), replacing the first-script-only grouping in `games/echo_vr/pc/scripts/functions.tsv`.
- New table `data/scripts/constant_scripts.tsv` (PC): 2,886 named graph constants with their role and every script that
  holds them (6,593 pairs); view `games/echo_vr/pc/scripts/constants.tsv`.
- New table `data/types.tsv`: every type symbol the indexed builds ship (1,003 hashes, 1,116 game/platform rows),
  with its class, layer suffix, first and last build and asset count; 22 have an unknown class. View
  `games/<game>/<platform>/types.tsv`.
- Releases now carry the whole data set as JSON (`echo-symbols.json.gz` and one file per game and platform), built
  by `tools/export_json.py` in a release workflow.
- New view `games/<game>/<platform>/shaders/shadersets.tsv`: shader-set names split into owner, material, pass and
  features.

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
