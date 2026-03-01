/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MediaTypeEnum } from '../models/MediaTypeEnum';
import type { MetaDetailDto } from '../models/MetaDetailDto';
import type { StremioCatalogDto } from '../models/StremioCatalogDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class StremioCatalogsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param mediaType
     * @param catalogId
     * @param token
     * @returns StremioCatalogDto
     * @throws ApiError
     */
    public catalog0(
        mediaType: MediaTypeEnum,
        catalogId: string,
        token: string,
    ): CancelablePromise<StremioCatalogDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/{token}/stremio/catalog/{mediaType}/{catalogId}.json',
            path: {
                'mediaType': mediaType,
                'catalogId': catalogId,
                'token': token,
            },
        });
    }
    /**
     * @param mediaType
     * @param catalogId
     * @param token
     * @returns StremioCatalogDto
     * @throws ApiError
     */
    public catalog1(
        mediaType: MediaTypeEnum,
        catalogId: string,
        token: string,
    ): CancelablePromise<StremioCatalogDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/{token}/stremio/catalog/{mediaType}/{catalogId}/{extra}.json',
            path: {
                'mediaType': mediaType,
                'catalogId': catalogId,
                'token': token,
            },
        });
    }
    /**
     * @param mediaType
     * @param id
     * @param token
     * @returns MetaDetailDto
     * @throws ApiError
     */
    public meta(
        mediaType: MediaTypeEnum,
        id: string,
        token: string,
    ): CancelablePromise<MetaDetailDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/{token}/stremio/meta/{mediaType}/{id}.json',
            path: {
                'mediaType': mediaType,
                'id': id,
                'token': token,
            },
        });
    }
}
