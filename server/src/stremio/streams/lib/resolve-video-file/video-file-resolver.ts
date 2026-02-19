import { filenameParse } from '@ctrl/video-filename-parser';
import isVideo from 'is-video';
import { findIndex, maxBy } from 'lodash';

import { TorrentFileInfo } from 'src/torrents-cache/type/torrent-file-info.type';
import { TrackerTorrent } from 'src/trackers/tracker.types';

import { ParsedStremioIdSeries } from '../../pipe/stream-id.pipe';
import { VideoFile } from '../../type/video-file.type';
import { parseTorrentMetadata } from '../parse-torrent-metadata';

export type VideoFileResolverType = {
  torrent: TrackerTorrent;
  series?: ParsedStremioIdSeries;
};

export class VideoFileResolver {
  private readonly torrent: TrackerTorrent;
  private readonly series: ParsedStremioIdSeries | undefined;

  constructor(private readonly payload: VideoFileResolverType) {
    const { torrent, series } = this.payload;

    this.torrent = torrent;
    this.series = series;
  }

  resolve(): VideoFile | null {
    let torrentFile: TorrentFileInfo | null = null;

    if (this.series) {
      torrentFile = this.resolveSeriesFile(this.series);
    } else {
      torrentFile = this.resolveLargestFile();
    }

    if (torrentFile === null) return torrentFile;

    const torrentMetadata = parseTorrentMetadata({
      name: this.torrent.name,
      languageFallback: this.torrent.language,
      resolutionFallback: this.torrent.resolution,
    });

    return {
      // Torrent információk
      imdbId: this.torrent.imdbId,
      tracker: this.torrent.tracker,
      torrentId: this.torrent.torrentId,
      infoHash: this.torrent.infoHash,
      seeders: this.torrent.seeders,
      torrentName: this.torrent.name,

      // Torrent meta információk
      ...torrentMetadata,

      // Fájl információk
      fileName: torrentFile.name,
      fileSize: torrentFile.size,
      fileIndex: torrentFile.index,

      notWebReady: false,
    };
  }

  private resolveLargestFile(): TorrentFileInfo | null {
    const largestfile = maxBy(this.torrent.files, (file) => file.size);

    if (!largestfile || !isVideo(largestfile.name)) return null;

    const fileIndex = findIndex(
      this.torrent.files,
      (file) => file.size === largestfile.size,
    );

    return this.torrent.files[fileIndex];
  }

  private resolveSeriesFile(
    series: ParsedStremioIdSeries,
  ): TorrentFileInfo | null {
    const seriesFile = this.torrent.files.find((file) => {
      const normalizedName = file.name.toLowerCase();
      const sampleOrTrash = this.isSampleOrTrash(normalizedName);
      if (sampleOrTrash) return false;

      const parsedFilename = filenameParse(file.name, true);

      if (!('isTv' in parsedFilename)) return false;

      const { seasons, episodeNumbers } = parsedFilename;

      const isSeason = seasons.includes(series.season);
      const isEpisode = episodeNumbers.includes(series.episode);

      if (!isSeason || !isEpisode) return false;

      return true;
    });

    if (!seriesFile) return null;

    return seriesFile;
  }

  private isSampleOrTrash(name: string): boolean {
    const isVideoFile = isVideo(name);
    if (!isVideoFile) return true;

    return this.isSample(name);
  }

  private isSample(name: string): boolean {
    const base = name.replace(/\.[^.]+$/, '');
    return /(^sample|sample$|sample-|-sample-|-sample)/.test(base);
  }
}
