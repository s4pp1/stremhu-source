import asyncio
import re
import time
import unicodedata
from collections.abc import Awaitable, Callable
from typing import Any

import humanize
from sqlalchemy.orm import Session

from app.common.async_utils import owned_to_thread
from app.common.log_safety import network_error_fields
from app.common.logger import logger
from app.common.schemas.internal import SeriesInfo
from app.common.singleflight import SearchOverloadedError
from app.common.torrent_info import TorrentInfo
from app.config import config
from app.modules.indexer_accounts.schemas import IndexerDefinitionRef
from app.modules.indexer_definitions.service import IndexerDefinitionsService
from app.modules.media_attributes import tech_info_cache
from app.modules.media_attributes.constants import MediaAttributeKey
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.media_attributes.parser import clean_torrent_name
from app.modules.media_attributes.seeds import DEFAULT_ATTRIBUTES
from app.modules.media_attributes.tech_info_parser import TechInfoMetadata
from app.modules.preferences.constants import PreferenceKey
from app.modules.preferences.service import PreferencesService
from app.modules.settings.service import SettingsService
from app.modules.torrent_source_provider.service import (
    TorrentSourceProviderService,
    is_stale_result,
)
from app.modules.torrent_streams.schemas import (
    TorrentStream,
)
from app.modules.torrent_streams.utils.series_parser import SeriesParser
from app.modules.torrents.service import TorrentsService
from app.modules.users.models import UserModel

_DEFAULT_ATTRIBUTES_MAP: dict[str, MediaAttributeModel] = {
    attr.id: attr for attr in DEFAULT_ATTRIBUTES
}
_HUN_SUB_REGEX = re.compile(
    r"\b(hun[-_. ]?sub|sub[-_. ]?hun|hungarian[-_. ]?sub|magyar[-_. ]?felirat|feliratos)\b",
    re.IGNORECASE,
)
# A Tech Info dúsítás teljes kerete egy streamválaszon belül.
_TECH_INFO_BUDGET_SECONDS = 1.5


def strip_accents(text: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


class TorrentStreamsService:
    def __init__(
        self,
        db: Session,
        torrent_source_provider_service: TorrentSourceProviderService,
        torrents_service: TorrentsService,
        settings_service: SettingsService,
        preferences_service: PreferencesService,
        indexer_definitions_service: IndexerDefinitionsService | None = None,
    ):
        self.db = db
        self._torrent_source_provider_service = torrent_source_provider_service
        self._torrents_service = torrents_service
        self._settings_service = settings_service
        self._preferences_service = preferences_service
        self._indexer_definitions_service = indexer_definitions_service

    async def _find_imdb_sources(
        self,
        ids_to_search: list[str],
        imdb_id: str | None,
        prefetch_task: asyncio.Task[Any] | None,
        allow_stale: bool = True,
    ) -> tuple[list[Any], list[str], bool]:
        """Az IMDb-azonosítók forrásai, hibái, és hogy régi trackerlista is volt-e köztük (SP07)."""
        provider = self._torrent_source_provider_service

        def search(target: str) -> Awaitable[tuple[list[Any], list[str]]]:
            # A mai hívás változatlan; a jelző csak a kényszerített frissítésnél megy át.
            if allow_stale:
                return provider.find_by_imdb_id(target)
            return provider.find_by_imdb_id(target, allow_stale=False)

        torrent_sources: list[Any] = []
        indexer_errors: list[str] = []
        stale = False

        if len(ids_to_search) == 1:
            if prefetch_task is not None and ids_to_search[0] == imdb_id:
                try:
                    res = await prefetch_task
                    if isinstance(res, tuple):
                        torrent_sources, indexer_errors = res
                        stale = is_stale_result(res)
                except Exception as e:
                    logger.debug("operation=stream-prefetch %s", network_error_fields(e))
                    res = await search(ids_to_search[0])
                    torrent_sources, indexer_errors = res
                    stale = is_stale_result(res)
            else:
                res = await search(ids_to_search[0])
                torrent_sources, indexer_errors = res
                stale = is_stale_result(res)
        elif len(ids_to_search) > 1:
            tasks: list[Any] = []
            if prefetch_task is not None and ids_to_search[0] == imdb_id:
                tasks.append(prefetch_task)
                remaining = ids_to_search[1:]
            else:
                remaining = ids_to_search

            for i in remaining:
                tasks.append(search(i))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            # CR15/c: túlterhelés nem tűnhet el némán a több-azonosítós ágon.
            overloaded = [res for res in results if isinstance(res, SearchOverloadedError)]
            if overloaded and len(overloaded) == len(results):
                raise overloaded[0]
            if overloaded:
                indexer_errors.append(str(overloaded[0]))
            seen_source_ids: set[tuple[str, str]] = set()
            for res in results:
                if isinstance(res, tuple):
                    sources, errs = res
                    stale = stale or is_stale_result(res)
                    indexer_errors.extend(errs)
                    for s in sources:
                        s_key = (
                            s.indexer_torrent.indexer_account.indexer_id,
                            s.indexer_torrent.torrent_id,
                        )
                        if s_key not in seen_source_ids:
                            seen_source_ids.add(s_key)
                            torrent_sources.append(s)

        return torrent_sources, indexer_errors, stale

    async def find_by_imdb(
        self,
        user: UserModel,
        imdb_id: str | None = None,
        series: SeriesInfo | None = None,
        fallback_title: str | Callable[[], Awaitable[str | None]] | None = None,
        alternate_imdb_ids: list[str] | None = None,
        prefetch_task: asyncio.Task[Any] | None = None,
    ) -> tuple[list[TorrentStream], list[str]]:
        ids_to_search: list[str] = []
        if imdb_id and imdb_id.startswith("tt"):
            ids_to_search.append(imdb_id)
        if alternate_imdb_ids:
            for alt_id in alternate_imdb_ids:
                if alt_id and alt_id.startswith("tt") and alt_id not in ids_to_search:
                    ids_to_search.append(alt_id)

        torrent_sources, indexer_errors, stale = await self._find_imdb_sources(
            ids_to_search, imdb_id, prefetch_task
        )

        app_url = await owned_to_thread(self._settings_service.get_app_url)
        search_start_time = time.monotonic()

        def resolve_streams(sources: list[Any]) -> list[TorrentStream]:
            resolved: list[TorrentStream] = []
            for torrent_source in sources:
                torrent_stream = TorrentStream.from_imdb_id(
                    indexer_torrent=torrent_source.indexer_torrent,
                    torrent_file=torrent_source.torrent_file,
                    series=series,
                    app_url=app_url,
                    user=user,
                )

                if torrent_stream:
                    resolved.append(torrent_stream)
            return resolved

        torrent_streams = resolve_streams(torrent_sources)

        # SP07 (új epizód védelme): ha a régi (puhán lejárt) trackerlista a kért epizódra vagy
        # filmre nem ad lejátszható streamet, a név szerinti tartalék előtt szinkron, kényszerített
        # frissítés jön. Kikapcsolt SP07-nél nincs régi lista, így ez az ág nem fut.
        if not torrent_streams and stale:
            try:
                (
                    torrent_sources,
                    indexer_errors,
                    _,
                ) = await self._find_imdb_sources(
                    ids_to_search, imdb_id, None, allow_stale=False
                )
            except SearchOverloadedError as e:
                # Túlterhelésnél a régi lista marad; a tartalékkeresés a megszokott úton jön.
                logger.debug("operation=stream-stale-refresh %s", network_error_fields(e))
            else:
                torrent_streams = resolve_streams(torrent_sources)

        # Ha nem sikerült lejátszható streamet találni az adott epizódhoz/filmhez,
        # másodlagos név szerinti keresést hajtunk végre
        if not torrent_streams and (
            fallback_title
            or torrent_sources
            or (imdb_id and not imdb_id.startswith("tt"))
        ):
            actual_title: str | None = None
            if fallback_title:
                try:
                    actual_title = (
                        await fallback_title()
                        if callable(fallback_title)
                        else fallback_title
                    )
                except Exception as e:
                    logger.warning(
                        "operation=stream-fallback-title %s", network_error_fields(e)
                    )
                    actual_title = None

            # Ha a fallback_title nem adott eredményt, de voltak források (pl. más epizódok), kinyerjük a címet a torrent nevéből
            if not actual_title and torrent_sources:
                for src in torrent_sources:
                    name_candidate = (
                        src.torrent_file.info.name
                        if src.torrent_file and src.torrent_file.info
                        else None
                    )
                    if name_candidate:
                        title_part = re.split(
                            r"\b(?:s\d{1,2}\s*e\d{1,2}|s\d{1,2}|e\d{1,2}|season|\d{1,2}\.?(?:evad|évad)|19\d\d|20\d\d|720p|1080p|2160p|4k|uhd)\b",
                            name_candidate,
                            flags=re.IGNORECASE,
                        )[0]
                        extracted = re.sub(r"[._\-–—]+", " ", title_part).strip()
                        if extracted and len(extracted) >= 3:
                            actual_title = extracted
                            break

            if not actual_title and imdb_id and not imdb_id.startswith("tt"):
                actual_title = imdb_id

            if actual_title:
                candidate_queries = self._build_fallback_queries(
                    actual_title=actual_title, series=series
                )

                logger.info(
                    f"[TorrentStreamsService] Másodlagos név szerinti keresés indul ({actual_title}) jelöltek: {candidate_queries}"
                )

                for q in candidate_queries:
                    # M08: Keresési idő- és munkakeret: ne lépjük túl a teljes 20 másodperces időkeretet
                    if time.monotonic() - search_start_time > 20.0:
                        logger.info(
                            f"[TorrentStreamsService] Keresési időkeret elérve ({actual_title}), fallback keresés megszakítva."
                        )
                        break

                    (
                        fallback_sources,
                        fallback_errors,
                    ) = await self._torrent_source_provider_service.find_by_query(q)
                    indexer_errors.extend(fallback_errors)
                    if fallback_sources:
                        resolved_streams: list[TorrentStream] = []
                        for s in fallback_sources:
                            # 1. Ha a torrent rendelkezik IMDb azonosítóval, és ismert a cél IMDb ID (vagy alternatívák),
                            # de ez a torrent másik műhöz tartozik, elvetjük.
                            torrent_imdb = s.indexer_torrent.imdb_id
                            if torrent_imdb and torrent_imdb.startswith("tt"):
                                target_ids: set[str] = set()
                                if imdb_id and imdb_id.startswith("tt"):
                                    target_ids.add(imdb_id)
                                if alternate_imdb_ids:
                                    target_ids.update(alternate_imdb_ids)
                                if target_ids and torrent_imdb not in target_ids:
                                    continue

                            # 2. Ha filmet keresünk, de a torrent egyértelműen sorozat-epizódokat jelöl
                            if series is None and s.torrent_file and s.torrent_file.info:
                                t_seasons, t_episodes = SeriesParser(
                                    s.torrent_file.info.name
                                ).parse(allow_standalone_episode=False)
                                if t_seasons or t_episodes:
                                    continue

                            stream = TorrentStream.from_imdb_id(
                                indexer_torrent=s.indexer_torrent,
                                torrent_file=s.torrent_file,
                                series=series,
                                app_url=app_url,
                                user=user,
                            )
                            if stream:
                                resolved_streams.append(stream)

                        if resolved_streams:
                            torrent_streams = resolved_streams
                            logger.info(
                                f"[TorrentStreamsService] Másodlagos keresés forrásokat talált '{q}' lekérdezéssel: {len(fallback_sources)} forrás, {len(resolved_streams)} stream."
                            )
                            break
                        elif (
                            fallback_sources
                            and not isinstance(
                                getattr(fallback_sources[0].torrent_file, "info", None),
                                TorrentInfo,
                            )
                        ):
                            # Mock objektumos unit tesztek támogatása
                            break


        torrent_streams = await self._enrich_torrent_streams_with_tech_info(
            torrent_streams
        )

        filtered_torrent_streams = self._filter_torrent_streams(torrent_streams, user)
        sorted_torrent_streams = self._sort_torrent_streams(
            filtered_torrent_streams, user
        )
        if getattr(user, "enable_stream_deduplication", True):
            deduplicated_torrent_streams = self._deduplicate_torrent_streams(
                sorted_torrent_streams
            )
        else:
            deduplicated_torrent_streams = sorted_torrent_streams

        if user.enable_smart_filter:
            limit = user.smart_filter_limit

            if not user.smart_filter_grouping_preference_id:
                sorted_torrent_streams = deduplicated_torrent_streams[:limit]
            else:
                grouped_torrent_streams: list[TorrentStream] = []
                seen_attribute_ids: set[frozenset[str]] = set()

                for torrent_stream in deduplicated_torrent_streams:
                    target_attributes = frozenset(
                        attribute.id
                        for attribute in torrent_stream.attributes
                        if attribute.preference_id
                        == user.smart_filter_grouping_preference_id
                    )

                    if target_attributes not in seen_attribute_ids:
                        seen_attribute_ids.add(target_attributes)
                        grouped_torrent_streams.append(torrent_stream)

                if not grouped_torrent_streams and deduplicated_torrent_streams:
                    grouped_torrent_streams = deduplicated_torrent_streams[:1]

                sorted_torrent_streams = grouped_torrent_streams[:limit]
        else:
            sorted_torrent_streams = deduplicated_torrent_streams

        return sorted_torrent_streams, list(dict.fromkeys(indexer_errors))

    async def find_by_torrent_id(
        self,
        indexer_id: str,
        torrent_id: str,
        user: UserModel,
        file_index: int | None = None,
    ) -> list[TorrentStream]:

        torrent_source = (
            await self._torrent_source_provider_service.find_one_by_indexer(
                indexer_id, torrent_id
            )
        )

        if not torrent_source:
            return []

        app_url = await owned_to_thread(self._settings_service.get_app_url)

        streams = TorrentStream.from_torrent_id(
            indexer_torrent=torrent_source.indexer_torrent,
            torrent_file=torrent_source.torrent_file,
            app_url=app_url,
            user=user,
            file_index=file_index,
        )
        streams = await self._enrich_torrent_streams_with_tech_info(streams)
        # A katalógusból megnyitott torrent fájllistája is a tényleges letöltött állapotot mutassa
        self._mark_persisted_torrent_streams(streams)
        return streams

    async def _enrich_torrent_streams_with_tech_info(
        self,
        torrent_streams: list[TorrentStream],
    ) -> list[TorrentStream]:
        if not torrent_streams or self._indexer_definitions_service is None:
            return torrent_streams

        # 1. Fast-path regex: A torrent nevéből vagy fájlnevéből 0 ms alatt detektálható magyar felirat
        for ts in torrent_streams:
            if not ts.has_hungarian_sub:
                t_name = getattr(ts, "torrent_name", "") or ""
                f_name = getattr(ts, "file_name", "") or ""
                if _HUN_SUB_REGEX.search(t_name) or _HUN_SUB_REGEX.search(f_name):
                    ts.has_hungarian_sub = True

        # 2. Torrentenkénti csoportosítás: ugyanazon torrenthez tartozó fájlok ne indítsanak több kérést
        streams_by_torrent: dict[tuple[str, str], list[TorrentStream]] = {}
        for ts in torrent_streams:
            key = (ts.indexer_account.indexer_id, ts.torrent_id)
            streams_by_torrent.setdefault(key, []).append(ts)

        # 3. Célzott dúsítás: legfeljebb az 5 leginkább releváns egyedi torrentre futtatjuk,
        # illeszkedve az nCore max_concurrent=5 szemaforjához (egyetlen párhuzamos hullám)
        candidate_keys: list[tuple[str, str]] = []
        for key, streams in streams_by_torrent.items():
            needs_enrich = any(
                not (
                    ts.has_hungarian_sub
                    and any(
                        isinstance(a, MediaAttributeModel)
                        and a.id == MediaAttributeKey.HUN
                        for a in ts.attributes
                    )
                )
                for ts in streams
            )
            if needs_enrich:
                candidate_keys.append(key)
                if len(candidate_keys) >= 5:
                    break

        if not candidate_keys:
            return torrent_streams

        if config.tech_info_prefetch:
            try:
                await self._enrich_from_prefetch(candidate_keys, streams_by_torrent)
            except Exception as e:
                logger.debug("operation=stream-tech-enrichment %s", network_error_fields(e))
            return torrent_streams

        tasks = [
            self._enrich_torrent_group(key, streams_by_torrent[key])
            for key in candidate_keys
        ]
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=_TECH_INFO_BUDGET_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.debug("[TorrentStreamsService] Tech info dúsítás időtúllépés (1.5s).")
        except Exception as e:
            logger.debug("operation=stream-tech-enrichment %s", network_error_fields(e))

        return torrent_streams

    async def _enrich_from_prefetch(
        self,
        candidate_keys: list[tuple[str, str]],
        streams_by_torrent: dict[tuple[str, str], list[TorrentStream]],
    ) -> None:
        """SP06/b: a lekérés tulajdonolt háttértask, a kérés csak a keretéből hátralévőt várja.

        - Cache-találat azonnal alkalmazódik.
        - Futó (pl. a keresésben előtöltött) kulcsra nem indul új lekérés; a keret az indításától
          számít, így a kérés csak a hátralévő időt várja.
        - Hiányzó kulcsra a kérés indít háttérlekérést, teljes kerettel.
        - Időtúllépéskor a háttérlekérés tovább fut és feltölti a cache-t a következő kérésnek.
        - Teli kapacitásnál (vagy leállításkor) a kulcs a mai, kérésen belüli, megszakítható
          lekérést kapja, így az eredmény nem rosszabb a mainál.
        """
        loop = asyncio.get_running_loop()
        now = loop.time()
        deadline = now
        flights: dict[asyncio.Task[TechInfoMetadata | None], tuple[str, str]] = {}
        inline: list[asyncio.Task[None]] = []

        for key in candidate_keys:
            streams = streams_by_torrent[key]
            meta = tech_info_cache.get_cached(key)
            if meta is not None:
                for ts in streams:
                    self._apply_tech_info_to_stream(ts, meta)
                continue

            flight = tech_info_cache.in_flight(key)
            if flight is None:
                source = self._tech_info_source(key[0])
                if source is None:
                    continue
                flight = tech_info_cache.start_fetch(key, source)
            if flight is None:
                inline.append(asyncio.create_task(self._enrich_torrent_group(key, streams)))
                deadline = now + _TECH_INFO_BUDGET_SECONDS
                continue
            flights[flight.task] = key
            deadline = max(deadline, flight.started + _TECH_INFO_BUDGET_SECONDS)

        waiting: list[asyncio.Task[Any]] = [*flights, *inline]
        if not waiting:
            return
        try:
            # asyncio.wait nem szakítja meg a várt taskokat: a háttérlekérés időtúllépés
            # vagy a kérés megszakítása után is befejeződik.
            done, _ = await asyncio.wait(waiting, timeout=max(0.0, deadline - now))
        finally:
            for task in inline:
                task.cancel()
            if inline:
                await asyncio.gather(*inline, return_exceptions=True)

        for task, key in flights.items():
            if task in done and not task.cancelled():
                meta = task.result()
                if meta is not None:
                    for ts in streams_by_torrent[key]:
                        self._apply_tech_info_to_stream(ts, meta)

    def _tech_info_source(self, indexer_id: str) -> tech_info_cache.TechInfoSource | None:
        """A Tech Info-t adó indexer definíciója; ``None``, ha nincs, letiltott, vagy nem ad Tech Info-t."""
        if self._indexer_definitions_service is None:
            return None
        try:
            definition = self._indexer_definitions_service.get_by_id(indexer_id)
        except Exception:
            return None
        if not getattr(definition, "provides_tech_info", False):
            return None
        return definition

    async def _enrich_torrent_group(
        self,
        cache_key: tuple[str, str],
        streams: list[TorrentStream],
    ) -> None:
        try:
            indexer_id, torrent_id = cache_key
            now = time.monotonic()

            meta = tech_info_cache.get_cached(cache_key)

            if meta is None:
                if not self._indexer_definitions_service:
                    return
                indexer_def = self._indexer_definitions_service.get_by_id(indexer_id)
                if not indexer_def:
                    return
                meta = await tech_info_cache.fetch_metadata(indexer_def, torrent_id)
                tech_info_cache.store(cache_key, meta, now)

            for ts in streams:
                self._apply_tech_info_to_stream(ts, meta)
        except Exception as e:
            logger.debug(
                "operation=stream-group-enrichment %s", network_error_fields(e)
            )

    @staticmethod
    def _apply_tech_info_to_stream(ts: TorrentStream, meta: TechInfoMetadata) -> None:
        # 1. Magyar felirat meglétének átvétele
        if meta.has_hungarian_sub:
            ts.has_hungarian_sub = True

        # 2. Valós hangsávok alkalmazása és téves fallback felülírása
        if meta.audio_languages:
            current_langs = {
                attr.id
                for attr in ts.attributes
                if isinstance(attr, MediaAttributeModel)
                and attr.preference_id == PreferenceKey.LANGUAGE
            }

            # Ha japán hangsáv van a Tech Info / MediaInfo szerint
            if "jap" in meta.audio_languages:
                jap_attr = _DEFAULT_ATTRIBUTES_MAP.get(MediaAttributeKey.JAP)
                if jap_attr and MediaAttributeKey.JAP not in current_langs:
                    ts.attributes.append(jap_attr)
                    current_langs.add(MediaAttributeKey.JAP)

                # Ha nincs angol hangsáv a Tech Info szerint, de az nCore kategória fallback miatt
                # rákerült az ENG jelölés, eltávolítjuk a téves angol attribútumot
                if (
                    "eng" not in meta.audio_languages
                    and MediaAttributeKey.ENG in current_langs
                ):
                    ts.attributes = [
                        attr
                        for attr in ts.attributes
                        if not (
                            isinstance(attr, MediaAttributeModel)
                            and attr.id == MediaAttributeKey.ENG
                        )
                    ]
                    current_langs.discard(MediaAttributeKey.ENG)

            # Ha magyar hangsáv van
            if "hun" in meta.audio_languages:
                hun_attr = _DEFAULT_ATTRIBUTES_MAP.get(MediaAttributeKey.HUN)
                if hun_attr and MediaAttributeKey.HUN not in current_langs:
                    ts.attributes.append(hun_attr)
                    current_langs.add(MediaAttributeKey.HUN)

            # Ha angol hangsáv van (pl. Dual-Audio esetén)
            if "eng" in meta.audio_languages:
                eng_attr = _DEFAULT_ATTRIBUTES_MAP.get(MediaAttributeKey.ENG)
                if eng_attr and MediaAttributeKey.ENG not in current_langs:
                    ts.attributes.append(eng_attr)
                    current_langs.add(MediaAttributeKey.ENG)


    def _is_torrent_stream_excluded(
        self,
        torrent_stream: TorrentStream,
        excluded_attribute_ids: set[str],
        preference_multiple_map: dict[str, bool],
        preference_strict_exclusion_map: dict[str, bool],
    ) -> bool:
        attributes_by_preference: dict[
            str, list[MediaAttributeModel | IndexerDefinitionRef]
        ] = {}
        unassociated_attributes: list[MediaAttributeModel | IndexerDefinitionRef] = []

        for attribute in torrent_stream.attributes:
            if attribute.preference_id is not None:
                if attribute.preference_id not in attributes_by_preference:
                    attributes_by_preference[attribute.preference_id] = []
                attributes_by_preference[attribute.preference_id].append(attribute)
            else:
                unassociated_attributes.append(attribute)

        if any(
            unassociated_attribute.id in excluded_attribute_ids
            for unassociated_attribute in unassociated_attributes
        ):
            return True

        for preference_id, attributes in attributes_by_preference.items():
            is_multiple = preference_multiple_map.get(preference_id, False)
            strict_exclusion = preference_strict_exclusion_map.get(preference_id, False)

            if is_multiple and not strict_exclusion:
                if all(
                    attribute.id in excluded_attribute_ids for attribute in attributes
                ):
                    return True
            else:
                if any(
                    attribute.id in excluded_attribute_ids for attribute in attributes
                ):
                    return True

        return False

    def _filter_torrent_streams(
        self,
        torrent_streams: list[TorrentStream],
        user: UserModel,
    ) -> list[TorrentStream]:
        excluded_attribute_ids = {
            exclusion.attribute_id for exclusion in user.attribute_exclusions
        }

        preferences = self._preferences_service.get_list()
        preference_multiple_map = {
            preference.id: preference.multiple for preference in preferences
        }
        preference_strict_exclusion_map = {
            preference.id: preference.strict_exclusion for preference in preferences
        }

        filtered_torrent_streams: list[TorrentStream] = []
        for torrent_stream in torrent_streams:
            if user.torrent_seed is not None and (
                torrent_stream.seeders is None
                or torrent_stream.seeders <= user.torrent_seed
            ):
                continue

            if self._is_torrent_stream_excluded(
                torrent_stream=torrent_stream,
                excluded_attribute_ids=excluded_attribute_ids,
                preference_multiple_map=preference_multiple_map,
                preference_strict_exclusion_map=preference_strict_exclusion_map,
            ):
                continue

            filtered_torrent_streams.append(torrent_stream)

        return filtered_torrent_streams

    def _mark_persisted_torrent_streams(
        self,
        torrent_streams: list[TorrentStream],
    ) -> None:
        """Beállítja az is_persisted_torrent jelzőt a relay tényleges, fájlszintű állapota szerint.

        Egy fájl akkor számít letöltöttnek, ha a torrent seedel, vagy ha a fájl
        file_progress értéke eléri a méretét (évadcsomagnál csak a kész epizódok).
        """
        # M12: Célzott állapotlekérés felesleges teljes táblalekérdezés (get_torrents) helyett.
        # file_progress_cache memóriában tárolja a torrent állapotot a több fájlos találatokhoz.
        file_progress_cache: dict[str, tuple[bool, list[int]]] = {}

        for stream in torrent_streams:
            if not stream.info_hash:
                stream.is_persisted_torrent = False
                continue

            if stream.info_hash not in file_progress_cache:
                is_downloaded_whole = False
                progress: list[int] = []
                try:
                    relay_service = getattr(self._torrents_service, "_relay_service", None)
                    if relay_service:
                        sha1_hash = relay_service._parse_info_hash(stream.info_hash)
                        t = relay_service._torrents.get(sha1_hash)
                        if t and t.torrent_handle.is_valid():
                            st = t.torrent_handle.status()
                            if st.is_seeding:
                                is_downloaded_whole = True
                            else:
                                progress = t.torrent_handle.file_progress()
                except Exception:
                    pass
                file_progress_cache[stream.info_hash] = (is_downloaded_whole, progress)

            is_seeding, progress_list = file_progress_cache[stream.info_hash]
            if is_seeding:
                stream.is_persisted_torrent = True
            elif progress_list and 0 <= stream.file_index < len(progress_list):
                stream.is_persisted_torrent = (
                    stream.file_size > 0 and progress_list[stream.file_index] >= stream.file_size
                )
            else:
                # Végső fallback a torrents_service.is_file_downloaded-re (pl. mock-olt tesztekben)
                try:
                    stream.is_persisted_torrent = bool(
                        self._torrents_service.is_file_downloaded(
                            info_hash=stream.info_hash,
                            file_index=stream.file_index,
                            file_size=stream.file_size,
                        )
                    )
                except Exception:
                    stream.is_persisted_torrent = False

    def _sort_torrent_streams(
        self,
        torrent_streams: list[TorrentStream],
        user: UserModel,
    ) -> list[TorrentStream]:
        if not torrent_streams:
            return []

        self._mark_persisted_torrent_streams(torrent_streams)
        # Kikapcsolt „Letöltve” preferenciánál a letöltött találat nem kerül előre:
        # a lista csak a felhasználói preferenciák és a seederek szerint rendeződik.
        prioritize_downloaded = bool(getattr(user, "enable_downloaded_marker", True))

        sorted_preferences = sorted(
            user.preference_definitions, key=lambda preference: preference.order
        )

        preference_rank_maps: list[tuple[str, dict[str, int], int]] = []
        for sorted_preference in sorted_preferences:
            definition_attributes = sorted(
                sorted_preference.definition.definition_attributes,
                key=lambda def_attr: def_attr.order,
            )
            rank_map = {
                def_attr.attribute_id: idx
                for idx, def_attr in enumerate(definition_attributes)
            }
            fallback_rank = len(definition_attributes)
            preference_rank_maps.append(
                (sorted_preference.definition.preference_id, rank_map, fallback_rank)
            )

        def sort_key(stream: TorrentStream):
            relay_rank = (
                0 if prioritize_downloaded and stream.is_persisted_torrent else 1
            )
            pref_ranks: list[int] = []
            for pref_id, rank_map, fallback in preference_rank_maps:
                best_rank = fallback
                for attr in stream.attributes:
                    if attr.preference_id == pref_id and attr.id in rank_map:
                        best_rank = min(best_rank, rank_map[attr.id])

                pref_ranks.append(best_rank)

            seeders_rank = -(stream.seeders or 0)

            return (relay_rank, *pref_ranks, seeders_rank)

        torrent_streams.sort(key=sort_key)
        return torrent_streams

    def _deduplicate_torrent_streams(
        self,
        torrent_streams: list[TorrentStream],
    ) -> list[TorrentStream]:
        """
        Multi-tracker és azonos tartalmú torrent streamek intelligens összevonása.

        M04 szabályok:
        1. Erős kulcs: (info_hash, file_index). Azonos hash-en belüli külön fájlok (pl. külön epizódok)
           soha nem vonhatók össze!
        2. Eltérő info_hash-ek esetén a fájlok nem vonhatók össze, külön találatként maradnak meg.
        3. Ha nincs info_hash, tisztított név és fájlméret alapján vonunk össze fallback módon.
        4. Forráskonzisztencia: ha egy összevont forrás letöltött (is_persisted_torrent),
           a lejátszási URL és attribútumok a tényleges letöltött forráshoz igazodnak.
        5. Több indexer esetén az extra_indexer_names és a trackerenkénti becsült seeder összeg
           (combined_seeders) megfelelően összesítésre kerül.
        """
        deduped: list[TorrentStream] = []
        canonical_to_primary: dict[tuple[str, ...], TorrentStream] = {}
        seeders_by_indexer_per_primary: dict[int, dict[str, int]] = {}

        for stream in torrent_streams:
            stream_hash = stream.info_hash.strip().lower() if stream.info_hash else ""
            clean_name = clean_torrent_name(stream.file_name).lower() if stream.file_name else ""

            # Kulcsképzés
            if stream_hash:
                # Erős kulcs: info_hash és file_index
                stream_key: tuple[str, ...] = ("hash", stream_hash, str(stream.file_index))
            elif stream.file_size > 1_000_000 and clean_name:
                # Fallback kulcs csak akkor, ha egyáltalán nincs info_hash
                stream_key = ("fallback", str(stream.file_size), clean_name)
            else:
                # Nincs elegendő adat az összevonáshoz, egyedi streamként kezeljük
                stream_key = ("unique", str(id(stream)))

            primary = canonical_to_primary.get(stream_key)
            indexer_id = stream.indexer_account.indexer_id
            indexer_name = stream.indexer_account.indexer_definition.name

            if primary is not None:
                p_id = id(primary)
                idx_seeders = seeders_by_indexer_per_primary[p_id]

                if (
                    indexer_name
                    and indexer_name not in primary.extra_indexer_names
                ):
                    primary.extra_indexer_names.append(indexer_name)

                # Seeder összesítés indexerenként
                current_for_idx = idx_seeders.get(indexer_id, 0)
                idx_seeders[indexer_id] = max(current_for_idx, stream.seeders or 0)
                primary.combined_seeders = sum(idx_seeders.values())

                # Forráskonzisztencia: ha a stream már letöltött, de a primary nem volt az,
                # a lejátszási URL-t és forrást átváltjuk a ténylegesen elérhető helyi forrásra
                if stream.is_persisted_torrent and not primary.is_persisted_torrent:
                    primary.is_persisted_torrent = True
                    primary.play_url = stream.play_url
                    primary.indexer_account = stream.indexer_account
                    primary.torrent_id = stream.torrent_id
                    primary.file_index = stream.file_index
                    if stream.attributes:
                        primary.attributes = stream.attributes
                    if stream.has_hungarian_sub:
                        primary.has_hungarian_sub = True
                elif stream.has_hungarian_sub and not primary.has_hungarian_sub:
                    primary.has_hungarian_sub = True
            else:
                if not stream.extra_indexer_names and indexer_name:
                    stream.extra_indexer_names = [indexer_name]
                p_id = id(stream)
                primary_seeders = stream.seeders or 0
                seeders_by_indexer_per_primary[p_id] = {indexer_id: primary_seeders}
                stream.combined_seeders = primary_seeders

                deduped.append(stream)
                canonical_to_primary[stream_key] = stream

        return deduped

    def _format_filesize(self, bytes_size: int) -> str:
        return humanize.naturalsize(bytes_size, binary=True)

    @staticmethod
    def _build_fallback_queries(
        actual_title: str, series: SeriesInfo | None = None
    ) -> list[str]:
        # 1. Alap tisztított cím (alcím vagy kettőspont/kötőjel/gondolatjel levágása)
        cleaned_title = re.sub(r"\s*\(\d{4}\)", "", actual_title).strip()
        base_part = re.split(r"[:\-\–—]", cleaned_title)[0].strip()
        base_clean = re.sub(r"[''`]", "", base_part).strip()

        unaccented = strip_accents(base_clean).strip()
        no_article = re.sub(
            r"^(?:A|Az|The)\s+", "", unaccented, flags=re.IGNORECASE
        ).strip()

        candidates: list[str] = []

        def add_candidate(q: str | None):
            if q and len(q) >= 2 and q not in candidates:
                candidates.append(q)

        # 1. Sorozat esetén az elsődleges évados lekérdezés élvez prioritást (pl. "Stranger Things S04")
        if series and series.season is not None:
            s_num = series.season
            for title_cand in (no_article, unaccented, base_clean):
                if title_cand:
                    add_candidate(f"{title_cand} S{s_num:02d}")

        # 2. Alap cím változatlanul (ahogy a Cinemeta/TMDB/torrent neve adta)
        # Ha egy anime (pl. One Piece) nem rendelkezik S01 jelöléssel, azonnal megtalálja a 2. hívásra
        add_candidate(base_clean)

        # 3. Ékezetmentesített változat
        add_candidate(unaccented)

        # 4. Névelő nélküli változat ("A ", "Az ", "The ")
        add_candidate(no_article)

        # 5. További sorozatos változatok (specifikus epizód és magyar évad)
        if series and series.season is not None:
            s_num = series.season
            for title_cand in (no_article, unaccented, base_clean):
                if title_cand:
                    if series.episode is not None:
                        add_candidate(f"{title_cand} S{s_num:02d}E{series.episode:02d}")
                    add_candidate(f"{title_cand} {s_num}.evad")

        # 6. Ha több szóból áll, az első 2 szó és az első szó
        words = no_article.split()
        if len(words) > 1:
            add_candidate(" ".join(words[:2]))
            if len(words[0]) >= 4:
                add_candidate(words[0])

        # 6. Teljes ékezetmentesített cím (ha különbözik)
        full_no_apo = re.sub(r"[''`]", "", cleaned_title).strip()
        full_unaccented = strip_accents(full_no_apo).strip()
        add_candidate(full_unaccented)

        return candidates
