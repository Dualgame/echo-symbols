# Data specification — v0.1

All tables are UTF-8 TSV with a header row, LF line endings and no BOM. Fields never contain a tab or newline and
are never quoted or escaped: a field is the exact bytes between two tabs. Each table is sorted by its first
column(s). `tools/validate.py` checks the format, every column's allowed values, every hash, a few cross-column rules,
and that cited hashes and builds exist. It does not re-check how a verdict was reached.

"Game file" below means a file from a downloaded game build.

## Hashes

`hash` is CSymbol64 of `name`, written `0x` + 16 lowercase hex digits. No other spelling is accepted (unpadded,
uppercase, decimal, signed or byte-swapped). Algorithm: [hashes/csymbol64.py](hashes/csymbol64.py). Names are
ASCII; `A`–`Z` are lowercased before hashing.

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

## Generated views

`tools/build_views.py` writes `games/` and `subsets/` from `data/` only. `validate.py` regenerates them and fails if
any byte differs.

- `games/<game>/<platform>/assets.tsv`: every hash in that game's membership table, with `hash`, `name`, `classes`,
  `tier`, `case`, `verdict`, `first_build`, `last_build`, `n_builds`.
- `games/<game>/<platform>/other.tsv`: every other row whose `source_game` and `source_platform` are that game and
  platform, with `hash`, `name`, `kind`, `tier`, `case`, `verdict`.
- JSON files are objects sorted by key, one entry per line, ASCII-escaped.

## Versioning

`MAJOR.MINOR.PATCH`: MAJOR changes a column or its meaning; MINOR adds rows or tables; PATCH corrects rows.
[CHANGELOG.md](CHANGELOG.md) records each release.
