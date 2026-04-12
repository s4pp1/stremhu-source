/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferenceEnum } from './PreferenceEnum';
import type { VideoQualityMetaDto } from './VideoQualityMetaDto';
export type VideoQualityPreferenceMetaDto = {
    /**
     * Videó minőség preferencia azonosító
     */
    value: PreferenceEnum;
    /**
     * Videó minőség elemek listája
     */
    items: Array<VideoQualityMetaDto>;
    /**
     * Megjelenített név
     */
    label: string;
    /**
     * Leírás
     */
    description: string;
};

