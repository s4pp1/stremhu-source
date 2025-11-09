import { Resolution, filenameParse } from '@ctrl/video-filename-parser';
import { Injectable } from '@nestjs/common';
import { filesize } from 'filesize';
import isVideo from 'is-video';
import _ from 'lodash';
import { Torrent, TorrentFile } from 'webtorrent';

import { RESOLUTION_LABEL_MAP } from 'src/common/common.constant';
import { LanguageEnum } from 'src/common/enums/language.enum';
import { ParsedFile } from 'src/common/utils/parse-torrent.util';
import { SettingsStore } from 'src/settings/core/settings.store';
import { TorrentCacheStore } from 'src/torrent-cache/core/torrent-cache.store';
import {
  TrackerTorrentError,
  TrackerTorrentStatusEnum,
  TrackerTorrentSuccess,
} from 'src/trackers/tracker.types';
import { TRACKER_LABEL_MAP } from 'src/trackers/trackers.constants';
import { TrackersService } from 'src/trackers/trackers.service';
import { User } from 'src/users/entities/user.entity';
import { WebTorrentService } from 'src/web-torrent/web-torrent.service';

import { StreamDto } from './dto/stremio-stream.dto';
import { ParsedStreamIdSeries } from './pipe/stream-id.pipe';
import {
  FindStreams,
  PlayStream,
  SelectVideoOptions,
  SelectedVideoFile,
  VideoFileLanguage,
  VideoFileResolution,
  VideoFileWithRank,
} from './stream.types';

@Injectable()
export class StremioStreamService {
  private inFlightPlay = new Map<
    string,
    Promise<{ file: TorrentFile; torrent: Torrent }>
  >();

  constructor(
    private torrentCacheStore: TorrentCacheStore,
    private trackersService: TrackersService,
    private webTorrentService: WebTorrentService,
    private settingsStore: SettingsStore,
  ) {}

  async streams(payload: FindStreams): Promise<StreamDto[]> {
    const { user, mediaType, imdbId, series } = payload;

    const setting = await this.settingsStore.findOneOrThrow();

    const torrents = await this.trackersService.findTorrents({
      mediaType: mediaType,
      imdbId: imdbId,
    });

    const torrentErrors: TrackerTorrentError[] = [];
    const torrentSuccesses: TrackerTorrentSuccess[] = [];

    torrents.forEach((torrent) => {
      if (torrent.status === TrackerTorrentStatusEnum.ERROR) {
        return torrentErrors.push(torrent);
      }
      return torrentSuccesses.push(torrent);
    });

    const videoFiles = this.findVideoFilesWithRank(torrentSuccesses, series);
    const filteredVideoFiles = this.filterVideoFiles(videoFiles, user);
    const sortedVideoFiles = this.sortVideoFiles(filteredVideoFiles);

    const streamErrors: StreamDto[] = torrentErrors.map((torrentError) => ({
      name: '❗ H I B A ❗',
      description: `❗ ${torrentError.message} ❗`,
      url: 'http://nincs.tracker.konfiguralva',
      behaviorHints: {
        notWebReady: true,
      },
    }));

    const streams: StreamDto[] = sortedVideoFiles.map((videoFile) => {
      const nameArray = _.compact([
        [videoFile.language.emoji, videoFile.resolution.label].join(' | '),
        videoFile.audio,
      ]);

      const fileSize = `💾 ${filesize(videoFile.fileSize)}`;
      const seeders = `🔼 ${videoFile.seeders}`;

      const descriptionArray = _.compact([
        `[${TRACKER_LABEL_MAP[videoFile.tracker]}]${videoFile.fileName}`,
        [fileSize, seeders, videoFile.language.label].join(' | '),
      ]);

      return {
        name: nameArray.join('\n'),
        description: descriptionArray.join('\n'),
        url: `${setting.endpoint}/api/${user.stremioToken}/stream/play/${videoFile.imdbId}/${videoFile.tracker}/${videoFile.torrentId}/${videoFile.fileIndex}`,
        behaviorHints: {
          notWebReady: true,
          bingeGroup: videoFile.infoHash,
        },
      };
    });

    return [...streams, ...streamErrors];
  }

  async playStream(
    payload: PlayStream,
  ): Promise<{ file: TorrentFile; torrent: Torrent }> {
    const { imdbId, tracker, torrentId, fileIdx } = payload;

    const key = `${imdbId}-${tracker}-${torrentId}-${fileIdx}`;
    const running = this.inFlightPlay.get(key);
    if (running) return running;

    const promise = this.fetchTorrent(payload);

    this.inFlightPlay.set(key, promise);

    try {
      const response = await promise;
      return response;
    } finally {
      this.inFlightPlay.delete(key);
    }
  }

  private async fetchTorrent(payload: PlayStream) {
    const { imdbId, tracker, torrentId, fileIdx } = payload;

    const torrentCache = await this.torrentCacheStore.findOne({
      imdbId,
      tracker,
      torrentId,
    });

    let torrent: Torrent | null = null;

    if (torrentCache) {
      torrent = await this.webTorrentService.getTorrent(
        torrentCache.parsed.infoHash,
      );
    }

    if (!torrent) {
      const torrentFile = await this.trackersService.findOneTorrent(
        tracker,
        torrentId,
      );

      torrent = await this.webTorrentService.getTorrent(
        torrentFile.parsed.infoHash,
      );

      if (!torrent) {
        torrent = await this.webTorrentService.addTorrent({
          ...torrentFile,
          parsed: torrentFile.parsed,
        });
      }
    }

    const file = this.webTorrentService.getFileByIndex(torrent, fileIdx);

    return { file, torrent };
  }

  private findVideoFilesWithRank(
    torrents: TrackerTorrentSuccess[],
    series?: ParsedStreamIdSeries,
  ): VideoFileWithRank[] {
    const torrentByFiles: VideoFileWithRank[] = [];

    for (const torrent of torrents) {
      if (!torrent.parsed.name) continue;

      const { resolution: torrentResolution, audioCodec: torrentAudioCodec } =
        filenameParse(torrent.parsed.name);

      const videoFile = this.selectVideoFile({
        files: torrent.parsed.files,
        series,
      });

      if (!videoFile) continue;

      const { resolution: fileResolution, audioCodec: fileAudioCodec } =
        filenameParse(videoFile.file.name);

      const resolution = torrentResolution ?? fileResolution;
      const audio = torrentAudioCodec ?? fileAudioCodec;

      const torrentByFile: VideoFileWithRank = {
        imdbId: torrent.imdbId,
        tracker: torrent.tracker,
        torrentId: torrent.torrentId,
        seeders: torrent.seeders,

        infoHash: torrent.parsed.infoHash,
        fileName: videoFile.file.name,
        fileSize: videoFile.file.length,
        fileIndex: videoFile.fileIndex,

        language: this.toLanguageInfo(torrent.language),
        resolution: this.toResolutionInfo(resolution || torrent.resolution),
        audio: audio,
      };

      torrentByFiles.push(torrentByFile);
    }

    return torrentByFiles;
  }

  private sortVideoFiles(videoFiles: VideoFileWithRank[]): VideoFileWithRank[] {
    const sortedVideoFiles = _.orderBy(
      videoFiles,
      [
        (videoFile) => videoFile.language.rank,
        (videoFile) => videoFile.resolution.rank,
        (videoFile) => videoFile.seeders,
      ],
      ['asc', 'asc', 'desc'],
    );

    return sortedVideoFiles;
  }

  private filterVideoFiles(
    videoFiles: VideoFileWithRank[],
    user: User,
  ): VideoFileWithRank[] {
    const { torrentLanguages, torrentResolutions, torrentSeed } = user;

    const filteredVideoFiles = videoFiles.filter((videoFile) => {
      const isLanguageSet = torrentLanguages.includes(videoFile.language.value);

      const isResolutionSet = torrentResolutions.includes(
        videoFile.resolution.value,
      );

      let isSeedSet = true;

      if (torrentSeed !== null) {
        isSeedSet = videoFile.seeders > torrentSeed;
      }

      return isLanguageSet && isResolutionSet && isSeedSet;
    });

    return filteredVideoFiles;
  }

  private selectVideoFile(
    payload: SelectVideoOptions,
  ): SelectedVideoFile | undefined {
    const { files, series } = payload;

    if (_.isUndefined(files) || !files.length) return;

    if (series) {
      let fileIndex = 0;

      const videoFile = files.find((mediaFile, index) => {
        const isSampleOrTrash = this.isSampleOrTrash(mediaFile);
        if (isSampleOrTrash) return false;

        const parsedFilename = filenameParse(mediaFile.name, true);

        if (!('isTv' in parsedFilename)) return false;

        const { seasons, episodeNumbers } = parsedFilename;

        const isSeason = seasons.includes(series.season);
        const isEpisode = episodeNumbers.includes(series.episode);

        if (!isSeason || !isEpisode) return false;

        fileIndex = index;
        return true;
      });

      if (!videoFile) return;

      return { file: videoFile, fileIndex };
    } else {
      const fileSizes = files.map((file) => file.length);
      const largestSize = _.max(fileSizes);
      const largestFileIndex = _.findIndex(
        files,
        (file) => file.length === largestSize,
      );

      return {
        file: files[largestFileIndex],
        fileIndex: largestFileIndex,
      };
    }
  }

  private isSampleOrTrash(file: ParsedFile) {
    const isVideoFile = isVideo(file.name);
    const isSample = file.name.includes('-sample.');
    return !isVideoFile || isSample;
  }

  private toLanguageInfo(language: LanguageEnum): VideoFileLanguage {
    const videoFileLanguage: VideoFileLanguage = {
      emoji: '🇭🇺',
      label: '🇭🇺 magyar',
      rank: 1,
      value: language,
    };

    if (language !== LanguageEnum.HU) {
      videoFileLanguage.emoji = '🇬🇧';
      videoFileLanguage.label = '🇬🇧 english';
      videoFileLanguage.rank = 2;
    }

    return videoFileLanguage;
  }

  private toResolutionInfo(resolution: Resolution): VideoFileResolution {
    switch (resolution) {
      case Resolution.R2160P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: 1,
        };
      case Resolution.R1080P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: 2,
        };
      case Resolution.R720P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: 3,
        };
      case Resolution.R576P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: 4,
        };
      case Resolution.R540P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: 5,
        };
      case Resolution.R480P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: 6,
        };
    }
  }
}
