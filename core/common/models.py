"""Központi modellregiszter.

Importálja az összes SQLAlchemy modellt, hogy a Base.metadata tartalmazza az összes táblát és
kapcsolatot (relationships) az Alembic migrációk és a PyInstaller csomagolás során is.
"""

# ruff: noqa: F401
import core.modules.attribute_exclusions.models
import core.modules.attributes.models
import core.modules.indexer_accounts.models
import core.modules.indexer_definitions.models
import core.modules.media_attributes.models
import core.modules.pairings.models
import core.modules.playback_histories.models
import core.modules.preference_definitions.models
import core.modules.preferences.models
import core.modules.roles.models
import core.modules.settings.models
import core.modules.system_preference_definitions.models
import core.modules.torrent_files.models
import core.modules.torrents.models
import core.modules.user_preference_definitions.models
import core.modules.users.models
