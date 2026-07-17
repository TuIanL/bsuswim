from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings


settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
    app.include_router(api_router, prefix=settings.api_prefix)

    # 启动即注册内置指标计算器（side_view_metrics / side_2d_kinematics），
    # 保证 ?calculator= 参数与 has_calculator 校验立即可用。
    from app.services.metrics.kinematics.registry import register_builtin_calculators

    register_builtin_calculators()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "backend"}

    return app


app = create_app()
