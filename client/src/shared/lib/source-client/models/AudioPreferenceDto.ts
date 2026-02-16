/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioQualityEnum } from './AudioQualityEnum';
import type { PreferenceEnum } from './PreferenceEnum';
export type AudioPreferenceDto = {
    preference: PreferenceEnum;
    preferred: Array<AudioQualityEnum>;
    blocked: Array<AudioQualityEnum>;
};

