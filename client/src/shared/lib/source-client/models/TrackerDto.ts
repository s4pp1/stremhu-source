/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TrackerEnum } from './TrackerEnum';
export type TrackerDto = {
    /**
     * Tracker azonosító
     */
    tracker: TrackerEnum;
    /**
     * Felhasználónév
     */
    username: string;
    password: string;
    /**
     * Teljes torrent letöltése
     */
    downloadFullTorrent: boolean;
    /**
     * Hit and Run védelem állapota
     */
    hitAndRun: boolean | null;
    /**
     * Seedben tartás ideje (másodperc)
     */
    keepSeedSeconds: number | null;
    /**
     * Utolsó frissítés időpontja
     */
    updatedAt: string;
    /**
     * Létrehozás időpontja
     */
    createdAt: string;
};

