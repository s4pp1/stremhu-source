import { Injectable } from '@nestjs/common';

import { TorrentsCacheStore } from 'src/torrents-cache/core/torrents-cache.store';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { TrackerDiscoveryService } from 'src/trackers/tracker-discovery.service';

import { MetaDetailDto } from '../dto/meta-detail.dto';
import { MetaPreviewDto } from '../dto/meta-preview.dto';
import { ContentTypeEnum } from '../enum/content-type.enum';
import { PosterShapeEnum } from '../enum/poster-shape.enum';
import { ADDON_APP_PREFIX_ID } from '../stremio.constants';

@Injectable()
export class StremioCatalogsService {
  constructor(
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
    private readonly torrentsCacheStore: TorrentsCacheStore,
  ) {}

  async getMetas(torrentId: string): Promise<MetaDetailDto[]> {
    return this.searchMetas(torrentId);
  }

  async searchMetas(torrentId: string): Promise<MetaPreviewDto[]> {
    const previews: MetaPreviewDto[] = [];

    const torrents = await this.trackerDiscoveryService.findOne(torrentId);

    for (const torrent of torrents) {
      if (torrent.status === 'rejected') {
        continue;
      }

      const preview = await this.getMeta(
        torrent.value.tracker,
        torrent.value.torrentId,
      );

      if (!preview) {
        continue;
      }

      previews.push(preview);
    }

    return previews;
  }

  async getMeta(
    tracker: TrackerEnum,
    torrentId: string,
  ): Promise<MetaDetailDto | null> {
    const torrentCache = await this.torrentsCacheStore.findOne({
      tracker,
      torrentId,
    });

    if (!torrentCache) {
      return null;
    }

    const { name } = torrentCache.info;

    return {
      id: this.buildId(tracker, torrentId),
      name: name,
      posterShape: PosterShapeEnum.REGULAR,
      type: ContentTypeEnum.MOVIE,
    };
  }

  private buildId(tracker: TrackerEnum, torrentId: string): string {
    const parts = [tracker, torrentId].filter((part) => part !== undefined);

    return `${ADDON_APP_PREFIX_ID}${parts.join(':')}`;
  }
}
