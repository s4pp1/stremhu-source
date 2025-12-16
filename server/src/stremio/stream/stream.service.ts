import {
  Resolution as ResolutionEnum,
  Source as SourceEnum,
  VideoCodec as VideoCodecEnum,
  filenameParse,
} from '@ctrl/video-filename-parser';
import { Injectable } from '@nestjs/common';
import { filesize } from 'filesize';
import isVideo from 'is-video';
import _ from 'lodash';
import { Torrent, TorrentFile } from 'webtorrent';

import { CatalogService } from 'src/catalog/catalog.service';
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
import { User } from 'src/users/entity/user.entity';
import { WebTorrentService } from 'src/web-torrent/web-torrent.service';

import { StreamDto } from './dto/stremio-stream.dto';
import { ParsedStreamIdSeries } from './pipe/stream-id.pipe';
import {
  AudioCodecConst,
  AudioCodecEnum,
  FindStreams,
  PlayStream,
  SelectVideoOptions,
  SelectedVideoFile,
  VideoFileLanguage,
  VideoFileResolution,
  VideoFileWithRank,
} from './stream.types';
import { HDR_PATTERNS } from './stremio.constants';

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
    private catalogService: CatalogService,
  ) {}

  async streams(payload: FindStreams): Promise<StreamDto[]> {
    const { user, mediaType, series } = payload;

    const { imdbId, originalImdbId } = await this.catalogService.resolveImdbId({
      imdbId: payload.imdbId,
      season: series?.season,
      episode: series?.episode,
    });

    const isSpecial = typeof originalImdbId === 'string';

    const endpoint = await this.settingsStore.getEndpoint();

    const torrents = await this.trackersService.findTorrents({
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

    const videoFiles = this.findVideoFilesWithRank(
      user,
      isSpecial,
      torrentSuccesses,
      series,
    );
    const filteredVideoFiles = this.filterVideoFiles(videoFiles, user);
    const sortedVideoFiles = this.sortVideoFiles(filteredVideoFiles);

    const streamErrors: StreamDto[] = torrentErrors.map((torrentError) => ({
      name: '❗ H I B A ❗',
      description: `❗ ${torrentError.message} ❗`,
      url: 'http://hiba.tortent',
      behaviorHints: {
        notWebReady: false,
      },
    }));

    const streams: StreamDto[] = sortedVideoFiles.map((videoFile) => {
      const hdr = videoFile.isHDR ? 'HDR' : undefined;

      const nameArray = _.compact([videoFile.resolution.label, hdr]);

      const isCamSource = videoFile.sources.includes(SourceEnum.CAM);

      if (isCamSource) {
        nameArray.push('📹 CAM');
      }

      const fileSize = `💾 ${filesize(videoFile.fileSize)}`;
      const seeders = `👥 ${videoFile.seeders}`;
      const tracker = `🧲 ${TRACKER_LABEL_MAP[videoFile.tracker]}`;
      const group = videoFile.group ? `🎯 ${videoFile.group}` : undefined;

      const descriptionArray = _.compact([
        _.compact([tracker, seeders]).join(' | '),
        _.compact([videoFile.language.label, videoFile.audioCodec]).join(' | '),
        _.compact([fileSize, group]).join(' | '),
      ]);

      const bingeGroup = [
        videoFile.tracker,
        videoFile.resolution.value.toLowerCase(),
        videoFile.language.value.toLowerCase(),
      ].join('-');

      return {
        name: nameArray.join(' | '),
        description: descriptionArray.join('\n'),
        url: `${endpoint}/api/${user.stremioToken}/stream/play/${videoFile.imdbId}/${videoFile.tracker}/${videoFile.torrentId}/${videoFile.fileIndex}`,
        behaviorHints: {
          notWebReady: videoFile.notWebReady,
          bingeGroup,
          filename: videoFile.fileName,
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
    user: User,
    isSpecial: boolean,
    torrents: TrackerTorrentSuccess[],
    series?: ParsedStreamIdSeries,
  ): VideoFileWithRank[] {
    const torrentByFiles: VideoFileWithRank[] = [];

    for (const torrent of torrents) {
      const torrentName = torrent.parsed.name;
      if (!torrentName) continue;

      const {
        sources: torrentSources,
        videoCodec: torrentVideoCodec,
        resolution: torrentResolution,
        audioCodec: torrentAudioCodec,
        group: torrentGroup,
      } = filenameParse(torrentName);

      const isHDR = HDR_PATTERNS.some((pattern) =>
        torrentName.includes(pattern),
      );

      const videoFile = this.selectVideoFile({
        files: torrent.parsed.files,
        series,
        isSpecial,
      });

      if (!videoFile) continue;

      const {
        sources: fileSources,
        videoCodec: fileVideoCodec,
        resolution: fileResolution,
        audioCodec: fileAudioCodec,
      } = filenameParse(videoFile.file.name);

      const videoCodec = torrentVideoCodec ?? fileVideoCodec;
      const resolution = torrentResolution ?? fileResolution;
      const audioCodec = torrentAudioCodec ?? fileAudioCodec;
      const sources = torrentSources ?? fileSources;

      const notWebReady = this.notWebReady(videoCodec, audioCodec);

      const torrentByFile: VideoFileWithRank = {
        imdbId: torrent.imdbId,
        tracker: torrent.tracker,
        torrentId: torrent.torrentId,
        seeders: torrent.seeders,
        group: torrentGroup || undefined,

        infoHash: torrent.parsed.infoHash,
        fileName: videoFile.file.name,
        fileSize: videoFile.file.length,
        fileIndex: videoFile.fileIndex,

        language: this.toLanguageInfo(torrent.language, user),
        resolution: this.toResolutionInfo(
          resolution || torrent.resolution,
          user,
        ),
        audioCodec,
        videoCodec,
        isHDR,
        sources,
        notWebReady,
      };

      torrentByFiles.push(torrentByFile);
    }

    return torrentByFiles;
  }

  private notWebReady(
    videoCodec: VideoCodecEnum | undefined,
    audioCodec: AudioCodecEnum | undefined,
  ): boolean {
    const notWebReadyVideoCodec = this.notWebReadyVideoCodec(videoCodec);
    const notWebReadyAudioCodec = this.notWebReadyAudioCodec(audioCodec);

    return notWebReadyVideoCodec || notWebReadyAudioCodec;
  }

  private notWebReadyVideoCodec(
    videoCodec: VideoCodecEnum | undefined,
  ): boolean {
    if (!videoCodec) return false;

    const notSupportedCodecs = [
      VideoCodecEnum.H265,
      VideoCodecEnum.X265,
      VideoCodecEnum.WMV,
      VideoCodecEnum.XVID,
      VideoCodecEnum.DVDR,
    ];

    return notSupportedCodecs.includes(videoCodec);
  }

  private notWebReadyAudioCodec(audioCodec: AudioCodecEnum | undefined) {
    if (!audioCodec) return false;

    const notSupportedCodecs = [
      AudioCodecConst.FLAC,
      AudioCodecConst.MP2,
      AudioCodecConst.DOLBY,
      AudioCodecConst.EAC3,
      AudioCodecConst.DTS,
      AudioCodecConst.DTSHD,
      AudioCodecConst.TRUEHD,
    ] as AudioCodecEnum[];

    return notSupportedCodecs.includes(audioCodec);
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
    const { files, series, isSpecial } = payload;

    if (_.isUndefined(files) || !files.length) return;

    if (series && !isSpecial) {
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
    if (!isVideoFile) return true;

    const parts = file.name.split('.');

    const startWithSample = parts[0] === 'sample';
    const endWithSample = _.nth(parts, -2) === 'sample';

    let containSample = false;
    ['sample-', '-sample-', '-sample'].forEach((smp) => {
      const contain = file.name.includes(smp);
      if (contain) containSample = true;
    });

    return startWithSample || endWithSample || containSample;
  }

  private toLanguageInfo(
    language: LanguageEnum,
    user: User,
  ): VideoFileLanguage {
    const index = user.torrentLanguages.indexOf(language);

    let rank: number | undefined = undefined;
    if (index !== -1) {
      rank = index + 1;
    }

    const videoFileLanguage: VideoFileLanguage = {
      label: '🌍 magyar',
      rank: rank || 91,
      value: language,
    };

    if (language !== LanguageEnum.HU) {
      videoFileLanguage.label = '🌍 english';
      videoFileLanguage.rank = rank || 92;
    }

    return videoFileLanguage;
  }

  private toResolutionInfo(
    resolution: ResolutionEnum,
    user: User,
  ): VideoFileResolution {
    const resolutionIndex = user.torrentResolutions.indexOf(resolution);

    let resolutionRank: number | undefined = undefined;
    if (resolutionIndex !== -1) {
      resolutionRank = resolutionIndex + 1;
    }

    switch (resolution) {
      case ResolutionEnum.R2160P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: resolutionRank || 91,
        };
      case ResolutionEnum.R1080P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: resolutionRank || 92,
        };
      case ResolutionEnum.R720P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: resolutionRank || 93,
        };
      case ResolutionEnum.R576P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: resolutionRank || 94,
        };
      case ResolutionEnum.R540P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: resolutionRank || 95,
        };
      case ResolutionEnum.R480P:
        return {
          label: RESOLUTION_LABEL_MAP[resolution],
          value: resolution,
          rank: resolutionRank || 96,
        };
    }
  }
}
