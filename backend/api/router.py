"""Main API router combining all sub-routers."""

from fastapi import APIRouter

from api.documents import router as documents_router
from api.interview import router as interview_router
from api.questions import router as questions_router
from api.evaluation import router as evaluation_router
from api.analytics import router as analytics_router
from api.realtime import router as realtime_router

api_router = APIRouter()

api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(interview_router, prefix="/interview", tags=["Interview"])
api_router.include_router(questions_router, prefix="/questions", tags=["Questions"])
api_router.include_router(evaluation_router, prefix="/evaluate", tags=["Evaluation"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(realtime_router, prefix="/realtime", tags=["Real-Time"])
