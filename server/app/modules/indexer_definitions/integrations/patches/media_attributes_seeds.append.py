from app.modules.preferences.seeds import (  # noqa: E402
    DISCOUNT_PREFERENCE_ID as _DISCOUNT_PREFERENCE_ID,
)

FREELEECH_ATTRIBUTE_ID = "freeleech"
HALFLEECH_ATTRIBUTE_ID = "halfleech"

DEFAULT_ATTRIBUTES.extend(
    [
        # ── Kedvezmény ──────────────────────────────────────────────────────
        MediaAttributeModel(
            id=FREELEECH_ATTRIBUTE_ID,
            name="FreeLeech",
            short_name="FL",
            description="A letöltés nem számít bele az arányba.",
            preference_id=_DISCOUNT_PREFERENCE_ID,
            pattern=r"\b(free[-_. ]?leech|freeleech)\b",
        ),
        MediaAttributeModel(
            id=HALFLEECH_ATTRIBUTE_ID,
            name="Half-leech",
            short_name="HL",
            description="A letöltésnek csak a fele számít bele az arányba.",
            preference_id=_DISCOUNT_PREFERENCE_ID,
            pattern=r"\b(half[-_. ]?leech|halfleech)\b",
        ),
        # ── Nyelvek ─────────────────────────────────────────────────────────
        MediaAttributeModel(
            id="fra",
            name="francia",
            short_name="Fre",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(french|truefrench|fran[çc]ais(?:e)?|vff|vfq|fre|fra)\b",
        ),
        MediaAttributeModel(
            id="ger",
            name="német",
            short_name="Ger",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(german|deutsch|ger|deu)\b",
        ),
        MediaAttributeModel(
            id="ita",
            name="olasz",
            short_name="Ita",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(italian|italiano|ita)\b",
        ),
        MediaAttributeModel(
            id="spa",
            name="spanyol",
            short_name="Spa",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(spanish|espa[nñ]ol|castellano|spa)\b",
        ),
        MediaAttributeModel(
            id="por",
            name="portugál",
            short_name="Por",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(portuguese|portugu[eê]s|brazilian|pt[-_. ]?br|por)\b",
        ),
        MediaAttributeModel(
            id="rus",
            name="orosz",
            short_name="Rus",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(russian|rus)\b",
        ),
        MediaAttributeModel(
            id="pol",
            name="lengyel",
            short_name="Pol",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(polish|polski|pol)\b",
        ),
        MediaAttributeModel(
            id="cze",
            name="cseh",
            short_name="Cze",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(czech|[cč]esk[yý]|cze|ces)\b",
        ),
        MediaAttributeModel(
            id="rom",
            name="román",
            short_name="Rom",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(romanian|rom[aâ]n[aă]|rou)\b",
        ),
        MediaAttributeModel(
            id="tur",
            name="török",
            short_name="Tur",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(turkish|t[uü]rk[cç]e|tur)\b",
        ),
        MediaAttributeModel(
            id="gre",
            name="görög",
            short_name="Gre",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(greek|ellinika|gre|ell)\b",
        ),
        MediaAttributeModel(
            id="nld",
            name="holland",
            short_name="Dut",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(dutch|nederlands|nld|dut)\b",
        ),
        MediaAttributeModel(
            id="swe",
            name="svéd",
            short_name="Swe",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(swedish|svenska|swe)\b",
        ),
        MediaAttributeModel(
            id="dan",
            name="dán",
            short_name="Dan",
            preference_id=PreferenceKey.LANGUAGE,
            # A bare "dan" szándékosan kimarad: gyakori név a release-ekben.
            pattern=r"\b(danish|dansk)\b",
        ),
        MediaAttributeModel(
            id="nor",
            name="norvég",
            short_name="Nor",
            preference_id=PreferenceKey.LANGUAGE,
            # A bare "nor" szándékosan kimarad: angol kötőszó.
            pattern=r"\b(norwegian|norsk)\b",
        ),
        MediaAttributeModel(
            id="jpn",
            name="japán",
            short_name="Jpn",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(japanese|jpn|jap)\b",
        ),
        MediaAttributeModel(
            id="kor",
            name="koreai",
            short_name="Kor",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(korean|kor)\b",
        ),
        MediaAttributeModel(
            id="zho",
            name="kínai",
            short_name="Chi",
            preference_id=PreferenceKey.LANGUAGE,
            pattern=r"\b(chinese|mandarin|cantonese|zho|chi|cmn)\b",
        ),
    ]
)
