import { Resolution } from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/common/enum/language.enum';
import { VideoQualityEnum } from 'src/stremio/streams/enum/video-quality.enum';

import { UserRoleEnum } from '../enum/user-role.enum';

export interface UserCoreToUpdate {
  userRole?: UserRoleEnum;
  username?: string;
  passwordHash?: string | null;
  torrentResolutions?: Resolution[];
  torrentVideoQualities?: VideoQualityEnum[];
  torrentLanguages?: LanguageEnum[];
  torrentSeed?: number | null;
  token?: string;
  onlyBestTorrent?: boolean;
}
