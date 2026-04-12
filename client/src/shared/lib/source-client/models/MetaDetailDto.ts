/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContentTypeEnum } from './ContentTypeEnum';
import type { MetaDetailBehaviorHintsDto } from './MetaDetailBehaviorHintsDto';
import type { MetaLinkDto } from './MetaLinkDto';
import type { MetaTrailerDto } from './MetaTrailerDto';
import type { MetaVideoDto } from './MetaVideoDto';
import type { PosterShapeEnum } from './PosterShapeEnum';
export type MetaDetailDto = {
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
    /**
     * ISO 8601, initial release date.
     *
     * For movies, this is the cinema debut.
     *
     * e.g. "2010-12-06T05:00:00.000Z"
     */
    released?: string;
    /**
     * Megjelenés éve
     */
    year?: string;
    /**
     * Előzetesek listája
     */
    trailers?: Array<MetaTrailerDto>;
    /**
     * Csatornákhoz és sorozatokhoz használatos.
     *
     * Ha nincs megadva (pl. filmnél), a Stremio feltételezi, hogy egy videó van, aminek az ID-ja megegyezik a meta ID-val.
     */
    videos?: Array<MetaVideoDto>;
    /**
     * Várható játékidő emberi formátumban.
     *
     * e.g. "120m"
     */
    runtime?: string;
    /**
     * Beszélt nyelv
     */
    language?: string;
    /**
     * Származási ország
     */
    country?: string;
    /**
     * Díjak leírása
     */
    awards?: string;
    /**
     * Hivatalos weboldal URL
     */
    website?: string;
    /**
     * Viselkedési tippek
     */
    behaviorHints?: MetaDetailBehaviorHintsDto;
    /**
     * Írók listája
     */
    writer?: Array<string>;
};

