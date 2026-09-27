from fastapi import APIRouter
from app.core.response import ApiResponse, success_response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=ApiResponse[dict])
async def health_check():
    return success_response(
        data={"status": "ok", "service": "furnace_backend"},
        message="Service is healthy"
    )
