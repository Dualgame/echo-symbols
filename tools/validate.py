#!/usr/bin/env python3
"""Validate the repository: data format, every hash, the generated views, and that no file holds private strings.

    python3 tools/validate.py

Exit 0 = every check passed. Extra private strings to search for (a username, a host) are read from the environment
variable ECHO_SYMBOLS_PRIVATE (comma-separated) or a gitignored `.private-literals` file, never from the repo.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True  # a .pyc embeds this checkout's absolute path
sys.path.insert(0, str(ROOT / "hashes"))
sys.path.insert(0, str(ROOT / "tools"))
from csymbol64 import canonical, csymbol64  # noqa: E402
from wwise32 import canonical32, wwise32  # noqa: E402
from build_views import build, read_tsv  # noqa: E402

BUILD = r"\d{6,17}"
NAMES = {  # column -> full-match pattern; every column of every row is checked, nothing is free text
    "hash": r"0x[0-9a-f]{16}", "name": r"[\x20-\x7e]*",
    "kind": r"asset|type|script_function|script_constant|internal_field|language_key|literal|other",
    "case": r"authored|adjudicated|folded", "tier": r"observed|inferred|legacy",
    "verdict": r"KEEP-observed|KEEP-corroborated|KEEP-bounded|UNCONFIRMED",
    "evidence": r"|inferred|symbols-only|stream-confirmed|source-only",
    "method": r"|grammar-recovery|literal|resource-binding|paired-symbol-record",
    "id_basis": r"resource|type|registered|stored|constant|none",
    "spelling_basis": r"observed|corroborated|search|legacy-corroborated|legacy-unknown",
    "p_chance": r"|[0-9.]+(e-?[0-9]+)?", "source_game": r"|echo_vr|lone_echo_1|lone_echo_2",
    "source_platform": r"|pc|quest", "source_build": "|" + BUILD,
}
MEMBERSHIP = {"hash": r"0x[0-9a-f]{16}", "classes": r"[A-Za-z0-9_]+(;[A-Za-z0-9_]+)*", "first_build": BUILD,
              "last_build": BUILD, "n_builds": r"[1-9][0-9]*"}
COVERAGE = {"class": r"[A-Za-z0-9_]+", "file_symbols": r"[0-9]+", "named": r"[0-9]+"}
BUILDS = {"build_id": BUILD, "game": r"echo_vr|lone_echo_1|lone_echo_2", "platform": r"pc|quest",
          "date": r"|\d{4}-\d{2}-\d{2}"}
LANES = {"game": BUILDS["game"], "platform": r"pc|quest", "builds_indexed": r"[0-9]+", "builds_listed": r"[0-9]+",
         "classes_indexed": r"[0-9]+", "status": r"indexed|partial", "note": r"[a-z0-9 ;,.]+"}
ID32, HASH = r"0x[0-9a-f]{8}", r"0x[0-9a-f]{16}"
WWISE = {"id": ID32, "name": r"[A-Za-z0-9_]+", "case": r"authored|folded",
         "verdict": r"KEEP-observed|KEEP-bounded|UNCONFIRMED", "spelling_basis": r"observed|search",
         "p_chance": NAMES["p_chance"], "source_game": BUILDS["game"], "source_platform": r"pc|quest",
         "source_build": BUILD}
USAGE = {"id": ID32, "kinds": r"(bus|effect|event|game_sync)(;(bus|effect|event|game_sync))*", "build": BUILD}
MEDIA = {"bank": HASH, "media": ID32, "label": r"[A-Za-z0-9_]+", "via_event": ID32, "build": BUILD}
FUNCTIONS = {"hash": HASH, "first_script": HASH, "n_scripts": r"[1-9][0-9]*", "build": BUILD}
NODE_CLASSES = {"hash": HASH, "name": r"[A-Z0-9_]+", "n_scripts": r"[1-9][0-9]*", "build": BUILD}
PRIVATE = [r"\b[A-Za-z]:[\\/][A-Za-z0-9_]", r"/home/", r"/mnt/", r"/tmp/", r"/Users/", r"\\\\[A-Za-z0-9.-]+\\",
           r"(?<![:/])//[A-Za-z0-9.-]+/", r"\b[0-9a-fA-F]{40,}\b",
           r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", r"[\w.+-]+@[\w-]+\.(com|net|org|io)\b"]
errors = []


def fail(msg):
    errors.append(msg)


def check_table(path, schema, sort_key="hash"):
    with open(path, encoding="utf-8", newline="\n") as f:
        header = f.readline().rstrip("\n").split("\t")
    if header != list(schema):
        fail(f"{path.name}: header {header}")
        return []
    rows = read_tsv(path)
    pats = {k: re.compile(v) for k, v in schema.items()}
    for i, r in enumerate(rows, 2):
        if len(r) != len(schema) or any(v is None for v in r.values()):
            fail(f"{path.name}:{i}: {len(r)} columns")
            continue
        for k, v in r.items():
            if not pats[k].fullmatch(v):
                fail(f"{path.name}:{i}: {k} = {v!r}")
    keys = [tuple(r[k] for k in sort_key.split(",")) for r in rows]
    if keys != sorted(set(keys)):
        fail(f"{path.name}: not sorted / unique by {sort_key}")
    return rows


def check_files():
    """LF only, no BOM, final newline, no private path / address / literal in ANY tracked or untracked file."""
    literals = [s for s in os.environ.get("ECHO_SYMBOLS_PRIVATE", "").split(",") if s]
    extra = ROOT / ".private-literals"
    if extra.is_file():
        literals += [s.strip() for s in extra.read_text().splitlines() if s.strip()]
    pats = [re.compile(p) for p in PRIVATE] + [re.compile(re.escape(s), re.I) for s in literals]
    files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True,
                           text=True).stdout.splitlines()
    files = files or [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()]
    for name in files:
        raw = (ROOT / name).read_bytes()
        if b"\r" in raw or raw.startswith(b"\xef\xbb\xbf") or (raw and not raw.endswith(b"\n")):
            fail(f"{name}: CR, BOM or missing final newline")
        text = raw.decode("utf-8", errors="replace")
        for p in pats:
            if name == "tools/validate.py" and p.pattern in PRIVATE:
                continue  # this file spells the generic patterns; supplied literals still apply to it
            m = p.search(text)
            if m:
                fail(f"{name}: private pattern {p.pattern[:24]!r} at offset {m.start()}")
    return len(literals)


def check_sounds_scripts(data, by_hash, builds):
    """data/wwise/ and data/scripts/: every id rehashes or resolves; returns the builds they cite."""
    cited = set()

    def lane_of(name, r, stem=None):  # a cited build must exist and belong to the file's game and platform
        b = builds.get(r["build"])
        if b and stem and f"{b['game']}-{b['platform']}" != stem:
            fail(f"{name}: build {r['build']} is not {stem}")
        cited.add(r["build"])

    wwise = {}
    for r in check_table(data / "wwise/names.tsv", WWISE, "id"):
        wwise[r["id"]] = r["name"]
        if canonical32(wwise32(r["name"])) != r["id"]:
            fail(f"wwise/names.tsv: {r['id']} does not hash {r['name']!r}")
        if (r["spelling_basis"] == "search") != bool(r["p_chance"]):
            fail(f"wwise/names.tsv: {r['id']} p_chance iff spelling_basis=search")
        want = ("KEEP-observed" if r["spelling_basis"] == "observed" else
                "KEEP-bounded" if r["p_chance"] and float(r["p_chance"]) <= 0.01 else "UNCONFIRMED")
        if r["verdict"] != want:
            fail(f"wwise/names.tsv: {r['id']} verdict {r['verdict']} (rule gives {want})")
        lane_of("wwise/names.tsv", {"build": r["source_build"]}, f"{r['source_game']}-{r['source_platform']}")
    for path in sorted((data / "wwise/usage").glob("*.tsv")):
        for r in check_table(path, USAGE, "id"):
            lane_of(f"wwise/usage/{path.name}", r, path.stem)
            if r["id"] not in wwise:
                fail(f"wwise/usage/{path.name}: {r['id']} not in wwise/names.tsv")
            if r["kinds"].split(";") != sorted(set(r["kinds"].split(";"))):
                fail(f"wwise/usage/{path.name}: {r['id']} kinds not sorted / unique")
    for path in sorted((data / "wwise/media").glob("*.tsv")):
        for r in check_table(path, MEDIA, "bank,media"):
            lane_of(f"wwise/media/{path.name}", r, path.stem)
            if r["bank"] not in by_hash:
                fail(f"wwise/media/{path.name}: bank {r['bank']} not in names.tsv")
            # a media id is not a name hash: its label is the via_event's name (or evt_<id>), + _NN if shared
            stem = re.escape(wwise.get(r["via_event"], "evt_" + r["via_event"][2:]))
            if not re.fullmatch(stem + r"(_\d{2})?", r["label"]):
                fail(f"wwise/media/{path.name}: {r['bank']} {r['media']} label does not follow via_event")
    for r in check_table(data / "scripts/functions.tsv", FUNCTIONS):
        lane_of("scripts/functions.tsv", r)
    for r in check_table(data / "scripts/node_classes.tsv", NODE_CLASSES):
        lane_of("scripts/node_classes.tsv", r)
        if canonical(csymbol64(r["name"])) != r["hash"]:
            fail(f"scripts/node_classes.tsv: {r['hash']} does not hash {r['name']!r}")
    return cited


def main():
    data = ROOT / "data"
    names = check_table(data / "names.tsv", NAMES)
    by_hash = {r["hash"]: r for r in names}
    for r in names:
        if canonical(csymbol64(r["name"])) != r["hash"]:
            fail(f"names.tsv: {r['hash']} does not hash {r['name']!r}")
        if (r["spelling_basis"] == "search") != bool(r["p_chance"]):
            fail(f"names.tsv: {r['hash']} p_chance iff spelling_basis=search")
        if r["verdict"] == "UNCONFIRMED" and r["id_basis"] not in ("resource", "stored"):
            fail(f"names.tsv: {r['hash']} UNCONFIRMED without an anchored id")
    builds = {r["build_id"] for r in check_table(data / "builds.tsv", BUILDS, "build_id")}
    cited = {r["source_build"] for r in names} - {""}
    lanes = check_table(data / "lanes.tsv", LANES, "game,platform")
    for lane in lanes:
        stem = f"{lane['game']}-{lane['platform']}.tsv"
        for m in check_table(data / "membership" / stem, MEMBERSHIP):
            cited |= {m["first_build"], m["last_build"]}
            if m["hash"] not in by_hash:
                fail(f"membership/{stem}: {m['hash']} not in names.tsv")
        for c in check_table(data / "coverage" / stem, COVERAGE, "class"):
            if int(c["named"]) > int(c["file_symbols"]):
                fail(f"coverage/{stem}: {c['class']} named > total")
    cited |= check_sounds_scripts(data, by_hash, {r["build_id"]: r for r in read_tsv(data / "builds.tsv")})
    if cited - builds:
        fail(f"builds.tsv: {len(cited - builds)} cited builds missing")
    for v in read_tsv(ROOT / "hashes/vectors.tsv"):
        if canonical(csymbol64(v["name"])) != v["hash"]:
            fail(f"vectors.tsv: {v['name']!r}")
    for v in read_tsv(ROOT / "hashes/wwise32_vectors.tsv"):
        if canonical32(wwise32(v["name"])) != v["id"]:
            fail(f"wwise32_vectors.tsv: {v['name']!r}")
    with tempfile.TemporaryDirectory() as tmp:
        build(Path(tmp))
        for sub in ("games", "subsets"):
            want = {p.relative_to(tmp): p.read_bytes() for p in (Path(tmp) / sub).rglob("*") if p.is_file()}
            have = {p.relative_to(ROOT): p.read_bytes() for p in (ROOT / sub).rglob("*") if p.is_file()}
            if want != have:
                fail(f"{sub}/ is stale: run tools/build_views.py ({len(set(want) ^ set(have))} files differ in set)")
    n_literals = check_files()
    n_wwise = len(read_tsv(data / "wwise/names.tsv"))
    for e in errors[:50]:
        print("FAIL", e)
    print(f"{len(names)} names, {len(builds)} builds, {len(lanes)} lanes, {n_wwise} Wwise names, "
          f"{n_literals} private literals checked: "
          + ("OK" if not errors else f"{len(errors)} errors"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
