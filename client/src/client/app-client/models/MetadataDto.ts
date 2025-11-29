/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LanguageDto } from './LanguageDto';
import type { ResolutionDto } from './ResolutionDto';
import type { TrackerDto } from './TrackerDto';
import type { UserRoleDto } from './UserRoleDto';
export type MetadataDto = {
    version: string;
    userRoles: Array<UserRoleDto>;
    resolutions: Array<ResolutionDto>;
    languages: Array<LanguageDto>;
    trackers: Array<TrackerDto>;
    endpoint: string;
};

