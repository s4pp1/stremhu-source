import { RowTorrentVideo } from 'src/torrent-videos/type/row-torrent-video.type';

import {
  VideoFileResolver,
  VideoFileResolverType,
} from './video-file-resolver';

export function resolveVideoFile(
  payload: VideoFileResolverType,
): RowTorrentVideo | null {
  const videoFileResolver = new VideoFileResolver(payload);
  return videoFileResolver.resolve();
}
