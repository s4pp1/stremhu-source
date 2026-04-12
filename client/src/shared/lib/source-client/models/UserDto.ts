/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserRoleEnum } from './UserRoleEnum';
export type UserDto = {
    /**
     * Felhasználói szerepkör
     */
    userRole: UserRoleEnum;
    /**
     * Felhasználó egyedi azonosítója
     */
    id: string;
    /**
     * Felhasználónév
     */
    username: string;
    /**
     * API token
     */
    token: string;
    /**
     * Torrent seed limit
     */
    torrentSeed: number | null;
    /**
     * Csak a legjobb torrentek megjelenítése
     */
    onlyBestTorrent: boolean;
    /**
     * Utolsó frissítés időpontja
     */
    updatedAt: string;
    /**
     * Létrehozás időpontja
     */
    createdAt: string;
};

