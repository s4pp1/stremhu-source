/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferenceEnum } from './PreferenceEnum';
import type { TrackerMetaDto } from './TrackerMetaDto';
export type TrackerPreferenceMetaDto = {
    /**
     * Tracker preferencia azonosító
     */
    value: PreferenceEnum;
    /**
     * Tracker elemek listája
     */
    items: Array<TrackerMetaDto>;
    /**
     * Megjelenített név
     */
    label: string;
    /**
     * Leírás
     */
    description: string;
};

