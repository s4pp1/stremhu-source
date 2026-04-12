/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type UpdateMeDto = {
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

