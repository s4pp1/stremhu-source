/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MetadataDto } from '../models/MetadataDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MetadataService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @returns MetadataDto
     * @throws ApiError
     */
    public metadata(): CancelablePromise<MetadataDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/metadata',
        });
    }
}
