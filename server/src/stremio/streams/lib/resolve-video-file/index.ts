import { VideoFile } from '../../type/video-file.type';
import {
  VideoFileResolver,
  VideoFileResolverType,
} from './video-file-resolver';

export function resolveVideoFile(
  payload: VideoFileResolverType,
): VideoFile | null {
  const videoFileResolver = new VideoFileResolver(payload);
  return videoFileResolver.resolve();
}
