from sqlalchemy.orm import Session

from app.common.logger import logger
from app.modules.roles.models import RoleModel
from app.modules.roles.seeds import DEFAULT_ROLES


class RolesService:
    def __init__(self, db: Session):
        self.db = db

    def find_list(self) -> list[RoleModel]:
        return self.db.query(RoleModel).all()

    def sync_to_db(self) -> None:
        """Szinkronizálja a kódbázisban definiált szerepköröket az adatbázissal.

        Frissíti a meglévőket, beszúrja az újakat, és törli azokat, amelyek
        kikerültek a kódból.
        """

        code_ids = {role.id for role in DEFAULT_ROLES}

        deleted_count = (
            self.db.query(RoleModel)
            .filter(RoleModel.id.not_in(code_ids))
            .delete(synchronize_session=False)
        )
        if deleted_count > 0:
            logger.info(f"🗑️ Törölve {deleted_count} elavult szerepkör a DB-ből.")

        for code_role in DEFAULT_ROLES:
            db_role = (
                self.db.query(RoleModel).filter(RoleModel.id == code_role.id).first()
            )

            if db_role:
                if db_role.name != code_role.name:
                    db_role.name = code_role.name
            else:
                self.db.add(RoleModel(id=code_role.id, name=code_role.name))

        self.db.commit()
