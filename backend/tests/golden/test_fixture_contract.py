import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

import fixtures.kinematics_golden_v1 as golden_fixture_module
from fixtures.kinematics_golden_v1 import GoldenFixtureError, load_golden_fixture
from fixtures.kinematics_golden_v1.mutations import apply_mutation_recipe


@pytest.mark.golden_contract
def test_golden_fixture_manifest_and_integrity_are_valid():
    fixture = load_golden_fixture()

    assert fixture.manifest["profile"] == "kinematics-golden.v1"
    assert fixture.manifest["frame_mapping"]["mode"] == "explicit"
    assert fixture.manifest["integrity"]["manifest_sha256"] != "TBD"
    assert set(fixture.expected_contract_paths) == {"ingest", "metrics", "report"}
    assert set(fixture.mutation_recipe_paths) == {"missing_right_wrist"}


@pytest.mark.golden_contract
def test_golden_fixture_preserves_non_affine_frame_gap():
    fixture = load_golden_fixture()
    mapping = json.loads(fixture.frame_mapping_path.read_text(encoding="utf-8"))
    entries = mapping["entries"]

    assert entries[55]["source_original_frame"] == 490
    assert entries[56]["source_original_frame"] == 498
    assert entries[94]["has_skeleton"] is False
    assert sum(entry["has_skeleton"] for entry in entries) == 104


def test_golden_fixture_rejects_path_escape():
    fixture = load_golden_fixture()

    with pytest.raises(GoldenFixtureError, match="escapes fixture root"):
        fixture._resolve_manifest_path("../../outside.json")


def test_golden_fixture_reports_missing_file_and_hash_mismatch(tmp_path: Path):
    fixture = load_golden_fixture()
    missing = tmp_path / "missing.bin"
    with pytest.raises(GoldenFixtureError, match="file missing"):
        fixture._verify_file("test", missing, "0" * 64)

    tampered = tmp_path / "tampered.bin"
    tampered.write_bytes(b"tampered")
    with pytest.raises(GoldenFixtureError, match="checksum mismatch"):
        fixture._verify_file("test", tampered, "0" * 64)


def test_golden_fixture_rejects_inconsistent_explicit_mapping(tmp_path: Path, monkeypatch):
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text(
        json.dumps(
            {
                "mode": "explicit",
                "source_original_offset": 10,
                "entries": [
                    {"annotation_frame": 0, "source_original_frame": 10, "source_video_frame": 0, "has_skeleton": True},
                    {"annotation_frame": 1, "source_original_frame": 13, "source_video_frame": 2, "has_skeleton": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(golden_fixture_module, "FIXTURE_DIR", tmp_path)
    fixture = golden_fixture_module.GoldenFixture()
    fixture._manifest = {
        "annotations": {"total_images": 2, "active_frames": 2},
        "frame_mapping": {"mode": "explicit", "mapping_file": "mapping.json"},
    }

    with pytest.raises(GoldenFixtureError, match="offset mismatch"):
        fixture._validate_frame_mapping()


def test_missing_right_wrist_mutation_is_deterministic(tmp_path: Path):
    fixture = load_golden_fixture()
    recipe = fixture.mutation_recipe_paths["missing_right_wrist"]
    output = tmp_path / "missing_right_wrist.xml"
    second_output = tmp_path / "missing_right_wrist.second.xml"

    apply_mutation_recipe(recipe, output)
    apply_mutation_recipe(recipe, second_output)
    assert output.read_bytes() == second_output.read_bytes()
    root = ET.parse(output).getroot()
    changed = [
        points
        for points in root.iter("points")
        if points.attrib.get("label") == "right-wrist" and points.attrib.get("outside") == "1"
    ]
    assert len(changed) == fixture.active_frames
