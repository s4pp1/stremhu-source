import datetime
import secrets
import sqlite3
import uuid
from collections.abc import Callable

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError

from app.common.schemas.internal import Success
from app.modules.pairings.enums import LinkResult, PairingStatusEnum
from app.modules.pairings.repository import PairingsRepository
from app.modules.pairings.schemas.internal import PairInit, PairStatus
from app.modules.users.models import UserModel


def _secure_user_code() -> str:
    return f"{secrets.randbelow(10_000):04d}"


def _unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="A párosítás átmenetileg nem elérhető.", headers={"Retry-After": "30"})


def _is_lock_error(error: OperationalError) -> bool:
    code = getattr(error.orig, "sqlite_errorcode", 0)
    return isinstance(code, int) and (code & 255) in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}


class PairingsService:
    def __init__(self, pairings_repository: PairingsRepository, *, now: Callable[[], datetime.datetime] = datetime.datetime.now, code_factory: Callable[[], str] | None = None):
        self._pairings_repository = pairings_repository
        self._now = now
        self._code_factory = code_factory or _secure_user_code

    def generate_pairing_codes(self) -> PairInit:
        now = self._now()
        expires_at = now + datetime.timedelta(minutes=10)
        for _ in range(16):
            user_code = self._code_factory()
            if len(user_code) != 4 or not user_code.isascii() or not user_code.isdecimal():
                raise ValueError("Invalid pairing code factory output")
            device_code = str(uuid.uuid4())
            try:
                inserted = self._pairings_repository.try_create_unique_pairing(user_code, device_code, expires_at, now)
            except IntegrityError:
                self._pairings_repository.db.rollback()
                raise _unavailable() from None
            except OperationalError as error:
                self._pairings_repository.db.rollback()
                if _is_lock_error(error):
                    raise _unavailable() from None
                raise
            if inserted:
                return PairInit(user_code=user_code, device_code=device_code, expires_at=expires_at)
        raise _unavailable()

    def poll_pairing_status(self, device_code: str) -> PairStatus:
        now = self._now()
        pairing = self._pairings_repository.find_valid_by_device_code(device_code, now)
        if pairing is None:
            if self._pairings_repository.find_by_device_code(device_code) is not None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="A párosítási kód lejárt!")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Érvénytelen eszköz kód!")
        if pairing.status == PairingStatusEnum.LINKED and pairing.user_id and pairing.user:
            return PairStatus(status=PairingStatusEnum.LINKED, token=pairing.user.api_key)
        return PairStatus(status=pairing.status)

    def authorize_pairing_code(self, user_code: str, user: UserModel) -> Success:
        if len(user_code) != 4 or not user_code.isascii() or not user_code.isdecimal():
            raise HTTPException(status_code=400, detail="A párosítási kód 4 ASCII számjegy.")
        now = self._now()
        try:
            result = self._pairings_repository.link_if_pending(user_code, user.id, now)
        except IntegrityError:
            self._pairings_repository.db.rollback()
            raise _unavailable() from None
        except OperationalError as error:
            self._pairings_repository.db.rollback()
            if _is_lock_error(error):
                raise _unavailable() from None
            raise
        if result in {LinkResult.LINKED_NOW, LinkResult.ALREADY_LINKED_TO_SAME_USER}:
            return Success(success=True)
        if result == LinkResult.CONFLICT:
            raise HTTPException(status_code=409, detail="A kód már másik felhasználóhoz tartozik.")
        pairing = self._pairings_repository.find_by_user_code(user_code)
        if pairing is not None and pairing.expires_at <= now:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="A kód már lejárt!")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Érvénytelen vagy lejárt kód!")

    def cleanup_expired_pairings(self) -> None:
        for pairing in self._pairings_repository.find_expired(self._now()):
            self._pairings_repository.delete(pairing)
