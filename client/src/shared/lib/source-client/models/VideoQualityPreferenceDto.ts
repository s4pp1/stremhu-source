/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferenceEnum } from './PreferenceEnum';
import type { VideoQualityEnum } from './VideoQualityEnum';
export type VideoQualityPreferenceDto = {
    preference: PreferenceEnum;
    preferred: Array<VideoQualityEnum>;
    blocked: Array<VideoQualityEnum>;
};

