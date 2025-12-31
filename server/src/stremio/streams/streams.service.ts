import {
  Source as SourceEnum,
  filenameParse,
} from '@ctrl/video-filename-parser';
import { Injectable } from '@nestjs/common';
import { compact, orderBy } from 'lodash';

import { CatalogService } from 'src/catalog/catalog.service';
import { LANGUAGE_LABEL_MAP } from 'src/common/constant/language.constant';
import { RESOLUTION_LABEL_MAP } from 'src/common/constant/resolution.constant';
import { VIDEO_QUALITY_LABEL_MAP } from 'src/common/constant/video-quality.constant';
import { formatFilesize } from 'src/common/utils/file.util';
import { SettingsStore } from 'src/settings/core/settings.store';
import { TrackerTorrentStatusEnum } from 'src/trackers/enum/tracker-torrent-status.enum';
import { TrackerDiscoveryService } from 'src/trackers/tracker-discovery.service';
import {
  TrackerTorrentError,
  TrackerTorrentSuccess,
} from 'src/trackers/tracker.types';
import { TRACKER_INFO } from 'src/trackers/trackers.constants';
import { UserDto } from 'src/users/dto/user.dto';
import { User } from 'src/users/entity/user.entity';

import { StreamDto } from './dto/stremio-stream.dto';
import { VideoQualityEnum } from './enum/video-quality.enum';
import { ParsedStreamIdSeries } from './pipe/stream-id.pipe';
import { FindStreams } from './type/find-streams.type';
import { VideoFile } from './type/video-file.type';
import { buildSelectors } from './util/build-selectors';
import { findVideoFile } from './util/find-video-file.util';
import { isNotWebReady } from './util/is-not-web-ready.util';
import { parseSourceType } from './util/parse-source-type.util';
import { parseVideoQualities } from './util/parse-video-qualities.util';

@Injectable()
export class StreamsService {
  constructor(
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
    private readonly settingsStore: SettingsStore,
    private readonly catalogService: CatalogService,
  ) {}

  async streams(payload: FindStreams): Promise<StreamDto[]> {
    const { user, mediaType, series } = payload;

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

    const torrentErrors: TrackerTorrentError[] = [];
    const torrentSuccesses: TrackerTorrentSuccess[] = [];

    torrents.forEach((torrent) => {
      if (torrent.status === TrackerTorrentStatusEnum.ERROR) {
        return torrentErrors.push(torrent);
      }

      return torrentSuccesses.push(torrent);
    });

    const videoFiles = this.findVideoFiles(isSpecial, torrentSuccesses, series);
    const filteredVideoFiles = this.filterVideoFiles(videoFiles, user);
    const sortedVideoFiles = this.sortVideoFiles(filteredVideoFiles, user);

    let streams: StreamDto[] = [];

    if (sortedVideoFiles.length > 0) {
      const endpoint = await this.settingsStore.getEndpoint();

      if (user.onlyBestTorrent) {
        const bestVideoFile = sortedVideoFiles[0];

        streams = [this.stream(bestVideoFile, user, endpoint)];
      } else {
        streams = sortedVideoFiles.map((videoFile) =>
          this.stream(videoFile, user, endpoint),
        );
      }
    }

    const streamErrors: StreamDto[] = torrentErrors.map((torrentError) =>
      this.streamError(torrentError),
    );

    return [...streams, ...streamErrors];
  }

  private stream(
    videoFile: VideoFile,
    user: UserDto,
    endpoint: string,
  ): StreamDto {
    const videoQualities = videoFile.videoQualities.filter(
      (videoQuality) => videoQuality !== VideoQualityEnum.SDR,
    );

    const readableVideoQualities = videoQualities
      .map((videoQuality) => VIDEO_QUALITY_LABEL_MAP[videoQuality])
      .join(', ');
    const readableResolution = RESOLUTION_LABEL_MAP[videoFile.resolution];

    const nameArray = compact([readableResolution, readableVideoQualities]);

    const isCamSource = videoFile.sources.includes(SourceEnum.CAM);

    if (isCamSource) {
      nameArray.push('📹 CAM');
    }

    const readableLanguage = `🌍 ${LANGUAGE_LABEL_MAP[videoFile.language]}`;

    const fileSize = `💾 ${formatFilesize(videoFile.fileSize)}`;
    const seeders = `👥 ${videoFile.seeders}`;
    const tracker = `🧲 ${TRACKER_INFO[videoFile.tracker].label}`;
    const group = videoFile.group ? `🎯 ${videoFile.group}` : undefined;

    const descriptionArray = compact([
      compact([tracker, seeders]).join(' | '),
      compact([readableLanguage, videoFile.audioCodec]).join(' | '),
      compact([fileSize, group]).join(' | '),
    ]);

    const bingeGroup = [
      videoFile.tracker,
      videoFile.resolution,
      videoFile.language,
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

  private streamError(torrentError: TrackerTorrentError) {
    return {
      name: '❗ H I B A ❗',
      description: `❗ ${torrentError.message} ❗`,
      url: 'http://hiba.tortent',
      behaviorHints: {
        notWebReady: false,
      },
    };
  }

  private findVideoFiles(
    isSpecial: boolean,
    torrents: TrackerTorrentSuccess[],
    series?: ParsedStreamIdSeries,
  ): VideoFile[] {
    const torrentByFiles: VideoFile[] = [];

    for (const torrent of torrents) {
      if (!torrent.name) continue;

      const {
        sources: torrentSources,
        videoCodec: torrentVideoCodec,
        resolution: torrentResolution,
        audioCodec: torrentAudioCodec,
        group: torrentGroup,
      } = filenameParse(torrent.name);

      const videoFile = findVideoFile({
        files: torrent.files,
        series,
        isSpecial,
      });

      if (!videoFile) continue;

      const {
        sources: fileSources,
        videoCodec: fileVideoCodec,
        resolution: fileResolution,
        audioCodec: fileAudioCodec,
      } = filenameParse(videoFile.name);

      const videoCodec = torrentVideoCodec ?? fileVideoCodec;
      const resolution = torrentResolution ?? fileResolution;
      const audioCodec = torrentAudioCodec ?? fileAudioCodec;
      const sources = torrentSources ?? fileSources;

      const torrentByFile: VideoFile = {
        imdbId: torrent.imdbId,
        tracker: torrent.tracker,
        torrentId: torrent.torrentId,
        seeders: torrent.seeders,
        group: torrentGroup || undefined,

        infoHash: torrent.infoHash,
        fileName: videoFile.name,
        fileSize: videoFile.size,
        fileIndex: videoFile.fileIndex,

        language: torrent.language,
        resolution: resolution || torrent.resolution,
        audioCodec,
        videoCodec,
        videoQualities: parseVideoQualities(torrent.name),
        sourceType: parseSourceType(torrent.name),
        sources,
        notWebReady: isNotWebReady(videoCodec, audioCodec),
      };

      torrentByFiles.push(torrentByFile);
    }

    return torrentByFiles;
  }

  private filterVideoFiles(videoFiles: VideoFile[], user: User): VideoFile[] {
    const {
      torrentLanguages,
      torrentResolutions,
      torrentVideoQualities,
      torrentSourceTypes,
      torrentSeed,
    } = user;

    const languageSelectors = buildSelectors(torrentLanguages);
    const resolutionSelectors = buildSelectors(torrentResolutions);
    const videoQualitySelectors = buildSelectors(torrentVideoQualities);
    const sourceTypeSelectors = buildSelectors(torrentSourceTypes);

    const filteredVideoFiles = videoFiles.filter((videoFile) => {
      let isSeedSet = true;

      if (torrentSeed !== null) {
        isSeedSet = videoFile.seeders > torrentSeed;
      }

      return (
        isSeedSet &&
        resolutionSelectors.filterToAllowed(videoFile.resolution) &&
        languageSelectors.filterToAllowed(videoFile.language) &&
        videoFile.videoQualities.some((videoQuality) =>
          videoQualitySelectors.filterToAllowed(videoQuality),
        ) &&
        sourceTypeSelectors.filterToAllowed(videoFile.sourceType)
      );
    });

    return filteredVideoFiles;
  }

  private sortVideoFiles(videoFiles: VideoFile[], user: User): VideoFile[] {
    const {
      torrentLanguages,
      torrentResolutions,
      torrentVideoQualities,
      torrentSourceTypes,
    } = user;

    const languageSelectors = buildSelectors(torrentLanguages);
    const resolutionSelectors = buildSelectors(torrentResolutions);
    const videoQualitySelectors = buildSelectors(torrentVideoQualities);
    const sourceTypeSelectors = buildSelectors(torrentSourceTypes);

    const sortedVideoFiles = orderBy(
      videoFiles,
      [
        (videoFile) => languageSelectors.priorityIndex(videoFile.language),
        (videoFile) => resolutionSelectors.priorityIndex(videoFile.resolution),
        (videoFile) => {
          const bestQualityRank = Math.min(
            ...videoFile.videoQualities.map((videoQuality) =>
              videoQualitySelectors.priorityIndex(videoQuality),
            ),
          );

          return bestQualityRank;
        },
        (videoFile) => sourceTypeSelectors.priorityIndex(videoFile.sourceType),
        (videoFile) => videoFile.seeders,
      ],
      ['asc', 'asc', 'asc', 'asc', 'desc'],
    );

    return sortedVideoFiles;
  }
}
