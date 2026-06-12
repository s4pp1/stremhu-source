import pydash
import sqlalchemy as sa
from common.logger import logger
from modules.attributes.models import AttributeModel
from modules.indexer_accounts.models import IndexerAccountModel
from modules.preferences.models import PreferenceModel
from modules.preferences.seeds import DEFAULT_PREFERENCES
from sqlalchemy.orm import Session, contains_eager


class PreferencesRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_list(self, user_id: str | None = None) -> list[PreferenceModel]:
        join_conditions = [
            PreferenceModel.id == AttributeModel.preference_id,
            sa.or_(
                AttributeModel.type != "indexer_definition",
                self.db.query(IndexerAccountModel.indexer_id)
                .filter(IndexerAccountModel.indexer_id == AttributeModel.id)
                .exists(),
            ),
        ]

        if user_id:
            from modules.attribute_exclusions.models import AttributeExclusionModel

            join_conditions.append(
                ~self.db.query(AttributeExclusionModel.id)
                .filter(
                    AttributeExclusionModel.attribute_id == AttributeModel.id,
                    AttributeExclusionModel.user_id == user_id,
                )
                .exists()
            )

        return (
            self.db.query(PreferenceModel)
            .join(
                AttributeModel,
                sa.and_(*join_conditions),
            )
            .options(contains_eager(PreferenceModel.attributes))
            .order_by(PreferenceModel.order.asc())
            .all()
        )

    def find_by_id(
        self,
        id: str,
        user_id: str | None = None,
    ) -> PreferenceModel | None:
        join_conditions = [
            PreferenceModel.id == AttributeModel.preference_id,
            sa.or_(
                AttributeModel.type != "indexer_definition",
                self.db.query(IndexerAccountModel.indexer_id)
                .filter(IndexerAccountModel.indexer_id == AttributeModel.id)
                .exists(),
            ),
        ]

        if user_id:
            from modules.attribute_exclusions.models import AttributeExclusionModel

            join_conditions.append(
                ~self.db.query(AttributeExclusionModel.id)
                .filter(
                    AttributeExclusionModel.attribute_id == AttributeModel.id,
                    AttributeExclusionModel.user_id == user_id,
                )
                .exists()
            )

        return (
            self.db.query(PreferenceModel)
            .join(
                AttributeModel,
                sa.and_(*join_conditions),
            )
            .filter(PreferenceModel.id == id)
            .options(contains_eager(PreferenceModel.attributes))
            .first()
        )

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

        # Meglévő rekordok lekérése egyetlen lekérdezéssel
        db_prefs_map = {
            db_pref.id: db_pref for db_pref in self.db.query(PreferenceModel).all()
        }

        fields = ["name", "description", "multiple", "emoji", "order"]
        for index, pref in enumerate(DEFAULT_PREFERENCES):
            pref.order = index

            if pref.id in db_prefs_map:
                db_pref = db_prefs_map[pref.id]

                if pydash.pick(db_pref, *fields) != pydash.pick(pref, *fields):
                    for field in fields:
                        setattr(db_pref, field, getattr(pref, field))
            else:
                new_pref = PreferenceModel(
                    id=pref.id,
                    **pydash.pick(pref, *fields),
                )
                self.db.add(new_pref)

        self.db.commit()
