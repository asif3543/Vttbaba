from .start import router as start_router
from .post import router as post_router
from .send import router as send_router
from .shortner import router as shortner_router
from .premium import router as premium_router
from .forcesub import router as fsub_router

from aiogram import Router
router = Router()
router.include_router(start_router)
router.include_router(post_router)
router.include_router(send_router)
router.include_router(shortner_router)
router.include_router(premium_router)
router.include_router(fsub_router)
