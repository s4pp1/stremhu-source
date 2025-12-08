/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StreamsResponseDto } from '../models/StreamsResponseDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class StremioStreamService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param mediaType
     * @param id
     * @param token Stremio addon token
     * @returns StreamsResponseDto
     * @throws ApiError
     */
    public streams(
        mediaType: 'series' | 'movie',
        id: string,
        token: string,
    ): CancelablePromise<StreamsResponseDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/{token}/stream/{mediaType}/{id}.json',
            path: {
                'mediaType': mediaType,
                'id': id,
                'token': token,
            },
        });
    }
    /**
     * @param imdbId
     * @param tracker
     * @param torrentId
     * @param fileIdx
     * @param token Stremio addon token
     * @returns any
     * @throws ApiError
     */
    public playStream(
        imdbId: string,
        tracker: 'ncore' | 'bithumen' | 'majomparade',
        torrentId: string,
        fileIdx: number,
        token: string,
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/{token}/stream/play/{imdbId}/{tracker}/{torrentId}/{fileIdx}',
            path: {
                'imdbId': imdbId,
                'tracker': tracker,
                'torrentId': torrentId,
                'fileIdx': fileIdx,
                'token': token,
            },
        });
    }
}
