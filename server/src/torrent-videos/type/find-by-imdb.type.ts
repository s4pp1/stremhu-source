import { MediaTypeEnum } from 'src/common/enum/media-type.enum';
import { ParsedStreamSeries } from 'src/stremio/streams/type/parsed-stream-series.type';
import { User } from 'src/users/entity/user.entity';

export type FindByImdb = {
  user: User;
  mediaType: MediaTypeEnum;
  imdbId: string;
  series?: ParsedStreamSeries;
};
