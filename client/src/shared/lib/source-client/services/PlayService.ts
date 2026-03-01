/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class PlayService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param tracker
     * @param torrentId
     * @param fileIdx
     * @param token
     * @returns any
     * @throws ApiError
     */
    public play(
        tracker: 'ncore' | 'bithumen' | 'majomparade' | 'insane',
        torrentId: string,
        fileIdx: number,
        token: string,
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/{token}/play/{tracker}/{torrentId}/{fileIdx}',
            path: {
                'tracker': tracker,
                'torrentId': torrentId,
                'fileIdx': fileIdx,
                'token': token,
            },
        });
    }
}
