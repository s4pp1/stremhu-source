/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferenceEnum } from './PreferenceEnum';
import type { ResolutionMetaDto } from './ResolutionMetaDto';
export type ResolutionPreferenceMetaDto = {
    /**
     * Felbontás preferencia azonosító
     */
    value: PreferenceEnum;
    /**
     * Felbontás elemek listája
     */
    items: Array<ResolutionMetaDto>;
    /**
     * Megjelenített név
     */
    label: string;
    /**
     * Leírás
     */
    description: string;
};

