import { AudioSpatialEnum } from 'src/preference-items/enum/audio-feature.enum';
import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';
import { SourceEnum } from 'src/preference-items/enum/source.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';

import { parseAudioQuality } from './util/parse-audio-quality.util';
import { parseAudioSpatial } from './util/parse-audio-spatial.util';
import { parseResolution } from './util/parse-resolution.util';
import { parseSource } from './util/parse-source.util';
import { parseVideoQuality } from './util/parse-video-quality.util';

export type TorrentMetadataParserType = {
  name: string;
  languageFallback: LanguageEnum;
  resolutionFallback: ResolutionEnum;
};

export class TorrentMetadataParser {
  private readonly normalizeName: string;
  private readonly languageFallback: LanguageEnum;
  private readonly resolutionFallback: ResolutionEnum;

  constructor(private readonly payload: TorrentMetadataParserType) {
    const { name, languageFallback, resolutionFallback } = this.payload;

    this.normalizeName = name.toLocaleLowerCase();
    this.languageFallback = languageFallback;
    this.resolutionFallback = resolutionFallback;
  }

  parseLanguage(): LanguageEnum {
    return this.languageFallback;
  }

  parseResolution(): ResolutionEnum {
    return parseResolution(this.normalizeName, this.resolutionFallback);
  }

  parseVideoQuality(): VideoQualityEnum[] {
    return parseVideoQuality(this.normalizeName);
  }

  parseSource(): SourceEnum {
    return parseSource(this.normalizeName);
  }

  parseAudioQuality(): AudioQualityEnum {
    return parseAudioQuality(this.normalizeName);
  }

  parseAudioSpatial(): AudioSpatialEnum | null {
    return parseAudioSpatial(this.normalizeName);
  }

  parse() {
    return {
      [PreferenceEnum.LANGUAGE]: this.parseLanguage(),
      [PreferenceEnum.RESOLUTION]: this.parseResolution(),
      [PreferenceEnum.VIDEO_QUALITY]: this.parseVideoQuality(),
      [PreferenceEnum.SOURCE]: this.parseSource(),
      [PreferenceEnum.AUDIO_QUALITY]: this.parseAudioQuality(),
      [PreferenceEnum.AUDIO_SPATIAL]: this.parseAudioSpatial(),
    };
  }
}
