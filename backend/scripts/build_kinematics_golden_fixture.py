"""Build a candidate golden contract without mutating the approved baseline.

The first implementation intentionally treats the existing expected JSON files as
the candidate input. A later full-stack runner can replace those files with the
observed pipeline output, while this command keeps the approval boundary explicit.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("backend/tests/fixtures/kinematics_golden_v1"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    manifest = json.loads((source_dir / "fixture_manifest.json").read_text(encoding="utf-8"))
    expected = manifest.get("expected_contracts", {})
    if not expected:
        raise SystemExit("fixture manifest has no expected_contracts")

    output_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for relative_path in expected.values():
        source = source_dir / relative_path
        if not source.is_file():
            raise SystemExit(f"missing expected contract: {source}")
        destination = output_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1

    candidate_manifest = output_dir / "fixture_manifest.json"
    candidate_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {copied} candidate contracts to {output_dir}")
    print("candidate is not approved; run approve_kinematics_golden_baseline.py explicitly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
