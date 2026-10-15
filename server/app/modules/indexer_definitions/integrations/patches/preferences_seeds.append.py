DISCOUNT_PREFERENCE_ID = "discount"

DEFAULT_PREFERENCES.append(
    PreferenceModel(
        id=DISCOUNT_PREFERENCE_ID,
        name="Kedvezmény",
        description="A torrent letöltési kedvezménye a trackeren (FreeLeech, Half-leech).",
        emoji="🎁",
    )
)
