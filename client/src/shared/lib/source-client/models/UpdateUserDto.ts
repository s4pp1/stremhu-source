/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserRoleEnum } from './UserRoleEnum';
export type UpdateUserDto = {
    /**
     * Felhasználói szerepkör
     */
    userRole?: UserRoleEnum;
    /**
     * Felhasználónév
     */
    username?: string;
    /**
     * Jelszó
     */
    password?: string;
    /**
     * Torrent seed limit
     */
    torrentSeed?: number | null;
    /**
     * Csak a legjobb torrentek megjelenítése
     */
    onlyBestTorrent?: boolean;
};

