import datetime
import uuid
from typing import cast

from sqlalchemy import delete, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.modules.pairings.enums import LinkResult, PairingStatusEnum
from app.modules.pairings.models import PairingModel


class PairingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_device_code(self, device_code: str) -> PairingModel | None:
        return self.db.query(PairingModel).filter_by(device_code=device_code).first()

    def find_valid_by_device_code(self, device_code: str, now: datetime.datetime) -> PairingModel | None:
        return self.db.query(PairingModel).filter(PairingModel.device_code == device_code, PairingModel.expires_at > now).first()

    def try_create_unique_pairing(self, code: str, device_code: str, expires_at: datetime.datetime, now: datetime.datetime) -> bool:
        self.db.execute(delete(PairingModel).where(PairingModel.user_code == code, PairingModel.expires_at <= now))
        statement = insert(PairingModel).values(id=str(uuid.uuid4()), user_code=code, device_code=device_code, expires_at=expires_at, created_at=now, status=PairingStatusEnum.PENDING, user_id=None).on_conflict_do_nothing(index_elements=[PairingModel.user_code])
        result = cast(CursorResult, self.db.execute(statement))
        return result.rowcount == 1

    def link_if_pending(self, user_code: str, user_id: str, now: datetime.datetime) -> LinkResult:
        statement = update(PairingModel).where(PairingModel.user_code == user_code, PairingModel.status == PairingStatusEnum.PENDING, PairingModel.expires_at > now).values(status=PairingStatusEnum.LINKED, user_id=user_id).execution_options(synchronize_session=False)
        result = cast(CursorResult, self.db.execute(statement))
        if result.rowcount == 1:
            return LinkResult.LINKED_NOW
        pairing = self.db.query(PairingModel).filter_by(user_code=user_code).populate_existing().first()
        if pairing is None or pairing.expires_at <= now:
            return LinkResult.EXPIRED_OR_MISSING
        if pairing.status == PairingStatusEnum.LINKED:
            return LinkResult.ALREADY_LINKED_TO_SAME_USER if pairing.user_id == user_id else LinkResult.CONFLICT
        return LinkResult.EXPIRED_OR_MISSING

    def find_by_user_code(self, user_code: str) -> PairingModel | None:
        return self.db.query(PairingModel).filter_by(user_code=user_code).first()

    def create(self, pairing: PairingModel) -> PairingModel:
        self.db.add(pairing)
        self.db.flush()
        return pairing

    def delete(self, pairing: PairingModel) -> None:
        self.db.delete(pairing)
        self.db.flush()

    def find_expired(self, now: datetime.datetime | None = None) -> list[PairingModel]:
        now = now or datetime.datetime.now()
        return self.db.query(PairingModel).filter(PairingModel.expires_at <= now).all()
