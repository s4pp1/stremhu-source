/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferenceEnum } from './PreferenceEnum';
import type { VideoQualityEnum } from './VideoQualityEnum';
export type VideoPreferenceDto = {
    preference: PreferenceEnum;
    preferred: Array<VideoQualityEnum>;
    blocked: Array<VideoQualityEnum>;
};

