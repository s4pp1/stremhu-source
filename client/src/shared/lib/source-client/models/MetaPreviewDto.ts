/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContentTypeEnum } from './ContentTypeEnum';
import type { MetaLinkDto } from './MetaLinkDto';
import type { PosterShapeEnum } from './PosterShapeEnum';
export type MetaPreviewDto = {
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
};

