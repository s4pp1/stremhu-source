import { BadRequestException, Injectable, PipeTransform } from '@nestjs/common';
import { isString, toInteger } from 'lodash';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { isTrackerEnum } from 'src/trackers/util/is-tracker-enum';

import {
  ADDON_APP_PREFIX_ID,
  ADDON_STREMHU_PREFIX_ID,
} from '../../stremio.constants';
import { StreamIdTypeEnum } from '../enum/stream-id-type.enum';
import { ParsedStreamId } from '../type/parsed-stream-id.type';
import { ParsedStreamSeries } from '../type/parsed-stream-series.type';

@Injectable()
export class ParseStreamIdPipe implements PipeTransform<
  string,
  ParsedStreamId
> {
  transform(value: string): ParsedStreamId {
    const isApp = value.startsWith(ADDON_APP_PREFIX_ID);

    if (isApp) {
      const appId = value.replace(ADDON_APP_PREFIX_ID, '');
      const [trackerPart, torrentIdPart, imdbIdPart] = appId.split(':');

      let tracker: TrackerEnum | undefined;
      if (isTrackerEnum(trackerPart)) {
        tracker = trackerPart;
      }

      let torrentId: string | undefined;
      if (isString(torrentIdPart)) {
        torrentId = torrentIdPart;
      }

      let imdbId: string | undefined;
      if (isString(imdbIdPart)) {
        imdbId = imdbIdPart;
      }

      if (
        tracker === undefined ||
        torrentId === undefined ||
        imdbId === undefined
      ) {
        throw new BadRequestException();
      }

      return {
        type: StreamIdTypeEnum.TORRENT,
        imdbId,
        torrentId,
        tracker,
      };
    }

    let metaId = value;

    const isStremHuMeta = value.startsWith(ADDON_STREMHU_PREFIX_ID);
    if (isStremHuMeta) {
      metaId = value.replace(ADDON_STREMHU_PREFIX_ID, '');
    }

    const parts = metaId.split(':');
    const [imdb, seasonPart, episodePart] = parts;

    let season: number | undefined;
    if (isString(seasonPart)) {
      season = toInteger(seasonPart);
    }

    let episode: number | undefined;
    if (isString(episodePart)) {
      episode = toInteger(episodePart);
    }

    let series: ParsedStreamSeries | undefined;

    if (season !== undefined && episode !== undefined) {
      series = { season, episode };
    }

    return { type: StreamIdTypeEnum.IMDB, imdbId: imdb, series };
  }
}
