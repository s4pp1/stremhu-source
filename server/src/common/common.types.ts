import { Resolution as ResolutionEnum } from '@ctrl/video-filename-parser';

import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { LanguageEnum } from './enum/language.enum';

export interface UserRoleOption {
  value: UserRoleEnum;
  label: string;
}

export interface ResolutionOption {
  value: ResolutionEnum;
  label: string;
}

export interface LanguageOption {
  value: LanguageEnum;
  label: string;
}
