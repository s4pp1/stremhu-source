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
    id: string;
    imdb_id?: string;
    type: ContentTypeEnum;
    name: string;
    poster?: string;
    posterShape: PosterShapeEnum;
    background?: string;
    logo?: string;
    description?: string;
    imdbRating?: string;
    releaseInfo?: string;
    genres?: Array<string>;
    cast?: Array<string>;
    director?: Array<string>;
    links?: Array<MetaLinkDto>;
    released?: string;
    year?: string;
    trailers?: Array<MetaTrailerDto>;
    videos?: Array<MetaVideoDto>;
    runtime?: string;
    language?: string;
    country?: string;
    awards?: string;
    website?: string;
    behaviorHints?: MetaDetailBehaviorHintsDto;
    writer?: Array<string>;
};

