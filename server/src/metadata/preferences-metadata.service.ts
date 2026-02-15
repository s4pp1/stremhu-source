import { Injectable } from '@nestjs/common';

import { AUDIO_QUALITY_OPTIONS } from 'src/preference-items/constant/audio-codec.constant';
import { LANGUAGE_OPTIONS } from 'src/preference-items/constant/language.constant';
import { RESOLUTION_OPTIONS } from 'src/preference-items/constant/resolution.constant';
import { SOURCE_OPTIONS } from 'src/preference-items/constant/source.constant';
import { VIDEO_QUALITY_OPTIONS } from 'src/preference-items/constant/video-quality.constant';
import { PREFERENCE_LABEL_MAP } from 'src/preferences/constant/preference.contant';
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

    return {
      value: PreferenceEnum.TRACKER,
      label: PREFERENCE_LABEL_MAP[PreferenceEnum.TRACKER],
      items: items,
    };
  }

  getLanguage(): LanguagePreferenceMetaDto {
    return {
      value: PreferenceEnum.LANGUAGE,
      label: PREFERENCE_LABEL_MAP[PreferenceEnum.LANGUAGE],
      items: LANGUAGE_OPTIONS,
    };
  }

  getResolution(): ResolutionPreferenceMetaDto {
    return {
      value: PreferenceEnum.RESOLUTION,
      label: PREFERENCE_LABEL_MAP[PreferenceEnum.RESOLUTION],
      items: RESOLUTION_OPTIONS,
    };
  }

  getVideoQuality(): VideoQualityPreferenceMetaDto {
    return {
      value: PreferenceEnum.VIDEO_QUALITY,
      label: PREFERENCE_LABEL_MAP[PreferenceEnum.VIDEO_QUALITY],
      items: VIDEO_QUALITY_OPTIONS,
    };
  }

  getSource(): SourcePreferenceMetaDto {
    return {
      value: PreferenceEnum.SOURCE,
      label: PREFERENCE_LABEL_MAP[PreferenceEnum.SOURCE],
      items: SOURCE_OPTIONS,
    };
  }

  getAudioQuality(): AudioQualityPreferenceMetaDto {
    return {
      value: PreferenceEnum.AUDIO_QUALITY,
      label: PREFERENCE_LABEL_MAP[PreferenceEnum.AUDIO_QUALITY],
      items: AUDIO_QUALITY_OPTIONS,
    };
  }
}
