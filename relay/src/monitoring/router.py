import time

from fastapi import APIRouter
from monitoring.schemas import Health

router = APIRouter()

START_TIME = time.time()


@router.get(
    "/health",
    response_model=Health,
    operation_id="health",
    tags=["Monitoring"],
)
async def health() -> Health:
    return Health(
        start_time=START_TIME,
    )
