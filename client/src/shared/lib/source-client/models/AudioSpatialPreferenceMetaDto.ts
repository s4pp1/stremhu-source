/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioSpatialMetaDto } from './AudioSpatialMetaDto';
import type { PreferenceEnum } from './PreferenceEnum';
export type AudioSpatialPreferenceMetaDto = {
    /**
     * Térhatású hang preferencia azonosító
     */
    value: PreferenceEnum;
    /**
     * Térhatású hang elemek listája
     */
    items: Array<AudioSpatialMetaDto>;
    /**
     * Megjelenített név
     */
    label: string;
    /**
     * Leírás
     */
    description: string;
};

