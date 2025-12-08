/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TorrentDto } from '../models/TorrentDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class WebTorrentService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @returns TorrentDto
     * @throws ApiError
     */
    public find(): CancelablePromise<Array<TorrentDto>> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/torrents',
        });
    }
    /**
     * @param infoHash
     * @returns any
     * @throws ApiError
     */
    public delete(
        infoHash: string,
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/torrents/{infoHash}',
            path: {
                'infoHash': infoHash,
            },
        });
    }
}
