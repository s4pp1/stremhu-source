import { filenameParse } from '@ctrl/video-filename-parser';
import isVideo from 'is-video';
import { findIndex, isUndefined, maxBy } from 'lodash';

import { SelectVideoOptions } from '../type/select-video-options.type';
import { SelectedVideoFile } from '../type/selected-video-file.type';

export function findVideoFile(
  payload: SelectVideoOptions,
): SelectedVideoFile | undefined {
  const { files, series, isSpecial } = payload;

  if (isUndefined(files) || !files.length) return;

  if (series && !isSpecial) {
    let fileIndex = 0;

    const videoFile = files.find((mediaFile, index) => {
      const sampleOrTrash = isSampleOrTrash(mediaFile.name);
      if (sampleOrTrash) return false;

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
    const largestFile = maxBy(files, (file) => file.length);
    if (!largestFile || !isVideo(largestFile.name)) return;

    const largestFileIndex = findIndex(
      files,
      (file) => file.name === largestFile.name,
    );

    return {
      file: files[largestFileIndex],
      fileIndex: largestFileIndex,
    };
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
