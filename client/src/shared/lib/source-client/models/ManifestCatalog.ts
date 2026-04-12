/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ManifestExtraDto } from './ManifestExtraDto';
export type ManifestCatalog = {
    /**
     * Tartalom típusa
     */
    type: ManifestCatalog.type;
    /**
     * Katalógus azonosító
     */
    id: string;
    /**
     * Katalógus neve
     */
    name: string;
    /**
     * Extra szűrési paraméterek
     */
    extra?: Array<ManifestExtraDto>;
};
export namespace ManifestCatalog {
    /**
     * Tartalom típusa
     */
    export enum type {
        MOVIE = 'movie',
        SERIES = 'series',
        CHANNEL = 'channel',
        TV = 'tv',
    }
}

