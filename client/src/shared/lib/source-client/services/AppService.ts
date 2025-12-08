/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthDto } from '../models/HealthDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class AppService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @returns HealthDto
     * @throws ApiError
     */
    public health(): CancelablePromise<HealthDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/health',
        });
    }
}
