from aiogram import Router

from . import export_users, start

def get_handlers_router() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(export_users.router)

    return router
