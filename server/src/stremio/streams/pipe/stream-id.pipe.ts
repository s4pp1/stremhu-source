import { Injectable, PipeTransform } from '@nestjs/common';
import { isString, toInteger } from 'lodash';

import { ADDON_PREFIX_ID } from '../../stremio.constants';

export interface ParsedStremioIdSeries {
  season: number;
  episode: number;
}

export interface ParsedStremioId {
  imdbId: string;
  series?: ParsedStremioIdSeries;
}

@Injectable()
export class StreamIdPipe implements PipeTransform<string, ParsedStremioId> {
  transform(value: string): ParsedStremioId {
    let metaId = value;

    const isStremHuMeta = metaId.startsWith(ADDON_PREFIX_ID);
    if (isStremHuMeta) {
      metaId = value.replace(ADDON_PREFIX_ID, '');
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

    let series: ParsedStremioIdSeries | undefined;

    if (season !== undefined && episode !== undefined) {
      series = { season, episode };
    }

    return { imdbId: imdb, series };
  }
}
