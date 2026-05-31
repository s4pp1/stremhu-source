from common.logger import logger
from modules.preferences.models import PreferenceModel
from modules.preferences.seeds import DEFAULT_PREFERENCES
from sqlalchemy.orm import Session


class PreferencesService:
    def __init__(self, db: Session):
        self.db = db

    def sync_to_db(self):
        """Szinkronizálja a kódbázisban definiált preferenciákat az adatbázissal.

        Frissíti a meglévőket, beszúrja az újakat, és törli azokat, amelyek
        kikerültek a kódból.
        """

        code_ids = {pref.id for pref in DEFAULT_PREFERENCES}

        deleted_count = (
            self.db.query(PreferenceModel)
            .filter(PreferenceModel.id.not_in(code_ids))
            .delete(synchronize_session=False)
        )
        if deleted_count > 0:
            logger.info(f"🗑️ Törölve {deleted_count} elavult kategória a DB-ből.")

        for pref in DEFAULT_PREFERENCES:
            db_pref = (
                self.db.query(PreferenceModel)
                .filter(PreferenceModel.id == pref.id)
                .first()
            )

            if db_pref:
                if db_pref.name != pref.name or db_pref.description != pref.description:
                    db_pref.name = pref.name
                    db_pref.description = pref.description
            else:
                new_pref = PreferenceModel(
                    id=pref.id,
                    name=pref.name,
                    description=pref.description,
                )
                self.db.add(new_pref)

        self.db.commit()
