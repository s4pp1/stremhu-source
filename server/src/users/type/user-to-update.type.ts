import { Resolution } from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/common/enum/language.enum';
import { AudioCodecEnum } from 'src/stremio/streams/enum/audio-codec.enum';
import { SourceTypeEnum } from 'src/stremio/streams/enum/source-type.enum';
import { VideoQualityEnum } from 'src/stremio/streams/enum/video-quality.enum';

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
