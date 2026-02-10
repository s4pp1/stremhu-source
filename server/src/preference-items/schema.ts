import { z } from 'zod';

import { PreferenceEnum } from 'src/preferences/enum/preference.enum';

import { AudioCodecEnum } from './enum/audio-codec.enum';
import { LanguageEnum } from './enum/language.enum';
import { ResolutionEnum } from './enum/resolution.enum';
import { SourceTypeEnum } from './enum/source-type.enum';
import { VideoQualityEnum } from './enum/video-quality.enum';

const base = z.object({
  order: z.number().int(),
});

export const preferenceItemSchema = z.discriminatedUnion('preference', [
  base.extend({
    preference: z.literal(PreferenceEnum.LANGUAGE),
    id: z.enum(LanguageEnum),
  }),
  base.extend({
    preference: z.literal(PreferenceEnum.RESOLUTION),
    id: z.enum(ResolutionEnum),
  }),
  base.extend({
    preference: z.literal(PreferenceEnum.VIDEO),
    id: z.enum(VideoQualityEnum),
  }),
  base.extend({
    preference: z.literal(PreferenceEnum.SOURCE),
    id: z.enum(SourceTypeEnum),
  }),
  base.extend({
    preference: z.literal(PreferenceEnum.AUDIO),
    id: z.enum(AudioCodecEnum),
  }),
]);
