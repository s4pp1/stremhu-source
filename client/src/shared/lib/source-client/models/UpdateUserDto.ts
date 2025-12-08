/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LanguageEnum } from './LanguageEnum';
import type { ResolutionEnum } from './ResolutionEnum';
import type { UserRoleEnum } from './UserRoleEnum';
export type UpdateUserDto = {
    userRole?: UserRoleEnum;
    torrentResolutions?: Array<ResolutionEnum>;
    torrentLanguages?: Array<LanguageEnum>;
    torrentSeed?: number | null;
};

