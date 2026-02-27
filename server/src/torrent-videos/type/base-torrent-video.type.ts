import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { TrackerOption } from 'src/trackers/type/tracker-option.type';

export type BaseTorrentVideo = {
  [PreferenceEnum.TRACKER]: TrackerOption;
  torrentId: string;

  infoHash: string;
  torrentName: string;
  fileName: string;
  fileSize: string;
  fileIndex: number;

  playUrl: string;
};
