/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LanguageEnum } from './LanguageEnum';
import type { ResolutionEnum } from './ResolutionEnum';
export type UpdateMePreferencesDto = {
    torrentResolutions: Array<ResolutionEnum>;
    torrentLanguages: Array<LanguageEnum>;
    torrentSeed: number | null;
};

