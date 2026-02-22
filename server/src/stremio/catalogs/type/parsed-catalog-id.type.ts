import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type ParsedCatalogId = {
  tracker: TrackerEnum;
  torrentId: string;
};
