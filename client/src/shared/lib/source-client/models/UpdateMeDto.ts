/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LanguageEnum } from './LanguageEnum';
import type { ResolutionEnum } from './ResolutionEnum';
import type { VideoQualityEnum } from './VideoQualityEnum';
export type UpdateMeDto = {
    username?: string;
    password?: string;
    torrentResolutions?: Array<ResolutionEnum>;
    torrentVideoQualities?: Array<VideoQualityEnum>;
    torrentLanguages?: Array<LanguageEnum>;
    torrentSeed?: number | null;
    onlyBestTorrent?: boolean;
};

