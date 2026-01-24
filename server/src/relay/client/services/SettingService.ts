/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UpdateSettings } from '../models/UpdateSettings';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class SettingService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Update
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public update(
        requestBody: UpdateSettings,
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/setting/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
