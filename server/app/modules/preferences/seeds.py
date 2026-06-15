from app.modules.preferences.constants import PreferenceKey
from app.modules.preferences.models import PreferenceModel

DEFAULT_PREFERENCES = [
    PreferenceModel(
        id=PreferenceKey.SITE,
        name="Torrent oldal",
        description="Az oldal, ahonnan a torrenteket keressük.",
    ),
    PreferenceModel(
        id=PreferenceKey.LANGUAGE,
        name="Nyelv",
        description="A tartalom nyelve hang alapján.",
        multiple=True,
        emoji="🌐",
    ),
    PreferenceModel(
        id=PreferenceKey.RESOLUTION,
        name="Felbontás",
        description="A videó képmérete, felbontása.",
        emoji="📺",
    ),
    PreferenceModel(
        id=PreferenceKey.VIDEO_QUALITY,
        name="Képminőség",
        description="A videó képi minőségi formátuma.",
        multiple=True,
        emoji="✨",
    ),
    PreferenceModel(
        id=PreferenceKey.EDITION,
        name="Kiadás",
        description="A film speciális kiadása / változata.",
        multiple=True,
        emoji="🏷️",
    ),
    PreferenceModel(
        id=PreferenceKey.SOURCE,
        name="Forrás",
        description="A kiadás forrástípusa / eredete.",
        multiple=True,
        emoji="💿",
    ),
    PreferenceModel(
        id=PreferenceKey.VIDEO_CODEC,
        name="Videókódoló",
        description="A videó kódolási eljárása (Codec).",
        emoji="🎞️",
    ),
    PreferenceModel(
        id=PreferenceKey.AUDIO_QUALITY,
        name="Hangminőség",
        description="A hangsáv formátuma / minősége",
        multiple=True,
        emoji="🔊",
    ),
    PreferenceModel(
        id=PreferenceKey.AUDIO_CHANNELS,
        name="Hangcsatornák",
        description="A hangsáv csatornáinak száma (pl. 2.0, 5.1).",
        emoji="📻",
    ),
    PreferenceModel(
        id=PreferenceKey.AUDIO_SPATIAL,
        name="Térhangzás",
        description="Objektumalapú surround hangzás",
        emoji="🌌",
    ),
]
