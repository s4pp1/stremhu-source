from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.common.database import get_db
from core.modules.pairings.repository import PairingsRepository
from core.modules.pairings.service import PairingsService


def create_pairings_service(db: Session) -> PairingsService:
    """Hozzárendeli a szervizt egy háttérfeladat vagy HTTP kérés adatbázis munkamenetéhez."""
    pairings_repository = PairingsRepository(db)
    return PairingsService(pairings_repository)


def get_pairings_service(
    db: Annotated[Session, Depends(get_db)],
) -> PairingsService:
    """FastAPI függőség-injektáló provider a PairingsService példányosításához."""
    return create_pairings_service(db)
