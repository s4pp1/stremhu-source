/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferenceEnum } from './PreferenceEnum';
import type { SourceMetaDto } from './SourceMetaDto';
export type SourcePreferenceMetaDto = {
    /**
     * Forrás preferencia azonosító
     */
    value: PreferenceEnum;
    /**
     * Forrás elemek listája
     */
    items: Array<SourceMetaDto>;
    /**
     * Megjelenített név
     */
    label: string;
    /**
     * Leírás
     */
    description: string;
};

