import re

from app.modules.media_attributes.parser import clean_torrent_name


class SeriesParser:
    # 1. FILE-LEVEL PATTERNS (Looking for exact SxxExx or Episodes)
    PATTERN_STANDARD = re.compile(
        r"s(\d{1,2})[ ._-]?e(\d{1,4})(?:(?:[ ._-]?-?[ ._-]?e)(\d{1,4}))?\b",
        re.IGNORECASE,
    )
    PATTERN_X_FORMAT = re.compile(
        r"\b(\d{1,2})x(\d{1,4})(?:-x?(\d{1,4}))?\b",
        re.IGNORECASE,
    )
    PATTERN_EXPLICIT = re.compile(
        r"\bseason[ ._-]?(\d{1,2})[ ._-]?(?:episode|ep)[ ._-]?(\d{1,4})(?:-(?:episode|ep)?[ ._-]?(\d{1,4}))?\b",
        re.IGNORECASE,
    )
    PATTERN_HUNGARIAN = re.compile(
        r"\b(\d{1,2})\.?\s*(?:évad|evad).*?(\d{1,4})\.?\s*(?:rész|resz)?(?:[ ._-]?(?:-|to)[ ._-]?(\d{1,4})\.?\s*(?:rész|resz)?)?",
        re.IGNORECASE,
    )
    PATTERN_FALLBACK_EPISODE = re.compile(
        r"\b(?:e|ep|episode[ ._-]?)(\d{1,4})(?:(?:[ ._-]?-?[ ._-]?e)(\d{1,4}))?\b|\b(\d{1,4})\.?\s*(?:rész|resz)(?:[ ._-]?-[ ._-]?(\d{1,4})\.?\s*(?:rész|resz)?)?\b",
        re.IGNORECASE,
    )

    # Cleaners for standalone episode extraction
    PATTERN_CLEAN_RESOLUTIONS = re.compile(
        r"\b\d{3,4}\s*[xX]\s*\d{3,4}\b|(1080|720|2160|480|576|540|20\d{2}|19\d{2})",
        re.IGNORECASE,
    )
    PATTERN_ALONE_EPISODE = re.compile(r"\b(\d{1,4})\b")

    # 2. FOLDER-LEVEL PATTERNS (Looking only for Seasons)
    PATTERN_MULTI_SEASON = re.compile(
        r"\b(?:s\d{1,2}[ ._+]+)+s\d{1,2}\b", re.IGNORECASE
    )
    PATTERN_SEASON_LIST = re.compile(
        r"\b(?:seasons?|s|évad|evad)[ ._-]?(\d{1,2}(?:\s*(?:-|to|,|&|and|\+)\s*(?:seasons?|s)?\s*\d{1,2})*)\b|"
        r"\b(\d{1,2}(?:\s*(?:-|to|,|&|and|\+)\s*\d{1,2})*)\.?\s*(?:évad|evad)\b",
        re.IGNORECASE,
    )

    def __init__(self, name: str):
        self.name_lower = clean_torrent_name(name).lower().replace("_", " ")

    @staticmethod
    def _expand_range(start: str, end: str | None) -> list[int]:
        start_int = int(start)
        if not end:
            return [start_int]
        end_int = int(end)
        if end_int < start_int:
            return [start_int]
        if end_int - start_int > 100:
            end_int = start_int + 100
        return list(range(start_int, end_int + 1))

    @staticmethod
    def _parse_season_list(s: str) -> list[int]:
        s_norm = re.sub(r"\s*(?:-|to)\s*", "-", s)
        tokens = re.split(r"[ ,&+]+|\band\b", s_norm)
        seasons = []
        for token in tokens:
            token = token.strip().lower()
            if not token:
                continue
            token = re.sub(r"(?:seasons?|s)", "", token)
            range_match = re.match(r"^(\d{1,2})-(\d{1,2})$", token)
            if range_match:
                seasons.extend(
                    SeriesParser._expand_range(
                        range_match.group(1), range_match.group(2)
                    )
                )
            else:
                num_match = re.match(r"^(\d{1,2})$", token)
                if num_match:
                    seasons.append(int(num_match.group(1)))
        return sorted(list(set(seasons)))

    def parse(
        self, context_seasons: list[int] | None = None
    ) -> tuple[list[int], list[int]]:
        """
        Univerzális parser mappákhoz és fájlokhoz.
        Megpróbálja feloldani az évadokat és az epizódokat.
        """
        # 1. Exact matches (S01E01)
        s, e = self._match_exact_sxx_exx()
        if s or e:
            return s, e

        # 2. Évadok keresése (pl. "Season 1", "S01-S03")
        s, _ = self._extract_seasons(self.name_lower)

        # 3. Kifejezett epizódok keresése (pl. "E01", "Episode 5")
        e, cleaned = self._extract_episodes(self.name_lower)

        # Ha bármelyik konkrét (évad vagy epizód) megvan, visszatérünk
        if s or e:
            return s, e

        # 4. Standalone fallback (tisztán számok, pl. "05")
        return self._extract_standalone_episode(cleaned, context_seasons)

    def _match_exact_sxx_exx(self) -> tuple[list[int], list[int]]:
        patterns = [
            self.PATTERN_STANDARD,
            self.PATTERN_X_FORMAT,
            self.PATTERN_EXPLICIT,
            self.PATTERN_HUNGARIAN,
        ]
        for pattern in patterns:
            match = pattern.search(self.name_lower)
            if match:
                season = int(match.group(1))
                episodes = self._expand_range(match.group(2), match.group(3))
                return [season], episodes
        return [], []

    def _extract_seasons(self, text: str) -> tuple[list[int], str]:
        seasons: list[int] = []
        multi_s_match = self.PATTERN_MULTI_SEASON.search(text)

        if multi_s_match:
            seasons = [
                int(s) for s in re.findall(r"s(\d{1,2})", multi_s_match.group(0))
            ]
            text = self.PATTERN_MULTI_SEASON.sub(" ", text)
        else:
            s_matches = list(self.PATTERN_SEASON_LIST.finditer(text))
            if s_matches:
                seasons_set = set()
                for s_match in s_matches:
                    val = s_match.group(1) or s_match.group(2)
                    if val:
                        seasons_set.update(self._parse_season_list(val))
                if seasons_set:
                    seasons = sorted(list(seasons_set))
                text = self.PATTERN_SEASON_LIST.sub(" ", text)

        return seasons, text

    def _extract_episodes(self, text: str) -> tuple[list[int], str]:
        episodes: list[int] = []
        e_match = self.PATTERN_FALLBACK_EPISODE.search(text)

        if e_match:
            if e_match.group(1):
                episodes = self._expand_range(e_match.group(1), e_match.group(2))
            elif e_match.group(3):
                episodes = self._expand_range(e_match.group(3), e_match.group(4))
            text = self.PATTERN_FALLBACK_EPISODE.sub(" ", text)

        return episodes, text

    def _extract_standalone_episode(
        self, text: str, current_seasons: list[int] | None
    ) -> tuple[list[int], list[int]]:
        episodes: list[int] = []
        seasons = list(current_seasons) if current_seasons is not None else []

        file_part = text.split("/")[-1]
        file_name_only = re.sub(r"\.[^.]+$", "", file_part)

        cleaned_file_part = self.PATTERN_CLEAN_RESOLUTIONS.sub("", file_name_only)
        alone_eps = self.PATTERN_ALONE_EPISODE.findall(cleaned_file_part)

        if alone_eps:
            # Heurisztika a legvalószínűbb epizód kiválasztására:
            # 1. Ha van 0-val kezdődő (pl. "01", "05"), az a legbiztosabb.
            # 2. Egyébként a legutolsó magányos szám (mert a címben lévő számok előrébb vannak).
            best_ep = alone_eps[-1]
            for ep_str in reversed(alone_eps):
                if ep_str.startswith("0") and len(ep_str) >= 2:
                    best_ep = ep_str
                    break

            ep_num = int(best_ep)
            if ep_num < 2000:
                episodes = [ep_num]

                if ep_num >= 100:
                    s_part = ep_num // 100
                    e_part = ep_num % 100
                    episodes = [e_part]

                    if s_part not in seasons:
                        seasons.append(s_part)

        return seasons, episodes
