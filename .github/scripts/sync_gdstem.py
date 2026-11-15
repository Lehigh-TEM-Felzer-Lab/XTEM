#!/usr/bin/env python3
"""Carries the changes of GDSTEM since the last sync into src/, and leaves the IO code of XTEM alone.

For every file GDSTEM changed since `last_synced` (.github/gdstem_sync.yaml) the script takes that file's own diff and applies it with
`git apply --3way` to the file of the same name in src/physics, src/io or src/driver. A file whose diff does not apply cleanly is left
as it was, and its diff is saved under sync/rejected/<sha>/ to be applied by hand. Files that XTEM replaced, parameter files, new,
deleted and renamed files are only listed in the report. Afterwards `last_synced` is the new commit.

usage: sync_gdstem.py [--ref gdstem/main] [--report report.md]   (fetch the remote first; run in a clean working tree)
"""
import argparse
import fnmatch
import pathlib
import subprocess
import sys

import yaml

root = pathlib.Path(__file__).resolve().parents[2]
cfg_file = root / ".github" / "gdstem_sync.yaml"
cfg = yaml.safe_load(cfg_file.read_text())
ap = argparse.ArgumentParser()
ap.add_argument("--ref", default="gdstem/main")
ap.add_argument("--report", default="sync_report.md")
args = ap.parse_args()


def git(*a: str, input: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *a], cwd=root, input=input, text=True, capture_output=True, check=check)


def match(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(pathlib.PurePath(path).name, p) for p in patterns)


last, new = cfg["last_synced"], git("rev-parse", args.ref).stdout.strip()
if last == new:
    print("up to date")
    sys.exit(0)

where = {p.name: p.parent.name for p in (root / "src").glob("*/*") if p.is_file()}
applied, rejected, manual, params, added, deleted, renamed = [], [], [], [], [], [], []

for line in git("diff", "--name-status", "-M", last, new).stdout.splitlines():
    status, *paths = line.split("\t")
    path = paths[-1]
    name = pathlib.PurePath(path).name
    if match(path, cfg["ignore"]):
        continue
    if match(path, cfg["params"]):
        params.append(path)
    elif match(path, cfg["manual"]):
        manual.append(path)
    elif status[0] == "R":
        renamed.append(f"{paths[0]} -> {paths[1]}")
    elif status == "A":
        added.append(f"{path} (GDSTEM layer: {pathlib.PurePath(path).parent.name})")
    elif status == "D":
        if name in where:
            deleted.append(path)
    elif name not in where:
        added.append(path + " (no file of this name in src/)")
    else:
        dest = f"src/{where[name]}"
        patch = git("diff", "--full-index", last, new, "--", path).stdout
        if git("apply", "--3way", f"-p{len(pathlib.PurePath(path).parts)}", f"--directory={dest}", "-", input=patch, check=False).returncode == 0:
            applied.append(f"{path} -> {dest}/{name}")
        else:
            git("checkout", "-q", "HEAD", "--", f"{dest}/{name}")
            out = root / "sync" / "rejected" / new[:7] / f"{name}.patch"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(patch)
            rejected.append(f"{path} -> {dest}/{name}  (diff saved as {out.relative_to(root)})")

cfg_file.write_text(cfg_file.read_text().replace(f"last_synced: {last}", f"last_synced: {new}"))
git("add", "-A")


def section(title: str, items: list[str], note: str) -> str:
    return f"\n### {title} ({len(items)})\n{note}\n" + "".join(f"- `{i}`\n" for i in items) if items else ""


rep = f"GDSTEM {last[:7]}..{new[:7]}\n"
rep += section("Applied", applied, "Applied with `git apply --3way`. Read the diff: renamed names (col, row -> lon, lat) and a hard-coded 12 for the number of steps are not caught by Git.")
rep += section("Not applied: conflict", rejected, "Apply by hand: `git apply --3way -p3 --directory=<dir> sync/rejected/<sha>/<file>.patch`, fix the markers, delete the patch file.")
rep += section("Not applied: XTEM replaced these files", manual, f"Port by hand if the change is science (`git diff {last[:7]} {new[:7]} -- <file>` in GDSTEM).")
rep += section("Parameter files", params, "Make the same change in params/*.yaml and params/provenance.md.")
rep += section("New in GDSTEM", added, "Decide whether it belongs in src/physics or src/io.")
rep += section("Deleted in GDSTEM", deleted, "Delete the file in src/ if the science no longer uses it.")
rep += section("Renamed in GDSTEM", renamed, "Rename the file in src/ and update includes.")
pathlib.Path(args.report).write_text(rep)
print(rep)
sys.exit(2 if rejected else 0)
