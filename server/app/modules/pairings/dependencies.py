from typing import Annotated
from app.common.database import get_db
from fastapi import Depends
from app.modules.pairings.repository import PairingsRepository
from app.modules.pairings.service import PairingsService
from sqlalchemy.orm import Session


def create_pairings_service(db: Session) -> PairingsService:
    """Hozzárendeli a szervizt egy háttérfeladat vagy HTTP kérés adatbázis munkamenetéhez."""
    pairings_repository = PairingsRepository(db)
    return PairingsService(pairings_repository)


def get_pairings_service(
    db: Annotated[Session, Depends(get_db)],
) -> PairingsService:
    """FastAPI függőség-injektáló provider a PairingsService példányosításához."""
    return create_pairings_service(db)
