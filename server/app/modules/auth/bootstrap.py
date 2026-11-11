"""A durable first-admin reservation; no request Session crosses this boundary."""

import sqlite3
from dataclasses import dataclass, field

from argon2 import PasswordHasher
from fastapi import HTTPException
from sqlalchemy import JSON, func, literal, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.common.database import isolated_db_session
from app.modules.roles.constants import UserRoleKey
from app.modules.settings.models import SettingModel
from app.modules.users.models import UserModel
from app.modules.users.schemas.api import UserResponse

BOOTSTRAP_COMPLETE_KEY = "auth_bootstrap_complete"


@dataclass(frozen=True)
class CommittedUserSnapshot:
    user: UserResponse = field(repr=False)
    session_epoch: int


def _disabled() -> HTTPException:
    return HTTPException(status_code=403, detail="A kezdeti regisztráció már lezárult.")


def _has_users(db: Session) -> bool:
    return (db.scalar(select(func.count()).select_from(UserModel)) or 0) > 0


def _sqlite_code(error: IntegrityError | OperationalError) -> int:
    code = getattr(error.orig, "sqlite_errorcode", 0)
    return code if isinstance(code, int) else 0


def initialize_bootstrap_state() -> None:
    """Backfill existing installations before serving requests, never a fresh DB.

    This conditional insert is one write transaction. It retains the closed
    state if all legacy users are later removed; user/key data is untouched.
    """
    with isolated_db_session() as db:
        values = select(literal(BOOTSTRAP_COMPLETE_KEY), literal({}, type_=JSON)).where(select(UserModel.id).exists())
        db.execute(insert(SettingModel).from_select(["key", "value"], values).on_conflict_do_nothing(index_elements=[SettingModel.key]))


class BootstrapService:
    def register_first_admin(self, username: str, password: str) -> CommittedUserSnapshot:
        try:
            return self._register(username, password)
        except HTTPException:
            raise
        except OperationalError as error:
            if (_sqlite_code(error) & 255) in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
                raise HTTPException(status_code=503, detail="A kezdeti regisztráció átmenetileg nem elérhető.", headers={"Retry-After":"30"}) from None
            raise RuntimeError("Bootstrap registration failed: kind=OperationalError") from None
        except Exception as error:
            # Validation/ORM error representations can contain hashes or keys.
            raise RuntimeError(f"Bootstrap registration failed: kind={type(error).__name__}") from None

    def _register(self, username: str, password: str) -> CommittedUserSnapshot:
        with isolated_db_session() as db:
            if db.get(SettingModel, BOOTSTRAP_COMPLETE_KEY) is not None or _has_users(db):
                raise _disabled()
        # Expensive preparation holds no database transaction or writer lock.
        prepared_hash = PasswordHasher().hash(password)
        marker_conflict = False
        try:
            with isolated_db_session() as db:
                # First write reserves bootstrap across independent connections.
                db.add(SettingModel(key=BOOTSTRAP_COMPLETE_KEY, value={}))
                try:
                    db.flush()
                except IntegrityError as error:
                    marker_conflict = _sqlite_code(error) in {sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY, sqlite3.SQLITE_CONSTRAINT_UNIQUE}
                    raise
                if _has_users(db):
                    raise _disabled()
                user = UserModel(username=username, password_hash=prepared_hash, role_id=UserRoleKey.ADMIN)
                db.add(user)
                db.flush()
                snapshot = CommittedUserSnapshot(user=UserResponse.model_validate(user), session_epoch=user.session_epoch)
            # Context commit has succeeded and no live ORM/session is returned.
            return snapshot
        except IntegrityError:
            if marker_conflict:
                with isolated_db_session() as db:
                    if db.get(SettingModel, BOOTSTRAP_COMPLETE_KEY) is not None:
                        raise _disabled() from None
            raise
