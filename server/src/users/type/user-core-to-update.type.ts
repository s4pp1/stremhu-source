import { Resolution } from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/common/enum/language.enum';

import { UserRoleEnum } from '../enum/user-role.enum';

export interface UserCoreToUpdate {
  userRole?: UserRoleEnum;
  username?: string;
  passwordHash?: string | null;
  torrentResolutions?: Resolution[];
  torrentLanguages?: LanguageEnum[];
  torrentSeed?: number | null;
  token?: string;
}
