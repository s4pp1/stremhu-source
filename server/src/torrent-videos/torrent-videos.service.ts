import { BadRequestException, Injectable } from '@nestjs/common';
import { orderBy } from 'lodash';

import { CatalogService } from 'src/catalog/catalog.service';
import { formatFilesize } from 'src/common/utils/file.util';
import { AUDIO_QUALITY_MAP } from 'src/preference-items/constant/audio-codec.constant';
import { AUDIO_SPATIAL_MAP } from 'src/preference-items/constant/audio-spatial.constant';
import { LANGUAGE_MAP } from 'src/preference-items/constant/language.constant';
import { RESOLUTION_MAP } from 'src/preference-items/constant/resolution.constant';
import { SOURCE_MAP } from 'src/preference-items/constant/source.constant';
import { VIDEO_QUALITY_MAP } from 'src/preference-items/constant/video-quality.constant';
import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';
import { AudioQualityOption } from 'src/preference-items/type/audio-codec-option.type';
import { AudioSpatialOption } from 'src/preference-items/type/audio-spatial-option.type';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { SettingsService } from 'src/settings/settings.service';
import { ParsedStreamSeries } from 'src/stremio/streams/type/parsed-stream-series.type';
import { buildSelectors } from 'src/stremio/streams/util/build-selectors';
import { TorrentsCacheStore } from 'src/torrents-cache/core/torrents-cache.store';
import { TorrentsService } from 'src/torrents/torrents.service';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { TrackersMetaService } from 'src/trackers/meta/trackers-meta.service';
import { TrackerDiscoveryService } from 'src/trackers/tracker-discovery.service';
import { TrackerTorrent } from 'src/trackers/tracker.types';
import { User } from 'src/users/entity/user.entity';
import { PreferenceValue } from 'src/users/preferences/type/preference-value.type';
import { UserPreference } from 'src/users/preferences/type/user-preference.type';
import { UserPreferencesService } from 'src/users/preferences/user-preferences.service';

import { resolveVideoFile } from './lib/resolve-video-file';
import { isSampleOrTrash } from './lib/resolve-video-file/utils';
import { BaseTorrentVideo } from './type/base-torrent-video.type';
import { FindByImdb } from './type/find-by-imdb.type';
import { RowTorrentVideo } from './type/row-torrent-video.type';
import { TorrentVideo } from './type/torrent-video.type';

@Injectable()
export class TorrentVideosService {
  constructor(
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
    private readonly settingsService: SettingsService,
    private readonly catalogService: CatalogService,
    private readonly torrentsService: TorrentsService,
    private readonly userPreferencesService: UserPreferencesService,
    private readonly torrentsCacheStore: TorrentsCacheStore,
    private readonly trackersMetaService: TrackersMetaService,
  ) {}

  async findByImdb(payload: FindByImdb): Promise<[TorrentVideo[], string[]]> {
    const { user, mediaType, imdbId, series } = payload;

    const userPreferences = await this.userPreferencesService.find(user.id);

    const { originalImdbId } = await this.catalogService.resolveImdbId({
      imdbId: payload.imdbId,
      season: series?.season,
      episode: series?.episode,
    });

    const isSpecial = typeof originalImdbId === 'string';

    const torrents = await this.trackerDiscoveryService.findTorrents({
      imdbId: imdbId,
      mediaType: !isSpecial ? mediaType : undefined,
    });

    let trackerTorrents: TrackerTorrent[] = [];
    let trackerErrors: string[] = [];

    torrents.forEach((torrent) => {
      if (torrent.status === 'fulfilled') {
        trackerTorrents = [...trackerTorrents, ...torrent.value];
      } else {
        const error = torrent.reason as Error;
        trackerErrors = [...trackerErrors, error.message];
      }
    });

    const rowTorrentVideos = this.resolveVideoFiles(
      trackerTorrents,
      isSpecial ? undefined : series,
    );

    const filteredRowTorrentVideos = this.filterTorrentVideos(
      rowTorrentVideos,
      user,
      userPreferences,
    );

    const sortedRowTorrentVideos = await this.sortTorrentVideos(
      filteredRowTorrentVideos,
      userPreferences,
    );

    const endpoint = await this.settingsService.getEndpoint();

    const torrentVideos: TorrentVideo[] = sortedRowTorrentVideos.map(
      (rowTorrentVideo) => {
        const videoQualities = rowTorrentVideo['video-quality']
          .filter((videoQuality) => videoQuality !== VideoQualityEnum.SDR)
          .map((videoQuality) => VIDEO_QUALITY_MAP[videoQuality]);

        const audioQualityEnum = rowTorrentVideo['audio-quality'];
        let audioQuality: AudioQualityOption | undefined;

        if (audioQualityEnum !== AudioQualityEnum.UNKNOWN) {
          audioQuality = AUDIO_QUALITY_MAP[audioQualityEnum];
        }

        const audioSpatialEnum = rowTorrentVideo['audio-spatial'];
        let audioSpatial: AudioSpatialOption | undefined;

        if (audioSpatialEnum) {
          audioSpatial = AUDIO_SPATIAL_MAP[audioSpatialEnum];
        }

        return {
          tracker: this.trackersMetaService.resolve(rowTorrentVideo.tracker),
          torrentId: rowTorrentVideo.torrentId,
          seeders: rowTorrentVideo.seeders,

          infoHash: rowTorrentVideo.infoHash,
          torrentName: rowTorrentVideo.torrentName,
          fileName: rowTorrentVideo.fileName,
          fileSize: formatFilesize(rowTorrentVideo.fileSize),
          fileIndex: rowTorrentVideo.fileIndex,

          [PreferenceEnum.LANGUAGE]: LANGUAGE_MAP[rowTorrentVideo.language],

          [PreferenceEnum.RESOLUTION]:
            RESOLUTION_MAP[rowTorrentVideo.resolution],

          [PreferenceEnum.VIDEO_QUALITY]: videoQualities,

          [PreferenceEnum.AUDIO_QUALITY]: audioQuality,

          [PreferenceEnum.AUDIO_SPATIAL]: audioSpatial,

          [PreferenceEnum.SOURCE]: SOURCE_MAP[rowTorrentVideo.source],

          isInRelay: rowTorrentVideo.isInRelay,
          playUrl: `${endpoint}/api/${user.token}/play/${rowTorrentVideo.tracker}/${rowTorrentVideo.torrentId}/${rowTorrentVideo.fileIndex}`,
        };
      },
    );

    return [torrentVideos, trackerErrors];
  }

  async findByTorrentId(
    user: User,
    tracker: TrackerEnum,
    torrentId: string,
  ): Promise<BaseTorrentVideo[]> {
    const endpoint = await this.settingsService.getEndpoint();
    await this.trackerDiscoveryService.findOneByTracker(tracker, torrentId);

    const torrentCache = await this.torrentsCacheStore.findOne({
      tracker,
      torrentId,
    });

    if (!torrentCache) {
      throw new BadRequestException();
    }

    const { files } = torrentCache.info;

    const videoFiles = files.filter(
      (file) => !isSampleOrTrash(file.name.toLowerCase()),
    );

    const sortedVideoFiles = orderBy(
      videoFiles,
      (videoFile) => videoFile.name,
      ['asc'],
    );

    return sortedVideoFiles.map((videoFile) => ({
      tracker: this.trackersMetaService.resolve(tracker),
      torrentId: torrentId,

      infoHash: torrentCache.info.infoHash,
      torrentName: torrentCache.info.name,
      fileName: videoFile.name,
      fileSize: formatFilesize(videoFile.size),
      fileIndex: videoFile.index,

      playUrl: `${endpoint}/api/${user.token}/play/${tracker}/${torrentId}/${videoFile.index}`,
    }));
  }

  private resolveVideoFiles(
    torrents: TrackerTorrent[],
    series?: ParsedStreamSeries,
  ): RowTorrentVideo[] {
    return torrents
      .map((torrent) => resolveVideoFile({ torrent, series }))
      .filter((videoFile) => videoFile !== null);
  }

  private filterTorrentVideos(
    torrentVideos: RowTorrentVideo[],
    user: User,
    userPreferences: UserPreference[],
  ): RowTorrentVideo[] {
    const blockedPreferences = userPreferences.filter(
      (userPreference) => userPreference.blocked.length !== 0,
    );

    const selectors = blockedPreferences.map((blockedPreference) =>
      buildSelectors(blockedPreference.preference, blockedPreference.blocked),
    );

    const { torrentSeed } = user;

    const filteredTorrentVideos = torrentVideos.filter((torrentVideo) => {
      if (torrentSeed !== null) {
        const isSeedFilter = torrentVideo.seeders <= torrentSeed;
        if (isSeedFilter) return false;
      }

      const blockeds = selectors.map((selector) =>
        selector.filterToBlocked(
          (preference) => torrentVideo[preference] ?? [],
        ),
      );

      return !blockeds.some((blocked) => blocked);
    });

    return filteredTorrentVideos;
  }

  private async sortTorrentVideos(
    torrentVideos: RowTorrentVideo[],
    userPreferences: UserPreference[],
  ): Promise<RowTorrentVideo[]> {
    const torrents = await this.torrentsService.find();

    const relayInfoHashes = new Set(
      torrents.map((torrent) => torrent.infoHash),
    );

    for (const torrentVideo of torrentVideos) {
      torrentVideo.isInRelay = relayInfoHashes.has(torrentVideo.infoHash);
    }

    const preferredPreferences = userPreferences.filter(
      (userPreference) => userPreference.preferred.length !== 0,
    );

    const selectors = preferredPreferences.map((preferredPreference) =>
      buildSelectors(
        preferredPreference.preference,
        preferredPreference.preferred,
      ),
    );

    const dynamicIteratees = selectors.map(
      (selector) => (videoFile: RowTorrentVideo) =>
        selector.priorityIndex(
          (preference) =>
            videoFile[preference] as PreferenceValue | PreferenceValue[],
        ),
    );

    const iteratees: Array<(videoFile: RowTorrentVideo) => number> = [
      (videoFile: RowTorrentVideo) => Number(!videoFile.isInRelay),
      ...dynamicIteratees,
      (videoFile: RowTorrentVideo) => videoFile.seeders,
    ];

    const orders: Array<'asc' | 'desc'> = [
      'asc',
      ...dynamicIteratees.map((): 'asc' => 'asc'),
      'desc',
    ];

    const sortedTorrentVideos = orderBy(torrentVideos, iteratees, orders);

    return sortedTorrentVideos;
  }
}
