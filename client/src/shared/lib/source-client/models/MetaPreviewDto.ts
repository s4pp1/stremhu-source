/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContentTypeEnum } from './ContentTypeEnum';
import type { MetaLinkDto } from './MetaLinkDto';
import type { PosterShapeEnum } from './PosterShapeEnum';
export type MetaPreviewDto = {
    /**
     * Type of the content.
     */
    type: ContentTypeEnum;
    /**
     * Poster can be square (1:1 aspect) or regular (1:0.675) or landscape (1:1.77).
     *
     * Defaults to 'regular'.
     */
    posterShape?: PosterShapeEnum;
    /**
     * Universal identifier.
     * You may use a prefix unique to your addon.
     *
     * Example: 'yt_id:UCrDkAvwZum-UTjHmzDI2iIw'
     */
    id: string;
    /**
     * IMDb azonosító
     */
    imdb_id?: string;
    /**
     * Name of the content.
     */
    name: string;
    /**
     * URL to PNG of poster.
     *
     * Accepted aspect ratios: 1:0.675 (IMDb poster type) or 1:1 (square).
     *
     * You can use any resolution, as long as the file size is below 100kb.
     * Below 50kb is recommended
     */
    poster?: string;
    /**
     * The background shown on the stremio detail page.
     *
     * Heavily encouraged if you want your content to look good.
     *
     * URL to PNG, max file size 500kb.
     */
    background?: string;
    /**
     * The logo shown on the stremio detail page.
     *
     * Encouraged if you want your content to look good.
     *
     * URL to PNG.
     */
    logo?: string;
    /**
     * A few sentences describing your content.
     */
    description?: string;
    /**
     * IMDb értékelés
     */
    imdbRating?: string;
    /**
     * Megjelenési információk
     */
    releaseInfo?: string;
    /**
     * Műfajok listája
     */
    genres?: Array<string>;
    /**
     * Szereplőgárda
     */
    cast?: Array<string>;
    /**
     * Rendező(k)
     */
    director?: Array<string>;
    /**
     * Can be used to link to internal pages of Stremio.
     *
     * example: array of actor / genre / director links.
     */
    links?: Array<MetaLinkDto>;
};

