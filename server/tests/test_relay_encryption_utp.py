import libtorrent
import pytest

from app.modules.relay.schemas import RelaySettingsUpdate
from app.modules.relay.service import RelayService, encryption_settings
from app.modules.settings.enums import RelayEncryptionEnum


def _apply(update: RelaySettingsUpdate) -> dict[str, object]:
    """Valódi libtorrent session-re alkalmazza a beállításokat, és visszaadja az érvényes értékeket."""
    session = libtorrent.session({"enable_dht": False, "enable_lsd": False})
    service = RelayService.__new__(RelayService)
    service._libtorrent_session = session
    service._torrent_connections_limit = 20
    service.update_settings(update)
    return dict(session.get_settings())


@pytest.mark.parametrize(
    ("mode", "policy", "level", "prefer_rc4"),
    [
        (
            RelayEncryptionEnum.ENABLED,
            libtorrent.enc_policy.enabled,
            libtorrent.enc_level.both,
            False,
        ),
        (
            RelayEncryptionEnum.FORCED,
            libtorrent.enc_policy.forced,
            libtorrent.enc_level.rc4,
            True,
        ),
        (
            RelayEncryptionEnum.DISABLED,
            libtorrent.enc_policy.disabled,
            libtorrent.enc_level.both,
            False,
        ),
    ],
)
def test_encryption_mode_applied_to_session(mode, policy, level, prefer_rc4):
    settings = _apply(RelaySettingsUpdate(encryption=mode))

    assert settings["out_enc_policy"] == int(policy)
    assert settings["in_enc_policy"] == int(policy)
    assert settings["allowed_enc_level"] == int(level)
    assert settings["prefer_rc4"] is prefer_rc4


def test_enabled_encryption_matches_libtorrent_defaults():
    defaults = dict(libtorrent.session({"enable_dht": False}).get_settings())

    for key, value in encryption_settings(RelayEncryptionEnum.ENABLED).items():
        assert defaults[key] == value


@pytest.mark.parametrize("enable_utp", [True, False])
def test_utp_toggle_applied_to_session(enable_utp):
    settings = _apply(RelaySettingsUpdate(enable_utp=enable_utp))

    assert settings["enable_outgoing_utp"] is enable_utp
    assert settings["enable_incoming_utp"] is enable_utp


def test_unset_fields_leave_session_untouched():
    settings = _apply(RelaySettingsUpdate())

    assert settings["out_enc_policy"] == int(libtorrent.enc_policy.enabled)
    assert settings["enable_outgoing_utp"] is True
