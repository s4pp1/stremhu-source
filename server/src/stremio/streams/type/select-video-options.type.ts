import { ParsedFile } from 'src/common/utils/parse-torrent.util';

import { ParsedStreamIdSeries } from '../pipe/stream-id.pipe';

export type SelectVideoOptions = {
  files: ParsedFile[] | undefined;
  series?: ParsedStreamIdSeries;
  isSpecial: boolean;
};
