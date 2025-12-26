import { Resolution as ResolutionEnum } from '@ctrl/video-filename-parser';

import { VideoQualityEnum } from 'src/stremio/streams/enum/video-quality.enum';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { LanguageEnum } from './enum/language.enum';

export type UserRoleOption = {
  value: UserRoleEnum;
  label: string;
};

export type ResolutionOption = {
  value: ResolutionEnum;
  label: string;
};

export type VideoQualityOption = {
  value: VideoQualityEnum;
  label: string;
};

export type LanguageOption = {
  value: LanguageEnum;
  label: string;
};
