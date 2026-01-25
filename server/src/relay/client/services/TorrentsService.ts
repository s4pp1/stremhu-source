/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AddTorrent } from '../models/AddTorrent';
import type { RelayTorrent } from '../models/RelayTorrent';
import type { RelayTorrentState } from '../models/RelayTorrentState';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class TorrentsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Get Torrents
     * @returns RelayTorrent Successful Response
     * @throws ApiError
     */
    public getTorrents(): CancelablePromise<Array<RelayTorrent>> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/torrents/',
        });
    }
    /**
     * Add Torrent
     * @param requestBody
     * @returns RelayTorrent Successful Response
     * @throws ApiError
     */
    public addTorrent(
        requestBody: AddTorrent,
    ): CancelablePromise<RelayTorrent> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/torrents/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Torrent
     * @param infoHash
     * @returns RelayTorrent Successful Response
     * @throws ApiError
     */
    public getTorrent(
        infoHash: string,
    ): CancelablePromise<RelayTorrent> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/torrents/{info_hash}',
            path: {
                'info_hash': infoHash,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Torrent
     * @param infoHash
     * @returns RelayTorrent Successful Response
     * @throws ApiError
     */
    public deleteTorrent(
        infoHash: string,
    ): CancelablePromise<RelayTorrent> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/torrents/{info_hash}',
            path: {
                'info_hash': infoHash,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Torrent State
     * @param infoHash
     * @returns RelayTorrentState Successful Response
     * @throws ApiError
     */
    public getTorrentState(
        infoHash: string,
    ): CancelablePromise<RelayTorrentState> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/torrents/{info_hash}/verification',
            path: {
                'info_hash': infoHash,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
