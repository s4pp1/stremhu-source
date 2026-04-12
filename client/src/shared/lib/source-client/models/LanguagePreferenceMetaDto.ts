/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LanguageMetaDto } from './LanguageMetaDto';
import type { PreferenceEnum } from './PreferenceEnum';
export type LanguagePreferenceMetaDto = {
    /**
     * Nyelv preferencia azonosító
     */
    value: PreferenceEnum;
    /**
     * Nyelv elemek listája
     */
    items: Array<LanguageMetaDto>;
    /**
     * Megjelenített név
     */
    label: string;
    /**
     * Leírás
     */
    description: string;
};

