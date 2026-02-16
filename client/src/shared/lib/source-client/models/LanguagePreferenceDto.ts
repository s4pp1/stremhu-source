/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LanguageEnum } from './LanguageEnum';
import type { PreferenceEnum } from './PreferenceEnum';
export type LanguagePreferenceDto = {
    preference: PreferenceEnum;
    preferred: Array<LanguageEnum>;
    blocked: Array<LanguageEnum>;
};

