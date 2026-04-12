/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioQualityMetaDto } from './AudioQualityMetaDto';
import type { PreferenceEnum } from './PreferenceEnum';
export type AudioQualityPreferenceMetaDto = {
    /**
     * Audió minőség preferencia azonosító
     */
    value: PreferenceEnum;
    /**
     * Audió minőség elemek listája
     */
    items: Array<AudioQualityMetaDto>;
    /**
     * Megjelenített név
     */
    label: string;
    /**
     * Leírás
     */
    description: string;
};

