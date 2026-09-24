from fastapi import APIRouter
from . import auth, chat, admin, health, models

router = APIRouter()

def include_routers(app):
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(admin.router)
    app.include_router(health.router)
    app.include_router(models.router)
