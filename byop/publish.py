"""Publish a layers dir as a GitHub Release and print its registry entry.

For sources whose layers are built locally (rasters, big CSVs) and not committed: run this on the
machine that has them. It validates the dir exactly as `byop validate` does, creates the release if it
doesn't exist, uploads every file, and prints the measures.json entry with sha256 pins computed from
the files it uploaded. Needs the GitHub CLI (`gh`) logged in as someone who can write to the repo.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .validate import load_spec, validate_layers_dir


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def layer_files(layers_dir: Path) -> list[Path]:
    """The spec plus exactly the files it names (stray files in the folder are not published)."""
    spec = load_spec(layers_dir)
    names = ["aggregation_spec.json", *sorted({layer["file"] for layer in spec["layers"].values()})]
    return [layers_dir / name for name in names]


def registry_entry(layers_dir: Path, *, name: str, repo: str, tag: str, targets: list[str],
                   allocation_method: str | None = None, confidence: str = "high") -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": name, "repo": repo, "tag": tag,
        "assets": {p.name: sha256(p) for p in layer_files(layers_dir)},
        "targets": targets, "confidence": confidence,
    }
    if allocation_method:
        entry["allocation_method"] = allocation_method
    return entry


def publish(layers_dir: Path, *, repo: str, tag: str, notes: str = "", dry_run: bool = False,
            lenient: bool = False) -> list[Path]:
    layers_dir = Path(layers_dir)
    validate_layers_dir(layers_dir, strict_catalog=not lenient)
    files = layer_files(layers_dir)
    if dry_run:
        return files
    exists = subprocess.run(["gh", "release", "view", tag, "--repo", repo], capture_output=True).returncode == 0
    if not exists:
        subprocess.run(["gh", "release", "create", tag, "--repo", repo, "--title", tag,
                        "--notes", notes or f"byop/v1 layers ({tag})"], check=True)
    subprocess.run(["gh", "release", "upload", tag, "--repo", repo, "--clobber", *map(str, files)], check=True)
    return files
