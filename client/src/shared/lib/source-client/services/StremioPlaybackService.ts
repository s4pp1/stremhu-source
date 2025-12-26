/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class StremioPlaybackService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param imdbId
     * @param tracker
     * @param torrentId
     * @param fileIdx
     * @param token
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
