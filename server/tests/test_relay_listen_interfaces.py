import pytest

from app.config import config


@pytest.mark.parametrize(
    ("interface", "expected"),
    [
        (None, "0.0.0.0:6881,[::]:6881"),
        ("", "0.0.0.0:6881,[::]:6881"),
        ("tun0", "tun0:6881"),
    ],
)
def test_listen_interfaces(
    monkeypatch: pytest.MonkeyPatch, interface: str | None, expected: str
) -> None:
    monkeypatch.setattr(config, "libtorrent_interface", interface)

    assert config.libtorrent_listen_interfaces(6881) == expected
