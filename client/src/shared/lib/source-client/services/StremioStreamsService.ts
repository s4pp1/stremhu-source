/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StreamsResponseDto } from '../models/StreamsResponseDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class StremioStreamsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param mediaType
     * @param id
     * @param token
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
}
