/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Health } from '../models/Health';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MonitoringService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Health
     * @returns Health Successful Response
     * @throws ApiError
     */
    public health(): CancelablePromise<Health> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/health',
        });
    }
}
