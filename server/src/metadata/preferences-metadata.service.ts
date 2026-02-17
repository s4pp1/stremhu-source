import { Injectable } from '@nestjs/common';

import { AUDIO_QUALITY_OPTIONS } from 'src/preference-items/constant/audio-codec.constant';
import { LANGUAGE_OPTIONS } from 'src/preference-items/constant/language.constant';
import { RESOLUTION_OPTIONS } from 'src/preference-items/constant/resolution.constant';
import { SOURCE_OPTIONS } from 'src/preference-items/constant/source.constant';
import { VIDEO_QUALITY_OPTIONS } from 'src/preference-items/constant/video-quality.constant';
import { PREFERENCE_MAP } from 'src/preferences/constant/preference.contant';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { TrackersMetaService } from 'src/trackers/meta/trackers-meta.service';
import { TrackersService } from 'src/trackers/trackers.service';

import {
  AudioQualityPreferenceMetaDto,
  LanguagePreferenceMetaDto,
  PreferenceMetaDto,
  ResolutionPreferenceMetaDto,
  SourcePreferenceMetaDto,
  TrackerPreferenceMetaDto,
  VideoQualityPreferenceMetaDto,
} from './dto/preference-meta.dto';

@Injectable()
export class PreferencesMetadataService {
  constructor(
    private readonly trackersService: TrackersService,
    private readonly trackersMetaService: TrackersMetaService,
  ) {}

  async get(): Promise<PreferenceMetaDto[]> {
    const tracker = await this.getTracker();

    const preferences = [
      tracker,
      this.getLanguage(),
      this.getResolution(),
      this.getVideoQuality(),
      this.getSource(),
      this.getAudioQuality(),
    ];

    return preferences;
  }

  async getTracker(): Promise<TrackerPreferenceMetaDto> {
    const trackers = await this.trackersService.find();
    const items = trackers.map((tracker) =>
      this.trackersMetaService.resolve(tracker.tracker),
    );

    const preference = PREFERENCE_MAP[PreferenceEnum.TRACKER];

    return {
      value: PreferenceEnum.TRACKER,
      label: preference.label,
      description: preference.description,
      items: items,
    };
  }

  getLanguage(): LanguagePreferenceMetaDto {
    const preference = PREFERENCE_MAP[PreferenceEnum.LANGUAGE];

    return {
      value: PreferenceEnum.LANGUAGE,
      label: preference.label,
      description: preference.description,
      items: LANGUAGE_OPTIONS,
    };
  }

  getResolution(): ResolutionPreferenceMetaDto {
    const preference = PREFERENCE_MAP[PreferenceEnum.RESOLUTION];

    return {
      value: PreferenceEnum.RESOLUTION,
      label: preference.label,
      description: preference.description,
      items: RESOLUTION_OPTIONS,
    };
  }

  getVideoQuality(): VideoQualityPreferenceMetaDto {
    const preference = PREFERENCE_MAP[PreferenceEnum.VIDEO_QUALITY];

    return {
      value: PreferenceEnum.VIDEO_QUALITY,
      label: preference.label,
      description: preference.description,
      items: VIDEO_QUALITY_OPTIONS,
    };
  }

  getSource(): SourcePreferenceMetaDto {
    const preference = PREFERENCE_MAP[PreferenceEnum.SOURCE];

    return {
      value: PreferenceEnum.SOURCE,
      label: preference.label,
      description: preference.description,
      items: SOURCE_OPTIONS,
    };
  }

  getAudioQuality(): AudioQualityPreferenceMetaDto {
    const preference = PREFERENCE_MAP[PreferenceEnum.AUDIO_QUALITY];

    return {
      value: PreferenceEnum.AUDIO_QUALITY,
      label: preference.label,
      description: preference.description,
      items: AUDIO_QUALITY_OPTIONS,
    };
  }
}
