/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthDto } from '../models/HealthDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MonitoringService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @returns HealthDto
     * @throws ApiError
     */
    public healthCheck(): CancelablePromise<HealthDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/health',
        });
    }
    /**
     * @param token
     * @returns HealthDto
     * @throws ApiError
     */
    public healthCheckWithToken(
        token: string,
    ): CancelablePromise<HealthDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/health/{token}',
            path: {
                'token': token,
            },
        });
    }
}
