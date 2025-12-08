/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ManifestDto = {
    id: string;
    name: string;
    description: string;
    version: string;
    resources: Array<string>;
    types: Array<'movie' | 'series' | 'channel' | 'tv'>;
    idPrefixes: Record<string, any>;
    catalogs: Array<string>;
    addonCatalogs: Record<string, any>;
    config: Array<string>;
    background: Record<string, any>;
    logo: Record<string, any>;
    contactEmail: Record<string, any>;
};

