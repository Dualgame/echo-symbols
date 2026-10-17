#!/usr/bin/env python3
"""Write every table in data/ as JSON: one file for the whole set and one per game and platform.

    python3 tools/export_json.py --out DIR [--gzip]

  echo-symbols.json            {"names": {hash: row + "membership": {lane: row}}, "types", "builds", "lanes",
                                "wwise": {"names", "usage", "media"}, "scripts": {...}}
  <game>-<platform>.json       the same shape, cut to the hashes, types, sounds and scripts of that game and platform

Every value is the TSV field as written (a string); nothing is added that data/ does not hold. The release workflow
attaches these files to each GitHub release; they are not committed, because each update would add tens of MB to
the history. Deterministic: same data/ in, same bytes out.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tools"))
from build_views import read_tsv  # noqa: E402


def load(data):
    lanes = read_tsv(data / "lanes.tsv")
    names = {r.pop("hash"): {**r, "membership": {}} for r in read_tsv(data / "names.tsv")}
    for lane in lanes:
        stem = f"{lane['game']}-{lane['platform']}"
        for m in read_tsv(data / "membership" / f"{stem}.tsv"):
            names[m.pop("hash")]["membership"][stem] = m
    return {
        "names": names, "types": read_tsv(data / "types.tsv"), "builds": read_tsv(data / "builds.tsv"),
        "lanes": lanes, "coverage": {f"{x['game']}-{x['platform']}": read_tsv(
            data / "coverage" / f"{x['game']}-{x['platform']}.tsv") for x in lanes},
        "wwise": {"names": read_tsv(data / "wwise/names.tsv"),
                  "usage": {p.stem: read_tsv(p) for p in sorted((data / "wwise/usage").glob("*.tsv"))},
                  "media": {p.stem: read_tsv(p) for p in sorted((data / "wwise/media").glob("*.tsv"))}},
        "scripts": {p.stem: read_tsv(p) for p in sorted((data / "scripts").glob("*.tsv"))},
    }


def lane_cut(full, stem):
    """One game and platform: its membership hashes plus the names its own files supplied."""
    game, platform = stem.split("-")
    builds = {b["build_id"] for b in full["builds"] if (b["game"], b["platform"]) == (game, platform)}
    names = {h: {**r, "membership": {k: v for k, v in r["membership"].items() if k == stem}}
             for h, r in full["names"].items()
             if stem in r["membership"] or (r["source_game"], r["source_platform"]) == (game, platform)}
    wwise_ids = {u["id"] for u in full["wwise"]["usage"].get(stem, [])}
    return {
        "names": names, "types": [t for t in full["types"] if (t["game"], t["platform"]) == (game, platform)],
        "builds": [b for b in full["builds"] if b["build_id"] in builds],
        "lanes": [x for x in full["lanes"] if (x["game"], x["platform"]) == (game, platform)],
        "coverage": {stem: full["coverage"][stem]},
        "wwise": {"names": [w for w in full["wwise"]["names"] if w["id"] in wwise_ids],
                  "usage": {k: v for k, v in full["wwise"]["usage"].items() if k == stem},
                  "media": {k: v for k, v in full["wwise"]["media"].items() if k == stem}},
        "scripts": {k: [r for r in v if r["build"] in builds] for k, v in full["scripts"].items()},
    }


def dump(path, obj, gz):
    raw = (json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")
    if gz:
        path = path.with_name(path.name + ".gz")
        raw = gzip.compress(raw, compresslevel=9, mtime=0)  # mtime=0: same bytes on every run
    path.write_bytes(raw)
    return path, len(raw)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--gzip", action="store_true", help="write .json.gz")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    full = load(ROOT / "data")
    outputs = [dump(a.out / "echo-symbols.json", full, a.gzip)]
    outputs += [dump(a.out / f"{stem}.json", lane_cut(full, stem), a.gzip) for stem in full["coverage"]]
    for path, size in outputs:
        print(f"{path.name}\t{size}")


if __name__ == "__main__":
    main()
