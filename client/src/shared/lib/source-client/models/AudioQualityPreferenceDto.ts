/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioQualityEnum } from './AudioQualityEnum';
import type { PreferenceEnum } from './PreferenceEnum';
export type AudioQualityPreferenceDto = {
    preference: PreferenceEnum;
    preferred: Array<AudioQualityEnum>;
    blocked: Array<AudioQualityEnum>;
};

