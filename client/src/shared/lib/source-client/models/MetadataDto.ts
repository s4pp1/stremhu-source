/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioCodecDto } from './AudioCodecDto';
import type { LanguageDto } from './LanguageDto';
import type { ResolutionDto } from './ResolutionDto';
import type { SourceTypeDto } from './SourceTypeDto';
import type { TrackerMetaDto } from './TrackerMetaDto';
import type { UserRoleDto } from './UserRoleDto';
import type { VideoQualityDto } from './VideoQualityDto';
export type MetadataDto = {
    version: string;
    userRoles: Array<UserRoleDto>;
    resolutions: Array<ResolutionDto>;
    videoQualities: Array<VideoQualityDto>;
    audioCodecs: Array<AudioCodecDto>;
    languages: Array<LanguageDto>;
    sourceTypes: Array<SourceTypeDto>;
    trackers: Array<TrackerMetaDto>;
    endpoint: string;
};

