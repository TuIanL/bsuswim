import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PAYLOAD = {
    "task_id": 1,
    "session_id": 2,
    "athlete": {"id": 3, "name": "测试运动员", "gender": "male", "level": "demo"},
    "session": {
        "id": 2,
        "title": "自由泳 50m 联调",
        "stroke_type": "freestyle",
        "distance_m": 50,
        "pool_length_m": 50,
        "session_date": "2026-06-17",
    },
    "videos": [
        {
            "video_file_id": 4,
            "view_type": "side",
            "video_url": "/uploads/demo.mp4",
            "video_path": "uploads/demo.mp4",
            "fps": 60,
            "resolution": "1920x1080",
            "sync_offset_ms": 0,
        }
    ],
    "callback_url": "/api/v1/analysis/1/result",
    "schema_version": "analysis.request.v1",
}


def run_with_path(path: Path, code: str, payload: dict) -> str:
    env = {**os.environ, "PYTHONPATH": str(path)}
    result = subprocess.run(
        [sys.executable, "-c", code],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        cwd=ROOT,
        env=env,
    )
    return result.stdout


backend_json = run_with_path(
    ROOT / "backend",
    """
import json, sys
from app.schemas.analysis import ModelAnalysisRequest
payload = json.load(sys.stdin)
request = ModelAnalysisRequest.model_validate(payload)
print(json.dumps(request.model_dump(mode="json")))
""",
    PAYLOAD,
)

model_json = run_with_path(
    ROOT / "model_service",
    """
import json, sys
from app.runtime import SwimModelRuntime
from app.schemas import AnalysisRequest
payload = json.load(sys.stdin)
request = AnalysisRequest.model_validate(payload)
response = SwimModelRuntime().analyze(request)
print(json.dumps(response.model_dump()))
""",
    json.loads(backend_json),
)

run_with_path(
    ROOT / "backend",
    """
import json, sys
from app.schemas.analysis import ModelAnalysisResult
payload = json.load(sys.stdin)
result = ModelAnalysisResult.model_validate(payload)
assert result.status == "completed"
assert result.schema_version == "swim-analysis.v1"
assert result.metrics["video_count"] == 1
print("model service contract ok")
""",
    json.loads(model_json),
)

print("backend request:", backend_json.strip())
print("model response:", model_json.strip())
print("model service contract ok")
