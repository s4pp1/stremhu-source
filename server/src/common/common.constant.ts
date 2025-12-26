import { Resolution as ResolutionEnum } from '@ctrl/video-filename-parser';

import { VideoQualityEnum } from 'src/stremio/streams/enum/video-quality.enum';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import {
  LanguageOption,
  ResolutionOption,
  UserRoleOption,
  VideoQualityOption,
} from './common.types';
import { LanguageEnum } from './enum/language.enum';

export const GLOBAL_ID = 'global';

export const USER_ROLE_OPTIONS: UserRoleOption[] = [
  { value: UserRoleEnum.ADMIN, label: 'adminisztrátor' },
  { value: UserRoleEnum.USER, label: 'felhasználó' },
];

export const USER_ROLE_LABEL_MAP = USER_ROLE_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<UserRoleEnum, string>,
);

export const RESOLUTION_OPTIONS: ResolutionOption[] = [
  { value: ResolutionEnum.R2160P, label: 'UHD (4K)' },
  { value: ResolutionEnum.R1080P, label: 'Full HD (1080p)' },
  { value: ResolutionEnum.R720P, label: 'HD (720p)' },
  { value: ResolutionEnum.R576P, label: 'SD (576p)' },
  { value: ResolutionEnum.R540P, label: 'SD (540p)' },
  { value: ResolutionEnum.R480P, label: 'SD (480p)' },
];

export const ALL_RESOLUTION = RESOLUTION_OPTIONS.map(
  (resolution) => resolution.value,
);

export const RESOLUTION_LABEL_MAP = RESOLUTION_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<ResolutionEnum, string>,
);

export const VIDEO_QUALITY_OPTIONS: VideoQualityOption[] = [
  { value: VideoQualityEnum.DV, label: 'Dolby Vision' },
  { value: VideoQualityEnum.HDR10P, label: 'HDR10+' },
  { value: VideoQualityEnum.HDR10, label: 'HDR10' },
  { value: VideoQualityEnum.HLG, label: 'HLG' },
  { value: VideoQualityEnum.SDR, label: 'SDR' },
];

export const VIDEO_QUALITY_LABEL_MAP = VIDEO_QUALITY_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<VideoQualityEnum, string>,
);

export const LANGUAGE_OPTIONS: LanguageOption[] = [
  { label: 'magyar', value: LanguageEnum.HU },
  { label: 'angol', value: LanguageEnum.EN },
];

export const LANGUAGE_LABEL_MAP = LANGUAGE_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<LanguageEnum, string>,
);
