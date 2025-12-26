import { ParsedFile } from 'src/common/utils/parse-torrent.util';

export type SelectedVideoFile = {
  fileIndex: number;
  file: ParsedFile;
};
