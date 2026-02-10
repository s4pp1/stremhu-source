import {
  Source as SourceEnum,
  filenameParse,
} from '@ctrl/video-filename-parser';
import { Injectable } from '@nestjs/common';
import { compact, orderBy } from 'lodash';

import { CatalogService } from 'src/catalog/catalog.service';
import { formatFilesize } from 'src/common/utils/file.util';
import { AUDIO_CODEC_LABEL_MAP } from 'src/preference-items/constant/audio-codec.constant';
import { LANGUAGE_LABEL_MAP } from 'src/preference-items/constant/language.constant';
import { RESOLUTION_LABEL_MAP } from 'src/preference-items/constant/resolution.constant';
import { VIDEO_QUALITY_LABEL_MAP } from 'src/preference-items/constant/video-quality.constant';
import { SettingsService } from 'src/settings/settings.service';
import { TorrentsService } from 'src/torrents/torrents.service';
import { TrackerDiscoveryService } from 'src/trackers/tracker-discovery.service';
import { TrackerTorrent } from 'src/trackers/tracker.types';
import { TRACKER_INFO } from 'src/trackers/trackers.constants';
import { UserDto } from 'src/users/dto/user.dto';
import { User } from 'src/users/entity/user.entity';

import { AudioCodecEnum } from '../../preference-items/enum/audio-codec.enum';
import { VideoQualityEnum } from '../../preference-items/enum/video-quality.enum';
import { StreamDto } from './dto/stremio-stream.dto';
import { ParsedStremioIdSeries } from './pipe/stream-id.pipe';
import { FindStreams } from './type/find-streams.type';
import { VideoFile } from './type/video-file.type';
import { buildSelectors } from './util/build-selectors';
import { findVideoFile } from './util/find-video-file.util';
import { isNotWebReady } from './util/is-not-web-ready.util';
import { parseAudioCodec } from './util/parse-audio-codec.util';
import { parseSourceType } from './util/parse-source-type.util';
import { parseVideoQualities } from './util/parse-video-qualities.util';

@Injectable()
export class StreamsService {
  constructor(
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
    private readonly settingsService: SettingsService,
    private readonly catalogService: CatalogService,
    private readonly torrentsService: TorrentsService,
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

    const videoFiles = this.findVideoFiles(isSpecial, trackerTorrents, series);
    const filteredVideoFiles = this.filterVideoFiles(videoFiles, user);
    const sortedVideoFiles = this.sortVideoFiles(filteredVideoFiles, user);

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

    const isActive = activeInfoHashes.has(videoFile.infoHash);
    if (isActive) {
      nameArray.unshift('⭐');
    }

    const readableLanguage = `🌍 ${LANGUAGE_LABEL_MAP[videoFile.language]}`;

    const fileSize = `💾 ${formatFilesize(videoFile.fileSize)}`;
    const seeders = `👥 ${videoFile.seeders}`;
    const tracker = `🧲 ${TRACKER_INFO[videoFile.tracker].label}`;

    let readableAudioCodec: string | undefined;

    if (videoFile.audioCodec !== AudioCodecEnum.UNKNOWN) {
      readableAudioCodec = `🔈 ${AUDIO_CODEC_LABEL_MAP[videoFile.audioCodec]}`;
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

  private findVideoFiles(
    isSpecial: boolean,
    torrents: TrackerTorrent[],
    series?: ParsedStremioIdSeries,
  ): VideoFile[] {
    const torrentByFiles: VideoFile[] = [];

    for (const torrent of torrents) {
      if (!torrent.name) continue;

      const {
        sources: torrentSources,
        videoCodec: torrentVideoCodec,
        resolution: torrentResolution,
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
      } = filenameParse(videoFile.name);

      const videoCodec = torrentVideoCodec ?? fileVideoCodec;
      const resolution = torrentResolution ?? fileResolution;
      const audioCodec = parseAudioCodec(torrent.name);
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
      torrentAudioCodecs,
      torrentSourceTypes,
      torrentSeed,
    } = user;

    const languageSelectors = buildSelectors(torrentLanguages);
    const resolutionSelectors = buildSelectors(torrentResolutions);
    const videoQualitySelectors = buildSelectors(torrentVideoQualities);
    const audioCodecSelectors = buildSelectors(torrentAudioCodecs);
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
        sourceTypeSelectors.filterToAllowed(videoFile.sourceType) &&
        audioCodecSelectors.filterToAllowed(videoFile.audioCodec)
      );
    });

    return filteredVideoFiles;
  }

  private sortVideoFiles(videoFiles: VideoFile[], user: User): VideoFile[] {
    const {
      torrentLanguages,
      torrentResolutions,
      torrentVideoQualities,
      torrentAudioCodecs,
      torrentSourceTypes,
    } = user;

    const languageSelectors = buildSelectors(torrentLanguages);
    const resolutionSelectors = buildSelectors(torrentResolutions);
    const videoQualitySelectors = buildSelectors(torrentVideoQualities);
    const audioCodecSelectors = buildSelectors(torrentAudioCodecs);
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
        (videoFile) => audioCodecSelectors.priorityIndex(videoFile.audioCodec),
        (videoFile) => videoFile.seeders,
      ],
      ['asc', 'asc', 'asc', 'asc', 'asc', 'desc'],
    );

    return sortedVideoFiles;
  }
}
