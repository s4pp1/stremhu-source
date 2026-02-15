/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferenceEnum } from './PreferenceEnum';
import type { SourceEnum } from './SourceEnum';
export type SourcePreferenceDto = {
    preference: PreferenceEnum;
    preferred: Array<SourceEnum>;
    blocked: Array<SourceEnum>;
};

