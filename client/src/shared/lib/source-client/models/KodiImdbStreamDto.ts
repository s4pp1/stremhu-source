/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioQualityMetaDto } from './AudioQualityMetaDto';
import type { AudioSpatialMetaDto } from './AudioSpatialMetaDto';
import type { LanguageMetaDto } from './LanguageMetaDto';
import type { ResolutionMetaDto } from './ResolutionMetaDto';
import type { SourceMetaDto } from './SourceMetaDto';
import type { TrackerMetaDto } from './TrackerMetaDto';
import type { VideoQualityMetaDto } from './VideoQualityMetaDto';
export type KodiImdbStreamDto = {
    torrentName: string;
    fileName: string;
    seeders: number;
    size: string;
    tracker: TrackerMetaDto;
    languages: Array<LanguageMetaDto>;
    resolution: ResolutionMetaDto;
    videoQualities: Array<VideoQualityMetaDto>;
    audioQuality?: AudioQualityMetaDto;
    audioSpatial?: AudioSpatialMetaDto;
    source: SourceMetaDto;
    url: string;
};

