/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TrackerEnum } from './TrackerEnum';
export type TrackerMetaDto = {
    /**
     * Tracker azonosító
     */
    value: TrackerEnum;
    /**
     * Megjelenített név
     */
    label: string;
    /**
     * Szükséges-e a teljes letöltés
     */
    requiresFullDownload: boolean;
    /**
     * Weboldal URL
     */
    url: string;
    /**
     * Részletek útvonala
     */
    detailsPath: string;
};

