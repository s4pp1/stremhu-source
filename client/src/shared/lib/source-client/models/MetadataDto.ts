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
     * Preferenciák listája (különböző típusú elemekkel)
     */
    preferences: Array<(TrackerPreferenceMetaDto | LanguagePreferenceMetaDto | ResolutionPreferenceMetaDto | VideoQualityPreferenceMetaDto | SourcePreferenceMetaDto | AudioQualityPreferenceMetaDto | AudioSpatialPreferenceMetaDto)>;
    /**
     * Felhasználói szerepkörök listája
     */
    userRoles: Array<UserRoleMetaDto>;
    /**
     * Trackerek listája
     */
    trackers: Array<TrackerMetaDto>;
    /**
     * API végpont
     */
    endpoint: string;
    /**
     * Az alkalmazás verziója
     */
    version: string;
};

