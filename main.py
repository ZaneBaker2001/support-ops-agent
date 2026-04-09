import uvicorn

from app.config import get_settings


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.api:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "dev",
    )