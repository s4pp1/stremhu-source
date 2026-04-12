/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ManifestBehaviorHintsDto } from './ManifestBehaviorHintsDto';
import type { ManifestCatalog } from './ManifestCatalog';
import type { ManifestConfigDto } from './ManifestConfigDto';
export type ManifestDto = {
    /**
     * Addon egyedi azonosítója
     */
    id: string;
    /**
     * Addon neve
     */
    name: string;
    /**
     * Addon leírása
     */
    description: string;
    /**
     * Addon verziója
     */
    version: string;
    /**
     * Támogatott erőforrások listája
     */
    resources: Array<Record<string, any>>;
    /**
     * Támogatott tartalom típusok
     */
    types: Array<'movie' | 'series' | 'channel' | 'tv'>;
    /**
     * ID előtagok
     */
    idPrefixes?: Array<string>;
    /**
     * Katalógusok listája
     */
    catalogs: Array<ManifestCatalog>;
    /**
     * Külső addon katalógusok
     */
    addonCatalogs?: Array<ManifestCatalog>;
    /**
     * Konfigurációs beállítások
     */
    config?: Array<ManifestConfigDto>;
    /**
     * Háttérkép URL
     */
    background?: string;
    /**
     * Logo URL
     */
    logo?: string;
    /**
     * Kapcsolati email
     */
    contactEmail?: string;
    /**
     * Viselkedési tippek
     */
    behaviorHints?: ManifestBehaviorHintsDto;
};

