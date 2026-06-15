from typing import cast

import pydash
import sqlalchemy as sa
from sqlalchemy.orm import Session, contains_eager, with_polymorphic

from app.common.logger import logger
from app.modules.attribute_exclusions.models import AttributeExclusionModel
from app.modules.attributes.models import AttributeModel
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.preferences.models import PreferenceModel
from app.modules.preferences.seeds import DEFAULT_PREFERENCES


class PreferencesRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_list(self, user_id: str | None = None) -> list[PreferenceModel]:
        attr_poly = cast(type[AttributeModel], with_polymorphic(AttributeModel, "*"))

        join_conditions = [
            PreferenceModel.id == attr_poly.preference_id,
            sa.or_(
                attr_poly.type != "indexer_definition",
                attr_poly.id.in_(sa.select(IndexerAccountModel.indexer_id)),
            ),
            sa.or_(
                attr_poly.type != "media",
                MediaAttributeModel.is_preferable.is_(True),
            ),
        ]

        if user_id:
            user_exclusions = sa.select(AttributeExclusionModel.attribute_id).where(
                AttributeExclusionModel.user_id == user_id
            )
            join_conditions.append(attr_poly.id.notin_(user_exclusions))

        stmt = (
            sa.select(PreferenceModel)
            .join(attr_poly, sa.and_(*join_conditions))
            .options(contains_eager(PreferenceModel.attributes.of_type(attr_poly)))
            .order_by(
                PreferenceModel.order.asc(),
                attr_poly.order.asc(),
            )
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def find_by_id(
        self,
        id: str,
        user_id: str | None = None,
    ) -> PreferenceModel | None:
        attr_poly = cast(type[AttributeModel], with_polymorphic(AttributeModel, "*"))

        join_conditions = [
            PreferenceModel.id == attr_poly.preference_id,
            sa.or_(
                attr_poly.type != "indexer_definition",
                attr_poly.id.in_(sa.select(IndexerAccountModel.indexer_id)),
            ),
            sa.or_(
                attr_poly.type != "media",
                MediaAttributeModel.is_preferable.is_(True),
            ),
        ]

        if user_id:
            user_exclusions = sa.select(AttributeExclusionModel.attribute_id).where(
                AttributeExclusionModel.user_id == user_id
            )
            join_conditions.append(attr_poly.id.notin_(user_exclusions))

        stmt = (
            sa.select(PreferenceModel)
            .join(attr_poly, sa.and_(*join_conditions))
            .filter(PreferenceModel.id == id)
            .options(contains_eager(PreferenceModel.attributes.of_type(attr_poly)))
            .order_by(attr_poly.order.asc())
        )
        return self.db.execute(stmt).unique().scalars().first()

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
