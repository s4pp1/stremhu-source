import datetime

from sqlalchemy.orm import Session

from app.modules.pairings.models import PairingModel


class PairingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_device_code(self, device_code: str) -> PairingModel | None:
        return self.db.query(PairingModel).filter_by(device_code=device_code).first()

    def find_by_user_code(self, user_code: str) -> PairingModel | None:
        return self.db.query(PairingModel).filter_by(user_code=user_code).first()

    def create(self, pairing: PairingModel) -> PairingModel:
        self.db.add(pairing)
        self.db.flush()
        return pairing

    def delete(self, pairing: PairingModel) -> None:
        self.db.delete(pairing)
        self.db.flush()

    def find_expired(self) -> list[PairingModel]:
        now = datetime.datetime.now()
        return self.db.query(PairingModel).filter(PairingModel.expires_at < now).all()
