from fastapi import APIRouter

from app.api.routes import chat, dashboard, educators, health, imports, students

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(students.router)
api_router.include_router(educators.router)
api_router.include_router(dashboard.router)
api_router.include_router(imports.router)
