from fastapi import APIRouter
from monitoring.schemas import Health

router = APIRouter()


@router.get(
    "/health",
    response_model=Health,
    operation_id="health",
    tags=["Monitoring"],
)
async def health() -> Health:
    return Health(ok=True)
