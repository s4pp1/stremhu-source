"""Központi modellregiszter.

Importálja az összes SQLAlchemy modellt, hogy a Base.metadata tartalmazza az összes táblát és
kapcsolatot (relationships) az Alembic migrációk és a PyInstaller csomagolás során is.
"""

# ruff: noqa: F401
import server.modules.attribute_exclusions.models
import server.modules.attributes.models
import server.modules.indexer_accounts.models
import server.modules.indexer_definitions.models
import server.modules.media_attributes.models
import server.modules.pairings.models
import server.modules.playback_histories.models
import server.modules.preference_definitions.models
import server.modules.preferences.models
import server.modules.roles.models
import server.modules.settings.models
import server.modules.system_preference_definitions.models
import server.modules.torrent_files.models
import server.modules.torrents.models
import server.modules.user_preference_definitions.models
import server.modules.users.models
