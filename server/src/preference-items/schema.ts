import { z } from 'zod';

import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { AudioSpatialEnum } from './enum/audio-feature.enum';
import { AudioQualityEnum } from './enum/audio-quality.enum';
import { LanguageEnum } from './enum/language.enum';
import { ResolutionEnum } from './enum/resolution.enum';
import { SourceEnum } from './enum/source.enum';
import { VideoQualityEnum } from './enum/video-quality.enum';

const base = z.object({
  order: z.number().int(),
});

export const preferenceItemSchema = z.discriminatedUnion('preference', [
  base.extend({
    preference: z.literal(PreferenceEnum.TRACKER),
    id: z.enum(TrackerEnum),
  }),
  base.extend({
    preference: z.literal(PreferenceEnum.LANGUAGE),
    id: z.enum(LanguageEnum),
  }),
  base.extend({
    preference: z.literal(PreferenceEnum.RESOLUTION),
    id: z.enum(ResolutionEnum),
  }),
  base.extend({
    preference: z.literal(PreferenceEnum.VIDEO_QUALITY),
    id: z.enum(VideoQualityEnum),
  }),
  base.extend({
    preference: z.literal(PreferenceEnum.SOURCE),
    id: z.enum(SourceEnum),
  }),
  base.extend({
    preference: z.literal(PreferenceEnum.AUDIO_QUALITY),
    id: z.enum(AudioQualityEnum),
  }),
  base.extend({
    preference: z.literal(PreferenceEnum.AUDIO_SPATIAL),
    id: z.enum(AudioSpatialEnum),
  }),
]);
