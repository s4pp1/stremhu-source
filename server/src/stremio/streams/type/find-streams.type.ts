import { StreamMediaTypeEnum } from 'src/stremio/enum/stream-media-type.enum';
import { User } from 'src/users/entity/user.entity';

import { ParsedStreamIdSeries } from '../pipe/stream-id.pipe';

export type FindStreams = {
  user: User;
  mediaType: StreamMediaTypeEnum;
  imdbId: string;
  series?: ParsedStreamIdSeries;
};
