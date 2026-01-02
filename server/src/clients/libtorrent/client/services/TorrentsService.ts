/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AddTorrent } from '../models/AddTorrent';
import type { File } from '../models/File';
import type { PrioritizeAndWait } from '../models/PrioritizeAndWait';
import type { PrioritizeAndWaitRequest } from '../models/PrioritizeAndWaitRequest';
import type { Torrent } from '../models/Torrent';
import type { UpdateSettings } from '../models/UpdateSettings';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class TorrentsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Get Torrents
     * @returns Torrent Successful Response
     * @throws ApiError
     */
    public getTorrents(): CancelablePromise<Array<Torrent>> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/torrents/',
        });
    }
    /**
     * Add Torrent
     * @param requestBody
     * @returns Torrent Successful Response
     * @throws ApiError
     */
    public addTorrent(
        requestBody: AddTorrent,
    ): CancelablePromise<Torrent> {
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
     * @returns Torrent Successful Response
     * @throws ApiError
     */
    public getTorrent(
        infoHash: string,
    ): CancelablePromise<Torrent> {
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
     * @returns Torrent Successful Response
     * @throws ApiError
     */
    public deleteTorrent(
        infoHash: string,
    ): CancelablePromise<Torrent> {
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
     * Get Torrent File
     * @param infoHash
     * @param fileIndex
     * @returns File Successful Response
     * @throws ApiError
     */
    public getTorrentFile(
        infoHash: string,
        fileIndex: number,
    ): CancelablePromise<File> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/torrents/{info_hash}/files/{file_index}',
            path: {
                'info_hash': infoHash,
                'file_index': fileIndex,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Prioritize And Wait
     * @param infoHash
     * @param fileIndex
     * @param streamId
     * @param requestBody
     * @returns PrioritizeAndWait Successful Response
     * @throws ApiError
     */
    public prioritizeAndWait(
        infoHash: string,
        fileIndex: number,
        streamId: string,
        requestBody: PrioritizeAndWaitRequest,
    ): CancelablePromise<PrioritizeAndWait> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/torrents/{info_hash}/files/{file_index}/prioritize_and_wait',
            path: {
                'info_hash': infoHash,
                'file_index': fileIndex,
            },
            query: {
                'stream_id': streamId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset Pieces Priorities
     * @param infoHash
     * @param fileIndex
     * @param streamId
     * @returns any Successful Response
     * @throws ApiError
     */
    public resetPiecesPriorities(
        infoHash: string,
        fileIndex: number,
        streamId: string,
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/torrents/{info_hash}/files/{file_index}/pieces/priorities/reset',
            path: {
                'info_hash': infoHash,
                'file_index': fileIndex,
            },
            query: {
                'stream_id': streamId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Settings
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public updateSettings(
        requestBody: UpdateSettings,
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/torrents/settings',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
