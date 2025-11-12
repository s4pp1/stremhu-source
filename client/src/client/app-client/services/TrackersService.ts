/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LoginTrackerDto } from '../models/LoginTrackerDto';
import type { TrackerCredentialDto } from '../models/TrackerCredentialDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class TrackersService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param requestBody
     * @returns any
     * @throws ApiError
     */
    public trackersControllerLoginTracker(
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
     * @returns TrackerCredentialDto
     * @throws ApiError
     */
    public trackersControllerTrackers(): CancelablePromise<Array<TrackerCredentialDto>> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/trackers',
        });
    }
    /**
     * @returns any
     * @throws ApiError
     */
    public trackersControllerCleanupHitAndRun(): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/trackers/hit-and-run',
        });
    }
    /**
     * @param tracker
     * @returns any
     * @throws ApiError
     */
    public trackersControllerDeleteTracker(
        tracker: 'ncore' | 'bithumen' | 'majomparade',
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
