/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ManifestDto } from '../models/ManifestDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class StremioManifestService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param token
     * @returns void
     * @throws ApiError
     */
    public configure(
        token: string,
    ): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/{token}/configure',
            path: {
                'token': token,
            },
            errors: {
                308: `Átirányítás a UI felületre.`,
            },
        });
    }
    /**
     * @param token
     * @returns ManifestDto
     * @throws ApiError
     */
    public manifest(
        token: string,
    ): CancelablePromise<ManifestDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/{token}/manifest.json',
            path: {
                'token': token,
            },
        });
    }
}
