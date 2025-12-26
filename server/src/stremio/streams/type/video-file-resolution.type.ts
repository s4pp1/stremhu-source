import { Resolution as ResolutionEnum } from '@ctrl/video-filename-parser';

export type VideoFileResolution = {
  label: string;
  value: ResolutionEnum;
  rank: number;
};
