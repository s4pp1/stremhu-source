/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioSpatialEnum } from './AudioSpatialEnum';
import type { PreferenceEnum } from './PreferenceEnum';
export type AudioSpatialPreferenceDto = {
    preference: PreferenceEnum;
    preferred: Array<AudioSpatialEnum>;
    blocked: Array<AudioSpatialEnum>;
};

