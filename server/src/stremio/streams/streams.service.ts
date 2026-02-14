import { Injectable } from '@nestjs/common';
import { compact, orderBy } from 'lodash';

import { CatalogService } from 'src/catalog/catalog.service';
import { formatFilesize } from 'src/common/utils/file.util';
import { AUDIO_QUALITY_LABEL_MAP } from 'src/preference-items/constant/audio-codec.constant';
import { LANGUAGE_LABEL_MAP } from 'src/preference-items/constant/language.constant';
import { RESOLUTION_LABEL_MAP } from 'src/preference-items/constant/resolution.constant';
import { VIDEO_QUALITY_LABEL_MAP } from 'src/preference-items/constant/video-quality.constant';
import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';
import { SourceEnum } from 'src/preference-items/enum/source.enum';
import { SettingsService } from 'src/settings/settings.service';
import { TorrentsService } from 'src/torrents/torrents.service';
import { TrackerDiscoveryService } from 'src/trackers/tracker-discovery.service';
import { TrackerTorrent } from 'src/trackers/tracker.types';
import { TRACKER_INFO } from 'src/trackers/trackers.constants';
import { PreferenceValue } from 'src/user-preferences/type/preference-value.type';
import { UserPreference } from 'src/user-preferences/type/user-preference.type';
import { UserPreferencesService } from 'src/user-preferences/user-preferences.service';
import { UserDto } from 'src/users/dto/user.dto';
import { User } from 'src/users/entity/user.entity';

import { VideoQualityEnum } from '../../preference-items/enum/video-quality.enum';
import { StreamDto } from './dto/stremio-stream.dto';
import { resolveVideoFile } from './lib/resolve-video-file';
import { ParsedStremioIdSeries } from './pipe/stream-id.pipe';
import { FindStreams } from './type/find-streams.type';
import { VideoFile } from './type/video-file.type';
import { buildSelectors } from './util/build-selectors';

@Injectable()
export class StreamsService {
  constructor(
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
    private readonly settingsService: SettingsService,
    private readonly catalogService: CatalogService,
    private readonly torrentsService: TorrentsService,
    private readonly userPreferencesService: UserPreferencesService,
  ) {}

  async streams(payload: FindStreams): Promise<StreamDto[]> {
    const { user, mediaType, series } = payload;

    const userPreferences = await this.userPreferencesService.find(user.id);

    const { imdbId, originalImdbId } = await this.catalogService.resolveImdbId({
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
    const streamErrors: StreamDto[] = [];

    torrents.forEach((torrent) => {
      if (torrent.status === 'fulfilled') {
        trackerTorrents = [...trackerTorrents, ...torrent.value];
      } else {
        const error = torrent.reason as Error;
        const streamError = this.streamError(error.message);
        streamErrors.push(streamError);
      }
    });

    const videoFiles = this.resolveVideoFiles(
      trackerTorrents,
      isSpecial ? undefined : series,
    );
    const filteredVideoFiles = this.filterVideoFiles(
      videoFiles,
      user,
      userPreferences,
    );
    const sortedVideoFiles = this.sortVideoFiles(
      filteredVideoFiles,
      userPreferences,
    );

    let streams: StreamDto[] = [];

    if (sortedVideoFiles.length > 0) {
      const endpoint = await this.settingsService.getEndpoint();
      const activeTorrents = await this.torrentsService.find();
      const activeInfoHashes = new Set(
        activeTorrents.map((torrent) => torrent.infoHash),
      );

      if (user.onlyBestTorrent) {
        const bestVideoFile = sortedVideoFiles[0];

        streams = [
          this.stream(bestVideoFile, user, endpoint, activeInfoHashes),
        ];
      } else {
        streams = sortedVideoFiles.map((videoFile) =>
          this.stream(videoFile, user, endpoint, activeInfoHashes),
        );
      }
    }

    return [...streams, ...streamErrors];
  }

  private stream(
    videoFile: VideoFile,
    user: UserDto,
    endpoint: string,
    activeInfoHashes: Set<string>,
  ): StreamDto {
    const videoQualities = videoFile['video-quality'].filter(
      (videoQuality) => videoQuality !== VideoQualityEnum.SDR,
    );

    const readableVideoQualities = videoQualities
      .map((videoQuality) => VIDEO_QUALITY_LABEL_MAP[videoQuality])
      .join(', ');
    const readableResolution = RESOLUTION_LABEL_MAP[videoFile.resolution];

    const nameArray = compact([readableResolution, readableVideoQualities]);

    const isCamSource = videoFile.source.includes(SourceEnum.THEATRICAL);

    if (isCamSource) {
      nameArray.push('📹 CAM');
    }

    const isActive = activeInfoHashes.has(videoFile.infoHash);
    if (isActive) {
      nameArray.unshift('⭐');
    }

    const readableLanguage = `🌍 ${LANGUAGE_LABEL_MAP[videoFile.language]}`;

    const fileSize = `💾 ${formatFilesize(videoFile.fileSize)}`;
    const seeders = `👥 ${videoFile.seeders}`;
    const tracker = `🧲 ${TRACKER_INFO[videoFile.tracker].label}`;

    let readableAudioCodec: string | undefined;

    if (videoFile['audio-quality'] !== AudioQualityEnum.UNKNOWN) {
      readableAudioCodec = `🔈 ${AUDIO_QUALITY_LABEL_MAP[videoFile['audio-quality']]}`;
    }

    const descriptionArray = compact([
      compact([tracker, seeders, fileSize]).join(' | '),
      compact([readableLanguage, readableAudioCodec]).join(' | '),
    ]);

    const bingeGroup = [
      videoFile.imdbId,
      videoFile.tracker,
      videoFile.torrentId,
    ].join('-');

    return {
      name: nameArray.join(' | '),
      description: descriptionArray.join('\n'),
      url: `${endpoint}/api/${user.token}/stream/play/${videoFile.imdbId}/${videoFile.tracker}/${videoFile.torrentId}/${videoFile.fileIndex}`,
      behaviorHints: {
        notWebReady: videoFile.notWebReady,
        bingeGroup,
        filename: videoFile.fileName,
      },
    };
  }

  private streamError(message: string) {
    return {
      name: '❗ HIBA ❗',
      description: `❗ ${message} ❗`,
      url: 'http://hiba.tortent',
      behaviorHints: {
        notWebReady: false,
      },
    };
  }

  private resolveVideoFiles(
    torrents: TrackerTorrent[],
    series?: ParsedStremioIdSeries,
  ): VideoFile[] {
    return torrents
      .map((torrent) => resolveVideoFile({ torrent, series }))
      .filter((videoFile) => videoFile !== null);
  }

  private filterVideoFiles(
    videoFiles: VideoFile[],
    user: User,
    userPreferences: UserPreference[],
  ): VideoFile[] {
    const blockedPreferences = userPreferences.filter(
      (userPreference) => userPreference.blocked.length !== 0,
    );

    const selectors = blockedPreferences.map((blockedPreference) =>
      buildSelectors(blockedPreference.preference, blockedPreference.blocked),
    );

    const { torrentSeed } = user;

    const filteredVideoFiles = videoFiles.filter((videoFile) => {
      if (torrentSeed !== null) {
        const isSeedFilter = videoFile.seeders < torrentSeed;
        if (isSeedFilter) return false;
      }

      const blockeds = selectors.map((selector) =>
        selector.filterToBlocked((preference) => videoFile[preference]),
      );

      return blockeds.some((blocked) => !blocked);
    });

    return filteredVideoFiles;
  }

  private sortVideoFiles(
    videoFiles: VideoFile[],
    userPreferences: UserPreference[],
  ): VideoFile[] {
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
      (selector) => (videoFile: VideoFile) =>
        selector.priorityIndex(
          (preference) =>
            videoFile[preference] as PreferenceValue | PreferenceValue[],
        ),
    );

    const iteratees: Array<(videoFile: VideoFile) => number> = [
      ...dynamicIteratees,
      (videoFile: VideoFile) => videoFile.seeders,
    ];

    const orders: Array<'asc' | 'desc'> = [
      ...dynamicIteratees.map((): 'asc' => 'asc'),
      'desc',
    ];

    const sortedVideoFiles = orderBy(videoFiles, iteratees, orders);

    return sortedVideoFiles;
  }
}
