/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LanguageDto } from './LanguageDto';
import type { ResolutionDto } from './ResolutionDto';
import type { TrackerMetaDto } from './TrackerMetaDto';
import type { UserRoleDto } from './UserRoleDto';
import type { VideoQualityDto } from './VideoQualityDto';
export type MetadataDto = {
    version: string;
    userRoles: Array<UserRoleDto>;
    resolutions: Array<ResolutionDto>;
    videoQualities: Array<VideoQualityDto>;
    languages: Array<LanguageDto>;
    trackers: Array<TrackerMetaDto>;
    endpoint: string;
};

