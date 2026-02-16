/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferenceEnum } from './PreferenceEnum';
import type { ResolutionEnum } from './ResolutionEnum';
export type ResolutionPreferenceDto = {
    preference: PreferenceEnum;
    preferred: Array<ResolutionEnum>;
    blocked: Array<ResolutionEnum>;
};

