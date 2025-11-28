import { Resolution } from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/common/enums/language.enum';

export interface UserToUpdate {
  username?: string;
  password?: string | null;
  torrentResolutions?: Resolution[];
  torrentLanguages?: LanguageEnum[];
  torrentSeed?: number | null;
}
