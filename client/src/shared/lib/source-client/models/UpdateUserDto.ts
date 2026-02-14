/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserRoleEnum } from './UserRoleEnum';
export type UpdateUserDto = {
    username?: string;
    password?: string;
    userRole?: UserRoleEnum;
    torrentSeed?: number | null;
    onlyBestTorrent?: boolean;
};

