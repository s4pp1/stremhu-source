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
    PATTERN_ANIME_DASH_EPISODE = re.compile(
        r"[-–—]\s*(?:ep|episode|rész|resz)?\s*(\d{1,4})(?:v\d+)?(?:[ ._-]?(?:-|to)[ ._-]?(\d{1,4}))?\b",
        re.IGNORECASE,
    )
    PATTERN_NUMERIC_RANGE = re.compile(
        r"\b(\d{1,4})\s*[-–—]\s*(\d{1,4})\b",
        re.IGNORECASE,
    )

    PATTERN_R_FORMAT = re.compile(
        r"\br([1-9])[ ._-]*(?:e|ep|episode|[-–—]|\s)\s*(\d{1,4})(?:-(?:e|ep|episode)?[ ._-]?(\d{1,4}))?\b",
        re.IGNORECASE,
    )
    PATTERN_ORDINAL_SEASON_EPISODE = re.compile(
        r"\b(\d{1,2})(?:st|nd|rd|th)[ ._-]+seasons?[ ._-]*(?:e|ep|episode|[-–—]|\s)\s*(\d{1,4})(?:-(?:e|ep|episode)?[ ._-]?(\d{1,4}))?\b",
        re.IGNORECASE,
    )
    PATTERN_SPECIAL_EPISODE = re.compile(
        r"\b(?:oad|ova|sp|special)[ ._-]?(\d{1,4})(?:(?:[ ._-]?-?[ ._-]?(?:oad|ova|sp|special))?(\d{1,4}))?\b",
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
        r"\b(?:seasons?|s|r|round|évad|evad)[ ._-]?(\d{1,2}(?:\s*(?:-|to|,|&|and|\+)\s*(?:seasons?|s|r)?\s*\d{1,2})*)(?:[ ._-]?p\d+)?\b|"
        r"\b(\d{1,2}(?:\s*(?:-|to|,|&|and|\+)\s*\d{1,2})*)\.?\s*(?:évad|evad)\b|"
        r"\b(\d{1,2})(?:st|nd|rd|th)[ ._-]+seasons?\b",
        re.IGNORECASE,
    )
    PATTERN_NORM_TO = re.compile(r"\s*(?:-|to)\s*", re.IGNORECASE)
    PATTERN_SEASON_SPLIT = re.compile(r"[ ,&+]+|\band\b", re.IGNORECASE)
    PATTERN_STRIP_SEASON = re.compile(r"(?:seasons?|s|r|round)", re.IGNORECASE)
    PATTERN_STRIP_ORDINAL = re.compile(r"(?:st|nd|rd|th)", re.IGNORECASE)
    PATTERN_STRIP_PART = re.compile(r"p\d+", re.IGNORECASE)
    PATTERN_SEASON_TOKEN_RANGE = re.compile(r"^(\d{1,2})-(\d{1,2})$")
    PATTERN_SEASON_TOKEN_NUM = re.compile(r"^(\d{1,2})$")
    PATTERN_LEAD_DIGIT = re.compile(r"^([1-9])\s+[A-Za-z]")
    PATTERN_FILE_EXT = re.compile(r"\.[^.]+$")
    GENERIC_SEASON_WORDS = (
        (re.compile(r"\b(?:the\s+final\s+season|final\s+season)\b", re.IGNORECASE), 4),
    )

    def __init__(self, name: str):
        self.raw_name = name
        self.name_lower = clean_torrent_name(name).lower()

    @staticmethod
    def _expand_range(start: str, end: str | None) -> list[int]:
        start_int = int(start)
        if not end:
            return [start_int]
        end_int = int(end)
        if end_int < start_int:
            return [start_int]
        if end_int - start_int > 250:
            end_int = start_int + 250
        return list(range(start_int, end_int + 1))

    @classmethod
    def _parse_season_list(cls, s: str) -> list[int]:
        s_norm = cls.PATTERN_NORM_TO.sub("-", s)
        tokens = cls.PATTERN_SEASON_SPLIT.split(s_norm)
        seasons = []
        for token in tokens:
            token = token.strip().lower()
            if not token:
                continue
            token = cls.PATTERN_STRIP_SEASON.sub("", token)
            token = cls.PATTERN_STRIP_ORDINAL.sub("", token)
            token = cls.PATTERN_STRIP_PART.sub("", token)
            range_match = cls.PATTERN_SEASON_TOKEN_RANGE.match(token)
            if range_match:
                seasons.extend(
                    cls._expand_range(
                        range_match.group(1), range_match.group(2)
                    )
                )
            else:
                num_match = cls.PATTERN_SEASON_TOKEN_NUM.match(token)
                if num_match:
                    seasons.append(int(num_match.group(1)))
        return sorted(list(set(seasons)))

    def parse(
        self,
        context_seasons: list[int] | None = None,
        allow_standalone_episode: bool = True,
    ) -> tuple[list[int], list[int]]:
        """
        Univerzális parser mappákhoz és fájlokhoz.
        Megpróbálja feloldani az évadokat és az epizódokat.
        """
        # 1. Exact matches (S01E01)
        s, e = self._match_exact_sxx_exx()
        if s and e:
            return s, e

        # 2. Évadok keresése (pl. "Season 1", "S01-S03", Anime Arc címek)
        seasons, cleaned = self._extract_seasons(self.name_lower)
        if not seasons and s:
            seasons = s

        # 3. Kifejezett epizódok keresése (pl. "E01", "Episode 5", " - 01 ")
        episodes, cleaned = self._extract_episodes(cleaned)
        if not episodes and e:
            episodes = e

        # Ha mindkettő megvan, visszatérünk
        if seasons and episodes:
            return seasons, episodes

        if not allow_standalone_episode:
            return seasons, episodes

        # 4. Standalone fallback (tisztán számok, pl. "05", "105")
        if not episodes:
            standalone_seasons, standalone_episodes = self._extract_standalone_episode(
                cleaned, current_seasons=seasons if seasons else context_seasons
            )
            if not seasons:
                seasons = standalone_seasons
            episodes = standalone_episodes

        return seasons, episodes

    def _match_exact_sxx_exx(self) -> tuple[list[int], list[int]]:
        patterns = [
            self.PATTERN_STANDARD,
            self.PATTERN_X_FORMAT,
            self.PATTERN_EXPLICIT,
            self.PATTERN_HUNGARIAN,
            self.PATTERN_R_FORMAT,
            self.PATTERN_ORDINAL_SEASON_EPISODE,
        ]
        for pattern in patterns:
            match = pattern.search(self.name_lower)
            if match:
                season = int(match.group(1))
                episodes = self._expand_range(match.group(2), match.group(3))
                return [season], episodes

        spec_match = self.PATTERN_SPECIAL_EPISODE.search(self.name_lower)
        if spec_match:
            episodes = self._expand_range(spec_match.group(1), spec_match.group(2))
            return [0], episodes

        return [], []

    def _extract_seasons(self, text: str) -> tuple[list[int], str]:
        seasons: list[int] = []

        for arc_pat, arc_s in self.GENERIC_SEASON_WORDS:
            if arc_pat.search(text):
                seasons = [arc_s]
                text = arc_pat.sub(" ", text)
                break

        if not seasons:
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
                        val = next((g for g in s_match.groups() if g is not None), None)
                        if val:
                            seasons_set.update(self._parse_season_list(val))
                    if seasons_set:
                        seasons = sorted(list(seasons_set))
                    text = self.PATTERN_SEASON_LIST.sub(" ", text)

        if not seasons:
            lead_digit = self.PATTERN_LEAD_DIGIT.match(text.strip())
            if lead_digit:
                seasons = [int(lead_digit.group(1))]

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

        if not episodes:
            range_match = self.PATTERN_NUMERIC_RANGE.search(text)
            if range_match:
                start_n, end_n = int(range_match.group(1)), int(range_match.group(2))
                if 0 < end_n - start_n <= 250 and not (1900 <= start_n <= 2050 and end_n <= 31):
                    episodes = self._expand_range(str(start_n), str(end_n))
                    text = self.PATTERN_NUMERIC_RANGE.sub(" ", text)

        if not episodes:
            raw_lower = getattr(self, "raw_name", "").lower()
            dash_match = self.PATTERN_ANIME_DASH_EPISODE.search(text) or (
                self.PATTERN_ANIME_DASH_EPISODE.search(raw_lower) if raw_lower else None
            )
            if dash_match:
                episodes = self._expand_range(dash_match.group(1), dash_match.group(2))
                text = self.PATTERN_ANIME_DASH_EPISODE.sub(" ", text)

        return episodes, text

    def _extract_standalone_episode(
        self, text: str, current_seasons: list[int] | None
    ) -> tuple[list[int], list[int]]:
        episodes: list[int] = []
        seasons = list(current_seasons) if current_seasons is not None else []

        file_part = text.split("/")[-1]
        file_name_only = self.PATTERN_FILE_EXT.sub("", file_part)

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

                # Ha a szám 3 jegyű (pl. 105), és az évad már ismert (pl. 1. évad),
                # felvesszük a relatív epizódszámot is alternatívaként ([105, 5])
                if ep_num >= 100:
                    s_guess = ep_num // 100
                    e_guess = ep_num % 100
                    if seasons and s_guess in seasons:
                        if e_guess not in episodes:
                            episodes.append(e_guess)

        return seasons, episodes
