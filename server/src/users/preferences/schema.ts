import { z } from 'zod';

import { AudioSpatialEnum } from 'src/preference-items/enum/audio-feature.enum';
import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';
import { SourceEnum } from 'src/preference-items/enum/source.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

const base = z.object({
  userId: z.string(),
  preferred: z.array(z.string()),
  blocked: z.array(z.string()),
  order: z.number().nullable(),
});

export const userPreferenceSchema = z
  .discriminatedUnion('preference', [
    base.extend({
      preference: z.literal(PreferenceEnum.TRACKER),
      preferred: z.array(z.enum(TrackerEnum)),
      blocked: z.array(z.enum(TrackerEnum)),
    }),
    base.extend({
      preference: z.literal(PreferenceEnum.LANGUAGE),
      preferred: z.array(z.enum(LanguageEnum)),
      blocked: z.array(z.enum(LanguageEnum)),
    }),
    base.extend({
      preference: z.literal(PreferenceEnum.RESOLUTION),
      preferred: z.array(z.enum(ResolutionEnum)),
      blocked: z.array(z.enum(ResolutionEnum)),
    }),
    base.extend({
      preference: z.literal(PreferenceEnum.VIDEO_QUALITY),
      preferred: z.array(z.enum(VideoQualityEnum)),
      blocked: z.array(z.enum(VideoQualityEnum)),
    }),
    base.extend({
      preference: z.literal(PreferenceEnum.SOURCE),
      preferred: z.array(z.enum(SourceEnum)),
      blocked: z.array(z.enum(SourceEnum)),
    }),
    base.extend({
      preference: z.literal(PreferenceEnum.AUDIO_QUALITY),
      preferred: z.array(z.enum(AudioQualityEnum)),
      blocked: z.array(z.enum(AudioQualityEnum)),
    }),
    base.extend({
      preference: z.literal(PreferenceEnum.AUDIO_SPATIAL),
      preferred: z.array(z.enum(AudioSpatialEnum)),
      blocked: z.array(z.enum(AudioSpatialEnum)),
    }),
  ])
  .superRefine((value, ctx) => {
    const preferredValues = value.preferred as string[];
    const blockedValues = value.blocked as string[];
    const preferredSet = new Set(preferredValues);
    const overlap = blockedValues.filter((item) => preferredSet.has(item));

    const duplicatePreferred = preferredValues.filter(
      (item, index) => preferredValues.indexOf(item) !== index,
    );
    if (duplicatePreferred.length) {
      const sharedValues = [...new Set(duplicatePreferred)].join(', ');
      ctx.addIssue({
        code: 'custom',
        path: ['preferred'],
        message: `A preferred listában nem lehet duplikáció: ${sharedValues}.`,
      });
    }

    const duplicateBlocked = blockedValues.filter(
      (item, index) => blockedValues.indexOf(item) !== index,
    );
    if (duplicateBlocked.length) {
      const sharedValues = [...new Set(duplicateBlocked)].join(', ');
      ctx.addIssue({
        code: 'custom',
        path: ['blocked'],
        message: `A blocked listában nem lehet duplikáció: ${sharedValues}.`,
      });
    }

    if (overlap.length) {
      const sharedValues = [...new Set(overlap)].join(', ');
      ctx.addIssue({
        code: 'custom',
        path: ['blocked'],
        message: `A preferred és blocked listák nem tartalmazhatják ugyanazt az értéket: ${sharedValues}.`,
      });
    }
  });
