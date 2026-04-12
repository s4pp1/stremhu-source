/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioQualityPreferenceMetaDto } from './AudioQualityPreferenceMetaDto';
import type { AudioSpatialPreferenceMetaDto } from './AudioSpatialPreferenceMetaDto';
import type { LanguagePreferenceMetaDto } from './LanguagePreferenceMetaDto';
import type { ResolutionPreferenceMetaDto } from './ResolutionPreferenceMetaDto';
import type { SourcePreferenceMetaDto } from './SourcePreferenceMetaDto';
import type { TrackerMetaDto } from './TrackerMetaDto';
import type { TrackerPreferenceMetaDto } from './TrackerPreferenceMetaDto';
import type { UserRoleMetaDto } from './UserRoleMetaDto';
import type { VideoQualityPreferenceMetaDto } from './VideoQualityPreferenceMetaDto';
export type MetadataDto = {
    /**
     * Elérhető trackerek
     */
    trackers: Array<TrackerMetaDto>;
    /**
     * Elérhető felhasználói szerepkörök
     */
    userRoles: Array<UserRoleMetaDto>;
    /**
     * Elérhető preferenciák listája
     */
    preferences: Array<(TrackerPreferenceMetaDto | LanguagePreferenceMetaDto | ResolutionPreferenceMetaDto | VideoQualityPreferenceMetaDto | SourcePreferenceMetaDto | AudioQualityPreferenceMetaDto | AudioSpatialPreferenceMetaDto)>;
    /**
     * Az alkalmazás verziója
     */
    version: string;
    /**
     * API végpont URL
     */
    endpoint: string;
};

