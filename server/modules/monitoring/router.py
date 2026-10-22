from fastapi import APIRouter

from server.common.schemas.api import SuccessResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=SuccessResponse,
    tags=["Monitoring"],
)
def health() -> SuccessResponse:
    return SuccessResponse(
        success=True,
        message="🚀 StremHU Source fut! 🚀",
    )
