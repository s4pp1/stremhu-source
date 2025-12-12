import { Resolution } from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/common/enums/language.enum';

import { UserRoleEnum } from '../enum/user-role.enum';

export interface UserToUpdate {
  userRole?: UserRoleEnum;
  username?: string;
  password?: string | null;
  torrentResolutions?: Resolution[];
  torrentLanguages?: LanguageEnum[];
  torrentSeed?: number | null;
}
