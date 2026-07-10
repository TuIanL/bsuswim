"""单元测试：legacy quality v1 → v2 适配器。"""

from app.services.annotation_quality.legacy import migrate_legacy_quality_payload, normalize_quality_payload


class TestLegacyMigration:
    def test_v2_identity(self):
        v2 = {
            "schema_version": "annotation-quality.v2",
            "status": "valid",
            "score": 90,
            "source_revision": 1,
            "validator_version": "1.0.0",
            "profile": {"id": "test", "version": "1"},
            "validated_at": "2026-01-01T00:00:00+00:00",
            "summary": {"blocking_count": 0, "error_count": 0, "warning_count": 0, "info_count": 0},
            "issues": [],
            "module_readiness": {},
        }
        result = normalize_quality_payload(v2)
        assert result.status == "valid"
        assert result.schema_version == "annotation-quality.v2"

    def test_legacy_good_to_valid(self):
        v1 = {
            "level": "good",
            "score": 85,
            "checks": [
                {"key": "has_fps", "status": "passed", "message": "ok"},
                {"key": "has_events", "status": "passed", "message": "ok"},
            ],
            "usable_modules": ["body_angle", "elbow_angle"],
            "disabled_modules": [],
        }
        result = migrate_legacy_quality_payload(v1)
        assert result.status == "valid"
        assert result.schema_version == "annotation-quality.v2"
        assert result.score >= 0

    def test_legacy_error_to_invalid(self):
        v1 = {
            "level": "error",
            "score": 30,
            "checks": [
                {"key": "has_fps", "status": "failed", "message": "no fps"},
                {"key": "has_events", "status": "passed", "message": "ok"},
            ],
            "usable_modules": [],
            "disabled_modules": [{"module": "joint_angles", "reason": "missing data"}],
        }
        result = migrate_legacy_quality_payload(v1)
        assert result.status == "invalid"
        assert result.issues is not None

    def test_legacy_warning(self):
        v1 = {
            "level": "warning",
            "score": 60,
            "checks": [{"key": "has_scale", "status": "failed", "message": "no scale"}],
            "usable_modules": [],
            "disabled_modules": [{"module": "speed_distance", "reason": "no scale"}],
        }
        result = migrate_legacy_quality_payload(v1)
        assert result.status == "warning"

    def test_empty_fallback_to_invalid(self):
        result = migrate_legacy_quality_payload({})
        assert result.status == "invalid"
