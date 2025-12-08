/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CatalogHealthDto } from '../models/CatalogHealthDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class StremHuCatalogService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @returns CatalogHealthDto
     * @throws ApiError
     */
    public health(): CancelablePromise<CatalogHealthDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/catalog/health',
        });
    }
}
