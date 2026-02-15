import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { DETAILS_PATH as BITHUMEN_DETAILS_PATH } from '../adapters/bithumen/bithumen.constants';
import { DETAILS_PATH as INSANE_DETAILS_PATH } from '../adapters/insane/insane.constants';
import { DETAILS_PATH as MAJOMPARADE_DETAILS_PATH } from '../adapters/majomparade/majomparade.constants';
import { DETAILS_PATH as NCORE_DETAILS_PATH } from '../adapters/ncore/ncore.constants';
import { TRACKER_LABEL } from '../constant/trackers-label.constant';
import { TrackerEnum } from '../enum/tracker.enum';
import { TrackerOption } from '../type/tracker-option.type';

@Injectable()
export class TrackersMetaService {
  private trackers: TrackerOption[];

  constructor(private readonly configService: ConfigService) {
    const ncoreUrl = this.configService.getOrThrow<string>('tracker.ncore-url');
    const bithumenUrl = this.configService.getOrThrow<string>(
      'tracker.bithumen-url',
    );
    const insaneUrl =
      this.configService.getOrThrow<string>('tracker.insane-url');
    const majomparadeUrl = this.configService.getOrThrow<string>(
      'tracker.majomparade-url',
    );

    this.trackers = [
      {
        value: TrackerEnum.NCORE,
        label: TRACKER_LABEL[TrackerEnum.NCORE],
        requiresFullDownload: false,
        url: ncoreUrl,
        detailsPath: NCORE_DETAILS_PATH,
      },
      {
        value: TrackerEnum.BITHUMEN,
        label: TRACKER_LABEL[TrackerEnum.BITHUMEN],
        requiresFullDownload: false,
        url: bithumenUrl,
        detailsPath: BITHUMEN_DETAILS_PATH,
      },
      {
        value: TrackerEnum.INSANE,
        label: TRACKER_LABEL[TrackerEnum.INSANE],
        requiresFullDownload: false,
        url: insaneUrl,
        detailsPath: INSANE_DETAILS_PATH,
      },
      {
        value: TrackerEnum.MAJOMPARADE,
        label: TRACKER_LABEL[TrackerEnum.MAJOMPARADE],
        requiresFullDownload: true,
        url: majomparadeUrl,
        detailsPath: MAJOMPARADE_DETAILS_PATH,
      },
    ];
  }

  all(): TrackerOption[] {
    return this.trackers;
  }

  resolve(trackerEnum: TrackerEnum): TrackerOption {
    const tracker = this.trackers.find(
      (tracker) => tracker.value === trackerEnum,
    );

    return tracker!;
  }
}
