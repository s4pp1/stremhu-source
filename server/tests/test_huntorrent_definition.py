"""HunTorrent: the browse search must ask for server-rendered results (server_search=1).

Without that parameter the site serves only an empty skeleton and loads the results in the
browser, so the parser sees no rows and every search silently returns nothing.
"""

import httpx
import pytest

from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.integrations.huntorrent import (
    HunTorrentIndexerDefinition,
)
from app.modules.media_attributes.constants import MediaAttributeKey

IMDB_ID = "tt0133093"

SHELL = """<html><body><div data-browse-workspace>
<div class="browse-skeleton-card"></div><div class="browse-skeleton-card"></div>
</div></body></html>"""


def table_row(torrent_id: int, seeders: int, imdb_id: str = IMDB_ID) -> str:
    return f"""<tr class="torrent-row" data-torrent-id="{torrent_id}" data-seeders="{seeders}">
<td class="torrent-category"><img alt="HD/Magyar"></td>
<td><a href="https://www.imdb.com/title/{imdb_id}/">IMDb</a></td>
<td class="torrent-meta"><a href="/download/{torrent_id}/fixturepass">Letöltés</a></td>
</tr>"""


def table_page(rows: list[str], next_page: int | None) -> str:
    pager = f'<a class="ht-pager-btn" href="/browse/?page={next_page}">Következő</a>' if next_page else ""
    return f"<html><body><table>{''.join(rows)}</table>{pager}</body></html>"


def poster_page() -> str:
    return f"""<html><body>
<div class="poster-item" id="poster-501">
<div class="poster-category"><span>sorozat/hd/külföldi</span></div>
<a href="https://www.imdb.com/title/{IMDB_ID}/">IMDb</a>
<div class="poster-stat"><span class="poster-stat-label">Seed</span><span class="poster-stat-value"><a>17</a></span></div>
<div class="poster-actions"><a href="/download/501/fixturepass">Letöltés</a></div>
</div></body></html>"""


def adapter_with(handler) -> tuple[HunTorrentIndexerDefinition, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    adapter = HunTorrentIndexerDefinition()
    adapter._client = IndexerClient(
        adapter, base_url=adapter.url, transport=httpx.MockTransport(record), follow_redirects=True
    )
    return adapter, seen


def html(body: str) -> httpx.Response:
    return httpx.Response(200, text=body, headers={"content-type": "text/html; charset=UTF-8"})


@pytest.mark.anyio
async def test_search_requests_server_rendered_results_across_pages():
    def site(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("server_search") != "1":
            return html(SHELL)
        if request.url.params.get("page") == "2":
            return html(table_page([table_row(103, 0)], None))
        return html(table_page([table_row(101, 12), table_row(102, 5, "tt9999999")], 2))

    adapter, seen = adapter_with(site)
    try:
        torrents = await adapter.find_torrents_by_imdb_id(IMDB_ID)
    finally:
        await adapter.close()

    assert [r.url.params.get("server_search") for r in seen] == ["1", "1"]
    assert [r.url.params.get("search") for r in seen] == [IMDB_ID, IMDB_ID]
    # Other titles on the page are filtered out by IMDb id; both pages are read.
    assert [(t.torrent_id, t.seeders) for t in torrents] == [("101", 12), ("103", 0)]
    first = torrents[0]
    assert first.download_url == "https://huntorrent.org/download/101/fixturepass"
    assert first.attribute_ids == [MediaAttributeKey.HUN, MediaAttributeKey.R720P]


@pytest.mark.anyio
async def test_text_search_uses_the_same_server_rendered_poster_view():
    adapter, seen = adapter_with(
        lambda request: html(poster_page() if request.url.params.get("server_search") == "1" else SHELL)
    )
    try:
        torrents = await adapter.find_torrents_by_query("matrix")
    finally:
        await adapter.close()

    assert [r.url.params.get("server_search") for r in seen] == ["1"]
    assert [(t.torrent_id, t.seeders, t.imdb_id) for t in torrents] == [("501", 17, IMDB_ID)]
    assert torrents[0].attribute_ids == [MediaAttributeKey.ENG, MediaAttributeKey.R720P]
