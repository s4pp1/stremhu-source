/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioCodecEnum } from './AudioCodecEnum';
import type { LanguageEnum } from './LanguageEnum';
import type { ResolutionEnum } from './ResolutionEnum';
import type { SourceTypeEnum } from './SourceTypeEnum';
import type { UserRoleEnum } from './UserRoleEnum';
import type { VideoQualityEnum } from './VideoQualityEnum';
export type UserDto = {
    id: string;
    username: string;
    token: string;
    userRole: UserRoleEnum;
    torrentResolutions: Array<ResolutionEnum>;
    torrentVideoQualities: Array<VideoQualityEnum>;
    torrentAudioCodecs: Array<AudioCodecEnum>;
    torrentSourceTypes: Array<SourceTypeEnum>;
    torrentLanguages: Array<LanguageEnum>;
    torrentSeed: number | null;
    onlyBestTorrent: boolean;
};

