from sqlalchemy import update
from sqlalchemy.orm import Session

from app.modules.users.models import UserModel


class UsersRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_list(self) -> list[UserModel]:
        return self.db.query(UserModel).all()

    def find_by_id(self, id: str) -> UserModel | None:
        return self.db.query(UserModel).filter_by(id=id).first()

    def find_by_username(self, username: str) -> UserModel | None:
        return self.db.query(UserModel).filter_by(username=username).first()

    def find_by_api_key(self, api_key: str) -> UserModel | None:
        return self.db.query(UserModel).filter_by(api_key=api_key).first()

    def bump_session_epoch(self, user_id: str) -> None:
        # Relative SQL update preserves simultaneous revocations. The caller
        # owns the password transaction and refreshes any loaded epoch.
        self.db.execute(
            update(UserModel).where(UserModel.id == user_id).values(
                session_epoch=UserModel.session_epoch + 1
            ).execution_options(synchronize_session=False)
        )

    def count(self) -> int:
        return self.db.query(UserModel).count()

    def create(self, user: UserModel) -> UserModel:
        self.db.add(user)
        self.db.flush()

        return user

    def delete(self, user_id: str) -> None:
        self.db.query(UserModel).filter_by(id=user_id).delete()
