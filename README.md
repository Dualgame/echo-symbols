# echo-symbols

Recovered names for the 64-bit name hashes (CSymbol64) used by **Lone Echo**, **Lone Echo II** and **Echo VR**
(PC and Quest). The games refer to assets, types, script functions and internal fields by hash. This repository maps
171,015 of those hashes back to their names, says how certain each name is, and records which game ships it.

Counts per game, per verdict and per resource class: [games/STATS.md](games/STATS.md) and each
`games/<game>/<platform>/STATUS.md`. All of these are generated from `data/`.

## Read this before you use a name

- **Most spellings are inferred.** Only about a quarter of rows (`tier = observed`) were seen as a string in a game
  file. The rest were found by a search or a naming rule, or are early (`legacy`) entries with no recorded source.
  If you need certainty, use only `tier = observed`.
- **Capitalisation is mostly unknown.** The hash treats `A`–`Z` as lowercase, so it cannot tell you how a name was
  capitalised. About three quarters of rows have `case = folded`: use those names exactly as given and do not
  "fix" their capitals.
- **Lone Echo and Lone Echo II are incomplete.** Only part of their builds or resource classes is indexed (see their
  `STATUS.md`). A missing row does not mean the asset is not in the game.
- **Media labels are not names.** A `.wem` id is not a hash of a name. `label` in `data/wwise/media/` is the name of
  an event that plays the file, so you can tell files apart; the original file name is unknown.
- Some names contain trailing spaces, quotes or other punctuation. These are part of the name: do not trim them.

Every column and value is defined in [SPEC.md](SPEC.md).

## Layout

| path | contents | source |
|---|---|---|
| `data/names.tsv` | one row per hash: the name and how certain it is | exported |
| `data/membership/<game>-<platform>.tsv` | the resource classes each hash ships under, and the first and last build | exported |
| `data/coverage/`, `data/builds.tsv`, `data/lanes.tsv` | named hashes per class, the builds cited, index status per game and platform | exported |
| `data/wwise/` | sound names (Wwise-32 ids), the kinds each bank uses them as, and a label for each media file | exported |
| `data/scripts/` | script function ids (named or not) and script node class names | exported |
| `games/<game>/<platform>/` | `assets.tsv` (names in that game's build index), `other.tsv` (other names from that game's files), `sounds/`, `scripts/`, `STATUS.md` | generated |
| `subsets/hash_lookup.json` | every row as a flat `{"0x…": name}` map, the format most existing tools read | generated |
| `subsets/types.json`, `subsets/<game>-<platform>.json` | type names only; one game's `assets.tsv` + `other.tsv` names | generated |
| `subsets/wwise_lookup.json` | every sound name as `{"0x…": name}` (8-digit ids) | generated |
| `hashes/csymbol64.py`, `hashes/vectors.tsv` | reference hash implementation and test vectors | by hand |
| `hashes/wwise32.py`, `hashes/wwise32_vectors.tsv` | the sound-name hash (FNV-1 32-bit) and test vectors | by hand |
| `tools/build_views.py`, `tools/validate.py` | regenerate `games/` and `subsets/`; check everything | by hand |

Legacy rows that are in no build index are in `data/names.tsv` and `subsets/hash_lookup.json` only, not in `games/`.

```bash
python3 hashes/csymbol64.py mpl_arena_a     # 0x576ed3f8428ebc4b
python3 tools/build_views.py                # after any change to data/
python3 tools/validate.py                   # format, every hash, generated files up to date, no private paths
```

Standard library only, Python 3.10 or newer.

## Provenance

Names were recovered from game files: package manifests, resource bodies, executables, shader and script binaries,
symbol tables. Each row cites its source by **build id only** (`source_build`). `legacy` rows have no recorded
source. This repository contains no game files, decompiled code, keys or audio.

## Contributing

Open an issue or pull request with the name, its hash, and the build it ships in. A new name is accepted when the
hash matches and the spelling is either seen in a game file or found by a search whose chance of a false match is
stated. Run `tools/validate.py` before you submit. It can also check for your own private strings (a username, a
local folder name): list them one per line in `.private-literals` (gitignored) or comma-separated in
`ECHO_SYMBOLS_PRIVATE`.

## Related

[echotools](https://github.com/echotools) publishes Echo VR tooling with its own symbol cache. These names work with
it, and with any tool that reads a flat `hash → name` JSON map.

## License

Data (`data/`, `games/`, `subsets/`, `hashes/vectors.tsv`): [CC0 1.0](LICENSE-DATA), public domain dedication.
Code and documentation: [MIT](LICENSE). Not affiliated with the games' developers or publishers: see
[NOTICE.md](NOTICE.md).
