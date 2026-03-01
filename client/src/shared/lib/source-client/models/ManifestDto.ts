/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ManifestBehaviorHintsDto } from './ManifestBehaviorHintsDto';
export type ManifestDto = {
    id: string;
    name: string;
    description: string;
    version: string;
    resources: Array<string>;
    types: Array<'movie' | 'series' | 'channel' | 'tv'>;
    idPrefixes: Array<string>;
    catalogs: Array<string>;
    addonCatalogs: Array<string>;
    config: Array<string>;
    background: string;
    logo: string;
    contactEmail: string;
    behaviorHints: ManifestBehaviorHintsDto;
};

