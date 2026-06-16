from fastapi import FastAPI

from app.runtime import SwimModelRuntime
from app.schemas import AnalysisRequest, AnalysisResponse

app = FastAPI(title="智泳云枢模型服务")
runtime = SwimModelRuntime()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "model_service"}


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest) -> AnalysisResponse:
    return runtime.analyze(request)
