import { Resolution } from '@ctrl/video-filename-parser';

import { AudioCodecEnum } from 'src/preference-items/enum/audio-codec.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { SourceTypeEnum } from 'src/preference-items/enum/source-type.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';

import { UserRoleEnum } from '../enum/user-role.enum';

export interface UserToUpdate {
  userRole?: UserRoleEnum;
  username?: string;
  password?: string | null;
  torrentResolutions?: Resolution[];
  torrentVideoQualities?: VideoQualityEnum[];
  torrentAudioCodecs?: AudioCodecEnum[];
  torrentSourceTypes?: SourceTypeEnum[];
  torrentLanguages?: LanguageEnum[];
  torrentSeed?: number | null;
  onlyBestTorrent?: boolean;
}
