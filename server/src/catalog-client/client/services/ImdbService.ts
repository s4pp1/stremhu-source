/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ImdbResolvePayloadDto } from '../models/ImdbResolvePayloadDto';
import type { ImdbResolveResponseDto } from '../models/ImdbResolveResponseDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class ImdbService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param token
     * @param requestBody
     * @returns ImdbResolveResponseDto
     * @throws ApiError
     */
    public imdbResolverControllerResolveSpecial(
        token: string,
        requestBody: ImdbResolvePayloadDto,
    ): CancelablePromise<ImdbResolveResponseDto> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/{token}/imdb/resolve/special',
            path: {
                'token': token,
            },
            body: requestBody,
            mediaType: 'application/json',
        });
    }
}
