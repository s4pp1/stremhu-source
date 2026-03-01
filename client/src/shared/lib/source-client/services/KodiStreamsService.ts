/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { KodiImdbStreamsDto } from '../models/KodiImdbStreamsDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class KodiStreamsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param imdbId
     * @param token
     * @param season
     * @param episode
     * @returns KodiImdbStreamsDto
     * @throws ApiError
     */
    public streams(
        imdbId: string,
        token: string,
        season?: number,
        episode?: number,
    ): CancelablePromise<KodiImdbStreamsDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/{token}/kodi/imdb/{imdbId}/streams',
            path: {
                'imdbId': imdbId,
                'token': token,
            },
            query: {
                'season': season,
                'episode': episode,
            },
        });
    }
}
