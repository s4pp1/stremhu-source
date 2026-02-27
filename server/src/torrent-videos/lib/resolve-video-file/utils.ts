import isVideo from 'is-video';

export function isSampleOrTrash(name: string): boolean {
  const isVideoFile = isVideo(name);
  if (!isVideoFile) return true;

  return isSample(name);
}

export function isSample(name: string): boolean {
  const base = name.replace(/\.[^.]+$/, '');
  return /(^sample|sample$|sample-|-sample-|-sample)/.test(base);
}
