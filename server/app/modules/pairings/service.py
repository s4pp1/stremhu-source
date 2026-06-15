import datetime
import random
import uuid

from fastapi import HTTPException, status

from app.common.schemas.internal import Success
from app.modules.pairings.enums import PairingStatusEnum
from app.modules.pairings.models import PairingModel
from app.modules.pairings.repository import PairingsRepository
from app.modules.pairings.schemas.internal import PairInit, PairStatus
from app.modules.users.models import UserModel


class PairingsService:
    def __init__(self, pairings_repository: PairingsRepository):
        self._pairings_repository = pairings_repository

    def generate_pairing_codes(self) -> PairInit:
        user_code = ""
        is_unique = False

        # Loop until we get a unique userCode within the active timeframes
        while not is_unique:
            user_code = "".join(random.choices("0123456789", k=4))
            existing = self._pairings_repository.find_by_user_code(user_code)
            if not existing:
                is_unique = True

        device_code = str(uuid.uuid4())
        expires_at = datetime.datetime.now() + datetime.timedelta(minutes=10)

        pairing = PairingModel(
            user_code=user_code,
            device_code=device_code,
            expires_at=expires_at,
            status=PairingStatusEnum.PENDING,
        )
        self._pairings_repository.create(pairing)

        return PairInit(
            user_code=user_code,
            device_code=device_code,
            expires_at=expires_at,
        )

    def poll_pairing_status(self, device_code: str) -> PairStatus:
        pairing = self._pairings_repository.find_by_device_code(device_code)

        if not pairing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Érvénytelen eszköz kód!",
            )

        if pairing.expires_at < datetime.datetime.now():
            pairing.status = PairingStatusEnum.EXPIRED
            # repo.create actually acts as save/update as it flushes changes
            self._pairings_repository.create(pairing)

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A párosítási kód lejárt!",
            )

        if pairing.status == PairingStatusEnum.LINKED and pairing.user_id:
            # We must load the user to return their API token
            if pairing.user:
                return PairStatus(
                    status=PairingStatusEnum.LINKED,
                    token=pairing.user.api_key,
                )

        return PairStatus(status=pairing.status)

    def authorize_pairing_code(self, user_code: str, user: UserModel) -> Success:
        pairing = self._pairings_repository.find_by_user_code(user_code)

        if not pairing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Érvénytelen vagy lejárt kód!",
            )

        if pairing.expires_at < datetime.datetime.now():
            pairing.status = PairingStatusEnum.EXPIRED
            self._pairings_repository.create(pairing)

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A kód már lejárt!",
            )

        pairing.status = PairingStatusEnum.LINKED
        pairing.user_id = user.id
        self._pairings_repository.create(pairing)

        return Success(success=True)

    def cleanup_expired_pairings(self) -> None:
        expired = self._pairings_repository.find_expired()
        for pairing in expired:
            self._pairings_repository.delete(pairing)
