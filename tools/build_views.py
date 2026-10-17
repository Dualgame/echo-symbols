#!/usr/bin/env python3
"""Regenerate games/ and subsets/ from data/. Deterministic: same data/ in, same bytes out.

    python3 tools/build_views.py            # rewrite games/ and subsets/ in place
    python3 tools/build_views.py --out DIR  # write elsewhere (validate.py compares the two)
"""
import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# A shader-set name: <owner>_<owner kind>~<material>~<pass>[~<feature>...]
SHADERSET = re.compile(r"(.+)_(radscn|radlvl|radins|raddynins)~([^~]+)~([^~]+)((?:~[^~]+)*)")


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


def sound_script_views(data, names, lane_dir, stem, lane_builds):
    """games/<game>/<platform>/sounds/ and scripts/; returns the STATUS.md lines for them."""
    lines = ["", "## Sounds and scripts", ""]
    wwise = {r["id"]: r for r in read_tsv(data / "wwise/names.tsv")}
    usage = data / "wwise/usage" / f"{stem}.tsv"
    if usage.is_file():
        used = [{**u, **wwise[u["id"]]} for u in read_tsv(usage)]
        write_tsv(lane_dir / "sounds/names.tsv", ["id", "name", "kinds", "verdict"], used)
        media = read_tsv(data / "wwise/media" / f"{stem}.tsv")
        banks = {}
        for m in media:
            banks.setdefault(names[m["bank"]]["name"], []).append({**m, "event": wwise.get(m["via_event"], {}).get("name", "")})
        for bank, body in banks.items():
            write_tsv(lane_dir / "sounds/media" / f"{bank}.tsv", ["media", "label", "via_event", "event"], body)
        by_event = sum(1 for m in media if m["via_event"] in wwise)
        lines.append(f"Sound names referenced by the banks: {len(used)}. Media: {len(media)} in {len(banks)} banks; "
                     f"{by_event} labelled from a named event, {len(media) - by_event} from an unnamed one.")
    else:
        lines.append("Sound bank contents (Wwise names, media) are not indexed for this game and platform.")
    funcs = [r for r in read_tsv(data / "scripts/functions.tsv") if r["build"] in lane_builds]
    nodes = [r for r in read_tsv(data / "scripts/node_classes.tsv") if r["build"] in lane_builds]
    if funcs or nodes:
        script = lambda h: names[h]["name"] if h in names else ""  # noqa: E731
        body = sorted(({"script_name": script(f["first_script"]), "script": f["first_script"], "hash": f["hash"],
                        "name": script(f["hash"]), "n_scripts": f["n_scripts"]} for f in funcs),
                      key=lambda r: (r["script_name"], r["script"], r["hash"]))
        write_tsv(lane_dir / "scripts/functions.tsv", ["script_name", "script", "hash", "name", "n_scripts"], body)
        write_tsv(lane_dir / "scripts/node_classes.tsv", ["hash", "name", "cased_name", "n_scripts"],
                  [{**n, "cased_name": script(n["hash"])} for n in nodes])
        lines.append(f"Script functions: {sum(1 for r in body if r['name'])} of {len(body)} named. "
                     f"Script node classes: {len(nodes)}.")
    else:
        lines.append("Script functions and node classes are not indexed for this game and platform.")
    return lines


def shader_views(lane_dir, rows):
    """games/<game>/<platform>/shaders/shadersets.tsv: shader-set names split into their parts."""
    body = []
    for r in rows:
        m = SHADERSET.fullmatch(r["name"])
        if m:
            body.append({**r, "owner": m[1], "owner_kind": m[2], "material": m[3], "pass": m[4],
                         "features": m[5][1:].replace("~", ";")})
    if not body:
        return []
    body.sort(key=lambda r: (r["owner"], r["material"], r["pass"], r["features"], r["hash"]))
    write_tsv(lane_dir / "shaders/shadersets.tsv", ["owner", "owner_kind", "material", "pass", "features", "hash",
                                                     "tier", "case"], body)
    return [f"Shader-set names split into owner, material, pass and features: {len(body)} "
            "(`shaders/shadersets.tsv`)."]


def status_md(lane, rows, assets, other, coverage, extra):
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
    return "\n".join(lines + extra) + "\n"


def stats_md(names, lanes, wwise):
    def table(col, title, rows):
        counts = {}
        for r in rows:
            counts[r[col] or "(none)"] = counts.get(r[col] or "(none)", 0) + 1
        out = [f"| {title} | rows | % |", "|---|---:|---:|"]
        ranked = sorted(counts.items(), key=lambda kv: -kv[1])
        out += [f"| `{k}` | {n} | {100 * n / len(rows):.1f} |" for k, n in ranked]
        return out + [""]

    rows = list(names.values())
    lines = ["# Statistics", "", f"Generated from `data/` by `tools/build_views.py`. **{len(rows)} names.**", "",
             "| game | platform | status | assets.tsv | other.tsv |", "|---|---|---|---:|---:|"]
    lines += [f"| {g} | {p} | {s} | {a} | {o} |" for g, p, s, a, o in lanes] + [""]
    for col, title in (("verdict", "verdict"), ("tier", "tier"), ("case", "case"), ("kind", "kind"),
                       ("spelling_basis", "spelling basis")):
        lines += table(col, title, rows)
    lines += ["## Wwise sound names", "", f"**{len(wwise)} names** in `data/wwise/names.tsv`.", ""]
    for col, title in (("verdict", "verdict"), ("spelling_basis", "spelling basis"), ("case", "case"),
                       ("source_game", "source game")):
        lines += table(col, title, wwise)
    return "\n".join(lines)


def build(out):
    data = ROOT / "data"
    names = {r["hash"]: r for r in read_tsv(data / "names.tsv")}
    for sub in ("games", "subsets"):
        shutil.rmtree(out / sub, ignore_errors=True)
    write_json(out / "subsets/hash_lookup.json", {h: r["name"] for h, r in names.items()})
    write_json(out / "subsets/types.json", {h: r["name"] for h, r in names.items() if r["kind"] == "type"})
    builds = read_tsv(data / "builds.tsv")
    wwise = read_tsv(data / "wwise/names.tsv")
    write_json(out / "subsets/wwise_lookup.json", {r["id"]: r["name"] for r in wwise})
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
        lane_builds = {b["build_id"] for b in builds if (b["game"], b["platform"]) == (game, platform)}
        extra = sound_script_views(data, names, lane_dir, stem, lane_builds)
        extra += shader_views(lane_dir, assets + other)
        (lane_dir / "STATUS.md").write_text(status_md(lane, assets + other, assets, other, coverage, extra),
                                            encoding="utf-8", newline="\n")
        write_json(out / "subsets" / f"{stem}.json", {r["hash"]: r["name"] for r in assets + other})
        summary.append((game, platform, lane["status"], len(assets), len(other)))
    (out / "games/STATS.md").write_text(stats_md(names, summary, wwise), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT)
    build(ap.parse_args().out)
