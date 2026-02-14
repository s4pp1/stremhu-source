/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioQualityPreferenceMetaDto } from './AudioQualityPreferenceMetaDto';
import type { LanguagePreferenceMetaDto } from './LanguagePreferenceMetaDto';
import type { ResolutionPreferenceMetaDto } from './ResolutionPreferenceMetaDto';
import type { SourcePreferenceMetaDto } from './SourcePreferenceMetaDto';
import type { TrackerMetaDto } from './TrackerMetaDto';
import type { UserRoleDto } from './UserRoleDto';
import type { VideoQualityPreferenceMetaDto } from './VideoQualityPreferenceMetaDto';
export type MetadataDto = {
    version: string;
    userRoles: Array<UserRoleDto>;
    preferences: Array<(LanguagePreferenceMetaDto | ResolutionPreferenceMetaDto | VideoQualityPreferenceMetaDto | SourcePreferenceMetaDto | AudioQualityPreferenceMetaDto)>;
    trackers: Array<TrackerMetaDto>;
    endpoint: string;
};

