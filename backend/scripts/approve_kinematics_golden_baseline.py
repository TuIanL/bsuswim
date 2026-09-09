"""Approve a candidate golden contract after displaying a JSON diff."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from difflib import unified_diff
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=Path("backend/tests/fixtures/kinematics_golden_v1"),
    )
    parser.add_argument("--reason", required=True)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_manifest_hash(manifest: dict) -> str:
    value = copy.deepcopy(manifest)
    value.setdefault("integrity", {})["manifest_sha256"] = ""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _show_diff(before: Path, after: Path) -> None:
    before_text = before.read_text(encoding="utf-8").splitlines(keepends=True) if before.exists() else []
    after_text = after.read_text(encoding="utf-8").splitlines(keepends=True)
    diff = unified_diff(before_text, after_text, fromfile=str(before), tofile=str(after))
    rendered = "".join(diff)
    if rendered:
        print(rendered)


def main() -> int:
    args = _parse_args()
    candidate_dir = args.candidate.resolve()
    fixture_dir = args.fixture_dir.resolve()
    if not args.reason.strip():
        raise SystemExit("--reason must not be empty")

    candidate_manifest_path = candidate_dir / "fixture_manifest.json"
    fixture_manifest_path = fixture_dir / "fixture_manifest.json"
    manifest = json.loads(fixture_manifest_path.read_text(encoding="utf-8"))
    candidate_manifest = json.loads(candidate_manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get("expected_contracts", {})

    for name, relative_path in expected.items():
        source = candidate_dir / relative_path
        destination = fixture_dir / relative_path
        if not source.is_file():
            raise SystemExit(f"candidate is missing {name}: {source}")
        _show_diff(destination, source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    integrity_files = manifest.setdefault("integrity", {}).setdefault("files", {})
    for relative_path in integrity_files:
        path = fixture_dir / relative_path
        if path.is_file():
            integrity_files[relative_path] = _sha256(path)
    manifest["integrity"]["approval_reason"] = args.reason.strip()
    manifest["integrity"]["manifest_sha256"] = ""
    manifest["integrity"]["manifest_sha256"] = _canonical_manifest_hash(manifest)
    fixture_manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"approved candidate baseline: {candidate_dir}")
    print(f"reason: {args.reason.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
