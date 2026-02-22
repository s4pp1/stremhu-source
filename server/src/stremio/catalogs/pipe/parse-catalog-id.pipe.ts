import { BadRequestException, Injectable, PipeTransform } from '@nestjs/common';
import { isString } from 'lodash';

import { ADDON_APP_PREFIX_ID } from 'src/stremio/stremio.constants';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { isTrackerEnum } from 'src/trackers/util/is-tracker-enum';

import { ParsedCatalogId } from '../type/parsed-catalog-id.type';

@Injectable()
export class ParseCatalogIdPipe implements PipeTransform<
  string,
  ParsedCatalogId
> {
  transform(value: string): ParsedCatalogId {
    let metaId = value;

    const isApp = metaId.startsWith(ADDON_APP_PREFIX_ID);
    if (isApp) {
      metaId = value.replace(ADDON_APP_PREFIX_ID, '');
    }

    const parts = metaId.split(':');
    const [trackerPart, torrentIdPart] = parts;

    let tracker: TrackerEnum | undefined;
    if (isTrackerEnum(trackerPart)) {
      tracker = trackerPart;
    }

    let torrentId: string | undefined;
    if (isString(torrentIdPart)) {
      torrentId = torrentIdPart;
    }

    if (tracker === undefined || torrentId === undefined) {
      throw new BadRequestException();
    }

    return { tracker, torrentId };
  }
}
