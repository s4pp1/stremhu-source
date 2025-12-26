/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LanguageEnum } from './LanguageEnum';
import type { ResolutionEnum } from './ResolutionEnum';
import type { UserRoleEnum } from './UserRoleEnum';
import type { VideoQualityEnum } from './VideoQualityEnum';
export type UpdateUserDto = {
    username?: string;
    password?: string;
    userRole?: UserRoleEnum;
    torrentResolutions?: Array<ResolutionEnum>;
    torrentVideoQualities?: Array<VideoQualityEnum>;
    torrentLanguages?: Array<LanguageEnum>;
    torrentSeed?: number | null;
    onlyBestTorrent?: boolean;
};

