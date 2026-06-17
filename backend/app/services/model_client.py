import httpx

from app.core.config import get_settings
from app.schemas import ModelAnalysisRequest, ModelAnalysisResult


class ModelServiceError(RuntimeError):
    pass


class ModelServiceClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def analyze(self, request: ModelAnalysisRequest) -> ModelAnalysisResult:
        url = f"{self.settings.model_service_url.rstrip('/')}/api/v1/analyze"
        try:
            async with httpx.AsyncClient(timeout=self.settings.model_service_timeout_seconds) as client:
                response = await client.post(url, json=request.model_dump(mode="json"))
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ModelServiceError(f"模型服务调用失败: {exc}") from exc

        try:
            result = ModelAnalysisResult.model_validate(response.json())
        except Exception as exc:
            raise ModelServiceError(f"模型服务响应无法校验: {exc}") from exc

        if result.status == "failed":
            raise ModelServiceError(result.error_message or "模型服务返回失败状态")

        return result
