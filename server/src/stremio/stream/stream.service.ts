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
import { TorrentFile } from 'webtorrent';

import { CatalogService } from 'src/catalog/catalog.service';
import { WebTorrentTorrent } from 'src/clients/webtorrent/webtorrent.types';
import { RESOLUTION_LABEL_MAP } from 'src/common/common.constant';
import { LanguageEnum } from 'src/common/enum/language.enum';
import { ParsedFile } from 'src/common/utils/parse-torrent.util';
import { SettingsStore } from 'src/settings/core/settings.store';
import { TorrentsCacheStore } from 'src/torrents-cache/core/torrents-cache.store';
import { TorrentsService } from 'src/torrents/torrents.service';
import { TrackerTorrentStatusEnum } from 'src/trackers/enum/tracker-torrent-status.enum';
import { TrackerDiscoveryService } from 'src/trackers/tracker-discovery.service';
import {
  TrackerTorrentError,
  TrackerTorrentSuccess,
} from 'src/trackers/tracker.types';
import { TRACKER_INFO } from 'src/trackers/trackers.constants';
import { User } from 'src/users/entity/user.entity';

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

@Injectable()
export class StremioStreamService {
  private inFlightPlay = new Map<string, Promise<TorrentFile>>();

  constructor(
    private readonly torrentsCacheStore: TorrentsCacheStore,
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
    private readonly torrentsService: TorrentsService,
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

    const endpoint = await this.settingsStore.getEndpoint();

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
      const hdrTypes = videoFile.hdrTypes.join(', ');

      const nameArray = _.compact([videoFile.resolution.label, hdrTypes]);

      const isCamSource = videoFile.sources.includes(SourceEnum.CAM);

      if (isCamSource) {
        nameArray.push('📹 CAM');
      }

      const fileSize = `💾 ${filesize(videoFile.fileSize)}`;
      const seeders = `👥 ${videoFile.seeders}`;
      const tracker = `🧲 ${TRACKER_INFO[videoFile.tracker].label}`;
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
        url: `${endpoint}/api/${user.token}/stream/play/${videoFile.imdbId}/${videoFile.tracker}/${videoFile.torrentId}/${videoFile.fileIndex}`,
        behaviorHints: {
          notWebReady: videoFile.notWebReady,
          bingeGroup,
          filename: videoFile.fileName,
        },
      };
    });

    return [...streams, ...streamErrors];
  }

  async playStream(payload: PlayStream): Promise<TorrentFile> {
    const { imdbId, tracker, torrentId, fileIndex } = payload;

    const key = `${imdbId}-${tracker}-${torrentId}-${fileIndex}`;
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
    const { imdbId, tracker, torrentId, fileIndex } = payload;

    const torrentCache = await this.torrentsCacheStore.findOne({
      imdbId,
      tracker,
      torrentId,
    });

    let torrent: WebTorrentTorrent | null = null;

    if (torrentCache) {
      torrent = await this.torrentsService.getTorrentForStream(
        torrentCache.parsed.infoHash,
      );
    }

    if (!torrent) {
      const torrentFile = await this.trackerDiscoveryService.findOneTorrent(
        tracker,
        torrentId,
      );

      torrent = await this.torrentsService.getTorrentForStream(
        torrentFile.parsed.infoHash,
      );

      if (!torrent) {
        torrent = await this.torrentsService.addTorrentForStream({
          ...torrentFile,
          parsedTorrent: torrentFile.parsed,
        });
      }
    }

    const file = this.torrentsService.getTorrentFileForStream(
      torrent,
      fileIndex,
    );

    return file;
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

      const hdrTypes = this.hdrTypes(torrentName);

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
        hdrTypes,
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
      const largestFile = _.maxBy(files, (file) => file.length);
      if (!largestFile || !isVideo(largestFile.name)) return;

      const largestFileIndex = _.findIndex(
        files,
        (file) => file.name === largestFile.name,
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

  private hdrTypes(torrentName: string) {
    const hdrTypes: string[] = [];

    // Dolby Vision
    const isDolbyVision = [
      '.Dolby.Vision.',
      '.DoVi.',
      '.DoVi-',
      '-DoVi.',
      '.DV.',
    ].some((dolbyVision) => torrentName.includes(dolbyVision));

    if (isDolbyVision) hdrTypes.push('Dolby Vision');

    // HDR
    const isHDR = ['.HDR.', '-HDR.', '.HDR-'].some((hdr) =>
      torrentName.includes(hdr),
    );

    if (isHDR) hdrTypes.push('HDR');

    // HDR10
    const isHDR10 = ['.HDR10.', '-HDR10.', '.HDR10-'].some((hdr) =>
      torrentName.includes(hdr),
    );

    if (isHDR10) hdrTypes.push('HDR10');

    // HDR10+
    const isHDRPlus = [
      '.HDR10Plus.',
      '-HDR10Plus.',
      '.HDR10Plus-',
      '.HDR10+.',
      '-HDR10+.',
      '.HDR10+-',
      '.HDR10P.',
      '-HDR10P.',
      '.HDR10P-',
    ].some((hdr) => torrentName.includes(hdr));

    if (isHDRPlus) hdrTypes.push('HDR10+');

    // HLG
    const isHLG = torrentName.includes('.HLG.');

    if (isHLG) hdrTypes.push('HLG');

    return hdrTypes;
  }
}
