# Data specification — v0.3

All tables are UTF-8 TSV with a header row, LF line endings and no BOM. Fields never contain a tab or newline and
are never quoted or escaped: a field is the exact bytes between two tabs. Each table is sorted by its first
column(s). `tools/validate.py` checks the format, every column's allowed values, every hash, a few cross-column rules,
and that cited hashes and builds exist. It does not re-check how a verdict was reached.

"Game file" below means a file from a downloaded game build.

## Hashes

`hash` is CSymbol64 of `name`, written `0x` + 16 lowercase hex digits. No other spelling is accepted (unpadded,
uppercase, decimal, signed or byte-swapped). Algorithm: [hashes/csymbol64.py](hashes/csymbol64.py). Names are
ASCII; `A`–`Z` are lowercased before hashing.

Sound names use a different hash, **Wwise-32**: FNV-1 32-bit of the lowercased name, written `0x` + 8 lowercase hex
digits ([hashes/wwise32.py](hashes/wwise32.py), vectors in `hashes/wwise32_vectors.tsv`). Wwise-32 ids appear only
in `data/wwise/`; every other `hash` column is CSymbol64.

## `data/names.tsv`

| column | values | meaning |
|---|---|---|
| `hash` | `0x` + 16 hex | the key |
| `name` | printable ASCII | the exact string that hashes to `hash`; may contain spaces, `"`, `:`, `~`, `.`, `/` |
| `kind` | `asset` · `type` · `script_function` · `script_constant` · `internal_field` · `language_key` · `literal` · `other` | what the hash names |
| `case` | `authored` · `adjudicated` · `folded` | `authored`: a game file spells it this way. `adjudicated`: game files spell it more than one way and a written rule chose one. `folded`: capitalisation unknown |
| `tier` | `observed` · `inferred` · `legacy` | `observed`: the string appears in a game file. `inferred`: found by a search or a naming rule. `legacy`: an early entry with no recorded source |
| `verdict` | `KEEP-observed` · `KEEP-corroborated` · `KEEP-bounded` · `UNCONFIRMED` | see [Verdicts](#verdicts) |
| `evidence` | `stream-confirmed` · `symbols-only` · `source-only` · `inferred` · empty | for observed rows, where the string was seen: a parsed resource, a symbol table or string section, or a source-like game file (descriptor, script). `inferred`: not seen. Empty for legacy rows |
| `method` | `paired-symbol-record` · `literal` · `resource-binding` · `grammar-recovery` · empty | how the name was obtained. Empty for legacy rows |
| `id_basis` | `resource` · `type` · `registered` · `stored` · `constant` · `none` | where the **hash itself** is seen: a shipped resource id, a type id, a type the engine registers, an id stored in a resource body, a 64-bit constant in code, or none of these (an id can be real without being indexed) |
| `spelling_basis` | `observed` · `corroborated` · `search` · `legacy-corroborated` · `legacy-unknown` | why the spelling is believed: seen as a string · supported by a non-search rule under [Verdicts](#verdicts) · found by a search, see `p_chance` · a legacy row with such support · a legacy row with none yet |
| `p_chance` | number or empty | set only when `spelling_basis` is `search`: the expected number of false matches per accepted row of that search, measured by running the same search on random 64-bit ids. A rate, not a probability, so it can exceed 1 |
| `source_game`, `source_platform` | `echo_vr` · `lone_echo_1` · `lone_echo_2`; `pc` · `quest`; empty for legacy rows | the game and platform whose files supplied the name |
| `source_build` | digits; empty for legacy rows | that build's id. The only provenance published |

### Verdicts

| verdict | rule |
|---|---|
| `KEEP-observed` | the spelling is read from a game file, and the read can be repeated |
| `KEEP-corroborated` | an independent fact supports the spelling: the id is stored in a resource body, a 64-bit code constant equals it, the name is built from an observed parent name or stem, the spelling appears in a binary section, or the engine registers the type |
| `KEEP-bounded` | found by a search with at most 0.01 expected false matches per row: either `p_chance` ≤ 0.01, or, for searches that allow arbitrary text at the end of a name, `p_chance` times the measured false-pass rate of a second filter ≤ 0.01. Rows with no `p_chance` were computed exactly from the hash after a known prefix (algebra, not search), or are a one-word name stored next to a bounded row |
| `UNCONFIRMED` | the id is real (`id_basis` `resource` or `stored`) but no evidence we hold proves the spelling. Use with care |

## `data/membership/<game>-<platform>.tsv`

`hash`, `classes` (`;`-joined resource classes the hash ships under; a class whose type name is unknown is written as
its hash), `first_build`, `last_build`, `n_builds` (number of indexed builds that ship it). Only hashes in
`names.tsv` are listed.

## Other tables

- `data/coverage/<game>-<platform>.tsv`: `class`, `file_symbols` (distinct hashes the indexed builds ship under that
  class), `named` (how many of them are in `names.tsv`).
- `data/builds.tsv`: `build_id`, `game`, `platform`, `date` (`YYYY-MM-DD`, empty when unknown). Every build cited
  by another table is listed.
- `data/lanes.tsv`: one row per game and platform: `builds_indexed` of `builds_listed`, `classes_indexed`, `status`
  (`indexed`: every downloaded build is indexed; `partial`: membership is incomplete) and a short `note`.

## Types: `data/types.tsv`

Key `hash`, `game`, `platform`: one row per type symbol (the hash a package uses to say what class an asset is)
that game's indexed builds ship. A type symbol is CSymbol64 of the class name plus a layer suffix, so one class has
a different hash per platform and layer.

| column | values | meaning |
|---|---|---|
| `hash` | `0x` + 16 hex | the type symbol as a package stores it |
| `class` | class name or empty | the class; empty when it is not known. A row with a class always has its name in `names.tsv` |
| `suffix` | `Win7` · `Win10` · `Android`, optionally + `GPU` or `Debug`; empty when `class` is | `hash` = CSymbol64(`class` + `suffix`) |
| `schema` | `win7` · `win10` · `android` | the package format the hash was read from (known even when the class is not) |
| `layer` | `primary` · `gpu` · `debug` · `unknown` | from the suffix; `unknown` when `class` is empty |
| `game`, `platform` | as in `builds.tsv` | |
| `first_build`, `last_build` | build ids | first and last indexed build of that game and platform that ships an asset of this type |
| `assets` | count | distinct asset hashes ever shipped under this type in that game and platform |

Only shipped type symbols are listed. A class does not have every suffix: the engine computes a type symbol only for
the layers the class has, so a hash computed for any other suffix is not a real type.

## Sounds: `data/wwise/`

Sound banks are CSymbol64 assets in `names.tsv`. The objects inside a bank (events, buses, states, switches, game
parameters) are named by Wwise-32 ids. Media files (`.wem`) inside a bank have an id that is **not** a name hash.

`data/wwise/names.tsv`, key `id`:

| column | values | meaning |
|---|---|---|
| `id` | `0x` + 8 hex | Wwise-32 of `name` |
| `name` | `[A-Za-z0-9_]+` | the name |
| `case` | `authored` · `folded` | as in `names.tsv`: `authored` = a game file spells it this way |
| `verdict` | `KEEP-observed` · `KEEP-bounded` · `UNCONFIRMED` | as in `names.tsv`: observed rows are `KEEP-observed`; a search row is `KEEP-bounded` when `p_chance` ≤ 0.01, else `UNCONFIRMED` |
| `spelling_basis` | `observed` · `search` | seen as a string in a game file, or found by a search (see `p_chance`) |
| `p_chance` | number or empty | as in `names.tsv`; set only for `search` rows |
| `source_game`, `source_platform`, `source_build` | as in `names.tsv` | the build whose files supplied the name (for `search`: the build whose banks hold the id) |

`data/wwise/usage/<game>-<platform>.tsv`, key `id`: `id` (in `wwise/names.tsv`), `kinds`, `build`. Lists the named
ids that the banks of `build` refer to. `kinds` is a `;`-joined sorted set of `event`, `bus` (bus or auxiliary bus),
`effect` (effect share set) and `game_sync` (a state, switch, game parameter or one of their groups; the bank does
not always say which).

`data/wwise/media/<game>-<platform>.tsv`, key `bank`, `media`: `bank` (CSymbol64 of the bank, in `names.tsv`),
`media` (the media id), `label`, `via_event` (Wwise-32 id of an event that plays the media), `build`. **`label` is
our label, not a recovered name.** It is the name of the shortest named event that plays the media, with `_NN`
added when that event plays several media; if no named event plays it, it is `evt_<via_event hex>` (+ `_NN`).
The same media id can appear in more than one bank.

## Scripts: `data/scripts/`

Each table has Echo VR PC and Quest rows, told apart by `build`. The two platforms share function, script and
class ids, so every key includes `build`. PC counts come from the script symbol files (PDB); Quest has none, so its
counts come from the script libraries' own symbol tables.

- `functions.tsv`, key `hash`, `build`: `hash` (CSymbol64 id of a script function), `first_script` (CSymbol64 of
  the first script asset, by id, whose symbols list it), `n_scripts` (how many scripts list it), `build`. The function's name,
  when known, is the `names.tsv` row with the same hash. Unnamed ids are listed so they can be named.
- `function_scripts.tsv`, key `function`, `script`, `build`: every script whose code holds the function id. `role` is
  `declares` (the script defines the function; per function this count equals `n_scripts`) or `references` (the
  script only uses it). `functions.tsv`'s `first_script` is always one of these rows.
- `constant_scripts.tsv`, key `constant`, `script`, `build`: graph constants (variables, events, node inputs, execution
  pins, ...) named in `names.tsv`, one row per script whose code holds the constant. `role`: `variable` ·
  `node_input_value` · `exec_pin` · `graph_state` · `event` · `function_data` · `rdata_table` · `type_or_funcparam` ·
  `expression_input` · `function_param` · `timeline_node_value` · `debug_name` · `other`; one role per constant.
- `node_classes.tsv`, key `hash`, `build`: `hash` (CSymbol64 of `name`), `name` (the node class as the script symbols
  spell it, in capitals: `[A-Z0-9_]+`), `n_scripts`, `build`. On Quest `n_scripts` is a lower bound: a class whose
  code was inlined into a library leaves no symbol there. `names.tsv` may hold the same hash with its authored case.

## Generated views

`tools/build_views.py` writes `games/` and `subsets/` from `data/` only. `validate.py` regenerates them and fails if
any byte differs.

- `games/<game>/<platform>/assets.tsv`: every hash in that game's membership table, with `hash`, `name`, `classes`,
  `tier`, `case`, `verdict`, `first_build`, `last_build`, `n_builds`.
- `games/<game>/<platform>/other.tsv`: every other row whose `source_game` and `source_platform` are that game and
  platform, with `hash`, `name`, `kind`, `tier`, `case`, `verdict`.
- `games/<game>/<platform>/sounds/names.tsv`: that platform's `wwise/usage` rows with `name` and `verdict`.
  `sounds/media/<bank>.tsv`: one file per bank, `media`, `label`, `via_event`, `event` (the event's name or empty).
- `games/<game>/<platform>/scripts/functions.tsv`: one row per `function_scripts.tsv` pair: `script_name`,
  `script`, `role`, `hash`, `name`, sorted by script name, so one script's functions are together.
  `scripts/constants.tsv`: the same layout for `constant_scripts.tsv`. `scripts/node_classes.tsv`: `hash`, `name`, `cased_name`
  (from `names.tsv`, or empty), `n_scripts`.
- `subsets/wwise_lookup.json`: every Wwise-32 name as `{"0x…": name}`.
- `games/<game>/<platform>/shaders/shadersets.tsv`: every name of that game's `assets.tsv` + `other.tsv` that has the
  shader-set form `<owner>_<owner_kind>~<material>~<pass>[~<feature>…]`, split into `owner`, `owner_kind`
  (`radscn` · `radlvl` · `radins` · `raddynins`), `material`, `pass`, `features` (`;`-joined, in name order), plus
  `hash`, `tier`, `case`. Sorted by owner, material, pass, features.
- `games/<game>/<platform>/types.tsv`: that game's `data/types.tsv` rows, `class`, `suffix`, `layer`, `hash`,
  `first_build`, `last_build`, `assets`, sorted by class (unknown classes last).
- JSON files are objects sorted by key, one entry per line, ASCII-escaped.

## JSON release files

Each GitHub release from 0.3.0 on has `echo-symbols.json.gz` and one `<game>-<platform>.json.gz`, written by
`tools/export_json.py`. They hold the same data as `data/` and nothing more: `names` is an object keyed by hash,
each row with its `membership` per `<game>-<platform>`; the other tables are lists of rows keyed by column name.
Every value is the TSV string. A per-game file holds that game's membership hashes plus the names its own files
supplied, and the types, builds, sounds and scripts of that game and platform. They are release files, not part of
the repository.

## Versioning

`MAJOR.MINOR.PATCH`: MAJOR changes a column or its meaning; MINOR adds rows or tables; PATCH corrects rows.
[CHANGELOG.md](CHANGELOG.md) records each release.
