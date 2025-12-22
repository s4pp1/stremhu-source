/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TrackerEnum } from './TrackerEnum';
export type TorrentDto = {
    tracker: TrackerEnum;
    name: string;
    downloadSpeed: number;
    uploadSpeed: number;
    progress: number;
    downloaded: number;
    uploaded: number;
    total: number;
    infoHash: string;
    isPersisted: boolean;
};

