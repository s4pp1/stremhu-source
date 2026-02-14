/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferenceEnum } from './PreferenceEnum';
import type { TrackerEnum } from './TrackerEnum';
export type TrackerPreferenceDto = {
    preference: PreferenceEnum;
    preferred: Array<TrackerEnum>;
    blocked: Array<TrackerEnum>;
};

