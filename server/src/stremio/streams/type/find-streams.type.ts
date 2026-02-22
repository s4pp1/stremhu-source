import { MediaTypeEnum } from 'src/common/enum/media-type.enum';

import { ParsedStreamId } from './parsed-stream-id.type';

export type FindStreams = {
  mediaType: MediaTypeEnum;
} & ParsedStreamId;
