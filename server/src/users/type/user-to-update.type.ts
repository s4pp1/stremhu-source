import { Resolution } from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/common/enum/language.enum';
import { VideoQualityEnum } from 'src/stremio/streams/enum/video-quality.enum';

import { UserRoleEnum } from '../enum/user-role.enum';

export interface UserToUpdate {
  userRole?: UserRoleEnum;
  username?: string;
  password?: string | null;
  torrentResolutions?: Resolution[];
  torrentVideoQualities?: VideoQualityEnum[];
  torrentLanguages?: LanguageEnum[];
  torrentSeed?: number | null;
  onlyBestTorrent?: boolean;
}
