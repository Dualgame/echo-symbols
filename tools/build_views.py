#!/usr/bin/env python3
"""Regenerate games/ and subsets/ from data/. Deterministic: same data/ in, same bytes out.

    python3 tools/build_views.py            # rewrite games/ and subsets/ in place
    python3 tools/build_views.py --out DIR  # write elsewhere (validate.py compares the two)
"""
import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_tsv(path):
    with open(path, encoding="utf-8", newline="\n") as f:
        header = f.readline().rstrip("\n").split("\t")
        rows = []
        for i, line in enumerate(f, 2):
            fields = line.rstrip("\n").split("\t")
            if len(fields) != len(header):  # zip() would silently drop an extra column
                raise ValueError(f"{path.name}:{i}: {len(fields)} fields, header has {len(header)}")
            rows.append(dict(zip(header, fields)))
        return rows


def write_tsv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(header) + "\n")
        f.writelines("\t".join(str(row[k]) for k in header) + "\n" for row in rows)


def write_json(path, mapping):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(sorted(mapping.items())), f, indent=0, ensure_ascii=True)
        f.write("\n")


def status_md(lane, rows, assets, other, coverage):
    game, platform = lane["game"], lane["platform"]
    named = sum(int(c["named"]) for c in coverage)
    total = sum(int(c["file_symbols"]) for c in coverage)
    tiers = {t: sum(1 for r in rows if r["tier"] == t) for t in ("observed", "inferred", "legacy")}
    lines = [f"# {game} / {platform}", "",
             f"Status: **{lane['status']}** — {lane['note']}.", "",
             f"Builds indexed: {lane['builds_indexed']} of {lane['builds_listed']} listed. "
             f"Classes indexed: {lane['classes_indexed']} (a class with an unknown type name is shown as `0x…`).", "",
             "| file | rows |", "|---|---:|",
             f"| `assets.tsv` (in this game's build index) | {len(assets)} |",
             f"| `other.tsv` (from this game's files, not in its build index) | {len(other)} |", "",
             f"Tiers: observed {tiers['observed']} · inferred {tiers['inferred']} · legacy {tiers['legacy']}.", "",
             "## Coverage per class", "",
             "A hash counts once for each class it ships under. "
             f"Overall {named} / {total} named.", "",
             "| class | hashes | named | % |", "|---|---:|---:|---:|"]
    for c in sorted(coverage, key=lambda c: (-int(c["file_symbols"]), c["class"])):
        t, k = int(c["file_symbols"]), int(c["named"])
        lines.append(f"| `{c['class']}` | {t} | {k} | {100 * k / t:.1f} |")
    return "\n".join(lines) + "\n"


def stats_md(names, lanes):
    rows = list(names.values())

    def table(col, title):
        counts = {}
        for r in rows:
            counts[r[col] or "(none)"] = counts.get(r[col] or "(none)", 0) + 1
        out = [f"| {title} | rows | % |", "|---|---:|---:|"]
        ranked = sorted(counts.items(), key=lambda kv: -kv[1])
        out += [f"| `{k}` | {n} | {100 * n / len(rows):.1f} |" for k, n in ranked]
        return out + [""]

    lines = ["# Statistics", "", f"Generated from `data/` by `tools/build_views.py`. **{len(rows)} names.**", "",
             "| game | platform | status | assets.tsv | other.tsv |", "|---|---|---|---:|---:|"]
    lines += [f"| {g} | {p} | {s} | {a} | {o} |" for g, p, s, a, o in lanes] + [""]
    for col, title in (("verdict", "verdict"), ("tier", "tier"), ("case", "case"), ("kind", "kind"),
                       ("spelling_basis", "spelling basis")):
        lines += table(col, title)
    return "\n".join(lines)


def build(out):
    data = ROOT / "data"
    names = {r["hash"]: r for r in read_tsv(data / "names.tsv")}
    for sub in ("games", "subsets"):
        shutil.rmtree(out / sub, ignore_errors=True)
    write_json(out / "subsets/hash_lookup.json", {h: r["name"] for h, r in names.items()})
    write_json(out / "subsets/types.json", {h: r["name"] for h, r in names.items() if r["kind"] == "type"})
    summary = []
    for lane in read_tsv(data / "lanes.tsv"):
        game, platform = lane["game"], lane["platform"]
        stem = f"{game}-{platform}"
        member = {m["hash"]: m for m in read_tsv(data / "membership" / f"{stem}.tsv")}
        assets = [{**names[h], **m} for h, m in sorted(member.items())]
        other = [r for h, r in sorted(names.items())
                 if h not in member and r["source_game"] == game and r["source_platform"] == platform]
        lane_dir = out / "games" / game / platform
        write_tsv(lane_dir / "assets.tsv", ["hash", "name", "classes", "tier", "case", "verdict", "first_build",
                                            "last_build", "n_builds"], assets)
        write_tsv(lane_dir / "other.tsv", ["hash", "name", "kind", "tier", "case", "verdict"], other)
        coverage = read_tsv(data / "coverage" / f"{stem}.tsv")
        (lane_dir / "STATUS.md").write_text(status_md(lane, assets + other, assets, other, coverage),
                                            encoding="utf-8", newline="\n")
        write_json(out / "subsets" / f"{stem}.json", {r["hash"]: r["name"] for r in assets + other})
        summary.append((game, platform, lane["status"], len(assets), len(other)))
    (out / "games/STATS.md").write_text(stats_md(names, summary), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT)
    build(ap.parse_args().out)
