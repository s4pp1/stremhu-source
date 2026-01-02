import { filenameParse } from '@ctrl/video-filename-parser';
import isVideo from 'is-video';
import { findIndex, maxBy } from 'lodash';

import { TrackerTorrentFile } from 'src/trackers/tracker.types';

import { SelectVideoOptions } from '../type/select-video-options.type';

export function findVideoFile(
  payload: SelectVideoOptions,
): TrackerTorrentFile | undefined {
  const { files, series, isSpecial } = payload;

  if (files.length === 0) return;

  if (series && !isSpecial) {
    const videoFile = files.find((mediaFile) => {
      const sampleOrTrash = isSampleOrTrash(mediaFile.name);
      if (sampleOrTrash) return false;

      const parsedFilename = filenameParse(mediaFile.name, true);

      if (!('isTv' in parsedFilename)) return false;

      const { seasons, episodeNumbers } = parsedFilename;

      const isSeason = seasons.includes(series.season);
      const isEpisode = episodeNumbers.includes(series.episode);

      if (!isSeason || !isEpisode) return false;

      return true;
    });

    if (!videoFile) return;

    return videoFile;
  } else {
    const largestFile = maxBy(files, (file) => file.size);
    if (!largestFile || !isVideo(largestFile.name)) return;

    const largestFileIndex = findIndex(
      files,
      (file) => file.size === largestFile.size,
    );

    return files[largestFileIndex];
  }
}

function isSampleOrTrash(fileName: string) {
  const normalizedName = fileName.toLowerCase();
  const isVideoFile = isVideo(normalizedName);
  if (!isVideoFile) return true;

  return isSample(normalizedName);
}

function isSample(normalizedName: string): boolean {
  const base = normalizedName.replace(/\.[^.]+$/, '');
  return /(^sample|sample$|sample-|-sample-|-sample)/.test(base);
}
