/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TrackerEnum } from './TrackerEnum';
export type TorrentDto = {
    /**
     * Tracker azonosító
     */
    tracker: TrackerEnum;
    /**
     * Torrent neve
     */
    name: string;
    /**
     * Letöltési sebesség
     */
    downloadSpeed: number;
    /**
     * Feltöltési sebesség
     */
    uploadSpeed: number;
    /**
     * Haladás (0-1)
     */
    progress: number;
    /**
     * Letöltött adat mennyisége
     */
    downloaded: number;
    /**
     * Feltöltött adat mennyisége
     */
    uploaded: number;
    /**
     * Teljes méret
     */
    total: number;
    /**
     * Info hash
     */
    infoHash: string;
    /**
     * Egyedi torrent azonosító
     */
    torrentId: string;
    /**
     * Mentve van-e az adatbázisba
     */
    isPersisted: boolean;
    /**
     * Teljes letöltés állapota
     */
    fullDownload: boolean | null;
    /**
     * Utolsó lejátszás időpontja
     */
    lastPlayedAt: string;
    /**
     * Utolsó frissítés időpontja
     */
    updatedAt: string;
    /**
     * Létrehozás időpontja
     */
    createdAt: string;
};

