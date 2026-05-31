import time

from fastapi import APIRouter
from modules.monitoring.schemas import Health

router = APIRouter()

START_TIME = time.time()


@router.get(
    "/health",
    response_model=Health,
    tags=["Monitoring"],
)
def health() -> Health:
    return Health(
        start_time=START_TIME,
    )
