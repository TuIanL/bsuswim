"""Declarative mutations for deterministic golden-fixture variants."""

from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any

from . import GoldenFixtureError


def apply_mutation_recipe(
    recipe_path: Path,
    output_path: Path,
    *,
    fixture_root: Path | None = None,
) -> Path:
    """Apply a supported mutation recipe and write a deterministic XML copy.

    The source fixture is never edited. The recipe's ``source`` path is
    resolved relative to the fixture root, which defaults to the directory
    containing ``mutations/``.
    """
    recipe = _load_recipe(recipe_path)
    fixture_root = (fixture_root or recipe_path.parent.parent).resolve()
    source = _resolve_fixture_path(fixture_root, recipe["source"])
    output_path = output_path.resolve()
    if output_path == source:
        raise GoldenFixtureError("Mutation output must not overwrite the source fixture")
    if not source.exists():
        raise GoldenFixtureError(f"Mutation source file does not exist: {source}")

    try:
        tree = ET.parse(source)
    except ET.ParseError as exc:
        raise GoldenFixtureError(f"Mutation source is invalid XML: {source}: {exc}") from exc

    if recipe["operation"] != "set_visibility" or recipe["visibility"] != "missing":
        raise GoldenFixtureError(
            "Only set_visibility with visibility=missing is supported by the golden mutation reader"
        )

    target_joint = _normalize_joint(recipe["joint"])
    active_images = [image for image in tree.getroot().iter("image") if image.find(".//skeleton") is not None]
    if recipe["frames"] == "all_active":
        target_images = active_images
    else:
        raise GoldenFixtureError(f"Unsupported mutation frame selector: {recipe['frames']!r}")

    changed = 0
    for image in target_images:
        matches = [
            points
            for points in image.findall(".//points")
            if _normalize_joint(points.attrib.get("label", "")) == target_joint
        ]
        if not matches:
            image_id = image.attrib.get("id", "?")
            raise GoldenFixtureError(f"Mutation joint {recipe['joint']!r} not found in image {image_id}")
        for points in matches:
            points.set("outside", "1")
            changed += 1

    if changed == 0:
        raise GoldenFixtureError(f"Mutation did not change any {recipe['joint']!r} points")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return output_path


def _load_recipe(recipe_path: Path) -> dict[str, Any]:
    try:
        recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GoldenFixtureError(f"Mutation recipe does not exist: {recipe_path}") from exc
    except json.JSONDecodeError as exc:
        raise GoldenFixtureError(f"Mutation recipe is invalid JSON: {recipe_path}: {exc}") from exc
    if not isinstance(recipe, dict):
        raise GoldenFixtureError("Mutation recipe must be a JSON object")
    required = ("schema_version", "operation", "joint", "frames", "visibility", "source")
    missing = [key for key in required if key not in recipe]
    if missing:
        raise GoldenFixtureError(f"Mutation recipe missing required fields: {', '.join(missing)}")
    if recipe["schema_version"] != "1.0":
        raise GoldenFixtureError(f"Unsupported mutation recipe schema: {recipe['schema_version']!r}")
    if recipe.get("deterministic") is not True:
        raise GoldenFixtureError("Mutation recipe must declare deterministic=true")
    return recipe


def _resolve_fixture_path(fixture_root: Path, relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path or Path(relative_path).is_absolute():
        raise GoldenFixtureError(f"Invalid mutation source path: {relative_path!r}")
    path = (fixture_root / relative_path).resolve()
    try:
        path.relative_to(fixture_root)
    except ValueError as exc:
        raise GoldenFixtureError(f"Mutation source escapes fixture root: {relative_path!r}") from exc
    return path


def _normalize_joint(label: str) -> str:
    return label.strip().lower().replace("-", "_").replace(" ", "_")
