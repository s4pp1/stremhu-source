import re

# Előfordított (pre-compiled) reguláris kifejezések az optimalizáció érdekében,
# mivel a StreamFileResolver cikluson belül hívja meg fájlonként.

PATTERN_STANDARD = re.compile(
    r"s(\d{1,2})[ ._-]?e(\d{1,4})(?:[ ._-]?(?:-|to)[ ._-]?(?:e)?(\d{1,4}))?\b"
)
PATTERN_MULTIPLIER = re.compile(
    r"\b(\d{1,2})x(\d{1,4})(?:[ ._-]?(?:-|to)[ ._-]?(?:x)?(\d{1,4}))?\b"
)
PATTERN_EXPLICIT = re.compile(
    r"\bseason[ ._-]?(\d{1,2})[ ._-]?(?:episode|ep)[ ._-]?(\d{1,4})(?:[ ._-]?(?:-|to)[ ._-]?(?:episode|ep)?[ ._-]?(\d{1,4}))?\b"
)
PATTERN_HUNGARIAN = re.compile(
    r"\b(\d{1,2})\.?\s*(?:évad|evad).*?(\d{1,4})\.?\s*(?:rész|resz)?(?:[ ._-]?(?:-|to)[ ._-]?(\d{1,4})\.?\s*(?:rész|resz)?)?"
)

PATTERN_MULTI_SEASON = re.compile(r"\b(?:s\d{1,2}[ ._+]+)+s\d{1,2}\b")
# New robust season pattern matching lists of seasons: "Season 1, 2, 3", "S01-S03", "1-3 évad"
PATTERN_SEASON_LIST = re.compile(
    r"\b(?:seasons?|s|évad|evad)[ ._-]?(\d{1,2}(?:\s*(?:-|to|,|&|and|\+)\s*(?:seasons?|s)?\s*\d{1,2})*)\b|"
    r"\b(\d{1,2}(?:\s*(?:-|to|,|&|and|\+)\s*\d{1,2})*)\.?\s*(?:évad|evad)\b",
    re.IGNORECASE,
)
PATTERN_FALLBACK_EPISODE = re.compile(
    r"\b(?:e|ep|episode[ ._-]?)(\d{1,4})(?:[ ._-]?(?:-|to)[ ._-]?(?:e|ep|episode)?[ ._-]?(\d{1,4}))?\b|\b(\d{1,4})\.?\s*(?:rész|resz)(?:[ ._-]?(?:-|to)[ ._-]?(\d{1,4})\.?\s*(?:rész|resz)?)?\b"
)

PATTERN_CLEAN_RESOLUTIONS = re.compile(
    r"\b\d{3,4}\s*[xX]\s*\d{3,4}\b|(1080|720|2160|480|576|540|20\d{2}|19\d{2})"
)
PATTERN_ALONE_EPISODE = re.compile(r"\b(\d{1,4})\b")


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


def _parse_season_list(s: str) -> list[int]:
    # Normalize spaces around hyphens and "to" to keep ranges intact as single tokens
    s_norm = re.sub(r"\s*(?:-|to)\s*", "-", s)
    # Split by separators: comma, &, and, +, spaces
    tokens = re.split(r"[ ,&+]+|\band\b", s_norm)
    seasons = []
    for token in tokens:
        token = token.strip().lower()
        if not token:
            continue
        # Strip optional "s" or "season" prefix in token (e.g. "s10" -> "10")
        token = re.sub(r"^(?:seasons?|s)", "", token)

        # Check if it is a range (e.g. "1-10")
        range_match = re.match(r"^(\d{1,2})-(\d{1,2})$", token)
        if range_match:
            seasons.extend(_expand_range(range_match.group(1), range_match.group(2)))
        else:
            # Single number
            num_match = re.match(r"^(\d{1,2})$", token)
            if num_match:
                seasons.append(int(num_match.group(1)))
    return sorted(list(set(seasons)))


def parse_season_episode(filename: str) -> tuple[list[int] | None, list[int] | None]:
    """
    Parses the season and episode numbers from a torrent filename.
    Returns a tuple of (seasons, episodes) where each is a list of integers, or None if not found.
    This replaces the PTN logic to provide better support for Hungarian patterns and range expansions.
    """
    filename_lower = filename.lower().replace("_", " ")

    # 1. Standard formátum: S01E01, S01.E01, S01_E01, S01E01-02, S01E01-E02
    match = PATTERN_STANDARD.search(filename_lower)
    if match:
        season = int(match.group(1))
        episodes = _expand_range(match.group(2), match.group(3))
        return [season], episodes

    # 2. Szorzó formátum: 1x01, 01x01, 1x01-02, 1x01-x02
    match = PATTERN_MULTIPLIER.search(filename_lower)
    if match:
        season = int(match.group(1))
        episodes = _expand_range(match.group(2), match.group(3))
        return [season], episodes

    # 3. Angol explicit: Season 1 Episode 1, Season 1 - Episode 1
    match = PATTERN_EXPLICIT.search(filename_lower)
    if match:
        season = int(match.group(1))
        episodes = _expand_range(match.group(2), match.group(3))
        return [season], episodes

    # 4. Magyar formátum: 1. évad 1. rész, 1.evad.1.resz, 1. évad 1-3. rész
    match = PATTERN_HUNGARIAN.search(filename_lower)
    if match:
        season = int(match.group(1))
        episodes = _expand_range(match.group(2), match.group(3))
        return [season], episodes

    seasons = None
    episodes = None

    # 5. Fallback teljes évadra (Season pack): S01, Season 1, 1. évad, S01-S07, 1-3. évad
    # Először ellenőrizzük a S01.S02.S03 (vagy S01 S02) formátumot
    multi_s_match = PATTERN_MULTI_SEASON.search(filename_lower)
    if multi_s_match:
        seasons = [int(s) for s in re.findall(r"s(\d{1,2})", multi_s_match.group(0))]
        filename_lower = PATTERN_MULTI_SEASON.sub(" ", filename_lower)
    else:
        s_matches = list(PATTERN_SEASON_LIST.finditer(filename_lower))
        if s_matches:
            seasons_set = set()
            for s_match in s_matches:
                val = s_match.group(1) or s_match.group(2)
                if val:
                    seasons_set.update(_parse_season_list(val))
            if seasons_set:
                seasons = sorted(list(seasons_set))
            filename_lower = PATTERN_SEASON_LIST.sub(" ", filename_lower)

    # 6. Fallback csak epizódra: E01, Ep 1, Episode 1, 1. rész, 001
    e_match = PATTERN_FALLBACK_EPISODE.search(filename_lower)
    if e_match:
        if e_match.group(1):
            episodes = _expand_range(e_match.group(1), e_match.group(2))
        elif e_match.group(3):
            episodes = _expand_range(e_match.group(3), e_match.group(4))
        filename_lower = PATTERN_FALLBACK_EPISODE.sub(" ", filename_lower)

    # Különálló 1-4 jegyű szám a fájlnév részben, ha nem sikerült máshogy epizódot találni
    if not episodes:
        # Csak a fájlnevet vizsgáljuk, az esetleges szülőmappák nélkül
        file_part = filename_lower.split("/")[-1]
        file_name_only = re.sub(r"\.[^.]+$", "", file_part)  # Kiterjesztés levágása

        cleaned_file_part = PATTERN_CLEAN_RESOLUTIONS.sub("", file_name_only)
        alone_ep = PATTERN_ALONE_EPISODE.search(cleaned_file_part)

        if alone_ep:
            ep_num = int(alone_ep.group(1))
            if ep_num < 2000:  # Csak reális epizódszámok
                episodes = [ep_num]

                # Ha 3 vagy 4 jegyű a szám (pl. 201, 1214), az sokszor SxxExx formátumot takar (S02E01, S12E14).
                if ep_num >= 100:
                    s_part = ep_num // 100
                    e_part = ep_num % 100
                    # Tegyük be a lehetséges epizódok közé a levágott értéket is
                    episodes.append(e_part)

                    # Ha nincs megadva évad, akkor is feltételezzük, hogy ez egy SxxExx formátum.
                    if seasons is None:
                        seasons = [s_part]
                    elif s_part not in seasons:
                        seasons.append(s_part)

    return seasons, episodes


def parse_seasons(filename: str) -> list[int] | None:
    """
    Parses only the season numbers from a torrent filename.
    """
    seasons, _ = parse_season_episode(filename)
    return seasons


def parse_episodes(filename: str) -> list[int] | None:
    """
    Parses only the episode numbers from a torrent filename.
    """
    _, episodes = parse_season_episode(filename)
    return episodes
