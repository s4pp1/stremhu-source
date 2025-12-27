/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LoginTrackerDto } from '../models/LoginTrackerDto';
import type { TrackerDto } from '../models/TrackerDto';
import type { UpdateTrackerDto } from '../models/UpdateTrackerDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class TrackersService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param requestBody
     * @returns any
     * @throws ApiError
     */
    public login(
        requestBody: LoginTrackerDto,
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/trackers',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @returns TrackerDto
     * @throws ApiError
     */
    public trackers(): CancelablePromise<Array<TrackerDto>> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/trackers',
        });
    }
    /**
     * @returns any
     * @throws ApiError
     */
    public cleanup(): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/trackers/cleanup',
        });
    }
    /**
     * @param tracker
     * @param requestBody
     * @returns any
     * @throws ApiError
     */
    public update(
        tracker: 'ncore' | 'bithumen' | 'majomparade' | 'diablo',
        requestBody: UpdateTrackerDto,
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/trackers/{tracker}',
            path: {
                'tracker': tracker,
            },
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @param tracker
     * @returns any
     * @throws ApiError
     */
    public delete(
        tracker: 'ncore' | 'bithumen' | 'majomparade' | 'diablo',
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/trackers/{tracker}',
            path: {
                'tracker': tracker,
            },
        });
    }
}
