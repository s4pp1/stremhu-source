from modules.attributes.enums import (
    AudioQualityEnum,
    AudioSpatialEnum,
    LanguageEnum,
    ResolutionEnum,
    SourceEnum,
    VideoQualityEnum,
)
from modules.attributes.models import AttributeModel
from modules.preferences.enums import PreferenceEnum

# TODO: Pattern hozzáadása, ami majd a regex-et tárolja

DEFAULT_ATTRIBUTES = [
    # Resolutions
    AttributeModel(
        id=ResolutionEnum.R2160P.value,
        name="UHD (4K)",
        preference_id=PreferenceEnum.RESOLUTION,
    ),
    AttributeModel(
        id=ResolutionEnum.R1080P.value,
        name="Full HD (1080p)",
        preference_id=PreferenceEnum.RESOLUTION,
    ),
    AttributeModel(
        id=ResolutionEnum.R720P.value,
        name="HD (720p)",
        preference_id=PreferenceEnum.RESOLUTION,
    ),
    AttributeModel(
        id=ResolutionEnum.R576P.value,
        name="SD (576p)",
        preference_id=PreferenceEnum.RESOLUTION,
    ),
    AttributeModel(
        id=ResolutionEnum.R540P.value,
        name="SD (540p)",
        preference_id=PreferenceEnum.RESOLUTION,
    ),
    AttributeModel(
        id=ResolutionEnum.R480P.value,
        name="SD (480p)",
        preference_id=PreferenceEnum.RESOLUTION,
    ),
    # Languages
    AttributeModel(
        id=LanguageEnum.HU.value,
        name="magyar",
        preference_id=PreferenceEnum.LANGUAGE,
    ),
    AttributeModel(
        id=LanguageEnum.EN.value,
        name="angol",
        preference_id=PreferenceEnum.LANGUAGE,
    ),
    # Video Qualities
    AttributeModel(
        id=VideoQualityEnum.DV.value,
        name="Dolby Vision",
        preference_id=PreferenceEnum.VIDEO_QUALITY,
    ),
    AttributeModel(
        id=VideoQualityEnum.HDR10P.value,
        name="HDR10+",
        preference_id=PreferenceEnum.VIDEO_QUALITY,
    ),
    AttributeModel(
        id=VideoQualityEnum.HDR10.value,
        name="HDR10",
        preference_id=PreferenceEnum.VIDEO_QUALITY,
    ),
    AttributeModel(
        id=VideoQualityEnum.HLG.value,
        name="HLG",
        preference_id=PreferenceEnum.VIDEO_QUALITY,
    ),
    AttributeModel(
        id=VideoQualityEnum.SDR.value,
        name="SDR",
        preference_id=PreferenceEnum.VIDEO_QUALITY,
    ),
    # Sources
    AttributeModel(
        id=SourceEnum.DISC_REMUX.value,
        name="Lemez (Remux - eredeti minőség)",
        preference_id=PreferenceEnum.SOURCE,
    ),
    AttributeModel(
        id=SourceEnum.DISC_RIP.value,
        name="Lemez (Rip / újrakódolt)",
        preference_id=PreferenceEnum.SOURCE,
    ),
    AttributeModel(
        id=SourceEnum.WEB_DL.value,
        name="Streaming (WEB-DL - eredeti)",
        preference_id=PreferenceEnum.SOURCE,
    ),
    AttributeModel(
        id=SourceEnum.WEB_RIP.value,
        name="Streaming (WEBRip - újrakódolt)",
        preference_id=PreferenceEnum.SOURCE,
    ),
    AttributeModel(
        id=SourceEnum.BROADCAST.value,
        name="TV (HDTV / közvetített)",
        preference_id=PreferenceEnum.SOURCE,
    ),
    AttributeModel(
        id=SourceEnum.THEATRICAL.value,
        name="Mozis felvétel (CAM/TS/TC)",
        preference_id=PreferenceEnum.SOURCE,
    ),
    AttributeModel(
        id=SourceEnum.UNKNOWN.value,
        name="Egyéb",
        preference_id=PreferenceEnum.SOURCE,
    ),
    # Audio Qualities
    AttributeModel(
        id=AudioQualityEnum.TRUEHD.value,
        name="Dolby TrueHD",
        preference_id=PreferenceEnum.AUDIO_QUALITY,
    ),
    AttributeModel(
        id=AudioQualityEnum.DTS_HD_MA.value,
        name="DTS-HD Master Audio",
        preference_id=PreferenceEnum.AUDIO_QUALITY,
    ),
    AttributeModel(
        id=AudioQualityEnum.DD_PLUS.value,
        name="Dolby Digital Plus",
        preference_id=PreferenceEnum.AUDIO_QUALITY,
    ),
    AttributeModel(
        id=AudioQualityEnum.DTS.value,
        name="DTS Core",
        preference_id=PreferenceEnum.AUDIO_QUALITY,
    ),
    AttributeModel(
        id=AudioQualityEnum.DD.value,
        name="Dolby Digital",
        preference_id=PreferenceEnum.AUDIO_QUALITY,
    ),
    AttributeModel(
        id=AudioQualityEnum.AAC.value,
        name="AAC",
        preference_id=PreferenceEnum.AUDIO_QUALITY,
    ),
    AttributeModel(
        id=AudioQualityEnum.UNKNOWN.value,
        name="Egyéb",
        preference_id=PreferenceEnum.AUDIO_QUALITY,
    ),
    # Audio Spatials
    AttributeModel(
        id=AudioSpatialEnum.DTS_X.value,
        name="DTS:X",
        preference_id=PreferenceEnum.AUDIO_SPATIAL,
    ),
    AttributeModel(
        id=AudioSpatialEnum.DOLBY_ATMOS.value,
        name="Dolby Atmos",
        preference_id=PreferenceEnum.AUDIO_SPATIAL,
    ),
    # Others
    AttributeModel(
        id="3d",
        name="3D",
        preference_id=None,
    ),
]
