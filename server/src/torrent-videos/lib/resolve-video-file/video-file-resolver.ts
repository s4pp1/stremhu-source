import { filenameParse } from '@ctrl/video-filename-parser';
import isVideo from 'is-video';
import { findIndex, maxBy } from 'lodash';

import { ParsedStreamSeries } from 'src/stremio/streams/type/parsed-stream-series.type';
import { RowTorrentVideo } from 'src/torrent-videos/type/row-torrent-video.type';
import { TorrentFileInfo } from 'src/torrents-cache/type/torrent-file-info.type';
import { TrackerTorrent } from 'src/trackers/tracker.types';

import { parseTorrentMetadata } from '../parse-torrent-metadata';
import { isSampleOrTrash } from './utils';

export type VideoFileResolverType = {
  torrent: TrackerTorrent;
  series?: ParsedStreamSeries;
};

export class VideoFileResolver {
  private readonly torrent: TrackerTorrent;
  private readonly series: ParsedStreamSeries | undefined;

  constructor(private readonly payload: VideoFileResolverType) {
    const { torrent, series } = this.payload;

    this.torrent = torrent;
    this.series = series;
  }

  resolve(): RowTorrentVideo | null {
    let torrentFile: TorrentFileInfo | null;

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

      isInRelay: false,
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
    series: ParsedStreamSeries,
  ): TorrentFileInfo | null {
    const seriesFile = this.torrent.files.find((file) => {
      const normalizedName = file.name.toLowerCase();
      const sampleOrTrash = isSampleOrTrash(normalizedName);
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
}
