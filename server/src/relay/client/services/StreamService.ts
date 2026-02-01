/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class StreamService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Stream
     * @param infoHash
     * @param fileIndex
     * @param range
     * @returns any Successful Response
     * @throws ApiError
     */
    public headStreamFile(
        infoHash: string,
        fileIndex: number,
        range?: (string | null),
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'HEAD',
            url: '/stream/{info_hash}/{file_index}',
            path: {
                'info_hash': infoHash,
                'file_index': fileIndex,
            },
            headers: {
                'Range': range,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Stream
     * @param infoHash
     * @param fileIndex
     * @param range
     * @returns any Successful Response
     * @throws ApiError
     */
    public getStreamFile(
        infoHash: string,
        fileIndex: number,
        range?: (string | null),
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/stream/{info_hash}/{file_index}',
            path: {
                'info_hash': infoHash,
                'file_index': fileIndex,
            },
            headers: {
                'Range': range,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
