"""
Главный файл FastAPI приложения
Beauty Salon Booking System - Anasteisha
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

from .config import get_settings
from .database import engine, Base

settings = get_settings()

# Создание таблиц в БД
Base.metadata.create_all(bind=engine)

# FastAPI приложение
app = FastAPI(
    title="Anasteisha - Beauty Salon API",
    description="API для системы онлайн-записи",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [settings.SITE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы
frontend_path = Path(__file__).parent.parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")

@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

@app.get("/")
async def read_root():
    return FileResponse(str(frontend_path.parent / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=settings.DEBUG)
