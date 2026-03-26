"""API v1 router."""
from fastapi import APIRouter
from app.api.v1 import auth, process, threads, users, reviews, metrics, gmail, analytics, traces

router = APIRouter()

router.include_router(auth.router, tags=["auth"])
router.include_router(process.router, tags=["process"])
router.include_router(threads.router, tags=["threads"])
router.include_router(users.router, tags=["users"])
router.include_router(reviews.router, tags=["reviews"])
router.include_router(metrics.router, tags=["metrics"])
router.include_router(gmail.router, tags=["gmail"])
router.include_router(analytics.router, tags=["analytics"])
router.include_router(traces.router, tags=["traces"])
